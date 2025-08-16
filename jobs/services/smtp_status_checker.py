"""
SMTP Status Checker Service
Provides functionality to check SMTP server connection status without sending emails.
"""
import smtplib
import socket
from typing import Dict, Any
from ..utils import decrypt_key


class SMTPStatusChecker:
    """Service for checking SMTP server connection status"""
    
    @staticmethod
    def check_smtp_connection(email_account) -> Dict[str, Any]:
        """
        Check SMTP server connection status for a given email account.
        
        Args:
            email_account: EmailAccount model instance
            
        Returns:
            Dict with status information including:
            - success: bool
            - status: str ('success'|'auth_failed'|'unreachable'|'error')
            - message: str
            - details: str (optional technical details)
        """
        try:
            # Decrypt the password
            password = decrypt_key(email_account.smtp_password_encrypted)
            
            # Basic connection test
            server = None
            try:
                # Create SMTP connection
                if email_account.use_ssl:
                    server = smtplib.SMTP_SSL(email_account.smtp_host, email_account.smtp_port, timeout=10)
                else:
                    server = smtplib.SMTP(email_account.smtp_host, email_account.smtp_port, timeout=10)
                    if email_account.smtp_port in [587, 25]:  # Common TLS ports
                        server.starttls()
                
                # Test authentication
                server.login(email_account.email_address, password)
                
                # If we get here, connection and auth succeeded
                return {
                    'success': True,
                    'status': 'success',
                    'message': '连接成功',
                    'details': f'SMTP服务器 {email_account.smtp_host}:{email_account.smtp_port} 连接正常'
                }
                
            except smtplib.SMTPAuthenticationError as e:
                return {
                    'success': False,
                    'status': 'auth_failed',
                    'message': '认证失败',
                    'details': f'用户名或密码错误: {str(e)}'
                }
                
            except (socket.gaierror, socket.timeout, ConnectionRefusedError) as e:
                return {
                    'success': False,
                    'status': 'unreachable',
                    'message': '服务器不可达',
                    'details': f'无法连接到 {email_account.smtp_host}:{email_account.smtp_port} - {str(e)}'
                }
                
            except smtplib.SMTPException as e:
                return {
                    'success': False,
                    'status': 'error',
                    'message': 'SMTP错误',
                    'details': f'SMTP协议错误: {str(e)}'
                }
                
            finally:
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass  # Ignore errors when closing connection
                        
        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'message': '检查失败',
                'details': f'未知错误: {str(e)}'
            }
    
    @staticmethod
    def get_status_badge_class(status: str) -> str:
        """Get Bootstrap badge class for status"""
        status_classes = {
            'success': 'bg-success',
            'auth_failed': 'bg-danger',
            'unreachable': 'bg-warning',
            'error': 'bg-secondary'
        }
        return status_classes.get(status, 'bg-secondary')
    
    @staticmethod
    def get_status_icon(status: str) -> str:
        """Get appropriate icon for status"""
        status_icons = {
            'success': '✅',
            'auth_failed': '🔴',
            'unreachable': '🟠',
            'error': '⚠️'
        }
        return status_icons.get(status, '❓')