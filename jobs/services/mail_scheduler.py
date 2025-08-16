import logging
from datetime import datetime, timedelta
from typing import Optional, List
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from jobs.models import ScheduledEmailTask, EmailLog, Candidate
from jobs.services.email_renderer import EmailRenderer
from jobs.services import mailing_service
from jobs.services import logging_service

logger = logging.getLogger(__name__)


class MailScheduler:
    """邮件调度器，负责管理定时邮件任务的执行"""
    
    def __init__(self):
        self.scheduler = None
        self._initialized = False
    
    def initialize(self):
        """初始化调度器"""
        if self._initialized:
            return
        
        jobstores = {'default': MemoryJobStore()}
        executors = {'default': ThreadPoolExecutor(20)}
        job_defaults = {'coalesce': False, 'max_instances': 3}
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.TIME_ZONE  # 使用与Django相同的时区
        )
        
        self._initialized = True
        logger.info("邮件调度器初始化完成")
    
    def start(self):
        """启动调度器"""
        if not self._initialized:
            self.initialize()
        
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("邮件调度器已启动")
            self.load_existing_tasks()
    
    def stop(self):
        """停止调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("邮件调度器已停止")
    
    def load_existing_tasks(self):
        """加载数据库中现有的定时任务"""
        try:
            active_tasks = ScheduledEmailTask.objects.filter(
                is_enabled=True,
                status=ScheduledEmailTask.TaskStatus.ACTIVE
            )
            
            for task in active_tasks:
                self.add_task(task)
                
            logger.info(f"已加载 {active_tasks.count()} 个定时任务")
        except Exception as e:
            logger.error(f"加载定时任务失败: {e}")
    
    def add_task(self, task: ScheduledEmailTask):
        """添加定时任务到调度器"""
        try:
            job_id = f"email_task_{task.id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            trigger = self._create_trigger(task)
            if not trigger:
                logger.warning(f"任务 {task.id} 无法创建触发器")
                return
            
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task.id],
                id=job_id,
                name=f"定时邮件任务: {task.name}",
                replace_existing=True
            )
            
            task.next_run_time = task.calculate_next_run()
            task.save(update_fields=['next_run_time'])
            
            logger.info(f"已添加定时任务: {task.name} (ID: {task.id})")
            
        except Exception as e:
            logger.error(f"添加定时任务失败: {e}")
    
    def remove_task(self, task_id: int):
        """从调度器中移除定时任务"""
        try:
            job_id = f"email_task_{task_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"已移除定时任务: {job_id}")
        except Exception as e:
            logger.error(f"移除定时任务失败: {e}")
    
    def _create_trigger(self, task: ScheduledEmailTask):
        """根据任务配置创建触发器"""
        try:
            if task.schedule_type == ScheduledEmailTask.ScheduleType.ONCE:
                return DateTrigger(run_date=task.start_time, timezone=settings.TIME_ZONE)
            
            elif task.schedule_type == ScheduledEmailTask.ScheduleType.DAILY:
                return CronTrigger(
                    hour=task.start_time.hour,
                    minute=task.start_time.minute,
                    timezone=settings.TIME_ZONE
                )
            
            elif task.schedule_type == ScheduledEmailTask.ScheduleType.WEEKLY:
                weekdays = task.schedule_config.get('weekdays', [])
                if not weekdays:
                    return None
                
                return CronTrigger(
                    day_of_week=','.join(str(day) for day in weekdays),
                    hour=task.start_time.hour,
                    minute=task.start_time.minute,
                    timezone=settings.TIME_ZONE
                )
            
            elif task.schedule_type == ScheduledEmailTask.ScheduleType.MONTHLY:
                day_of_month = task.schedule_config.get('day_of_month', 1)
                return CronTrigger(
                    day=day_of_month,
                    hour=task.start_time.hour,
                    minute=task.start_time.minute,
                    timezone=settings.TIME_ZONE
                )
            
            return None
            
        except Exception as e:
            logger.error(f"创建触发器失败: {e}")
            return None
    
    def _execute_task(self, task_id: int):
        """执行定时任务"""
        try:
            with transaction.atomic():
                task = ScheduledEmailTask.objects.select_for_update().get(id=task_id)
                
                if not task.is_enabled or task.status != ScheduledEmailTask.TaskStatus.ACTIVE:
                    logger.info(f"任务 {task_id} 已禁用或状态异常，跳过执行")
                    return
                
                if task.end_time and timezone.now() > task.end_time:
                    task.status = ScheduledEmailTask.TaskStatus.COMPLETED
                    task.save()
                    logger.info(f"任务 {task_id} 已到达结束时间，标记为完成")
                    return
                
                # 根据目标类型获取收件人
                if task.target_type == ScheduledEmailTask.TargetType.CANDIDATE_GROUP:
                    if not task.group:
                        logger.error(f"任务 {task_id} 未指定候选人分组")
                        return
                    
                    candidates = task.group.candidates.filter(emails__isnull=False).exclude(emails=[])
                    if not candidates.exists():
                        logger.warning(f"任务 {task_id} 的候选人分组中没有有效邮箱的候选人")
                        return
                    recipients = list(candidates)
                    
                elif task.target_type == ScheduledEmailTask.TargetType.CONTACT_GROUP:
                    if not task.contact_group:
                        logger.error(f"任务 {task_id} 未指定联系人分组")
                        return
                    
                    contacts = task.contact_group.get_active_contacts()
                    if not contacts:
                        logger.warning(f"任务 {task_id} 的联系人分组中没有有效联系人")
                        return
                    
                    # 直接使用联系人列表，不再进行转换
                    recipients = list(contacts)
                else:
                    logger.error(f"任务 {task_id} 目标类型未知: {task.target_type}")
                    return
                
                # 执行邮件发送，带有失败保护
                try:
                    success_count, failed_count = self._send_group_emails(task, recipients)
                except Exception as e:
                    logger.error(f"任务 {task_id} 邮件发送失败: {e}")
                    success_count, failed_count = 0, len(recipients)
                
                # 更新任务统计信息
                task.total_executions += 1
                task.successful_executions += success_count
                task.failed_executions += failed_count
                task.last_run_time = timezone.now()
                
                # 计算下次执行时间
                if task.schedule_type == ScheduledEmailTask.ScheduleType.ONCE:
                    task.status = ScheduledEmailTask.TaskStatus.COMPLETED
                    task.next_run_time = None
                else:
                    task.next_run_time = task.calculate_next_run()
                
                task.save()
                
                logger.info(f"任务 {task_id} 执行完成: 成功 {success_count}, 失败 {failed_count}")
                
                # 如果失败率过高，记录警告
                if failed_count > 0 and success_count == 0:
                    logger.warning(f"任务 {task_id} 所有邮件发送失败，请检查邮箱配置")
                elif failed_count > success_count:
                    logger.warning(f"任务 {task_id} 失败率过高: 失败 {failed_count}, 成功 {success_count}")
                
        except ScheduledEmailTask.DoesNotExist:
            logger.error(f"任务 {task_id} 不存在")
        except Exception as e:
            logger.error(f"执行任务 {task_id} 失败: {e}")
    
    def _send_group_emails(self, task: ScheduledEmailTask, recipients: List) -> tuple:
        """发送分组邮件，带有失败保护机制"""
        success_count = 0
        failed_count = 0
        
        # 确保导入mailing_service
        from jobs.services import mailing_service
        
        try:
            # 检查是否使用多邮箱发送
            if task.use_multi_accounts and task.selected_accounts.exists():
                # 使用多邮箱发送
                from jobs.services.multi_email_service import get_multi_email_sender
                sender = get_multi_email_sender(task.user)
                
                # 获取目标分组（可能是候选人分组或联系人分组）
                target_group = task.get_target_group()
                
                result = sender.send_batch_emails(
                    candidates=candidates,
                    template_subject=task.template.subject,
                    template_content=task.template.body,
                    selected_accounts=list(task.selected_accounts.all()),
                    group=target_group
                )
                
                success_count = result['success']
                failed_count = result['failed']
                
                # 记录多邮箱发送的详细信息
                if result.get('admin_notified'):
                    logger.info(f"定时任务 {task.id} 中有邮件发送失败，已通知管理员")
                
            else:
                # 使用单邮箱发送，采用新的失败保护机制
                email_logs = []
                target_group = task.get_target_group()
                
                # 根据目标类型确定分组
                if task.target_type == ScheduledEmailTask.TargetType.CANDIDATE_GROUP:
                    group = target_group
                    contact_group = None
                else:
                    group = None
                    contact_group = target_group
                
                # 创建所有邮件任务
                for recipient in recipients:
                    try:
                        # 检查收件人类型
                        from jobs.models import Contact
                        if isinstance(recipient, Contact):
                            # 联系人
                            email_task = mailing_service.create_email_task(
                                user=task.user,
                                from_account=task.from_account,
                                contact=recipient,
                                subject=task.template.subject,
                                content=task.template.body,
                                contact_group=contact_group,
                                trigger_type=EmailLog.TriggerType.AUTO
                            )
                            recipient_name = recipient.name
                        else:
                            # 候选人
                            email_task = mailing_service.create_email_task(
                                user=task.user,
                                from_account=task.from_account,
                                candidate=recipient,
                                subject=task.template.subject,
                                content=task.template.body,
                                group=group,
                                trigger_type=EmailLog.TriggerType.AUTO
                            )
                            recipient_name = recipient.name
                        
                        if email_task:
                            email_logs.append(email_task)
                            logger.debug(f"为{recipient_name} 创建邮件任务成功 (ID: {email_task.id})")
                        else:
                            failed_count += 1
                            logger.warning(f"为{recipient_name} 创建邮件任务失败")
                    
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"为{recipient.name} 创建邮件任务异常: {e}")
                
                # 使用带有失败保护的批量发送机制
                if email_logs:
                    result = mailing_service.send_bulk_emails_with_protection(
                        email_logs=email_logs,
                        continue_on_failure=True  # 确保失败不阻塞其他邮件
                    )
                    
                    success_count += result['success']
                    failed_count += result['failed'] + result['skipped']
                    
                    # 记录管理员通知状态
                    if result.get('admin_notified'):
                        logger.info(f"定时任务 {task.id} 中有邮件发送失败，已通知管理员")
                    
                    # 记录详细的发送结果
                    logger.info(f"定时任务 {task.id} 邮件发送详情: 总数 {result['total']}, 成功 {result['success']}, 失败 {result['failed']}, 跳过 {result['skipped']}")
                
        except Exception as e:
            # 即使发生意外错误，也要记录详细信息并通知管理员
            logger.error(f"定时任务 {task.id} 邮件发送过程中发生严重错误: {e}", exc_info=True)
            
            # 尝试发送管理员通知
            try:
                mailing_service.notify_admin_failure(
                    failed_account=task.from_account,
                    recipient="定时任务系统",
                    error_message=f"定时任务 {task.id} ({task.name}) 执行异常: {str(e)}",
                    failure_count=1
                )
            except Exception as notify_error:
                logger.error(f"发送定时任务失败通知时也发生错误: {notify_error}")
            
            return 0, len(candidates)
        
        return success_count, failed_count
    
    def get_job_status(self, task_id: int) -> Optional[dict]:
        """获取任务状态"""
        try:
            job_id = f"email_task_{task_id}"
            job = self.scheduler.get_job(job_id)
            
            if job:
                return {
                    'job_id': job_id,
                    'next_run_time': job.next_run_time,
                    'trigger': str(job.trigger)
                }
            else:
                return None
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None
    
    def get_all_jobs(self) -> List[dict]:
        """获取所有调度任务"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'job_id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time,
                    'trigger': str(job.trigger)
                })
            return jobs
        except Exception as e:
            logger.error(f"获取所有任务失败: {e}")
            return []


# 全局调度器实例
mail_scheduler = MailScheduler() 