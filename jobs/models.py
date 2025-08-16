from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True, verbose_name="公司名称")
    description = models.TextField(blank=True, null=True, verbose_name="公司描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self): return self.name

    class Meta: ordering = ['name']; verbose_name = "公司"; verbose_name_plural = "公司"


class Job(models.Model):
    class JobStatus(models.TextChoices):
        PENDING = '待处理', '待处理';
        IN_PROGRESS = '进行中', '进行中';
        CLOSED = '已关闭', '已关闭';
        SUCCESS = '成功', '成功'

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")
    title = models.CharField(max_length=255, db_index=True, verbose_name="职位名称")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs', verbose_name="公司")
    department = models.CharField(max_length=255, blank=True, null=True, verbose_name="所属部门")
    salary_range = models.CharField(max_length=100, blank=True, null=True, verbose_name="薪资范围")
    level_set = models.JSONField(default=list, blank=True, verbose_name="职级要求")
    status = models.CharField(max_length=50, choices=JobStatus.choices, default=JobStatus.PENDING, db_index=True,
                              verbose_name="职位状态")
    locations = models.JSONField(default=list, blank=True, verbose_name="工作地点")
    raw_skills = models.JSONField(default=list, blank=True, verbose_name="原始技能(未处理)")
    keywords = models.JSONField(default=list, blank=True, verbose_name="标准化关键词")
    job_description = models.TextField(blank=True, null=True, verbose_name="职位描述")
    job_requirement = models.TextField(blank=True, null=True, verbose_name="职位要求")
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self): return f"{self.title} at {self.company.name}"

    class Meta: ordering = ['-updated_at']; verbose_name = "职位"; verbose_name_plural = "职位"


class ApiKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="所属用户")
    provider = models.CharField(max_length=100, help_text="服务商的唯一标识, 例如 'qwen', 'kimi'",
                                verbose_name="服务商")
    api_key_encrypted = models.BinaryField(help_text="加密后的API密钥", verbose_name="加密密钥")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self): return f"API Key for {self.provider.upper()} by {self.user.username}"


    def get_decrypted_key(self):
        """解密并返回API密钥"""
        try:
            from .utils import decrypt_key
            return decrypt_key(self.api_key_encrypted)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'解密API密钥失败: {e}')
            return None
    class Meta: unique_together = ('user', 'provider'); ordering = [
        'provider']; verbose_name = "API密钥"; verbose_name_plural = "API密钥"


class CandidateGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")
    name = models.CharField(max_length=255, verbose_name="分组名称")
    description = models.TextField(blank=True, null=True, verbose_name="分组描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self): return self.name

    class Meta: unique_together = ('user', 'name'); ordering = [
        'name']; verbose_name = "候选人分组"; verbose_name_plural = "候选人分组"


class Candidate(models.Model):
    class Gender(models.TextChoices):
        MALE = '男', '男'
        FEMALE = '女', '女'
        OTHER = '其他', '其他'
        UNKNOWN = '未知', '未知'
    
    class EducationLevel(models.TextChoices):
        HIGH_SCHOOL = '高中', '高中'
        COLLEGE = '大专', '大专'
        BACHELOR = '本科', '本科'
        MASTER = '硕士', '硕士'
        DOCTOR = '博士', '博士'
        OTHER = '其他', '其他'
        UNKNOWN = '未知', '未知'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")
    name = models.CharField(max_length=255, db_index=True, verbose_name="姓名")
    emails = models.JSONField(default=list, blank=True, verbose_name="邮箱地址 (多个)")
    homepage = models.URLField(max_length=255, blank=True, null=True, verbose_name="个人主页")
    github_profile = models.URLField(max_length=255, blank=True, null=True, verbose_name="GitHub主页")
    linkedin_profile = models.URLField(max_length=255, blank=True, null=True, verbose_name="领英主页")
    external_id = models.BigIntegerField(blank=True, null=True, db_index=True, verbose_name="外部系统ID")
    raw_skills = models.JSONField(default=list, blank=True, verbose_name="原始技能(未处理)")
    keywords = models.JSONField(default=list, blank=True, verbose_name="标准化关键词")
    # 新增字段
    birthday = models.DateField(blank=True, null=True, verbose_name="出生年月日")
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.UNKNOWN, verbose_name="性别")
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="所在地")
    education_level = models.CharField(max_length=20, choices=EducationLevel.choices, default=EducationLevel.UNKNOWN, verbose_name="最高学历")
    # 新增字段：AI预测的职位标签
    predicted_position = models.CharField(max_length=255, blank=True, null=True, verbose_name="AI预测职位", help_text="AI根据简历内容判断该候选人目前从事或适合的职位名称")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    applications = models.ManyToManyField(Job, through='Application', related_name='candidates')
    groups = models.ManyToManyField(CandidateGroup, blank=True, related_name='candidates', verbose_name="所属分组")

    def __str__(self): return self.name
    
    @property
    def age(self):
        """计算候选人当前年龄"""
        if not self.birthday:
            return None
        
        from datetime import date
        today = date.today()
        
        # 如果只有年份信息，按1月1日计算
        birth_year = self.birthday.year
        age = today.year - birth_year
        
        # 如果今年生日还没到，年龄减1
        # 这里简化处理：如果是1月1日的生日（即只有年份），直接按年份差计算
        if self.birthday.month == 1 and self.birthday.day == 1:
            # 只有年份的情况，按年份差计算
            return age
        else:
            # 有具体月日的情况，考虑生日是否已过
            if (today.month, today.day) < (self.birthday.month, self.birthday.day):
                age -= 1
            return age
    
    @property 
    def birth_year_only(self):
        """返回只有年份的出生日期字符串"""
        if not self.birthday:
            return ""
        return str(self.birthday.year)

    class Meta: ordering = ['-updated_at']; verbose_name = "候选人"; verbose_name_plural = "候选人"


class Application(models.Model):
    class ApplicationStatus(models.TextChoices):
        MATCHED = '已匹配', '已匹配';
        APPLIED = '已申请', '已申请';
        INTERVIEWING = '面试中', '面试中';
        OFFERED = '已Offer', '已Offer';
        REJECTED = '已拒绝', '已拒绝'

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, verbose_name="候选人")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, verbose_name="职位")
    status = models.CharField(max_length=50, choices=ApplicationStatus.choices, default=ApplicationStatus.MATCHED,
                              verbose_name="状态")
    matched_keywords = models.JSONField(default=list, blank=True, verbose_name="匹配到的关键词")
    application_date = models.DateTimeField(auto_now_add=True, verbose_name="申请/匹配日期")

    class Meta: unique_together = ('candidate', 'job'); ordering = [
        '-application_date']; verbose_name = "申请记录"; verbose_name_plural = "申请记录"


class EmailAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_accounts', verbose_name="所属用户")
    email_address = models.EmailField(unique=True, verbose_name="邮箱地址")
    sender_name = models.CharField(max_length=255, blank=True, default="", verbose_name="发件人姓名", 
                                 help_text="邮件中显示的发件人姓名，如：张三 <zhang@example.com>")
    smtp_host = models.CharField(max_length=255, verbose_name="SMTP服务器")
    smtp_port = models.PositiveIntegerField(verbose_name="端口")
    smtp_password_encrypted = models.BinaryField(verbose_name="加密后的密码/授权码")
    use_ssl = models.BooleanField(default=True, verbose_name="使用SSL/TLS加密", 
                                  help_text="勾选以启用加密连接（根据端口自动选择TLS或SSL）")
    is_default = models.BooleanField(default=False, verbose_name="是否为默认邮箱")
    # **新增字段**
    signature = models.TextField(blank=True, null=True, verbose_name="邮箱签名 (支持HTML)")
    daily_send_limit = models.PositiveIntegerField(default=200, verbose_name="每日发送上限")
    imap_host = models.CharField(max_length=255, blank=True, null=True, verbose_name="IMAP服务器")
    imap_port = models.PositiveIntegerField(blank=True, null=True, verbose_name="IMAP端口")
    imap_use_ssl = models.BooleanField(default=True, verbose_name="IMAP使用SSL")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    @classmethod
    def get_email_provider_presets(cls):
        """获取常用邮箱服务商的预设配置"""
        return {
            'gmail': {
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'imap_host': 'imap.gmail.com',
                'imap_port': 993,
                'use_ssl': True,
                'imap_use_ssl': True,
                'help_text': '请使用应用专用密码，而非账户密码'
            },
            'qq': {
                'smtp_host': 'smtp.qq.com',
                'smtp_port': 587,
                'imap_host': 'imap.qq.com',
                'imap_port': 993,
                'use_ssl': True,
                'imap_use_ssl': True,
                'help_text': '请在QQ邮箱设置中开启SMTP/IMAP服务，并使用授权码'
            },
            'tencent_exmail': {
                'smtp_host': 'smtp.exmail.qq.com',
                'smtp_port': 587,
                'imap_host': 'imap.exmail.qq.com',
                'imap_port': 993,
                'use_ssl': True,
                'imap_use_ssl': True,
                'help_text': '腾讯企业邮箱，请使用完整邮箱地址作为用户名'
            },
            '163': {
                'smtp_host': 'smtp.163.com',
                'smtp_port': 587,
                'imap_host': 'imap.163.com',
                'imap_port': 993,
                'use_ssl': True,
                'imap_use_ssl': True,
                'help_text': '请在163邮箱设置中开启SMTP/IMAP服务，并使用授权码'
            }
        }
    
    def get_provider_info(self):
        """根据邮箱地址自动识别服务商"""
        if not self.email_address or '@' not in self.email_address:
            return 'custom'
            
        try:
            domain = self.email_address.split('@')[1].lower()
        except (IndexError, AttributeError):
            return 'custom'
        
        if 'gmail.com' in domain:
            return 'gmail'
        elif 'qq.com' in domain:
            return 'qq'  
        elif 'exmail.qq.com' in domain:
            return 'tencent_exmail'
        elif '163.com' in domain:
            return '163'
        elif 'outlook.com' in domain or 'hotmail.com' in domain:
            return 'outlook'
        else:
            return 'custom'

    def __str__(self): return self.email_address

    def get_smtp_connection_params(self):
        """获取SMTP连接参数，智能选择TLS/SSL"""
        # 根据端口智能选择加密方式
        if not self.use_ssl:
            # 不使用加密
            return {'use_tls': False, 'use_ssl': False}
        elif self.smtp_port == 465:
            # 端口465通常使用SSL
            return {'use_tls': False, 'use_ssl': True}  
        elif self.smtp_port in [587, 25]:
            # 端口587和25通常使用TLS
            return {'use_tls': True, 'use_ssl': False}
        else:
            # 默认使用TLS（比较常见且安全）
            return {'use_tls': True, 'use_ssl': False}

    class Meta: ordering = ['-is_default', 'email_address']; verbose_name = "邮箱账户"; verbose_name_plural = "邮箱账户"


