import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from typing import List, Dict, Any
from django.contrib.auth.models import User
from ..models import EmailLog, Candidate, Job, EmailAccount
from ..utils import decrypt_key
from . import template_service

logger = logging.getLogger(__name__)


def create_email_task(
        user: User,
        from_account: EmailAccount,
        candidate: Candidate = None,
        contact = None,
        subject: str = None,
        content: str = None,
        job: Job = None,
        group=None,
        contact_group=None,
        trigger_type: str = EmailLog.TriggerType.MANUAL
) -> EmailLog:
    """
    创建一封待发送的邮件并存入数据库队列。
    支持候选人或联系人作为收件人。
    邮件内容此时应包含占位符，将在发送时被渲染。
    """
    # 验证收件人
    if not candidate and not contact:
        logging.error("必须指定候选人或联系人作为收件人")
        return None
    
    # 获取邮箱地址和姓名
    email_address = None
    recipient_name = None
    
    if candidate:
        if not candidate.emails:
            logging.warning(f"Candidate {candidate.name} (ID: {candidate.id}) has no email address, skipping task creation.")
            return None
        email_address = candidate.emails[0] if isinstance(candidate.emails, list) else candidate.emails
        recipient_name = candidate.name
    elif contact:
        if not contact.email:
            logging.warning(f"Contact {contact.name} (ID: {contact.id}) has no email address, skipping task creation.")
            return None
        email_address = contact.email
        recipient_name = contact.name

    log_entry = EmailLog.objects.create(
        user=user,
        from_account=from_account,
        candidate=candidate,
        contact=contact,
        job=job,
        group=group,
        contact_group=contact_group,
        subject=subject,  # Store subject with placeholders
        content=content,  # Store content with placeholders
        status=EmailLog.EmailStatus.PENDING,
        trigger_type=trigger_type
    )
    logging.info(
        f"Email task (ID: {log_entry.id}) created for {recipient_name} using account {from_account.email_address}.")
    return log_entry


def process_pending_emails(max_retries: int = 3, specific_email_id: int = None):
    """
    处理邮件发送队列的核心逻辑。
    
    Args:
        max_retries: 最大重试次数
        specific_email_id: 指定处理特定的邮件任务ID，如果为None则处理所有待处理任务
    """
    if specific_email_id:
        # 只处理指定的邮件任务
        emails_to_send = EmailLog.objects.filter(
            id=specific_email_id,
            status__in=[EmailLog.EmailStatus.PENDING, EmailLog.EmailStatus.FAILED],
            retry_count__lt=max_retries
        ).select_related('candidate', 'from_account', 'user', 'job', 'job__company')
    else:
        # 处理所有待处理任务
        emails_to_send = EmailLog.objects.filter(
            status__in=[EmailLog.EmailStatus.PENDING, EmailLog.EmailStatus.FAILED],
            retry_count__lt=max_retries
        ).select_related('candidate', 'from_account', 'user', 'job', 'job__company')

    sent_count = 0
    failed_count = 0

    for log_entry in emails_to_send:
        try:
            # Validate required fields and determine recipient
            if not log_entry.from_account or not log_entry.user:
                raise ValueError("邮件任务缺少发送账户或用户信息。")
            
            # Determine recipient email and validate
            recipient_email = None
            template_recipient = None
            
            if log_entry.candidate:
                if not log_entry.candidate.emails:
                    raise ValueError(f"候选人 {log_entry.candidate.name} 没有邮箱地址。")
                recipient_email = log_entry.candidate.emails[0] if isinstance(log_entry.candidate.emails, list) else log_entry.candidate.emails
                template_recipient = log_entry.candidate
            elif log_entry.contact:
                if not log_entry.contact.email:
                    raise ValueError(f"联系人 {log_entry.contact.name} 没有邮箱地址。")
                recipient_email = log_entry.contact.email
                template_recipient = log_entry.contact
            else:
                raise ValueError("邮件任务必须指定候选人或联系人作为收件人。")

            # **核心改动**: 将 from_account 和正确的收件人传递给渲染函数
            rendered_subject = template_service.render_template(log_entry.subject, template_recipient, log_entry.job, log_entry.user, log_entry.from_account)
            rendered_content = template_service.render_template(log_entry.content, template_recipient, log_entry.job, log_entry.user, log_entry.from_account)

            password = decrypt_key(log_entry.from_account.smtp_password_encrypted)

            # 配置SMTP连接
            from django.core.mail import get_connection
            # 获取正确的TLS/SSL参数，确保不与全局设置冲突
            connection_params = log_entry.from_account.get_smtp_connection_params()
            
            # 确保只有一个加密选项被启用，避免与全局设置冲突
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=log_entry.from_account.smtp_host,
                port=log_entry.from_account.smtp_port,
                username=log_entry.from_account.email_address,
                password=password,
                fail_silently=False,
                use_tls=connection_params.get('use_tls', False),
                use_ssl=connection_params.get('use_ssl', False)
            )
            
            send_mail(
                subject=rendered_subject,
                message=rendered_content,
                html_message=rendered_content,
                from_email=log_entry.from_account.email_address,
                recipient_list=[recipient_email],
                fail_silently=False,
                connection=connection,
            )

            log_entry.status = EmailLog.EmailStatus.SUCCESS
            log_entry.sent_at = timezone.now()
            log_entry.save()
            sent_count += 1
            logging.info(f"邮件任务 ID: {log_entry.id} 发送成功。")

        except Exception as e:
            log_entry.status = EmailLog.EmailStatus.FAILED
            log_entry.failure_reason = str(e)
            log_entry.retry_count += 1
            log_entry.save()
            failed_count += 1
            logging.error(f"邮件任务 ID: {log_entry.id} 发送失败 (第 {log_entry.retry_count} 次尝试): {e}")

    return {"sent": sent_count, "failed": failed_count}


