"""
Django管理命令：收取邮件
用法：python manage.py fetch_emails [--days=7] [--user=username]
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from jobs.services.imap_service import create_imap_fetch_task


class Command(BaseCommand):
    help = '收取用户邮箱的新邮件'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='收取多少天内的邮件 (默认: 1)'
        )
        
        parser.add_argument(
            '--user',
            type=str,
            help='指定用户名 (不指定则为所有用户)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只检查配置，不实际收取邮件'
        )

    def handle(self, *args, **options):
        days = options['days']
        username = options['user']
        dry_run = options['dry_run']
        
        # 获取用户列表
        if username:
            try:
                users = [User.objects.get(username=username)]
            except User.DoesNotExist:
                raise CommandError(f'用户 "{username}" 不存在')
        else:
            # 获取所有配置了邮箱的用户
            users = User.objects.filter(email_accounts__isnull=False).distinct()
        
        if not users:
            self.stdout.write(
                self.style.WARNING('没有找到配置了邮箱的用户')
            )
            return
        
        self.stdout.write(f'开始为 {len(users)} 个用户收取邮件...')
        
        total_emails = 0
        total_errors = 0
        
        for user in users:
            self.stdout.write(f'\n处理用户: {user.username}')
            
            # 检查用户的邮箱配置
            email_accounts = user.email_accounts.filter(
                imap_host__isnull=False,
                imap_host__gt=''
            )
            
            if not email_accounts.exists():
                self.stdout.write(
                    self.style.WARNING(f'  用户 {user.username} 没有配置IMAP邮箱')
                )
                continue
            
            if dry_run:
                self.stdout.write(f'  检查到 {email_accounts.count()} 个配置的IMAP邮箱:')
                for account in email_accounts:
                    self.stdout.write(f'    - {account.email_address} ({account.imap_host}:{account.imap_port})')
                continue
            
            try:
                result = create_imap_fetch_task(user, days)
                
                if result['success']:
                    user_total = result['total_emails']
                    total_emails += user_total
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'  成功收取 {user_total} 封邮件')
                    )
                    
                    # 显示详细结果
                    for account, count in result['results'].items():
                        if count > 0:
                            self.stdout.write(f'    {account}: {count} 封')
                        
                else:
                    total_errors += 1
                    self.stdout.write(
                        self.style.ERROR(f'  收取失败: {result["error"]}')
                    )
                    
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f'  收取异常: {str(e)}')
                )
        
        # 输出汇总
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('\n检查完成！使用 --dry-run=false 开始实际收取')
            )
        else:
            self.stdout.write(f'\n邮件收取完成!')
            self.stdout.write(f'总共收取: {total_emails} 封邮件')
            if total_errors > 0:
                self.stdout.write(
                    self.style.WARNING(f'错误数量: {total_errors} 个用户')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('所有用户处理成功!')
                )