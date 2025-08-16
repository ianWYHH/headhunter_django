from django.contrib import admin
from .models import (
    Company, Job, Candidate, ScheduledEmailTask, 
    EmailAccount, EmailAccountStats, IncomingEmail, EmailLog, EmailTemplate,
    Contact, ContactGroup, ContactOperationLog
)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'status', 'updated_at')
    list_filter = ('status', 'company')
    search_fields = ('title', 'company__name', 'job_description')
    autocomplete_fields = ('company',) # 方便地搜索公司

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'predicted_position', 'location', 'education_level', 'updated_at')
    list_filter = ('gender', 'education_level', 'predicted_position')
    search_fields = ('name', 'emails', 'predicted_position', 'location')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ScheduledEmailTask)
class ScheduledEmailTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'group', 'schedule_type', 'status', 'is_enabled', 'next_run_time', 'created_at')
    list_filter = ('schedule_type', 'status', 'is_enabled', 'user')
    search_fields = ('name', 'user__username', 'group__name')
    readonly_fields = ('last_run_time', 'next_run_time', 'total_executions', 'successful_executions', 'failed_executions', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'name', 'description')
        }),
        ('任务配置', {
            'fields': ('group', 'template', 'from_account')
        }),
        ('调度设置', {
            'fields': ('schedule_type', 'start_time', 'end_time', 'schedule_config')
        }),
        ('任务状态', {
            'fields': ('status', 'is_enabled', 'last_run_time', 'next_run_time')
        }),
        ('执行统计', {
            'fields': ('total_executions', 'successful_executions', 'failed_executions')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ('email_address', 'user', 'is_default', 'daily_send_limit', 'created_at')
    list_filter = ('is_default', 'use_ssl', 'imap_use_ssl', 'user')
    search_fields = ('email_address', 'user__username', 'smtp_host', 'imap_host')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'email_address', 'is_default', 'signature')
        }),
        ('发送配置', {
            'fields': ('daily_send_limit', 'smtp_host', 'smtp_port', 'use_ssl')
        }),
        ('收信配置', {
            'fields': ('imap_host', 'imap_port', 'imap_use_ssl'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(EmailAccountStats)
class EmailAccountStatsAdmin(admin.ModelAdmin):
    list_display = ('email_account', 'date', 'sent_count', 'failed_count', 'remaining_quota', 'last_updated')
    list_filter = ('date', 'email_account__user', 'email_account')
    search_fields = ('email_account__email_address',)
    readonly_fields = ('last_updated',)
    date_hierarchy = 'date'
    ordering = ['-date', 'email_account']
    
    def remaining_quota(self, obj):
        return obj.remaining_quota
    remaining_quota.short_description = '剩余额度'


@admin.register(IncomingEmail)
class IncomingEmailAdmin(admin.ModelAdmin):
    list_display = ('sender_email', 'subject_short', 'candidate', 'received_account', 'email_type', 'is_read', 'received_at')
    list_filter = ('email_type', 'is_read', 'is_important', 'received_account', 'received_at')
    search_fields = ('sender_email', 'sender_name', 'subject', 'content')
    readonly_fields = ('message_id', 'processed_at', 'received_at', 'created_at')
    date_hierarchy = 'received_at'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('candidate', 'original_email_log', 'received_account')
        }),
        ('发件人信息', {
            'fields': ('sender_email', 'sender_name')
        }),
        ('邮件内容', {
            'fields': ('subject', 'content', 'html_content')
        }),
        ('邮件元数据', {
            'fields': ('message_id', 'in_reply_to', 'references', 'email_type'),
            'classes': ('collapse',)
        }),
        ('状态信息', {
            'fields': ('is_read', 'is_important', 'attachments_count')
        }),
        ('时间信息', {
            'fields': ('received_at', 'processed_at', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def subject_short(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_short.short_description = '邮件主题'


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'subject_short', 'from_account', 'status', 'trigger_type', 'sent_at')
    list_filter = ('status', 'trigger_type', 'from_account', 'sent_at')
    search_fields = ('candidate__name', 'subject', 'content', 'from_account__email_address')
    readonly_fields = ('sent_at', 'message_id')
    date_hierarchy = 'sent_at'
    
    def candidate_name(self, obj):
        return obj.candidate.name if obj.candidate else 'N/A'
    candidate_name.short_description = '候选人'
    
    def subject_short(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_short.short_description = '邮件主题'


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'tags', 'created_by', 'updated_at')
    list_filter = ('created_by', 'updated_by', 'created_at')
    search_fields = ('name', 'subject', 'body', 'tags')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'tags', 'created_by', 'updated_by')
        }),
        ('邮件内容', {
            'fields': ('subject', 'body')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'group', 'template', 'from_account')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'email', 'phone', 'position', 'company', 
        'department', 'is_active', 'contact_frequency', 'updated_at'
    )
    list_filter = (
        'gender', 'is_active', 'created_at', 'updated_at'
    )
    search_fields = (
        'name', 'email', 'phone', 'position', 'department', 'company'
    )
    readonly_fields = (
        'contact_frequency', 'last_contact_date', 'created_by', 'updated_by',
        'created_at', 'updated_at'
    )
    raw_id_fields = ('created_by', 'updated_by')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'gender', 'email', 'phone')
        }),
        ('工作信息', {
            'fields': ('company', 'position', 'department')
        }),
        ('附加信息', {
            'fields': ('notes', 'is_active')
        }),
        ('联系记录', {
            'fields': ('last_contact_date', 'contact_frequency'),
            'classes': ('collapse',)
        }),
        ('元数据', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        """批量激活联系人"""
        updated = queryset.update(is_active=True, updated_by=request.user)
        self.message_user(request, f'成功激活 {updated} 个联系人')
    make_active.short_description = "激活选中的联系人"
    
    def make_inactive(self, request, queryset):
        """批量停用联系人"""
        updated = queryset.update(is_active=False, updated_by=request.user)
        self.message_user(request, f'成功停用 {updated} 个联系人')
    make_inactive.short_description = "停用选中的联系人"
    
    def save_model(self, request, obj, form, change):
        """保存时自动设置操作者"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ContactGroup)
class ContactGroupAdmin(admin.ModelAdmin):
    """联系人分组管理 - 与CandidateGroup保持一致的简化设计"""
    list_display = ('name', 'user', 'get_contact_count', 'created_at', 'updated_at')
    list_filter = ('user', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('contacts',)
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'user')
        }),
        ('联系人管理', {
            'fields': ('contacts',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_contact_count(self, obj):
        """获取分组中联系人数量"""
        return obj.contacts.filter(is_active=True).count()
    get_contact_count.short_description = "联系人数量"


@admin.register(ContactOperationLog)
class ContactOperationLogAdmin(admin.ModelAdmin):
    list_display = (
        'operation_type', 'operator', 'get_target_name', 'operation_time', 'ip_address'
    )
    list_filter = (
        'operation_type', 'operation_time', 'operator'
    )
    search_fields = (
        'operation_description', 'contact__name', 'contact_group__name', 'operator__username'
    )
    readonly_fields = (
        'operation_type', 'operation_time', 'operator', 'contact', 'contact_group',
        'operation_description', 'old_values', 'new_values', 'ip_address', 'user_agent'
    )
    date_hierarchy = 'operation_time'
    
    fieldsets = (
        ('操作信息', {
            'fields': ('operation_type', 'operation_time', 'operator')
        }),
        ('关联对象', {
            'fields': ('contact', 'contact_group')
        }),
        ('操作详情', {
            'fields': ('operation_description', 'old_values', 'new_values')
        }),
        ('请求信息', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def get_target_name(self, obj):
        """获取操作目标名称"""
        if obj.contact:
            return f"联系人: {obj.contact.name}"
        elif obj.contact_group:
            return f"分组: {obj.contact_group.name}"
        return "无"
    get_target_name.short_description = "操作目标"
    
    def has_add_permission(self, request):
        """禁止手动添加日志"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改日志"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """只允许超级用户删除日志"""
        return request.user.is_superuser