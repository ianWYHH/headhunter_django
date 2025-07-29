from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (
    Job, Candidate, CandidateGroup, EmailLog, EmailAccount,
    EmailTemplate, UserSignature, Company
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
        # 从settings中获取所有AI模型提供商，并去重
        provider_choices = sorted(
            list(set((p_info['provider'], p_info['provider'].upper()) for p_key, p_info in settings.AI_MODELS.items())))
        self.fields['provider'].choices = provider_choices


class CandidateForm(forms.ModelForm):
    emails_str = forms.CharField(label="邮箱 (逗号分隔)", required=False)
    keywords_str = forms.CharField(label="关键词 (逗号分隔)", required=False)

    class Meta:
        model = Candidate
        fields = ['name', 'homepage', 'github_profile', 'linkedin_profile', 'external_id']
        labels = {'name': '姓名', 'homepage': '个人主页', 'github_profile': 'GitHub主页',
                  'linkedin_profile': '领英主页', 'external_id': '外部系统ID'}

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
    smtp_password = forms.CharField(label="密码/授权码", widget=forms.PasswordInput, required=True)

    class Meta:
        model = EmailAccount
        fields = ['email_address', 'smtp_host', 'smtp_port', 'use_ssl', 'is_default']
        labels = {'email_address': '邮箱地址', 'smtp_host': 'SMTP服务器', 'smtp_port': '端口', 'use_ssl': '使用SSL加密',
                  'is_default': '设为默认发件箱'}


class EmailComposeForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=EmailAccount.objects.none(), label="选择发件邮箱")
    subject = forms.CharField(label="邮件主题", max_length=255)
    content = forms.CharField(label="邮件内容",
                              widget=forms.Textarea(attrs={'rows': 10, 'id': 'email-content-textarea'}))
    template = forms.ModelChoiceField(queryset=EmailTemplate.objects.all(), required=False, label="选择模板",
                                      empty_label="-- 手动撰写 --")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['from_account'].queryset = EmailAccount.objects.filter(user=user)
        self.fields['from_account'].empty_label = None
        # HTMX attributes for template loading
        self.fields['template'].widget.attrs.update({
            'hx-get': '/load-template/',
            'hx-target': '#email-compose-fields',
            'hx-swap': 'innerHTML',
        })

    def clean(self):
        # Update hx-get URL with the selected template's ID
        cleaned_data = super().clean()
        template = cleaned_data.get('template')
        if template:
            self.fields['template'].widget.attrs['hx-get'] = f"/load-template/{template.id}/"
        return cleaned_data


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


class UserSignatureForm(forms.ModelForm):
    class Meta:
        model = UserSignature
        fields = ['content']
        labels = {'content': '签名内容 (支持HTML)'}
        widgets = {'content': forms.Textarea(attrs={'rows': 5})}