class EmailLog(models.Model):
    class EmailStatus(models.TextChoices):
        SUCCESS = '成功', '成功';
        FAILED = '失败', '失败';
        PENDING = '待发送', '待发送';
        CANCELED = '已取消', '已取消'

    class TriggerType(models.TextChoices):
        AUTO = '自动', '自动';
        MANUAL = '手动', '手动'

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="操作者")
    from_account = models.ForeignKey(EmailAccount, on_delete=models.SET_NULL, null=True, verbose_name="发件邮箱")
    candidate = models.ForeignKey(Candidate, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='email_logs', verbose_name="候选人")
    contact = models.ForeignKey('Contact', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='email_logs', verbose_name="联系人")
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="相关职位")
    group = models.ForeignKey(CandidateGroup, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="目标分组")
    contact_group = models.ForeignKey('ContactGroup', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="目标联系人分组")
    subject = models.CharField(max_length=255, verbose_name="邮件主题")
    content = models.TextField(verbose_name="邮件内容")
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="发送时间")
    status = models.CharField(max_length=50, choices=EmailStatus.choices, default=EmailStatus.PENDING,
                              verbose_name="发送状态")
    failure_reason = models.TextField(blank=True, null=True, verbose_name="失败原因")
    retry_count = models.PositiveSmallIntegerField(default=0, verbose_name="重试次数")
    trigger_type = models.CharField(max_length=50, choices=TriggerType.choices, default=TriggerType.MANUAL,
                                    verbose_name="触发方式")
    remarks = models.TextField(blank=True, null=True, verbose_name="备注")
    message_id = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name="服务商消息ID")
    is_opened = models.BooleanField(default=False, verbose_name="是否打开")
    opened_at = models.DateTimeField(blank=True, null=True, verbose_name="首次打开时间")
    is_clicked = models.BooleanField(default=False, verbose_name="是否点击")

    def __str__(self): 
        recipient = 'N/A'
        try:
            if self.candidate and hasattr(self.candidate, 'name') and self.candidate.name:
                recipient = self.candidate.name
            elif self.contact and hasattr(self.contact, 'name') and self.contact.name:
                recipient = self.contact.name
        except (AttributeError, ValueError):
            recipient = 'N/A'
        
        subject = getattr(self, 'subject', 'No Subject') or 'No Subject'
        return f"Email to {recipient} - {subject}"

    class Meta: ordering = ['-sent_at']; verbose_name = "邮件发送记录"; verbose_name_plural = "邮件发送记录"


class ActionLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="操作者")
    action_time = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")
    action_description = models.CharField(max_length=255, verbose_name="操作描述")
    related_object_str = models.CharField(max_length=255, blank=True, null=True, verbose_name="关联对象")

    def __str__(
            self): return f"{self.user.username if self.user else '系统'} @ {self.action_time}: {self.action_description}"

    class Meta: ordering = ['-action_time']; verbose_name = "操作日志"; verbose_name_plural = "操作日志"


class EmailTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="模板名称")
    subject = models.CharField(max_length=255, verbose_name="邮件主题")
    body = models.TextField(verbose_name="邮件正文", help_text="支持占位符和HTML")
    tags = models.CharField(max_length=255, blank=True, verbose_name="分类/标签", help_text="多个标签用逗号分隔")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_templates",
                                   verbose_name="创建者")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="updated_templates",
                                   verbose_name="最后修改者")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return self.name

    class Meta: ordering = ['name']; verbose_name = "邮件模板"; verbose_name_plural = "邮件模板"


# **新增模型**
class EmailReply(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="处理人")
    in_reply_to = models.ForeignKey(EmailLog, on_delete=models.SET_NULL, null=True, blank=True, related_name='email_replies',
                                    verbose_name="回复的邮件")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='email_replies',
                                  verbose_name="发件候选人")
    from_email = models.EmailField(verbose_name="发件人邮箱")
    to_account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='email_replies',
                                   verbose_name="收件账户")
    subject = models.CharField(max_length=255, verbose_name="邮件主题")
    body = models.TextField(verbose_name="邮件正文")
    received_at = models.DateTimeField(verbose_name="收到时间")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply from {self.candidate.name} to {self.to_account.email_address}"

    class Meta:
        ordering = ['-received_at']
        verbose_name = "邮件回复"
        verbose_name_plural = "邮件回复"