def create_admin_notification_task(admin_email: str, subject: str, content: str) -> bool:
    """
    创建管理员通知邮件任务
    
    Args:
        admin_email: 管理员邮箱
        subject: 通知主题
        content: 通知内容
        
    Returns:
        是否创建成功
    """
    try:
        # 查找超级用户作为发送者
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            logger.warning("未找到超级用户，无法发送管理员通知")
            return False
        
        # 查找可用的邮箱账户
        available_account = EmailAccount.objects.filter(
            user=admin_user,
            is_default=True
        ).first()
        
        if not available_account:
            available_account = EmailAccount.objects.filter(user=admin_user).first()
        
        if not available_account:
            logger.warning("未找到可用的邮箱账户，无法发送管理员通知")
            return False
        
        # 直接发送通知邮件，不创建EmailLog记录（避免循环）
        try:
            password = decrypt_key(available_account.smtp_password_encrypted)
            
            # 配置SMTP连接
            from django.core.mail import get_connection
            # 获取正确的TLS/SSL参数
            connection_params = available_account.get_smtp_connection_params()
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=available_account.smtp_host,
                port=available_account.smtp_port,
                username=available_account.email_address,
                password=password,
                fail_silently=False,
                **connection_params
            )
            
            send_mail(
                subject=f"[系统通知] {subject}",
                message=content,
                html_message=content.replace('\n', '<br>'),
                from_email=available_account.email_address,
                recipient_list=[admin_email],
                fail_silently=False,
                connection=connection,
            )
            
            logger.info(f"管理员通知邮件发送成功: {admin_email}")
            return True
            
        except Exception as e:
            logger.error(f"发送管理员通知邮件失败: {e}")
            return False
            
    except Exception as e:
        logger.error(f"创建管理员通知任务失败: {e}")
        return False


def notify_admin_failure(failed_account: EmailAccount, recipient: str, error_message: str, 
                        failure_count: int = 1, admin_email: str = None) -> bool:
    """
    发送管理员失败告警邮件
    
    Args:
        failed_account: 失败的邮箱账户
        recipient: 原始收件人
        error_message: 错误信息
        failure_count: 失败次数
        admin_email: 管理员邮箱（可选，默认使用settings中的配置）
        
    Returns:
        是否发送成功
    """
    try:
        # 确定管理员邮箱
        if not admin_email:
            admin_email = getattr(settings, 'ADMIN_EMAIL', None)
            if not admin_email:
                # 尝试从DEFAULT_FROM_EMAIL获取
                admin_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        
        if not admin_email:
            logger.warning("未配置管理员邮箱，无法发送失败告警")
            return False
        
        # 构建告警邮件内容
        subject = f"邮件发送失败告警 - {failed_account.email_address}"
        
        content = f"""
邮件发送失败告警

失败详情：
- 失败邮箱: {failed_account.email_address}
- 目标收件人: {recipient}
- 失败次数: {failure_count}
- 错误信息: {error_message}
- 失败时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

邮箱配置信息：
- SMTP服务器: {failed_account.smtp_host}:{failed_account.smtp_port}
- SSL设置: {'启用' if failed_account.use_ssl else '禁用'}
- 每日发送限制: {failed_account.daily_send_limit}

建议处理方案：
1. 检查邮箱账户配置是否正确
2. 验证SMTP服务器连接状态
3. 确认邮箱密码/授权码是否有效
4. 检查收件人邮箱地址是否正确

---
智能猎头招聘管理系统
"""
        
        # 发送告警邮件
        return create_admin_notification_task(admin_email, subject, content)
        
    except Exception as e:
        logger.error(f"发送管理员失败告警时发生错误: {e}")
        return False


