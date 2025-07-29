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
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")
    name = models.CharField(max_length=255, db_index=True, verbose_name="姓名")
    emails = models.JSONField(default=list, blank=True, verbose_name="邮箱地址 (多个)")
    homepage = models.URLField(max_length=255, blank=True, null=True, verbose_name="个人主页")
    github_profile = models.URLField(max_length=255, blank=True, null=True, verbose_name="GitHub主页")
    linkedin_profile = models.URLField(max_length=255, blank=True, null=True, verbose_name="领英主页")
    external_id = models.BigIntegerField(blank=True, null=True, db_index=True, verbose_name="外部系统ID")
    raw_skills = models.JSONField(default=list, blank=True, verbose_name="原始技能(未处理)")
    keywords = models.JSONField(default=list, blank=True, verbose_name="标准化关键词")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    applications = models.ManyToManyField(Job, through='Application', related_name='candidates')
    groups = models.ManyToManyField(CandidateGroup, blank=True, related_name='candidates', verbose_name="所属分组")

    def __str__(self): return self.name

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
    smtp_host = models.CharField(max_length=255, verbose_name="SMTP服务器")
    smtp_port = models.PositiveIntegerField(verbose_name="端口")
    smtp_password_encrypted = models.BinaryField(verbose_name="加密后的密码/授权码")
    use_ssl = models.BooleanField(default=True, verbose_name="使用SSL")
    is_default = models.BooleanField(default=False, verbose_name="是否为默认邮箱")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self): return self.email_address

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
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="相关职位")
    group = models.ForeignKey(CandidateGroup, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="目标分组")
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

    def __str__(self): return f"Email to {self.candidate.name if self.candidate else 'N/A'} - {self.subject}"

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
    """(已更新) 邮件模板模型，所有用户共享"""
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


class UserSignature(models.Model):
    """(已更新) 用户个人邮件签名模型 (每个用户唯一)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="signature", verbose_name="所属用户")
    content = models.TextField(verbose_name="签名内容 (支持HTML)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return f"Signature for {self.user.username}"

    class Meta: verbose_name = "用户签名"; verbose_name_plural = "用户签名"
