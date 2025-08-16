"""
多邮箱轮流发送服务
"""
import logging
from datetime import date, datetime
from typing import List, Optional, Tuple, Dict, Any
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from django.contrib.auth.models import User
from ..models import EmailAccount, EmailAccountStats, EmailLog, Candidate
from ..utils import decrypt_key
from . import mailing_service
from .email_renderer import EmailRenderer

logger = logging.getLogger(__name__)


class MultiEmailSender:
    """多邮箱轮流发送管理器"""
    
    def __init__(self, user: User):
        self.user = user
        self.available_accounts = self._get_available_accounts()
        
    def _get_available_accounts(self) -> List[EmailAccount]:
        """获取当前用户所有可用的邮箱账户"""
        return list(self.user.email_accounts.filter(
            daily_send_limit__gt=0
        ).order_by('-is_default', 'email_address'))
    
    def _get_account_daily_stats(self, account: EmailAccount, target_date: date = None) -> EmailAccountStats:
        """获取或创建邮箱的当日统计记录"""
        if target_date is None:
            target_date = timezone.now().date()
            
        stats, created = EmailAccountStats.objects.get_or_create(
            email_account=account,
            date=target_date,
            defaults={
                'sent_count': 0,
                'failed_count': 0
            }
        )
        
        if created:
            logger.info(f"为邮箱 {account.email_address} 创建 {target_date} 的统计记录")
            
        return stats
    
    def get_best_account_for_sending(self, required_count: int = 1) -> Optional[EmailAccount]:
        """
        选择最佳的发送邮箱
        
        Args:
            required_count: 需要发送的邮件数量
            
        Returns:
            最佳的邮箱账户，如果没有可用账户则返回None
        """
        if not self.available_accounts:
            logger.warning(f"用户 {self.user.username} 没有配置可用的邮箱账户")
            return None
        
        today = timezone.now().date()
        best_account = None
        max_remaining = 0
        
        for account in self.available_accounts:
            stats = self._get_account_daily_stats(account, today)
            remaining = stats.remaining_quota
            
            # 如果当前邮箱剩余额度足够，并且比之前找到的更好
            if remaining >= required_count and remaining > max_remaining:
                best_account = account
                max_remaining = remaining
        
        if best_account:
            logger.info(f"选择邮箱 {best_account.email_address}，剩余额度: {max_remaining}")
        else:
            logger.warning(f"所有邮箱都没有足够的剩余额度发送 {required_count} 封邮件")
            
        return best_account
    
    def get_accounts_for_batch_sending(self, total_count: int) -> List[Tuple[EmailAccount, int]]:
        """
        为批量发送分配邮箱
        
        Args:
            total_count: 总共需要发送的邮件数量
            
        Returns:
            List of (EmailAccount, count) 元组，表示每个邮箱分配的发送数量
        """
        if not self.available_accounts:
            return []
        
        today = timezone.now().date()
        allocation = []
        remaining_count = total_count
        
        # 按剩余额度排序邮箱
        accounts_with_quota = []
        for account in self.available_accounts:
            stats = self._get_account_daily_stats(account, today)
            if stats.remaining_quota > 0:
                accounts_with_quota.append((account, stats.remaining_quota))
        
        # 按剩余额度倒序排序
        accounts_with_quota.sort(key=lambda x: x[1], reverse=True)
        
        # 分配邮件数量
        for account, quota in accounts_with_quota:
            if remaining_count <= 0:
                break
                
            allocated = min(remaining_count, quota)
            allocation.append((account, allocated))
            remaining_count -= allocated
            
            logger.info(f"分配给邮箱 {account.email_address}: {allocated} 封邮件")
        
        if remaining_count > 0:
            logger.warning(f"还有 {remaining_count} 封邮件无法分配，所有邮箱额度不足")
        
        return allocation
    
    def _get_selected_accounts_allocation(self, selected_accounts: List[EmailAccount], total_count: int) -> List[Tuple[EmailAccount, int]]:
        """
        为指定的邮箱账户分配发送数量
        
        Args:
            selected_accounts: 指定的邮箱账户列表
            total_count: 总共需要发送的邮件数量
            
        Returns:
            List of (EmailAccount, count) 元组，表示每个邮箱分配的发送数量
        """
        if not selected_accounts:
            return []
        
        today = timezone.now().date()
        allocation = []
        remaining_count = total_count
        
        # 按剩余额度排序邮箱
        accounts_with_quota = []
        for account in selected_accounts:
            stats = self._get_account_daily_stats(account, today)
            if stats.remaining_quota > 0:
                accounts_with_quota.append((account, stats.remaining_quota))
        
        if not accounts_with_quota:
            logger.warning("指定的邮箱都没有剩余额度")
            return []
        
        # 按剩余额度倒序排序
        accounts_with_quota.sort(key=lambda x: x[1], reverse=True)
        
        # 分配邮件数量
        for account, quota in accounts_with_quota:
            if remaining_count <= 0:
                break
                
            allocated = min(remaining_count, quota)
            allocation.append((account, allocated))
            remaining_count -= allocated
            
            logger.info(f"分配给指定邮箱 {account.email_address}: {allocated} 封邮件")
        
        if remaining_count > 0:
            logger.warning(f"指定邮箱额度不足，还有 {remaining_count} 封邮件无法分配")
        
        return allocation
    
    @transaction.atomic
    def send_single_email(self, account: EmailAccount, candidate: Candidate, 
                         subject: str, content: str, **kwargs) -> EmailLog:
        """
        使用指定邮箱发送单封邮件
        
        Args:
            account: 发送邮箱
            candidate: 候选人
            subject: 邮件主题
            content: 邮件内容
            **kwargs: 其他参数
            
        Returns:
            EmailLog记录
        """
        # 检查邮箱今日发送额度
        today = timezone.now().date()
        stats = self._get_account_daily_stats(account, today)
        
        if stats.is_quota_exceeded:
            raise ValidationError(f"邮箱 {account.email_address} 今日发送额度已用完")
        
        try:
            # 创建邮件任务
            email_log = mailing_service.create_email_task(
                user=self.user,
                from_account=account,
                candidate=candidate,
                subject=subject,
                content=content,
                **kwargs
            )
            
            if email_log:
                # 立即处理这个邮件任务
                try:
                    result = mailing_service.process_pending_emails(max_retries=1, specific_email_id=email_log.id)
                    
                    # 重新读取任务状态
                    email_log.refresh_from_db()
                    
                    if email_log.status == EmailLog.EmailStatus.SUCCESS:
                        # 更新统计
                        stats.sent_count += 1
                        stats.save()
                        logger.info(f"邮箱 {account.email_address} 发送成功，今日已发送: {stats.sent_count}")
                    else:
                        # 更新失败统计
                        stats.failed_count += 1
                        stats.save()
                        logger.warning(f"邮箱 {account.email_address} 发送失败，今日失败: {stats.failed_count}")
                        
                except Exception as process_error:
                    # 处理邮件时发生异常
                    stats.failed_count += 1
                    stats.save()
                    logger.error(f"邮箱 {account.email_address} 处理邮件异常: {process_error}")
                    email_log.status = EmailLog.EmailStatus.FAILED
                    email_log.failure_reason = str(process_error)
                    email_log.save()
            else:
                # 创建任务失败
                stats.failed_count += 1
                stats.save()
                logger.error(f"邮箱 {account.email_address} 创建邮件任务失败")
            
            return email_log
            
        except Exception as e:
            # 更新失败统计
            stats.failed_count += 1
            stats.save()
            logger.error(f"邮箱 {account.email_address} 发送异常: {e}")
            raise
    
    def send_batch_emails(self, candidates: List[Candidate], template_subject: str, 
                         template_content: str, selected_accounts: Optional[List[EmailAccount]] = None, 
                         async_mode: bool = True, **kwargs) -> dict:
        """
        批量发送邮件，支持同步和异步模式
        
        Args:
            candidates: 候选人列表
            template_subject: 邮件主题模板
            template_content: 邮件内容模板
            selected_accounts: 指定的邮箱账户列表
            async_mode: 是否使用异步模式（默认True）
            **kwargs: 其他参数
            
        Returns:
            发送结果统计
        """
        total_count = len(candidates)
        if total_count == 0:
            return {'success': 0, 'failed': 0, 'details': [], 'mode': 'sync'}
        
        if async_mode:
            return self._send_batch_emails_async(candidates, template_subject, template_content, selected_accounts, **kwargs)
        else:
            return self._send_batch_emails_sync(candidates, template_subject, template_content, selected_accounts, **kwargs)
    
    def _send_batch_emails_async(self, candidates: List[Candidate], template_subject: str, 
                                template_content: str, selected_accounts: Optional[List[EmailAccount]] = None, **kwargs) -> dict:
        """
        异步批量发送邮件 - 只创建任务，不立即发送
        """
        # 获取邮箱分配方案
        if selected_accounts and len(selected_accounts) > 0:
            allocation = self._get_selected_accounts_allocation(selected_accounts, len(candidates))
        else:
            allocation = self.get_accounts_for_batch_sending(len(candidates))
            
        if not allocation:
            logger.error("没有可用的邮箱账户进行批量发送")
            return {'success': 0, 'failed': len(candidates), 'details': [], 'mode': 'async'}
        
        # 渲染邮件内容
        rendered_emails = EmailRenderer.render_batch_emails(
            template_content=template_content,
            template_subject=template_subject,
            candidates=candidates,
            user=self.user
        )
        
        created_tasks = []
        failed_count = 0
        candidate_index = 0
        
        # 按分配方案创建邮件任务
        for account, count in allocation:
            if candidate_index >= len(rendered_emails):
                break
                
            for i in range(count):
                if candidate_index >= len(rendered_emails):
                    break
                    
                email_data = rendered_emails[candidate_index]
                candidate = email_data['candidate']
                subject = email_data['subject']
                content = email_data['content']
                
                try:
                    # 只创建任务，不立即发送
                    email_log = mailing_service.create_email_task(
                        user=self.user,
                        from_account=account,
                        candidate=candidate,
                        subject=subject,
                        content=content,
                        **kwargs
                    )
                    
                    if email_log:
                        created_tasks.append(email_log)
                        logger.info(f"创建邮件任务 ID: {email_log.id} for {candidate.name}")
                    else:
                        failed_count += 1
                        logger.error(f"创建邮件任务失败 for {candidate.name}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"创建邮件任务异常 for {candidate.name}: {e}")
                    
                candidate_index += 1
        
        logger.info(f"批量任务创建完成: 成功创建 {len(created_tasks)} 个任务, 失败 {failed_count} 个")
        
        return {
            'mode': 'async',
            'task_ids': [task.id for task in created_tasks],
            'total_count': len(candidates),
            'created_count': len(created_tasks),
            'failed_count': failed_count,
            'status': 'queued'
        }
    
    def _send_batch_emails_sync(self, candidates: List[Candidate], template_subject: str, 
                               template_content: str, selected_accounts: Optional[List[EmailAccount]] = None, **kwargs) -> dict:
        """
        同步批量发送邮件 - 立即发送（原有逻辑，保留兼容性）
        """
        total_count = len(candidates)
        
        # 获取邮箱分配方案
        if selected_accounts and len(selected_accounts) > 0:
            allocation = self._get_selected_accounts_allocation(selected_accounts, total_count)
        else:
            allocation = self.get_accounts_for_batch_sending(total_count)
            
        if not allocation:
            logger.error("没有可用的邮箱账户进行批量发送")
            return {'success': 0, 'failed': total_count, 'details': [], 'mode': 'sync'}
        
        # 渲染邮件内容
        rendered_emails = EmailRenderer.render_batch_emails(
            template_content=template_content,
            template_subject=template_subject,
            candidates=candidates,
            user=self.user
        )
        
        success_count = 0
        failed_count = 0
        details = []
        candidate_index = 0
        
        # 按分配方案发送邮件
        for account, count in allocation:
            if candidate_index >= len(rendered_emails):
                break
                
            for i in range(count):
                if candidate_index >= len(rendered_emails):
                    break
                    
                email_data = rendered_emails[candidate_index]
                candidate = email_data['candidate']
                subject = email_data['subject']
                content = email_data['content']
                
                try:
                    email_log = self.send_single_email(
                        account=account,
                        candidate=candidate,
                        subject=subject,
                        content=content,
                        **kwargs
                    )
                    
                    if email_log and email_log.status == EmailLog.EmailStatus.SUCCESS:
                        success_count += 1
                        details.append({
                            'candidate': candidate.name,
                            'account': account.email_address,
                            'status': 'success'
                        })
                    else:
                        failed_count += 1
                        details.append({
                            'candidate': candidate.name,
                            'account': account.email_address,
                            'status': 'failed',
                            'reason': email_log.failure_reason if email_log else 'Unknown'
                        })
                        
                except Exception as e:
                    failed_count += 1
                    details.append({
                        'candidate': candidate.name,
                        'account': account.email_address,
                        'status': 'error',
                        'reason': str(e)
                    })
                    
                candidate_index += 1
        
        logger.info(f"批量发送完成: 成功 {success_count}, 失败 {failed_count}")
        
        return {
            'mode': 'sync',
            'success': success_count,
            'failed': failed_count,
            'details': details
        }
    
    def get_batch_sending_status(self, task_ids: List[int]) -> dict:
        """
        获取批量发送任务的状态
        
        Args:
            task_ids: 邮件任务ID列表
            
        Returns:
            批量任务状态统计
        """
        from ..models import EmailLog
        
        if not task_ids:
            return {'success': 0, 'failed': 0, 'pending': 0, 'total': 0, 'completed': True}
        
        # 查询所有相关任务
        tasks = EmailLog.objects.filter(id__in=task_ids)
        
        success_count = tasks.filter(status=EmailLog.EmailStatus.SUCCESS).count()
        failed_count = tasks.filter(status=EmailLog.EmailStatus.FAILED).count()
        pending_count = tasks.filter(status=EmailLog.EmailStatus.PENDING).count()
        total_count = len(task_ids)
        
        # 是否全部完成（成功或失败）
        completed = (success_count + failed_count) == total_count
        
        # 获取详细信息
        details = []
        for task in tasks:
            details.append({
                'id': task.id,
                'candidate': task.candidate.name if task.candidate else (task.contact.name if task.contact else 'Unknown'),
                'status': task.status,
                'account': task.from_account.email_address if task.from_account else 'Unknown',
                'failure_reason': task.failure_reason if task.failure_reason else None,
                'sent_at': task.sent_at.isoformat() if task.sent_at else None
            })
        
        return {
            'success': success_count,
            'failed': failed_count,
            'pending': pending_count,
            'total': total_count,
            'completed': completed,
            'progress_percent': round((success_count + failed_count) / total_count * 100, 1) if total_count > 0 else 0,
            'details': details
        }

    def get_accounts_status(self) -> List[dict]:
        """获取所有邮箱的当前状态"""
        today = timezone.now().date()
        status_list = []
        
        for account in self.available_accounts:
            stats = self._get_account_daily_stats(account, today)
            status_list.append({
                'email_address': account.email_address,
                'is_default': account.is_default,
                'daily_limit': account.daily_send_limit,
                'sent_today': stats.sent_count,
                'failed_today': stats.failed_count,
                'remaining_quota': stats.remaining_quota,
                'is_quota_exceeded': stats.is_quota_exceeded,
                'last_updated': stats.last_updated
            })
        
        return status_list


    def test_email_connection(self, account: EmailAccount, test_recipient: str, 
                             test_subject: str = "邮箱连接测试", test_content: str = "这是一封测试邮件，用于验证邮箱配置是否正确。") -> Dict[str, Any]:
        """
        测试邮箱连接和发送功能
        
        Args:
            account: 要测试的邮箱账户
            test_recipient: 测试收件人邮箱
            test_subject: 测试邮件主题
            test_content: 测试邮件内容
            
        Returns:
            包含测试结果的字典
        """
        test_result = {
            'success': False,
            'account': account.email_address,
            'recipient': test_recipient,
            'message': '',
            'error_details': None,
            'timestamp': timezone.now()
        }
        
        try:
            # 验证邮箱账户基本信息
            if not account.smtp_host or not account.smtp_port:
                raise ValidationError("SMTP服务器配置不完整")
            
            if not account.smtp_password_encrypted:
                raise ValidationError("邮箱密码未设置")
            
            # 解密密码
            password = decrypt_key(account.smtp_password_encrypted)
            if not password:
                raise ValidationError("密码解密失败")
            
            # 验证收件人邮箱格式
            from django.core.validators import validate_email
            try:
                validate_email(test_recipient)
            except Exception:
                raise ValidationError("收件人邮箱格式无效")
            
            # 构建完整的测试邮件内容
            full_content = f"""
{test_content}

---
测试信息:
- 发件邮箱: {account.email_address}
- SMTP服务器: {account.smtp_host}:{account.smtp_port}
- SSL设置: {'启用' if account.use_ssl else '禁用'}
- 测试时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
- 来源系统: 智能猎头招聘管理系统
"""
            
            # 尝试发送测试邮件
            from django.core.mail import get_connection
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=account.smtp_host,
                port=account.smtp_port,
                username=account.email_address,
                password=password,
                **account.get_smtp_connection_params(),
                fail_silently=False,
            )
            
            send_mail(
                subject=f"[测试] {test_subject}",
                message=full_content,
                html_message=full_content.replace('\n', '<br>'),
                from_email=account.email_address,
                recipient_list=[test_recipient],
                fail_silently=False,
                connection=connection,
            )
            
            # 发送成功
            test_result.update({
                'success': True,
                'message': f'测试邮件发送成功！已发送到 {test_recipient}'
            })
            
            logger.info(f"邮箱 {account.email_address} 测试成功，收件人: {test_recipient}")
            
        except ValidationError as e:
            test_result.update({
                'message': f'配置验证失败: {str(e)}',
                'error_details': str(e)
            })
            logger.warning(f"邮箱 {account.email_address} 配置验证失败: {e}")
            
        except Exception as e:
            # 解析常见的SMTP错误
            error_message = str(e).lower()
            
            if 'authentication failed' in error_message or 'auth' in error_message:
                user_message = "邮箱认证失败，请检查邮箱地址和密码/授权码是否正确"
            elif 'connection' in error_message or 'network' in error_message:
                user_message = "网络连接失败，请检查SMTP服务器地址和端口设置"
            elif 'ssl' in error_message or 'tls' in error_message:
                user_message = "SSL/TLS连接失败，请检查SSL设置是否正确"
            elif 'timeout' in error_message:
                user_message = "连接超时，请检查网络状况和服务器设置"
            elif 'recipient' in error_message:
                user_message = "收件人地址无效或被拒绝"
            else:
                user_message = f"发送失败: {str(e)}"
            
            test_result.update({
                'message': user_message,
                'error_details': str(e)
            })
            
            logger.error(f"邮箱 {account.email_address} 测试失败: {e}")
        
        return test_result


def get_multi_email_sender(user: User) -> MultiEmailSender:
    """获取多邮箱发送器实例"""
    return MultiEmailSender(user)


def test_email_account(account: EmailAccount, test_recipient: str, 
                      test_subject: str = "邮箱连接测试", 
                      test_content: str = "这是一封测试邮件，用于验证邮箱配置是否正确。") -> Dict[str, Any]:
    """
    独立的邮箱测试函数，可直接调用
    
    Args:
        account: 要测试的邮箱账户
        test_recipient: 测试收件人邮箱
        test_subject: 测试邮件主题
        test_content: 测试邮件内容
        
    Returns:
        包含测试结果的字典
    """
    sender = MultiEmailSender(account.user)
    return sender.test_email_connection(account, test_recipient, test_subject, test_content)