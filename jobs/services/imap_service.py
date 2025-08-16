"""
IMAP邮件收取服务
"""
import imaplib
import email
import logging
import re
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import List, Optional, Dict, Tuple
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import EmailAccount, IncomingEmail, EmailLog, Candidate
from ..utils import decrypt_key

logger = logging.getLogger(__name__)


class IMAPEmailReceiver:
    """IMAP邮件接收器"""
    
    def __init__(self, email_account: EmailAccount):
        self.account = email_account
        self.connection = None
        
    def connect(self) -> bool:
        """连接到IMAP服务器"""
        try:
            if not self.account.imap_host:
                logger.error(f"邮箱 {self.account.email_address} 未配置IMAP服务器")
                return False
            
            # 解密密码
            password = decrypt_key(self.account.smtp_password_encrypted)
            
            # 建立连接
            if self.account.imap_use_ssl:
                self.connection = imaplib.IMAP4_SSL(
                    self.account.imap_host, 
                    self.account.imap_port or 993
                )
            else:
                self.connection = imaplib.IMAP4(
                    self.account.imap_host, 
                    self.account.imap_port or 143
                )
            
            # 登录
            self.connection.login(self.account.email_address, password)
            logger.info(f"成功连接到 {self.account.email_address} 的IMAP服务器")
            return True
            
        except Exception as e:
            logger.error(f"连接IMAP服务器失败 {self.account.email_address}: {e}")
            return False
    
    def disconnect(self):
        """断开IMAP连接"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def __enter__(self):
        if self.connect():
            return self
        else:
            raise ConnectionError(f"无法连接到 {self.account.email_address} 的IMAP服务器")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def _decode_header(self, header_value: str) -> str:
        """解码邮件头部"""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        result = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    try:
                        result += part.decode(encoding)
                    except:
                        result += part.decode('utf-8', errors='ignore')
                else:
                    result += part.decode('utf-8', errors='ignore')
            else:
                result += part
        
        return result.strip()
    
    def _extract_text_content(self, msg: email.message.Message) -> Tuple[str, str]:
        """提取邮件的文本和HTML内容"""
        text_content = ""
        html_content = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # 跳过附件
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        text_content = part.get_payload(decode=True).decode(charset, errors='ignore')
                    except:
                        text_content = str(part.get_payload())
                        
                elif content_type == "text/html":
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        html_content = part.get_payload(decode=True).decode(charset, errors='ignore')
                    except:
                        html_content = str(part.get_payload())
        else:
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or 'utf-8'
            
            try:
                content = msg.get_payload(decode=True).decode(charset, errors='ignore')
            except:
                content = str(msg.get_payload())
            
            if content_type == "text/html":
                html_content = content
            else:
                text_content = content
        
        return text_content.strip(), html_content.strip()
    
    def _count_attachments(self, msg: email.message.Message) -> int:
        """计算附件数量"""
        count = 0
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in content_disposition:
                    count += 1
        return count
    
    def _detect_email_type(self, subject: str, content: str, sender_email: str) -> str:
        """检测邮件类型"""
        subject_lower = subject.lower()
        content_lower = content.lower()
        
        # 检测自动回复
        auto_reply_keywords = [
            'auto reply', 'automatic reply', 'out of office', 'auto-reply',
            '自动回复', '外出', '休假', '不在办公室', 'vacation'
        ]
        
        for keyword in auto_reply_keywords:
            if keyword in subject_lower or keyword in content_lower:
                return IncomingEmail.EmailType.AUTO_REPLY
        
        # 检测退信
        bounce_keywords = [
            'delivery failure', 'undelivered', 'bounced', 'delivery status notification',
            '投递失败', '退信', '邮件被退回'
        ]
        
        for keyword in bounce_keywords:
            if keyword in subject_lower or keyword in content_lower:
                return IncomingEmail.EmailType.BOUNCE
        
        # 默认为回复
        return IncomingEmail.EmailType.REPLY
    
    def _find_related_candidate(self, sender_email: str, subject: str, references: str) -> Optional[Candidate]:
        """根据发件人邮箱查找相关候选人"""
        try:
            # 首先通过邮箱精确匹配
            candidates = Candidate.objects.filter(emails__contains=[sender_email])
            if candidates.exists():
                return candidates.first()
            
            # 尝试通过邮箱域名模糊匹配
            email_domain = sender_email.split('@')[1] if '@' in sender_email else None
            if email_domain:
                for candidate in Candidate.objects.all():
                    for email_addr in candidate.emails or []:
                        if email_domain in email_addr:
                            return candidate
            
            return None
            
        except Exception as e:
            logger.error(f"查找相关候选人失败: {e}")
            return None
    
    def _find_original_email(self, in_reply_to: str, references: str, sender_email: str) -> Optional[EmailLog]:
        """查找原始邮件记录"""
        try:
            if in_reply_to:
                # 通过 Message-ID 查找
                email_log = EmailLog.objects.filter(message_id=in_reply_to).first()
                if email_log:
                    return email_log
            
            if references:
                # 通过 References 查找
                ref_ids = references.split()
                for ref_id in ref_ids:
                    email_log = EmailLog.objects.filter(message_id=ref_id.strip('<>')).first()
                    if email_log:
                        return email_log
            
            # 通过候选人邮箱查找最近的邮件
            candidate = self._find_related_candidate(sender_email, "", "")
            if candidate:
                return EmailLog.objects.filter(
                    candidate=candidate,
                    from_account=self.account
                ).order_by('-sent_at').first()
            
            return None
            
        except Exception as e:
            logger.error(f"查找原始邮件失败: {e}")
            return None
    
    def fetch_new_emails(self, days_back: int = 7) -> List[IncomingEmail]:
        """获取新邮件"""
        if not self.connection:
            logger.error("IMAP连接未建立")
            return []
        
        try:
            # 选择收件箱
            self.connection.select('INBOX')
            
            # 计算搜索日期
            since_date = (timezone.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')
            
            # 搜索邮件
            status, messages = self.connection.search(None, f'SINCE {since_date}')
            if status != 'OK':
                logger.error(f"搜索邮件失败: {status}")
                return []
            
            email_ids = messages[0].split()
            new_emails = []
            
            logger.info(f"找到 {len(email_ids)} 封邮件需要处理")
            
            for email_id in email_ids:
                try:
                    # 获取邮件
                    status, msg_data = self.connection.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    # 解析邮件
                    msg = email.message_from_bytes(msg_data[0][1])
                    incoming_email = self._parse_email_message(msg)
                    
                    if incoming_email:
                        new_emails.append(incoming_email)
                        
                except Exception as e:
                    logger.error(f"处理邮件 {email_id} 失败: {e}")
                    continue
            
            logger.info(f"成功处理 {len(new_emails)} 封新邮件")
            return new_emails
            
        except Exception as e:
            logger.error(f"获取邮件失败: {e}")
            return []
    
    @transaction.atomic
    def _parse_email_message(self, msg: email.message.Message) -> Optional[IncomingEmail]:
        """解析邮件消息并保存到数据库"""
        try:
            # 提取基本信息
            message_id = msg.get('Message-ID', '').strip('<>')
            if not message_id:
                logger.warning("邮件缺少Message-ID，跳过")
                return None
            
            # 检查是否已经处理过
            if IncomingEmail.objects.filter(message_id=message_id).exists():
                logger.debug(f"邮件 {message_id} 已经处理过，跳过")
                return None
            
            # 提取发件人信息
            from_header = self._decode_header(msg.get('From', ''))
            sender_name, sender_email = parseaddr(from_header)
            
            if not sender_email:
                logger.warning(f"邮件 {message_id} 发件人邮箱为空，跳过")
                return None
            
            # 提取其他头部信息
            subject = self._decode_header(msg.get('Subject', ''))
            in_reply_to = msg.get('In-Reply-To', '').strip('<>')
            references = msg.get('References', '')
            
            # 提取邮件内容
            text_content, html_content = self._extract_text_content(msg)
            attachments_count = self._count_attachments(msg)
            
            # 解析接收时间
            date_header = msg.get('Date')
            received_at = timezone.now()  # 默认值
            
            if date_header:
                try:
                    received_at = parsedate_to_datetime(date_header)
                    if received_at.tzinfo is None:
                        received_at = timezone.make_aware(received_at)
                except:
                    pass
            
            # 检测邮件类型
            email_type = self._detect_email_type(subject, text_content, sender_email)
            
            # 查找相关候选人和原始邮件
            candidate = self._find_related_candidate(sender_email, subject, references)
            original_email = self._find_original_email(in_reply_to, references, sender_email)
            
            # 创建收件邮件记录
            incoming_email = IncomingEmail.objects.create(
                candidate=candidate,
                original_email_log=original_email,
                received_account=self.account,
                sender_email=sender_email,
                sender_name=self._decode_header(sender_name) if sender_name else "",
                subject=subject,
                content=text_content or html_content,  # 优先使用文本内容
                html_content=html_content,
                message_id=message_id,
                in_reply_to=in_reply_to,
                references=references,
                received_at=received_at,
                email_type=email_type,
                attachments_count=attachments_count
            )
            
            logger.info(f"成功保存收件邮件: {sender_email} -> {subject[:50]}")
            return incoming_email
            
        except Exception as e:
            logger.error(f"解析邮件失败: {e}")
            return None


class IMAPService:
    """IMAP服务管理器"""
    
    @staticmethod
    def fetch_emails_for_account(email_account: EmailAccount, days_back: int = 7) -> List[IncomingEmail]:
        """为指定邮箱账户收取邮件"""
        try:
            with IMAPEmailReceiver(email_account) as receiver:
                return receiver.fetch_new_emails(days_back)
        except Exception as e:
            logger.error(f"收取邮箱 {email_account.email_address} 的邮件失败: {e}")
            return []
    
    @staticmethod
    def fetch_emails_for_user(user, days_back: int = 7) -> Dict[str, List[IncomingEmail]]:
        """为用户的所有邮箱账户收取邮件"""
        results = {}
        
        # 获取用户配置了IMAP的邮箱账户
        email_accounts = user.email_accounts.filter(
            imap_host__isnull=False,
            imap_host__gt=''
        )
        
        for account in email_accounts:
            logger.info(f"开始收取邮箱 {account.email_address} 的邮件")
            emails = IMAPService.fetch_emails_for_account(account, days_back)
            results[account.email_address] = emails
            logger.info(f"邮箱 {account.email_address} 收取到 {len(emails)} 封新邮件")
        
        return results
    
    @staticmethod
    def get_unread_emails_for_user(user) -> List[IncomingEmail]:
        """获取用户的所有未读邮件"""
        return IncomingEmail.objects.filter(
            received_account__user=user,
            is_read=False
        ).order_by('-received_at')
    
    @staticmethod
    def mark_email_as_read(email_id: int, user) -> bool:
        """将邮件标记为已读"""
        try:
            email = IncomingEmail.objects.get(
                id=email_id,
                received_account__user=user
            )
            email.is_read = True
            email.save()
            return True
        except IncomingEmail.DoesNotExist:
            return False
    
    @staticmethod
    def get_emails_for_candidate(candidate: Candidate) -> List[IncomingEmail]:
        """获取候选人的所有收件邮件"""
        return IncomingEmail.objects.filter(
            candidate=candidate
        ).order_by('-received_at')


def create_imap_fetch_task(user, days_back: int = 1):
    """创建IMAP收取任务（可用于定时任务）"""
    try:
        results = IMAPService.fetch_emails_for_user(user, days_back)
        total_emails = sum(len(emails) for emails in results.values())
        
        logger.info(f"用户 {user.username} 的IMAP收取任务完成，共收取 {total_emails} 封新邮件")
        
        return {
            'success': True,
            'total_emails': total_emails,
            'results': {account: len(emails) for account, emails in results.items()}
        }
        
    except Exception as e:
        logger.error(f"用户 {user.username} 的IMAP收取任务失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }