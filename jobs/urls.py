from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # 职位管理
    path('', views.index, name='index'),
    path('jobs-list/', views.job_list_partial, name='job_list_partial'),
    path('job/<int:job_id>/', views.job_detail_view, name='job_detail'),
    path('job/<int:job_id>/delete/', views.job_delete_view, name='job_delete'),

    # 候选人管理
    path('candidates/', views.candidate_dashboard_view, name='candidate_dashboard'),
    path('candidates-list/', views.candidate_list_partial, name='candidate_list_partial'),
    path('candidate/<int:candidate_id>/', views.candidate_detail_view, name='candidate_detail'),
    path('candidate/<int:candidate_id>/delete/', views.candidate_delete_view, name='candidate_delete'),
    path('candidate/<int:candidate_id>/find-matches/', views.find_matches_view, name='find_matches'),

    # 分组管理
    path('groups/', views.group_management_view, name='group_management'),
    path('groups/<int:group_id>/', views.group_detail_view, name='group_detail'),
    path('groups/<int:group_id>/delete/', views.group_delete_view, name='group_delete'),
    path('groups/<int:group_id>/remove-candidate/<int:candidate_id>/', views.remove_candidate_from_group_view,
         name='remove_candidate_from_group'),
    path('candidates/add-to-group/', views.add_candidates_to_group_view, name='add_to_group'),

    # 邮件功能
    path('candidate/<int:candidate_id>/compose-email/', views.compose_email_view, name='compose_email'),
    path('groups/<int:group_id>/compose-email/', views.compose_group_email_view, name='compose_group_email'),
    path('candidate/<int:candidate_id>/email-history/', views.email_history_view, name='email_history'),
    path('email-log/<int:log_id>/', views.email_log_detail_view, name='email_log_detail'),
    path('email-log/<int:log_id>/save-remark/', views.save_email_remark_view, name='save_email_remark'),

    # AI 辅助功能
    path('ai/generate-email/', views.ai_generate_email_view, name='ai_generate_email'),
    path('ai/optimize-email/', views.ai_optimize_email_view, name='ai_optimize_email'),
    path('ai/generate-template/', views.ai_generate_template_view, name='ai_generate_template'), # **新增URL**

    # 任务与日志
    path('tasks/', views.task_queue_view, name='task_queue'),
    path('tasks/email/<int:log_id>/cancel/', views.cancel_email_task_view, name='cancel_email_task'),
    path('logs/', views.action_log_view, name='action_log'),

    # 邮件设置 (模板与签名)
    path('email-settings/', views.email_settings_view, name='email_settings'),
    path('email-settings/template/add/', views.add_template_view, name='add_template'),
    path('email-settings/template/<int:template_id>/edit/', views.edit_template_view, name='edit_template'),
    path('email-settings/template/<int:template_id>/delete/', views.delete_template_view, name='delete_template'),

    # 邮箱账户管理
    path('email-accounts/', views.email_account_list_view, name='email_account_management'),
    path('email-accounts/add/', views.email_account_add_view, name='email_account_add'),
    path('email-accounts/<int:account_id>/edit/', views.email_account_edit_view, name='email_account_edit'),
    path('email-accounts/<int:account_id>/delete/', views.email_account_delete_view, name='email_account_delete'),

    # API密钥管理
    path('keys/', views.api_key_management_view, name='api_key_management'),
    path('keys/<int:key_id>/delete/', views.api_key_delete_view, name='api_key_delete'),

    # AI解析流程
    path('preview-jobs/', views.preview_jobs_view, name='preview_jobs'),
    path('preview-candidates/', views.preview_candidates_view, name='preview_candidates'),
    path('parse-jobs/', views.parse_and_show_jobs_view, name='parse_jobs'),
    path('parse-candidates/', views.parse_and_show_candidates_view, name='parse_candidates'),
    path('save-parsed-jobs/', views.save_parsed_jobs_view, name='save_jobs'),
    path('save-parsed-candidates/', views.save_parsed_candidates_view, name='save_candidates'),

    # 模板加载功能
    path('load-template/', views.load_template_view, name='load_template'),
]
