from django.contrib import admin
from .models import Company, Job

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