import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from ..models import EmailLog, Candidate, Job, EmailAccount, User
from ..utils import decrypt_key
from . import template_service


def create_email_task(
        user: User,
        from_account: EmailAccount,
        candidate: Candidate,
        subject: str,
        content: str,
        job: Job = None,
        group=None,
        trigger_type: str = EmailLog.TriggerType.MANUAL
) -> EmailLog:
    """
    创建一封待发送的邮件并存入数据库队列。
    邮件内容此时应包含占位符。
    """
    if not candidate.emails:
        logging.warning(f"候选人 {candidate.name} (ID: {candidate.id}) 没有邮箱地址，无法创建邮件任务。")
        return None

    log_entry = EmailLog.objects.create(
        user=user,
        from_account=from_account,
        candidate=candidate,
        job=job,
        group=group,
        subject=subject,
        content=content,
        status=EmailLog.EmailStatus.PENDING,
        trigger_type=trigger_type
    )
    logging.info(
        f"已为候选人 {candidate.name} 创建邮件任务 (ID: {log_entry.id})，使用邮箱 {from_account.email_address}。")
    return log_entry


def process_pending_emails(max_retries: int = 3):
    """
    处理邮件发送队列的核心逻辑。
    这个函数应该由一个后台定时任务来调用。
    """
    emails_to_send = EmailLog.objects.filter(
        status__in=[EmailLog.EmailStatus.PENDING, EmailLog.EmailStatus.FAILED],
        retry_count__lt=max_retries
    ).select_related('candidate', 'from_account', 'user', 'job', 'job__company')

    sent_count = 0
    failed_count = 0

    for log_entry in emails_to_send:
        try:
            if not all([log_entry.candidate, log_entry.candidate.emails, log_entry.from_account, log_entry.user]):
                raise ValueError("邮件任务缺少候选人、收件箱、发件箱或用户信息。")

            logging.info(
                f"正在处理邮件任务 ID: {log_entry.id}，发件人: {log_entry.from_account.email_address}，收件人: {log_entry.candidate.emails[0]}")

            # (核心升级) 在发送前渲染模板
            rendered_subject = template_service.render_template(log_entry.subject, log_entry.candidate, log_entry.job,
                                                                log_entry.user)
            rendered_content = template_service.render_template(log_entry.content, log_entry.candidate, log_entry.job,
                                                                log_entry.user)

            password = decrypt_key(log_entry.from_account.smtp_password_encrypted)

            send_mail(
                subject=rendered_subject,
                message=rendered_content,  # 发送纯文本邮件
                from_email=log_entry.from_account.email_address,
                recipient_list=[log_entry.candidate.emails[0]],
                fail_silently=False,
                auth_user=log_entry.from_account.email_address,
                auth_password=password,
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