class ScheduledEmailTask(models.Model):
    """定时发送邮件任务模型"""
    class TaskStatus(models.TextChoices):
        ACTIVE = 'active', '启用'
        PAUSED = 'paused', '暂停'
        COMPLETED = 'completed', '已完成'
        CANCELLED = 'cancelled', '已取消'
    
    class ScheduleType(models.TextChoices):
        ONCE = 'once', '单次发送'
        DAILY = 'daily', '每日发送'
        WEEKLY = 'weekly', '每周发送'
        MONTHLY = 'monthly', '每月发送'
        CUSTOM = 'custom', '自定义'
    
    class TargetType(models.TextChoices):
        CANDIDATE_GROUP = 'candidate_group', '候选人分组'
        CONTACT_GROUP = 'contact_group', '联系人分组'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")
    name = models.CharField(max_length=255, verbose_name="任务名称")
    
    # 目标类型和分组
    target_type = models.CharField(max_length=20, choices=TargetType.choices, default=TargetType.CANDIDATE_GROUP, verbose_name="目标类型")
    group = models.ForeignKey(CandidateGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='scheduled_tasks', verbose_name="候选人分组")
    contact_group = models.ForeignKey('ContactGroup', on_delete=models.CASCADE, null=True, blank=True, related_name='scheduled_tasks', verbose_name="联系人分组")
    
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, verbose_name="邮件模板")
    from_account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, null=True, blank=True, verbose_name="单一发件邮箱")
    
    # 多邮箱支持
    use_multi_accounts = models.BooleanField(default=False, verbose_name="使用多邮箱发送")
    selected_accounts = models.ManyToManyField(EmailAccount, blank=True, related_name='scheduled_tasks', verbose_name="选择的邮箱账户")
    
    # 调度配置
    schedule_type = models.CharField(max_length=20, choices=ScheduleType.choices, default=ScheduleType.ONCE, verbose_name="调度类型")
    start_time = models.DateTimeField(verbose_name="开始时间")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="结束时间")
    
    # 自定义调度配置（JSON格式）
    schedule_config = models.JSONField(default=dict, blank=True, verbose_name="调度配置", 
                                     help_text="存储具体的调度规则，如每周几、每月几号等")
    
    # 任务状态
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.ACTIVE, verbose_name="任务状态")
    last_run_time = models.DateTimeField(blank=True, null=True, verbose_name="上次执行时间")
    next_run_time = models.DateTimeField(blank=True, null=True, verbose_name="下次执行时间")
    
    # 执行统计
    total_executions = models.PositiveIntegerField(default=0, verbose_name="总执行次数")
    successful_executions = models.PositiveIntegerField(default=0, verbose_name="成功次数")
    failed_executions = models.PositiveIntegerField(default=0, verbose_name="失败次数")
    
    # 其他配置
    description = models.TextField(blank=True, null=True, verbose_name="任务描述")
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    def clean(self):
        """模型验证"""
        from django.core.exceptions import ValidationError
        
        if self.target_type == self.TargetType.CANDIDATE_GROUP:
            if not self.group:
                raise ValidationError({'group': '选择候选人分组时，必须指定候选人分组'})
            if self.contact_group:
                raise ValidationError({'contact_group': '选择候选人分组时，不能同时指定联系人分组'})
        elif self.target_type == self.TargetType.CONTACT_GROUP:
            if not self.contact_group:
                raise ValidationError({'contact_group': '选择联系人分组时，必须指定联系人分组'})
            if self.group:
                raise ValidationError({'group': '选择联系人分组时，不能同时指定候选人分组'})
    
    def get_target_group(self):
        """获取目标分组"""
        if self.target_type == self.TargetType.CANDIDATE_GROUP:
            return self.group
        elif self.target_type == self.TargetType.CONTACT_GROUP:
            return self.contact_group
        return None
    
    def get_target_recipients(self):
        """获取目标收件人列表"""
        if self.target_type == self.TargetType.CANDIDATE_GROUP and self.group:
            # 返回候选人列表 - Candidate模型没有is_active字段，返回所有候选人
            return self.group.candidates.all()
        elif self.target_type == self.TargetType.CONTACT_GROUP and self.contact_group:
            # 返回联系人列表
            return self.contact_group.get_active_contacts()
        return []
    
    def get_target_display(self):
        """获取目标显示名称"""
        target_group = self.get_target_group()
        if target_group:
            return f"{self.get_target_type_display()}: {target_group.name}"
        return "未设置目标"

    def __str__(self):
        target_group = self.get_target_group()
        group_name = target_group.name if target_group else "未设置"
        return f"{self.name} - {group_name}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "定时邮件任务"
        verbose_name_plural = "定时邮件任务"
    
    def get_schedule_config_display(self):
        """获取调度配置的显示文本（确保时区正确）"""
        from django.utils import timezone
        
        # 确保时间显示使用本地时区
        display_time = self.start_time
        if display_time and timezone.is_aware(display_time):
            display_time = timezone.localtime(display_time)
        
        if self.schedule_type == self.ScheduleType.ONCE:
            if display_time:
                return f"单次执行: {display_time.strftime('%Y-%m-%d %H:%M')}"
            return "单次执行"
        elif self.schedule_type == self.ScheduleType.DAILY:
            if display_time:
                return f"每日执行: {display_time.strftime('%H:%M')}"
            return "每日执行"
        elif self.schedule_type == self.ScheduleType.WEEKLY:
            schedule_config = self.schedule_config or {}
            weekdays = schedule_config.get('weekdays', [])
            weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            weekday_str = ', '.join([weekday_names[i] for i in weekdays if 0 <= i < 7])
            time_str = display_time.strftime('%H:%M') if display_time else ''
            return f"每周执行: {weekday_str} {time_str}"
        elif self.schedule_type == self.ScheduleType.MONTHLY:
            schedule_config = self.schedule_config or {}
            day_of_month = schedule_config.get('day_of_month', 1)
            time_str = display_time.strftime('%H:%M') if display_time else ''
            return f"每月执行: {day_of_month}号 {time_str}"
        else:
            return "自定义调度"
    
    def calculate_next_run(self):
        """计算下次执行时间"""
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        now = timezone.now()
        
        if self.schedule_type == self.ScheduleType.ONCE:
            if self.start_time > now:
                return self.start_time
            else:
                return None
        elif self.schedule_type == self.ScheduleType.DAILY:
            # 计算今天的执行时间
            today_time = now.replace(
                hour=self.start_time.hour,
                minute=self.start_time.minute,
                second=0,
                microsecond=0
            )
            if today_time <= now:
                # 今天的时间已过，计算明天
                return today_time + timedelta(days=1)
            else:
                return today_time
        elif self.schedule_type == self.ScheduleType.WEEKLY:
            schedule_config = self.schedule_config or {}
            weekdays = schedule_config.get('weekdays', [])
            if not weekdays:
                return None
            
            # 找到下一个执行日期
            current_weekday = now.weekday()
            for weekday in sorted(weekdays):
                if weekday > current_weekday:
                    days_ahead = weekday - current_weekday
                    next_date = now + timedelta(days=days_ahead)
                    return next_date.replace(
                        hour=self.start_time.hour,
                        minute=self.start_time.minute,
                        second=0,
                        microsecond=0
                    )
            
            # 如果本周没有合适的日期，计算下周
            days_ahead = 7 - current_weekday + weekdays[0]
            next_date = now + timedelta(days=days_ahead)
            return next_date.replace(
                hour=self.start_time.hour,
                minute=self.start_time.minute,
                second=0,
                microsecond=0
            )
        elif self.schedule_type == self.ScheduleType.MONTHLY:
            schedule_config = self.schedule_config or {}
            day_of_month = schedule_config.get('day_of_month', 1)
            
            # 计算本月执行时间
            try:
                this_month = now.replace(day=day_of_month, hour=self.start_time.hour, 
                                       minute=self.start_time.minute, second=0, microsecond=0)
                if this_month > now:
                    return this_month
            except ValueError:
                # 如果本月没有这一天（如31号），跳过
                pass
            
            # 计算下月执行时间
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=day_of_month,
                                       hour=self.start_time.hour, minute=self.start_time.minute,
                                       second=0, microsecond=0)
            else:
                next_month = now.replace(month=now.month + 1, day=day_of_month,
                                       hour=self.start_time.hour, minute=self.start_time.minute,
                                       second=0, microsecond=0)
            
            try:
                return next_month
            except ValueError:
                # 如果下月也没有这一天，返回None
                return None
        
        return None


