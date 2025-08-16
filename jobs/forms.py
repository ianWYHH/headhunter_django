from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (
    Job, Candidate, CandidateGroup, EmailLog, EmailAccount,
    EmailTemplate, Company, ScheduledEmailTask, IncomingEmail,
    Contact, ContactGroup, ContactOperationLog
)


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': '用户名'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': '密码'})


class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fieldname in self.fields:
            self.fields[fieldname].widget.attrs.update({'class': 'form-control'})


class JobForm(forms.ModelForm):
    company_name = forms.CharField(label="公司名称", max_length=255)
    level_set_str = forms.CharField(label="职级 (逗号分隔)", required=False)
    locations_str = forms.CharField(label="地点 (逗号分隔)", required=False)
    keywords_str = forms.CharField(label="标准化关键词 (逗号分隔)", required=False)

    class Meta:
        model = Job
        fields = ['title', 'company_name', 'department', 'salary_range', 'status', 'job_description', 'job_requirement',
                  'notes']
        labels = {'title': '职位名称', 'department': '所属部门', 'salary_range': '薪资范围', 'status': '职位状态',
                  'job_description': '职位描述', 'job_requirement': '职位要求', 'notes': '备注'}
        widgets = {'job_description': forms.Textarea(attrs={'rows': 5}),
                   'job_requirement': forms.Textarea(attrs={'rows': 5}), 'notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['company_name'].initial = self.instance.company.name
            self.fields['level_set_str'].initial = ', '.join(self.instance.level_set or [])
            self.fields['locations_str'].initial = ', '.join(self.instance.locations or [])
            self.fields['keywords_str'].initial = ', '.join(self.instance.keywords or [])

    def save(self, commit=True):
        company_name = self.cleaned_data.get('company_name')
        company, _ = Company.objects.get_or_create(name=company_name)
        self.instance.company = company
        self.instance.level_set = [s.strip() for s in self.cleaned_data.get('level_set_str', '').split(',') if
                                   s.strip()]
        self.instance.locations = [s.strip() for s in self.cleaned_data.get('locations_str', '').split(',') if
                                   s.strip()]
        self.instance.keywords = [s.strip() for s in self.cleaned_data.get('keywords_str', '').split(',') if s.strip()]
        return super().save(commit=commit)


class JobParseForm(forms.Form):
    file_upload = forms.FileField(label="上传文件 (TXT, XLSX, DOCX)", required=False)
    text_content = forms.CharField(label="或 粘贴职位描述", widget=forms.Textarea, required=False)

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("file_upload") and not cleaned_data.get("text_content"): raise forms.ValidationError(
            "请至少提供文件或文本内容中的一项。")
        return cleaned_data


class CandidateParseForm(forms.Form):
    file_upload = forms.FileField(label="上传简历文件 (TXT, XLSX, DOCX)", required=False)
    text_content = forms.CharField(label="或 粘贴简历原文", widget=forms.Textarea, required=False)

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("file_upload") and not cleaned_data.get("text_content"): raise forms.ValidationError(
            "请至少提供文件或文本内容中的一项。")
        return cleaned_data


class ApiKeyForm(forms.Form):
    provider = forms.ChoiceField(label="服务商")
    api_key = forms.CharField(label="API Key", widget=forms.TextInput(attrs={'autocomplete': 'off'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        provider_choices = sorted(
            list(set((p_info['provider'], p_info['provider'].upper()) for p_key, p_info in settings.AI_MODELS.items())))
        self.fields['provider'].choices = provider_choices


class CandidateForm(forms.ModelForm):
    emails_str = forms.CharField(label="邮箱 (逗号分隔)", required=False)
    keywords_str = forms.CharField(label="关键词 (逗号分隔)", required=False)

    class Meta:
        model = Candidate
        fields = ['name', 'emails_str', 'homepage', 'github_profile', 'linkedin_profile', 'external_id', 
                  'birthday', 'gender', 'location', 'education_level', 'predicted_position', 'keywords_str']
        labels = {'name': '姓名', 'homepage': '个人主页', 'github_profile': 'GitHub主页',
                  'linkedin_profile': '领英主页', 'external_id': '外部系统ID',
                  'birthday': '出生年月日', 'gender': '性别', 'location': '所在地', 'education_level': '最高学历', 'predicted_position': 'AI预测职位'}
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '如：北京、上海、深圳'}),
            'education_level': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['emails_str'].initial = ', '.join(self.instance.emails or [])
            self.fields['keywords_str'].initial = ', '.join(self.instance.keywords or [])

    def save(self, commit=True):
        self.instance.emails = [s.strip() for s in self.cleaned_data.get('emails_str', '').split(',') if s.strip()]
        self.instance.keywords = [s.strip() for s in self.cleaned_data.get('keywords_str', '').split(',') if s.strip()]
        return super().save(commit=commit)


class CandidateGroupForm(forms.ModelForm):
    class Meta:
        model = CandidateGroup
        fields = ['name', 'description']
        labels = {'name': '分组名称', 'description': '分组描述'}
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class EmailAccountForm(forms.ModelForm):
    # **核心改动**: 将密码字段设为非必填，以便在编辑时无需重新输入
    smtp_password = forms.CharField(
        label="密码/授权码",
        widget=forms.PasswordInput(render_value=False), # Don't show password value for security
        required=False,
        help_text="新建账户时必填。编辑时留空表示不修改现有密码。"
    )

    class Meta:
        model = EmailAccount
        # **核心改动**: 加入所有新字段
        fields = [
            'email_address', 'sender_name', 'is_default', 'signature', 'daily_send_limit',
            'smtp_host', 'smtp_port', 'use_ssl',
            'imap_host', 'imap_port', 'imap_use_ssl'
        ]
        labels = {
            'email_address': '邮箱地址', 'sender_name': '发件人姓名', 'is_default': '设为默认发件箱',
            'signature': '邮箱签名 (支持HTML)', 'daily_send_limit': '每日发送上限',
            'smtp_host': 'SMTP服务器', 'smtp_port': 'SMTP端口', 'use_ssl': 'SMTP使用SSL',
            'imap_host': 'IMAP服务器', 'imap_port': 'IMAP端口', 'imap_use_ssl': 'IMAP使用SSL'
        }
        widgets = {
            'signature': forms.Textarea(attrs={'rows': 5}),
            'email_address': forms.EmailInput(attrs={'class': 'form-control'}),
            'sender_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例如：张三'}),
            'smtp_host': forms.TextInput(attrs={'class': 'form-control'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 65535}),
            'daily_send_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'imap_host': forms.TextInput(attrs={'class': 'form-control'}),
            'imap_port': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 65535}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing an existing instance, make password optional
        if self.instance and self.instance.pk:
            self.fields['smtp_password'].help_text = "留空表示不修改现有密码。"
        else:
            # For new accounts, password is required
            self.fields['smtp_password'].required = True
            self.fields['smtp_password'].help_text = "请输入邮箱密码或授权码。"
    
    def clean_smtp_password(self):
        """Validate password field based on whether this is creation or editing"""
        password = self.cleaned_data.get('smtp_password')
        
        # For new accounts, password is required
        if not self.instance.pk and not password:
            raise forms.ValidationError("新建邮箱账户时必须提供密码/授权码。")
        
        return password
    
    def clean_email_address(self):
        """Ensure email address is unique for this user"""
        email = self.cleaned_data.get('email_address')
        if email:
            # Check for duplicates, excluding current instance if editing
            existing = EmailAccount.objects.filter(email_address=email)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError("该邮箱地址已被使用。")
        
        return email


class EmailComposeForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=EmailAccount.objects.none(), label="选择发件邮箱")
    subject = forms.CharField(label="邮件主题", max_length=255)
    content = forms.CharField(label="邮件内容",
                              widget=forms.Textarea(attrs={'rows': 10, 'id': 'email-content-textarea'}))
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.all(),
        required=False,
        label="选择模板",
        empty_label="-- 手动撰写 --",
        # **核心修复**: 移除动态属性，改为在模板中直接设置
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['from_account'].queryset = EmailAccount.objects.filter(user=user)
        self.fields['from_account'].empty_label = None


class EmailRemarkForm(forms.ModelForm):
    class Meta:
        model = EmailLog
        fields = ['remarks']
        labels = {'remarks': ''}
        widgets = {'remarks': forms.Textarea(attrs={'rows': 3, 'placeholder': '添加或修改备注...'})}


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['name', 'tags', 'subject', 'body']
        labels = {'name': '模板名称', 'tags': '标签 (逗号分隔)', 'subject': '邮件主题', 'body': '邮件正文'}
        widgets = {'body': forms.Textarea(attrs={'rows': 12})}


class MultiEmailSendForm(forms.Form):
    """多邮箱批量发送表单"""
    candidate_group = forms.ModelChoiceField(
        queryset=CandidateGroup.objects.all(),  # 先设置为all，在__init__中过滤
        label="候选人分组",
        help_text="选择要发送邮件的候选人分组",
        empty_label="-- 请选择分组 --"
    )
    
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.all(),
        label="邮件模板",
        help_text="选择要使用的邮件模板",
        empty_label="-- 请选择模板 --"
    )
    
    SEND_MODE_CHOICES = [
        ('auto_multi', '自动分配多邮箱轮流发送'),
        ('selected_accounts', '选择指定邮箱发送'),
        ('single_account', '使用单个邮箱发送'),
    ]
    
    send_mode = forms.ChoiceField(
        choices=SEND_MODE_CHOICES,
        widget=forms.RadioSelect,
        label="发送模式",
        initial='auto_multi',
        help_text="选择邮件发送方式"
    )
    
    selected_accounts = forms.ModelMultipleChoiceField(
        queryset=EmailAccount.objects.all(),  # 先设置为all，在__init__中过滤
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="选择邮箱账户",
        help_text="选择要使用的邮箱账户（多选）"
    )
    
    single_account = forms.ModelChoiceField(
        queryset=EmailAccount.objects.all(),  # 先设置为all，在__init__中过滤
        required=False,
        label="单个发送邮箱",
        help_text="选择单个邮箱进行发送",
        empty_label="-- 请选择邮箱 --"
    )
    
    send_immediately = forms.BooleanField(
        required=False,
        initial=True,
        label="立即发送",
        help_text="取消勾选可稍后手动触发发送"
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 设置用户相关的查询集
        self.fields['candidate_group'].queryset = CandidateGroup.objects.filter(user=user)
        user_accounts = EmailAccount.objects.filter(user=user)
        self.fields['selected_accounts'].queryset = user_accounts
        self.fields['single_account'].queryset = user_accounts
        
        # 如果用户只有一个邮箱，默认选择单邮箱模式
        if user_accounts.count() <= 1:
            self.fields['send_mode'].initial = 'single_account'
        
    def clean(self):
        cleaned_data = super().clean()
        send_mode = cleaned_data.get('send_mode')
        selected_accounts = cleaned_data.get('selected_accounts')
        single_account = cleaned_data.get('single_account')
        
        if send_mode == 'selected_accounts' and not selected_accounts:
            raise forms.ValidationError("选择指定邮箱模式时，必须至少选择一个邮箱账户")
        
        if send_mode == 'single_account' and not single_account:
            raise forms.ValidationError("选择单邮箱模式时，必须指定一个邮箱账户")
        
        return cleaned_data


class EmailAccountStatsForm(forms.Form):
    """邮箱统计查询表单"""
    email_account = forms.ModelChoiceField(
        queryset=EmailAccount.objects.none(),
        required=False,
        label="邮箱账户",
        empty_label="-- 全部邮箱 --"
    )
    
    date_from = forms.DateField(
        required=False,
        label="开始日期",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        required=False,
        label="结束日期", 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email_account'].queryset = EmailAccount.objects.filter(user=user)


class IncomingEmailFilterForm(forms.Form):
    """收件邮件筛选表单"""
    received_account = forms.ModelChoiceField(
        queryset=EmailAccount.objects.none(),
        required=False,
        label="接收邮箱",
        empty_label="-- 全部邮箱 --"
    )
    
    candidate = forms.ModelChoiceField(
        queryset=Candidate.objects.none(),
        required=False,
        label="候选人",
        empty_label="-- 全部候选人 --"
    )
    
    email_type = forms.ChoiceField(
        choices=[('', '-- 全部类型 --')] + IncomingEmail.EmailType.choices,
        required=False,
        label="邮件类型"
    )
    
    is_read = forms.ChoiceField(
        choices=[('', '-- 全部 --'), ('false', '未读'), ('true', '已读')],
        required=False,
        label="阅读状态"
    )
    
    date_from = forms.DateField(
        required=False,
        label="开始日期",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        required=False,
        label="结束日期",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['received_account'].queryset = EmailAccount.objects.filter(user=user)
        self.fields['candidate'].queryset = Candidate.objects.filter(user=user)


class ScheduledEmailTaskForm(forms.ModelForm):
    """定时邮件任务表单"""
    
    # 自定义字段用于前端交互
    schedule_type_display = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.HiddenInput()
    )
    
    # 周几选择（用于每周调度）
    weekdays = forms.MultipleChoiceField(
        choices=[
            (0, '周一'), (1, '周二'), (2, '周三'), (3, '周四'),
            (4, '周五'), (5, '周六'), (6, '周日')
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        help_text="选择每周执行的时间"
    )
    
    # 每月几号（用于每月调度）
    day_of_month = forms.IntegerField(
        min_value=1,
        max_value=31,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="选择每月执行的日期（1-31）"
    )
    
    # 多邮箱选择字段
    use_multi_accounts = forms.BooleanField(
        required=False,
        initial=False,
        label="使用多邮箱发送",
        help_text="勾选后可选择多个邮箱轮流发送，避免单个邮箱限制"
    )
    
    selected_accounts = forms.ModelMultipleChoiceField(
        queryset=EmailAccount.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="选择邮箱账户",
        help_text="选择要使用的邮箱账户（多选）"
    )
    
    # 目标类型选择
    target_type = forms.ChoiceField(
        choices=ScheduledEmailTask.TargetType.choices,
        initial=ScheduledEmailTask.TargetType.CANDIDATE_GROUP,
        label="目标类型",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'target-type-select'})
    )
    
    # 覆盖字段定义以确保正确的初始化
    group = forms.ModelChoiceField(
        queryset=CandidateGroup.objects.all(),  # 先设置为all，在__init__中过滤
        label="候选人分组",
        empty_label="-- 请选择候选人分组 --",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    contact_group = forms.ModelChoiceField(
        queryset=ContactGroup.objects.all(),
        label="联系人分组", 
        empty_label="-- 请选择联系人分组 --",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.all(),
        label="邮件模板", 
        empty_label="-- 请选择模板 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    from_account = forms.ModelChoiceField(
        queryset=EmailAccount.objects.all(),  # 先设置为all，在__init__中过滤
        label="发件邮箱",
        empty_label="-- 请选择邮箱 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ScheduledEmailTask
        fields = [
            'name', 'target_type', 'group', 'contact_group', 'template', 'from_account', 'schedule_type',
            'start_time', 'end_time', 'description', 'is_enabled'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'schedule_type': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_time': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': '任务名称',
            'schedule_type': '调度类型',
            'start_time': '开始时间',
            'end_time': '结束时间（可选）',
            'description': '任务描述',
            'is_enabled': '是否启用',
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if user:
            # 限制用户只能看到自己的分组、模板和邮箱
            self.fields['group'].queryset = CandidateGroup.objects.filter(user=user)
            self.fields['contact_group'].queryset = ContactGroup.objects.filter(user=user)
            self.fields['template'].queryset = EmailTemplate.objects.all()  # 模板是全局的
            user_accounts = EmailAccount.objects.filter(user=user)
            self.fields['from_account'].queryset = user_accounts
            self.fields['selected_accounts'].queryset = user_accounts
        
        # 设置初始值
        if self.instance.pk:
            if self.instance.schedule_type == ScheduledEmailTask.ScheduleType.WEEKLY:
                self.fields['weekdays'].initial = self.instance.schedule_config.get('weekdays', [])
            elif self.instance.schedule_type == ScheduledEmailTask.ScheduleType.MONTHLY:
                self.fields['day_of_month'].initial = self.instance.schedule_config.get('day_of_month', 1)
            
            # 设置多邮箱字段的初始值
            self.fields['use_multi_accounts'].initial = self.instance.use_multi_accounts
            if self.instance.use_multi_accounts:
                self.fields['selected_accounts'].initial = self.instance.selected_accounts.all()
    
    def clean(self):
        cleaned_data = super().clean()
        schedule_type = cleaned_data.get('schedule_type')
        target_type = cleaned_data.get('target_type')
        group = cleaned_data.get('group')
        contact_group = cleaned_data.get('contact_group')
        
        # 验证目标分组
        if target_type == ScheduledEmailTask.TargetType.CANDIDATE_GROUP:
            if not group:
                raise forms.ValidationError({'group': '选择候选人分组时，必须指定候选人分组'})
            if contact_group:
                raise forms.ValidationError({'contact_group': '选择候选人分组时，不能同时指定联系人分组'})
        elif target_type == ScheduledEmailTask.TargetType.CONTACT_GROUP:
            if not contact_group:
                raise forms.ValidationError({'contact_group': '选择联系人分组时，必须指定联系人分组'})
            if group:
                raise forms.ValidationError({'group': '选择联系人分组时，不能同时指定候选人分组'})
        
        # 验证每周调度的配置
        if schedule_type == ScheduledEmailTask.ScheduleType.WEEKLY:
            weekdays = cleaned_data.get('weekdays')
            if not weekdays:
                raise forms.ValidationError("每周调度必须选择至少一个工作日")
            cleaned_data['schedule_config'] = {'weekdays': weekdays}
        
        # 验证每月调度的配置
        elif schedule_type == ScheduledEmailTask.ScheduleType.MONTHLY:
            day_of_month = cleaned_data.get('day_of_month')
            if not day_of_month:
                raise forms.ValidationError("每月调度必须指定日期")
            if day_of_month < 1 or day_of_month > 31:
                raise forms.ValidationError("每月调度日期必须在1-31之间")
            cleaned_data['schedule_config'] = {'day_of_month': day_of_month}
        
        # 验证时间范围
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # 验证开始时间不能是过去时间（除非是编辑现有任务）
        if start_time and not self.instance.pk:
            from django.utils import timezone
            if start_time <= timezone.now():
                raise forms.ValidationError("开始时间不能设置为过去时间")
        
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError("结束时间必须晚于开始时间")
        
        # 验证邮箱选择
        use_multi_accounts = cleaned_data.get('use_multi_accounts')
        selected_accounts = cleaned_data.get('selected_accounts')
        from_account = cleaned_data.get('from_account')
        
        if use_multi_accounts:
            if not selected_accounts:
                raise forms.ValidationError("使用多邮箱发送时，必须至少选择一个邮箱账户")
        else:
            if not from_account:
                raise forms.ValidationError("使用单邮箱发送时，必须选择一个发件邮箱")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 设置调度配置
        if self.cleaned_data.get('schedule_type') == ScheduledEmailTask.ScheduleType.WEEKLY:
            instance.schedule_config = {'weekdays': self.cleaned_data.get('weekdays', [])}
        elif self.cleaned_data.get('schedule_type') == ScheduledEmailTask.ScheduleType.MONTHLY:
            instance.schedule_config = {'day_of_month': self.cleaned_data.get('day_of_month', 1)}
        else:
            instance.schedule_config = {}
        
        # 设置多邮箱配置
        instance.use_multi_accounts = self.cleaned_data.get('use_multi_accounts', False)
        
        if commit:
            instance.save()
            # 处理多对多关系
            if instance.use_multi_accounts:
                selected_accounts = self.cleaned_data.get('selected_accounts', [])
                instance.selected_accounts.set(selected_accounts)
            else:
                instance.selected_accounts.clear()
        
        return instance


class ContactForm(forms.ModelForm):
    """联系人表单"""
    
    class Meta:
        model = Contact
        fields = [
            'name', 'gender', 'email', 'phone', 'position', 'company', 
            'department', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入姓名'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '请输入邮箱地址'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入电话号码'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入职位'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入公司名称'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入部门'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '请输入备注信息'}),
        }
        labels = {
            'name': '姓名',
            'gender': '性别', 
            'email': '邮箱地址',
            'phone': '电话号码',
            'position': '职位',
            'company': '所属公司',
            'department': '部门',
            'notes': '备注',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 设置必填字段标识
        for field_name in ['name', 'email', 'company']:
            self.fields[field_name].required = True
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        company = self.cleaned_data.get('company')
        
        if email and company:
            # 检查同一公司内邮箱是否重复
            existing = Contact.objects.filter(email=email, company=company)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError(f"该邮箱在 {company} 公司已存在")
        
        return email
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 设置创建者和更新者
        if self.user:
            if not instance.pk:  # 新建
                instance.created_by = self.user
            instance.updated_by = self.user
        
        if commit:
            instance.save()
        
        return instance


class ContactGroupForm(forms.ModelForm):
    """联系人分组表单"""
    
    selected_contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="选择联系人",
        help_text="选择要加入此分组的联系人"
    )
    
    class Meta:
        model = ContactGroup
        fields = ['name', 'description']
        labels = {'name': '分组名称', 'description': '分组描述'}
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 设置联系人选项
        self.fields['selected_contacts'].queryset = Contact.objects.filter(is_active=True).order_by('company', 'name')
        
        # 如果是编辑模式，设置已选择的联系人
        if self.instance.pk:
            self.fields['selected_contacts'].initial = self.instance.contacts.all()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 设置创建者 - 与CandidateGroupForm保持一致
        if not instance.pk and self.user:
            instance.user = self.user
        
        if commit:
            instance.save()
            # 处理多对多关系
            selected_contacts = self.cleaned_data.get('selected_contacts', [])
            instance.contacts.set(selected_contacts)
        
        return instance


class ContactSearchForm(forms.Form):
    """联系人搜索表单"""
    
    search_query = forms.CharField(
        max_length=200,
        required=False,
        label="搜索关键词",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜索姓名、邮箱、电话或公司名称...',
            'id': 'search-input'
        })
    )
    
    company = forms.CharField(
        max_length=200,
        required=False,
        label="筛选公司",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入公司名称'})
    )
    
    position = forms.CharField(
        max_length=100,
        required=False,
        label="职位",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入职位关键词'})
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        label="部门",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入部门关键词'})
    )
    
    contact_group = forms.ModelChoiceField(
        queryset=ContactGroup.objects.all(),
        required=False,
        label="所属分组",
        empty_label="-- 全部分组 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_active = forms.ChoiceField(
        choices=[('', '-- 全部状态 --'), ('true', '有效'), ('false', '无效')],
        required=False,
        label="状态筛选",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['contact_group'].queryset = ContactGroup.objects.filter(user=user).order_by('name')
        else:
            self.fields['contact_group'].queryset = ContactGroup.objects.order_by('name')


class ContactEmailForm(forms.Form):
    """给联系人发送邮件的表单"""
    
    contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="选择联系人",
        help_text="选择要发送邮件的联系人"
    )
    
    contact_groups = forms.ModelMultipleChoiceField(
        queryset=ContactGroup.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="选择分组",
        help_text="选择要发送邮件的联系人分组"
    )
    
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.none(),
        required=False,
        label="邮件模板",
        empty_label="-- 选择模板或手动编写 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    subject = forms.CharField(
        max_length=255,
        label="邮件主题",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入邮件主题'})
    )
    
    content = forms.CharField(
        label="邮件内容",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 12,
            'placeholder': '请输入邮件内容...',
            'id': 'email-content-textarea'
        })
    )
    
    from_account = forms.ModelChoiceField(
        queryset=EmailAccount.objects.none(),
        label="发件邮箱",
        empty_label="-- 请选择发件邮箱 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    send_immediately = forms.BooleanField(
        required=False,
        initial=True,
        label="立即发送",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 设置用户相关的查询集
        self.fields['contacts'].queryset = Contact.objects.filter(is_active=True).order_by('company', 'name')
        self.fields['contact_groups'].queryset = ContactGroup.objects.filter(user=user).order_by('name')
        self.fields['template'].queryset = EmailTemplate.objects.all().order_by('name')
        self.fields['from_account'].queryset = EmailAccount.objects.filter(user=user)
    
    def clean(self):
        cleaned_data = super().clean()
        contacts = cleaned_data.get('contacts')
        contact_groups = cleaned_data.get('contact_groups')
        
        if not contacts and not contact_groups:
            raise forms.ValidationError("请至少选择一个联系人或一个分组")
        
        return cleaned_data


class UnifiedEmailSendForm(forms.Form):
    """统一的邮件发送表单 - 支持候选人和联系人"""
    
    SEND_TYPE_CHOICES = [
        ('candidate_group', '候选人分组'),
        ('contact_group', '联系人分组'),
    ]
    
    send_type = forms.ChoiceField(
        choices=SEND_TYPE_CHOICES,
        label="发送类型",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    # 候选人分组
    candidate_group = forms.ModelChoiceField(
        queryset=CandidateGroup.objects.none(),
        required=False,
        label="候选人分组",
        empty_label="-- 选择候选人分组 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # 选定候选人
    selected_candidates = forms.ModelMultipleChoiceField(
        queryset=Candidate.objects.none(),
        required=False,
        label="选择候选人",
        widget=forms.CheckboxSelectMultiple
    )
    
    # 联系人分组
    contact_group = forms.ModelChoiceField(
        queryset=ContactGroup.objects.none(),
        required=False,
        label="联系人分组",
        empty_label="-- 选择联系人分组 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # 选定联系人
    selected_contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.none(),
        required=False,
        label="选择联系人",
        widget=forms.CheckboxSelectMultiple
    )
    
    # 邮件模板
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.none(),
        required=False,
        label="邮件模板",
        empty_label="-- 选择模板或手动编写 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # 邮件主题
    subject = forms.CharField(
        max_length=255,
        label="邮件主题",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入邮件主题'})
    )
    
    # 邮件内容
    content = forms.CharField(
        label="邮件内容",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 12,
            'placeholder': '请输入邮件内容...',
            'id': 'unified-email-content-textarea'
        })
    )
    
    # 发件邮箱
    from_account = forms.ModelChoiceField(
        queryset=EmailAccount.objects.none(),
        label="发件邮箱",
        empty_label="-- 请选择发件邮箱 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # 立即发送
    send_immediately = forms.BooleanField(
        required=False,
        initial=True,
        label="立即发送",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 设置用户相关的查询集
        self.fields['candidate_group'].queryset = CandidateGroup.objects.filter(user=user).order_by('name')
        self.fields['selected_candidates'].queryset = Candidate.objects.all().order_by('name')
        self.fields['contact_group'].queryset = ContactGroup.objects.filter(user=user).order_by('name')
        self.fields['selected_contacts'].queryset = Contact.objects.filter(is_active=True).order_by('company', 'name')
        self.fields['template'].queryset = EmailTemplate.objects.all().order_by('name')
        self.fields['from_account'].queryset = EmailAccount.objects.filter(user=user)
    
    def clean(self):
        cleaned_data = super().clean()
        send_type = cleaned_data.get('send_type')
        
        # 根据发送类型验证相应字段
        if send_type == 'candidate_group':
            if not cleaned_data.get('candidate_group'):
                raise forms.ValidationError("请选择候选人分组")
        elif send_type == 'contact_group':
            if not cleaned_data.get('contact_group'):
                raise forms.ValidationError("请选择联系人分组")
        
        # 验证立即发送时必须选择发件邮箱
        if cleaned_data.get('send_immediately') and not cleaned_data.get('from_account'):
            raise forms.ValidationError("立即发送时必须选择发件邮箱")
        
        return cleaned_data

