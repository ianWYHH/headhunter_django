"""
修复定时任务时区问题的管理命令
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import ScheduledEmailTask
from jobs.services.mail_scheduler import mail_scheduler


class Command(BaseCommand):
    help = '修复定时任务的时区问题，重新同步所有活跃的定时任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示需要修复的任务，不执行实际修复',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('开始修复定时任务时区问题...'))
        
        # 获取所有活跃的定时任务
        active_tasks = ScheduledEmailTask.objects.filter(
            is_enabled=True,
            status=ScheduledEmailTask.TaskStatus.ACTIVE
        )
        
        if not active_tasks.exists():
            self.stdout.write(self.style.WARNING('没有找到活跃的定时任务'))
            return
        
        fixed_count = 0
        error_count = 0
        
        for task in active_tasks:
            try:
                self.stdout.write(f'处理任务: {task.name} (ID: {task.id})')
                
                # 显示当前配置信息
                self.stdout.write(f'  调度类型: {task.get_schedule_type_display()}')
                self.stdout.write(f'  开始时间: {task.start_time}')
                self.stdout.write(f'  调度配置: {task.get_schedule_config_display()}')
                
                if task.next_run_time:
                    self.stdout.write(f'  下次执行: {task.next_run_time}')
                
                if not dry_run:
                    # 从调度器中移除旧任务
                    mail_scheduler.remove_task(task.id)
                    
                    # 重新计算下次执行时间（使用正确的时区）
                    task.next_run_time = task.calculate_next_run()
                    task.save(update_fields=['next_run_time'])
                    
                    # 重新添加到调度器
                    mail_scheduler.add_task(task)
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ 任务已重新同步'))
                    self.stdout.write(f'  新的下次执行时间: {task.next_run_time}')
                else:
                    self.stdout.write(self.style.WARNING(f'  [DRY RUN] 需要重新同步'))
                
                fixed_count += 1
                self.stdout.write('')  # 空行分隔
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ 处理任务失败: {str(e)}')
                )
        
        # 输出汇总信息
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'[DRY RUN] 完成扫描，找到 {fixed_count} 个需要修复的任务')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'修复完成！成功处理 {fixed_count} 个任务')
            )
            
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'处理过程中遇到 {error_count} 个错误')
            )
        
        # 重启调度器以确保配置生效
        if not dry_run:
            try:
                mail_scheduler.stop()
                mail_scheduler.start()
                self.stdout.write(self.style.SUCCESS('调度器已重启，使用新的时区配置'))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'重启调度器失败: {str(e)}')
                )