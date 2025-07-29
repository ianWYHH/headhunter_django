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
    邮件内容此时应包含占位符，将在发送时被渲染。
    """
    if not candidate.emails:
        logging.warning(f"Candidate {candidate.name} (ID: {candidate.id}) has no email address, skipping task creation.")
        return None

    log_entry = EmailLog.objects.create(
        user=user,
        from_account=from_account,
        candidate=candidate,
        job=job,
        group=group,
        subject=subject,  # Store subject with placeholders
        content=content,  # Store content with placeholders
        status=EmailLog.EmailStatus.PENDING,
        trigger_type=trigger_type
    )
    logging.info(
        f"Email task (ID: {log_entry.id}) created for candidate {candidate.name} using account {from_account.email_address}.")
    return log_entry


def process_pending_emails(max_retries: int = 3):
    """
    处理邮件发送队列的核心逻辑。
    这个函数由后台定时任务(send_queued_emails)调用。
    """
    emails_to_send = EmailLog.objects.filter(
        status__in=[EmailLog.EmailStatus.PENDING, EmailLog.EmailStatus.FAILED],
        retry_count__lt=max_retries
    ).select_related('candidate', 'from_account', 'user', 'job', 'job__company')

    sent_count = 0
    failed_count = 0

    for log_entry in emails_to_send:
        try:
            # 确保所有必要的关联对象都存在
            if not all([log_entry.candidate, log_entry.candidate.emails, log_entry.from_account, log_entry.user]):
                raise ValueError("Task is missing required information (candidate, recipient, sender, or user).")

            logging.info(
                f"Processing email task ID: {log_entry.id}, from: {log_entry.from_account.email_address}, to: {log_entry.candidate.emails[0]}")

            # **核心升级**: 在发送前渲染模板，替换占位符
            rendered_subject = template_service.render_template(log_entry.subject, log_entry.candidate, log_entry.job, log_entry.user)
            rendered_content = template_service.render_template(log_entry.content, log_entry.candidate, log_entry.job, log_entry.user)

            # 解密发件箱密码
            password = decrypt_key(log_entry.from_account.smtp_password_encrypted)

            # 使用Django内置的send_mail发送邮件
            send_mail(
                subject=rendered_subject,
                message=rendered_content,  # Django会自动处理HTML，但这里我们只发送纯文本
                html_message=rendered_content, # 为支持HTML格式的邮件客户端提供HTML版本
                from_email=log_entry.from_account.email_address,
                recipient_list=[log_entry.candidate.emails[0]],
                fail_silently=False,
                auth_user=log_entry.from_account.email_address,
                auth_password=password,
            )

            # 更新任务状态为成功
            log_entry.status = EmailLog.EmailStatus.SUCCESS
            log_entry.sent_at = timezone.now()
            log_entry.save()
            sent_count += 1
            logging.info(f"Email task ID: {log_entry.id} sent successfully.")

        except Exception as e:
            # 更新任务状态为失败，并记录原因和重试次数
            log_entry.status = EmailLog.EmailStatus.FAILED
            log_entry.failure_reason = str(e)
            log_entry.retry_count += 1
            log_entry.save()
            failed_count += 1
            logging.error(f"Email task ID: {log_entry.id} failed (Attempt {log_entry.retry_count}): {e}")

    return {"sent": sent_count, "failed": failed_count}