class EmailAccountStats(models.Model):
    """邮箱账户每日发送统计"""
    email_account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='daily_stats', verbose_name="邮箱账户")
    date = models.DateField(verbose_name="统计日期")
    sent_count = models.PositiveIntegerField(default=0, verbose_name="已发送数量")
    failed_count = models.PositiveIntegerField(default=0, verbose_name="发送失败数量")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")
    
    class Meta:
        unique_together = ['email_account', 'date']
        ordering = ['-date']
        verbose_name = "邮箱发送统计"
        verbose_name_plural = "邮箱发送统计"
    
    def __str__(self):
        return f"{self.email_account.email_address} - {self.date} ({self.sent_count})"
    
    @property
    def remaining_quota(self):
        """当日剩余发送额度"""
        return max(0, self.email_account.daily_send_limit - self.sent_count)
    
    @property
    def is_quota_exceeded(self):
        """是否超出当日发送限制"""
        return self.sent_count >= self.email_account.daily_send_limit


class IncomingEmail(models.Model):
    """收到的邮件（IMAP收取的回信）"""
    class EmailType(models.TextChoices):
        REPLY = 'reply', '回复'
        AUTO_REPLY = 'auto_reply', '自动回复'
        BOUNCE = 'bounce', '退信'
        OTHER = 'other', '其他'
    
    candidate = models.ForeignKey(Candidate, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='incoming_emails', verbose_name="关联候选人")
    original_email_log = models.ForeignKey(EmailLog, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='incoming_replies', verbose_name="原始邮件")
    received_account = models.ForeignKey(EmailAccount, on_delete=models.SET_NULL, null=True, verbose_name="接收邮箱")
    
    sender_email = models.EmailField(verbose_name="发件人邮箱")
    sender_name = models.CharField(max_length=255, blank=True, verbose_name="发件人姓名")
    subject = models.CharField(max_length=500, verbose_name="邮件主题")
    content = models.TextField(verbose_name="邮件内容")
    html_content = models.TextField(blank=True, null=True, verbose_name="HTML内容")
    
    message_id = models.CharField(max_length=255, unique=True, verbose_name="邮件消息ID")
    in_reply_to = models.CharField(max_length=255, blank=True, null=True, verbose_name="回复的消息ID")
    references = models.TextField(blank=True, null=True, verbose_name="引用消息ID")
    
    received_at = models.DateTimeField(verbose_name="收到时间")
    processed_at = models.DateTimeField(auto_now_add=True, verbose_name="处理时间")
    email_type = models.CharField(max_length=20, choices=EmailType.choices, 
                                  default=EmailType.REPLY, verbose_name="邮件类型")
    
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    is_important = models.BooleanField(default=False, verbose_name="是否重要")
    attachments_count = models.PositiveIntegerField(default=0, verbose_name="附件数量")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        ordering = ['-received_at']
        verbose_name = "收件邮件"
        verbose_name_plural = "收件邮件"
    
    def __str__(self):
        return f"来自 {self.sender_email} - {self.subject[:50]}"