def send_bulk_emails_with_protection(email_logs: List[EmailLog], 
                                   max_retries: int = 3,
                                   continue_on_failure: bool = True) -> Dict[str, Any]:
    """
    批量发送邮件，带有失败保护机制
    
    Args:
        email_logs: 要发送的邮件日志列表
        max_retries: 最大重试次数
        continue_on_failure: 是否在失败时继续发送其他邮件
        
    Returns:
        发送结果统计
    """
    results = {
        'total': len(email_logs),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'details': [],
        'admin_notified': False
    }
    
    first_failure_notified = False
    
    for log_entry in email_logs:
        try:
            # 基本验证 - 支持候选人或联系人
            recipient_valid = False
            recipient_name = None
            recipient_email = None
            
            if log_entry.candidate and log_entry.candidate.emails:
                recipient_valid = True
                recipient_name = log_entry.candidate.name
                recipient_email = log_entry.candidate.emails[0] if isinstance(log_entry.candidate.emails, list) else log_entry.candidate.emails
            elif log_entry.contact and log_entry.contact.email:
                recipient_valid = True
                recipient_name = log_entry.contact.name
                recipient_email = log_entry.contact.email
            
            if not recipient_valid or not log_entry.from_account or not log_entry.user:
                log_entry.status = EmailLog.EmailStatus.FAILED
                log_entry.failure_reason = "邮件任务缺少必要信息"
                log_entry.save()
                results['failed'] += 1
                results['details'].append({
                    'log_id': log_entry.id,
                    'status': 'failed',
                    'reason': '缺少必要信息'
                })
                continue
            
            # 渲染邮件内容 - 支持候选人或联系人
            try:
                # 使用候选人或联系人进行模板渲染
                template_recipient = log_entry.candidate if log_entry.candidate else log_entry.contact
                rendered_subject = template_service.render_template(
                    log_entry.subject, template_recipient, log_entry.job, 
                    log_entry.user, log_entry.from_account
                )
                rendered_content = template_service.render_template(
                    log_entry.content, template_recipient, log_entry.job, 
                    log_entry.user, log_entry.from_account
                )
            except Exception as e:
                log_entry.status = EmailLog.EmailStatus.FAILED
                log_entry.failure_reason = f"模板渲染失败: {str(e)}"
                log_entry.save()
                results['failed'] += 1
                results['details'].append({
                    'log_id': log_entry.id,
                    'status': 'failed',
                    'reason': f'模板渲染失败: {str(e)}'
                })
                
                if continue_on_failure:
                    continue
                else:
                    break
            
            # 发送邮件
            try:
                password = decrypt_key(log_entry.from_account.smtp_password_encrypted)
                
                # 配置SMTP连接
                from django.core.mail import get_connection
                # 获取正确的TLS/SSL参数
                connection_params = log_entry.from_account.get_smtp_connection_params()
                connection = get_connection(
                    backend='django.core.mail.backends.smtp.EmailBackend',
                    host=log_entry.from_account.smtp_host,
                    port=log_entry.from_account.smtp_port,
                    username=log_entry.from_account.email_address,
                    password=password,
                    fail_silently=False,
                    **connection_params
                )
                
                send_mail(
                    subject=rendered_subject,
                    message=rendered_content,
                    html_message=rendered_content,
                    from_email=log_entry.from_account.email_address,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                    connection=connection,
                )
                
                # 发送成功
                log_entry.status = EmailLog.EmailStatus.SUCCESS
                log_entry.sent_at = timezone.now()
                log_entry.failure_reason = ""
                log_entry.save()
                results['success'] += 1
                results['details'].append({
                    'log_id': log_entry.id,
                    'status': 'success',
                    'recipient': recipient_email
                })
                
                logger.info(f"邮件任务 ID: {log_entry.id} 发送成功")
                
            except Exception as e:
                # 邮件发送失败
                log_entry.status = EmailLog.EmailStatus.FAILED
                log_entry.failure_reason = str(e)
                log_entry.retry_count += 1
                log_entry.save()
                results['failed'] += 1
                results['details'].append({
                    'log_id': log_entry.id,
                    'status': 'failed',
                    'reason': str(e),
                    'retry_count': log_entry.retry_count
                })
                
                logger.error(f"邮件任务 ID: {log_entry.id} 发送失败 (第 {log_entry.retry_count} 次尝试): {e}")
                
                # 首次失败时发送管理员通知
                if not first_failure_notified:
                    success = notify_admin_failure(
                        failed_account=log_entry.from_account,
                        recipient=recipient_email,
                        error_message=str(e),
                        failure_count=log_entry.retry_count
                    )
                    if success:
                        results['admin_notified'] = True
                        first_failure_notified = True
                
                if not continue_on_failure:
                    break
        
        except Exception as e:
            # 处理过程中的意外错误
            logger.error(f"处理邮件任务 ID: {log_entry.id} 时发生意外错误: {e}")
            results['skipped'] += 1
            results['details'].append({
                'log_id': log_entry.id,
                'status': 'skipped',
                'reason': f'处理异常: {str(e)}'
            })
            
            if not continue_on_failure:
                break
    
    logger.info(f"批量邮件发送完成: 总数 {results['total']}, 成功 {results['success']}, 失败 {results['failed']}, 跳过 {results['skipped']}")
    
    return results