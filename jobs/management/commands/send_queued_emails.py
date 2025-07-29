import datetime
from django.core.management.base import BaseCommand
from jobs.services import mailing_service, logging_service


class Command(BaseCommand):
    help = '处理数据库中所有待发送的邮件任务。'

    def handle(self, *args, **options):
        """
        命令的执行入口。
        """
        self.stdout.write(f"[{datetime.datetime.now()}] 开始处理邮件发送队列...")

        try:
            # 调用我们之前编写的邮件处理服务
            result = mailing_service.process_pending_emails()

            success_count = result.get('sent', 0)
            failed_count = result.get('failed', 0)

            summary_message = f"处理完成。成功发送 {success_count} 封，失败 {failed_count} 封。"

            # 将执行结果打印到标准输出，这对于在宝塔面板查看日志很有用
            self.stdout.write(self.style.SUCCESS(summary_message))

            # (可选) 如果有邮件发送，也可以记录一个系统级别的操作日志
            if success_count > 0 or failed_count > 0:
                logging_service.create_log(user=None, action_description=f"后台邮件任务: {summary_message}")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"处理邮件队列时发生严重错误: {e}"))