class Contact(models.Model):
    """公司联系人模型"""
    class Gender(models.TextChoices):
        MALE = 'male', '男'
        FEMALE = 'female', '女'
        OTHER = 'other', '其他'
        UNKNOWN = 'unknown', '未知'
    
    # 基本信息
    name = models.CharField(max_length=100, verbose_name="姓名", db_index=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.UNKNOWN, verbose_name="性别")
    email = models.EmailField(verbose_name="邮箱地址", db_index=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name="电话号码", db_index=True)
    position = models.CharField(max_length=100, blank=True, default="", verbose_name="职位")
    
    # 公司信息 - 改为手动输入字段
    company = models.CharField(max_length=200, verbose_name="所属公司", db_index=True, help_text="手动输入公司名称")
    
    # 附加信息
    department = models.CharField(max_length=100, blank=True, default="", verbose_name="部门")
    notes = models.TextField(blank=True, default="", verbose_name="备注")
    
    # 联系记录
    last_contact_date = models.DateTimeField(blank=True, null=True, verbose_name="最后联系时间")
    contact_frequency = models.PositiveIntegerField(default=0, verbose_name="联系次数")
    
    # 元数据
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_contacts', verbose_name="创建者")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='updated_contacts', verbose_name="最后修改者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 状态
    is_active = models.BooleanField(default=True, verbose_name="是否有效")
    
    class Meta:
        verbose_name = "联系人"
        verbose_name_plural = "联系人"
        ordering = ['-updated_at']
        unique_together = ['email', 'company']  # 同一公司内邮箱唯一
        indexes = [
            models.Index(fields=['name', 'company']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['company']),  # 为公司字段添加索引
        ]
    
    def __str__(self):
        return f"{self.name} ({self.company})"
    
    def get_full_contact_info(self):
        """获取完整联系信息"""
        info = f"{self.name}"
        if self.position:
            info += f" - {self.position}"
        if self.company:
            info += f" @ {self.company}"
        return info


