from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jobs'
    
    def ready(self):
        """Django应用启动时执行"""
        import logging
        
        # 避免在开发环境中重复启动
        import sys
        if 'runserver' in sys.argv or 'runsslserver' in sys.argv:
            try:
                from jobs.services.mail_scheduler import mail_scheduler
                mail_scheduler.start()
                logging.info("邮件调度器已在Django启动时初始化")
            except Exception as e:
                logging.error(f"启动邮件调度器失败: {e}")