class ContactGroup(models.Model):
    """联系人分组模型 - 与CandidateGroup保持一致的设计"""
    # 基本信息 - 与CandidateGroup一致
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")
    name = models.CharField(max_length=255, verbose_name="分组名称")
    description = models.TextField(blank=True, null=True, verbose_name="分组描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 多对多关系：一个联系人可以属于多个分组
    contacts = models.ManyToManyField(Contact, blank=True, related_name='contact_groups', verbose_name="分组联系人")
    
    class Meta:
        unique_together = ('user', 'name')  # 与CandidateGroup一致：同一用户的分组名称唯一
        ordering = ['name']
        verbose_name = "联系人分组"
        verbose_name_plural = "联系人分组"
    
    def __str__(self):
        return self.name
    
    def get_active_contacts(self):
        """获取分组中的有效联系人"""
        return self.contacts.filter(is_active=True)
    
    def get_contact_count(self):
        """获取分组中联系人数量"""
        return self.contacts.filter(is_active=True).count()
    get_contact_count.short_description = "联系人数量"


class ContactOperationLog(models.Model):
    """联系人操作日志模型"""
    class OperationType(models.TextChoices):
        CREATE = 'create', '新增'
        UPDATE = 'update', '修改'
        DELETE = 'delete', '删除'
        EMAIL_SENT = 'email_sent', '发送邮件'
        GROUP_ADD = 'group_add', '加入分组'
        GROUP_REMOVE = 'group_remove', '移出分组'
    
    # 操作信息
    operation_type = models.CharField(max_length=20, choices=OperationType.choices, verbose_name="操作类型")
    operation_time = models.DateTimeField(auto_now_add=True, verbose_name="操作时间", db_index=True)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="操作人")
    
    # 关联对象
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True, 
                               related_name='operation_logs', verbose_name="关联联系人")
    contact_group = models.ForeignKey(ContactGroup, on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='operation_logs', verbose_name="关联分组")
    
    # 操作详情
    operation_description = models.TextField(verbose_name="操作描述")
    old_values = models.JSONField(default=dict, blank=True, verbose_name="修改前的值")
    new_values = models.JSONField(default=dict, blank=True, verbose_name="修改后的值")
    
    # 元数据
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="操作IP")
    user_agent = models.CharField(max_length=500, blank=True, verbose_name="用户代理")
    
    class Meta:
        verbose_name = "联系人操作日志"
        verbose_name_plural = "联系人操作日志"
        ordering = ['-operation_time']
        indexes = [
            models.Index(fields=['operation_time']),
            models.Index(fields=['operator', 'operation_time']),
            models.Index(fields=['contact', 'operation_time']),
        ]
    
    def __str__(self):
        return f"{self.operator} {self.get_operation_type_display()} {self.contact or self.contact_group} - {self.operation_time.strftime('%Y-%m-%d %H:%M')}"
