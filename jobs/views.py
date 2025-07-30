import json
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db.models import Q, Count
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, JsonResponse
from django.conf import settings
from django.core.paginator import Paginator

from .models import (
    Job, Company, ApiKey, Candidate, CandidateGroup, EmailLog, EmailAccount,
    ActionLog, EmailTemplate
)
from .forms import (
    JobForm, JobParseForm, ApiKeyForm, CandidateForm,
    CandidateParseForm, CandidateGroupForm, EmailComposeForm, EmailRemarkForm,
    CustomAuthenticationForm, CustomUserCreationForm, EmailAccountForm,
    EmailTemplateForm
)
from .services import parsing_service, matching_service, mailing_service, logging_service, ai_service
from .utils import encrypt_key


# --- 用户认证视图 ---
def login_view(request):
    if request.user.is_authenticated: return redirect('jobs:index')
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username');
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user);
                logging_service.create_log(user, "用户登录");
                return redirect('jobs:index')
            else:
                messages.error(request, "用户名或密码无效。")
        else:
            messages.error(request, "用户名或密码无效。")
    form = CustomAuthenticationForm();
    return render(request, 'jobs/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated: return redirect('jobs:index')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save();
            login(request, user)
            logging_service.create_log(user, "新用户注册并登录");
            messages.success(request, "注册成功！")
            return redirect('jobs:index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'jobs/register.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        logging_service.create_log(request.user, "用户登出");
        logout(request)
    return redirect('login')


# --- 职位管理视图 ---
@login_required
def index(request):
    context = {'companies': Company.objects.all(), 'statuses': Job.JobStatus.choices, 'parse_form': JobParseForm()}
    return render(request, 'jobs/index.html', context)


@login_required
def job_list_partial(request):
    search_keyword = request.GET.get('search', '');
    company_id = request.GET.get('company', '');
    status = request.GET.get('status', '')
    query = Job.objects.select_related('company').all()
    if search_keyword: query = query.filter(
        Q(title__icontains=search_keyword) | Q(company__name__icontains=search_keyword))
    if company_id: query = query.filter(company_id=company_id)
    if status: query = query.filter(status=status)
    return render(request, 'jobs/partials/job_list_table.html', {'jobs': query})


@login_required
@require_http_methods(["GET", "POST"])
def job_detail_view(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES, instance=job)
        if form.is_valid():
            form.save();
            messages.success(request, f"职位 '{job.title}' 更新成功！")
            logging_service.create_log(request.user, "更新职位", job)
            response = HttpResponse(status=204);
            response['HX-Refresh'] = 'true';
            return response
    else:
        form = JobForm(instance=job)
    return render(request, 'jobs/partials/job_detail_panel.html', {'job': job, 'form': form})


@login_required
@require_POST
def job_delete_view(request, job_id):
    job = get_object_or_404(Job, pk=job_id);
    job_title = job.title;
    logging_service.create_log(request.user, "删除职位", job);
    job.delete()
    messages.success(request, f"职位 '{job_title}' 已被删除。")
    response = HttpResponse(status=204);
    response['HX-Refresh'] = 'true';
    return response


# --- 候选人管理视图 ---
@login_required
def candidate_dashboard_view(request):
    context = {'parse_form': CandidateParseForm(), 'groups': CandidateGroup.objects.all()}
    return render(request, 'jobs/candidate_dashboard.html', context)


@login_required
def candidate_list_partial(request):
    search_keyword = request.GET.get('search', '')
    query = Candidate.objects.all()
    if search_keyword:
        query = query.filter(Q(name__icontains=search_keyword) | Q(emails__icontains=search_keyword) | Q(
            keywords__icontains=search_keyword))
    return render(request, 'jobs/partials/candidate_list_table.html', {'candidates': query})


@login_required
@require_http_methods(["GET", "POST"])
def candidate_detail_view(request, candidate_id):
    candidate = get_object_or_404(Candidate, pk=candidate_id)
    if request.method == 'POST':
        form = CandidateForm(request.POST, instance=candidate)
        if form.is_valid():
            form.save();
            messages.success(request, f"候选人 '{candidate.name}' 更新成功！")
            logging_service.create_log(request.user, "更新候选人", candidate)
            response = HttpResponse(status=204);
            response['HX-Refresh'] = 'true';
            return response
    else:
        form = CandidateForm(instance=candidate)
    return render(request, 'jobs/partials/candidate_detail_panel.html', {'candidate': candidate, 'form': form})


@login_required
@require_POST
def candidate_delete_view(request, candidate_id):
    candidate = get_object_or_404(Candidate, pk=candidate_id);
    logging_service.create_log(request.user, "删除候选人", candidate)
    candidate_name = candidate.name;
    candidate.delete()
    messages.success(request, f"候选人 '{candidate_name}' 已被删除。")
    response = HttpResponse(status=204);
    response['HX-Refresh'] = 'true';
    return response


@login_required
@require_http_methods(["GET"])
def find_matches_view(request, candidate_id):
    candidate = get_object_or_404(Candidate, pk=candidate_id)
    matched_jobs = matching_service.find_matching_jobs(candidate)
    context = {'candidate': candidate, 'matched_jobs': matched_jobs}
    return render(request, 'jobs/partials/matching_results.html', context)


# --- 分组管理视图 ---
@login_required
@require_http_methods(["GET", "POST"])
def group_management_view(request):
    if request.method == 'POST':
        form = CandidateGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False);
            group.user = request.user;
            group.save()
            messages.success(request, f"成功创建分组 '{form.cleaned_data['name']}'。")
            logging_service.create_log(request.user, "创建分组", group)
            return redirect('jobs:group_management')
    else:
        form = CandidateGroupForm()
    groups = CandidateGroup.objects.annotate(member_count=Count('candidates')).all()
    context = {'form': form, 'groups': groups};
    return render(request, 'jobs/group_management.html', context)


@login_required
@require_http_methods(["GET"])
def group_detail_view(request, group_id):
    group = get_object_or_404(CandidateGroup, pk=group_id)
    members = group.candidates.all()
    context = {'group': group, 'members': members}
    return render(request, 'jobs/group_detail.html', context)


@login_required
@require_POST
def remove_candidate_from_group_view(request, group_id, candidate_id):
    group = get_object_or_404(CandidateGroup, pk=group_id);
    candidate = get_object_or_404(Candidate, pk=candidate_id)
    candidate.groups.remove(group)
    logging_service.create_log(request.user, f"从分组 '{group.name}' 移除候选人", candidate)
    messages.success(request, f"已将候选人 '{candidate.name}' 从分组 '{group.name}' 中移除。")
    members = group.candidates.all()
    context = {'group': group, 'members': members}
    return render(request, 'jobs/partials/group_member_list.html', context)


@login_required
@require_POST
def group_delete_view(request, group_id):
    group = get_object_or_404(CandidateGroup, pk=group_id);
    logging_service.create_log(request.user, "删除分组", group)
    group_name = group.name;
    group.delete()
    messages.success(request, f"分组 '{group_name}' 已被删除。");
    return redirect('jobs:group_management')


@login_required
@require_POST
def add_candidates_to_group_view(request):
    candidate_ids = request.POST.getlist('candidate_ids');
    group_id = request.POST.get('group_id')
    if not candidate_ids: messages.warning(request, "您没有选择任何候选人。"); return redirect(
        'jobs:candidate_dashboard')
    if not group_id: messages.warning(request, "您没有选择要添加到的分组。"); return redirect('jobs:candidate_dashboard')
    group = get_object_or_404(CandidateGroup, pk=group_id);
    candidates = Candidate.objects.filter(pk__in=candidate_ids)
    for candidate in candidates: candidate.groups.add(group)
    logging_service.create_log(request.user, f"批量添加 {len(candidate_ids)} 人至分组", group)
    messages.success(request, f"成功将 {len(candidate_ids)} 位候选人添加到分组 '{group.name}'。");
    return redirect('jobs:candidate_dashboard')


# --- 邮件功能视图 ---
def _get_enabled_ai_models(user):
    saved_providers = ApiKey.objects.filter(user=user).values_list('provider', flat=True)
    return {key: model_info for key, model_info in settings.AI_MODELS.items() if
            model_info['provider'] in saved_providers}


@login_required
@require_http_methods(["GET", "POST"])
def compose_email_view(request, candidate_id):
    candidate = get_object_or_404(Candidate, pk=candidate_id)
    if request.method == 'POST':
        form = EmailComposeForm(request.user, request.POST)
        if form.is_valid():
            email_task = mailing_service.create_email_task(
                user=request.user, from_account=form.cleaned_data['from_account'], candidate=candidate,
                subject=form.cleaned_data['subject'], content=form.cleaned_data['content']
            )
            if email_task:
                messages.success(request, f"已为候选人 '{candidate.name}' 创建邮件发送任务。")
                logging_service.create_log(request.user, "发送邮件", candidate)
            else:
                messages.warning(request, f"未能为候选人 '{candidate.name}' 创建邮件任务，因为该候选人没有邮箱地址。")
            response = HttpResponse(status=204);
            response['HX-Refresh'] = 'true';
            return response
    else:
        form = EmailComposeForm(request.user)

    context = {
        'form': form,
        'candidate': candidate,
        'jobs': Job.objects.all(),
        'enabled_models': _get_enabled_ai_models(request.user)
    }
    return render(request, 'jobs/partials/email_compose_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def compose_group_email_view(request, group_id):
    group = get_object_or_404(CandidateGroup, pk=group_id)
    candidates_in_group = group.candidates.all()
    if request.method == 'POST':
        form = EmailComposeForm(request.user, request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject'];
            content = form.cleaned_data['content']
            from_account = form.cleaned_data['from_account'];
            created_count = 0
            for candidate in candidates_in_group:
                task = mailing_service.create_email_task(
                    user=request.user, from_account=from_account, candidate=candidate,
                    subject=subject, content=content, group=group
                )
                if task: created_count += 1
            messages.success(request, f"已为分组 '{group.name}' 的 {created_count} 位候选人创建了邮件发送任务。")
            logging_service.create_log(request.user, f"群发邮件至分组", group)
            response = HttpResponse(status=204);
            response['HX-Refresh'] = 'true';
            return response
    else:
        form = EmailComposeForm(request.user)
    context = {
        'form': form,
        'group': group,
        'recipient_count': candidates_in_group.count(),
        'jobs': Job.objects.all(),
        'enabled_models': _get_enabled_ai_models(request.user)
    }
    return render(request, 'jobs/partials/group_email_compose_form.html', context)


@login_required
@require_http_methods(["GET"])
def email_history_view(request, candidate_id):
    candidate = get_object_or_404(Candidate, pk=candidate_id)
    email_logs = candidate.email_logs.filter(user=request.user)
    context = {'candidate': candidate, 'email_logs': email_logs};
    return render(request, 'jobs/partials/email_history_panel.html', context)


@login_required
@require_http_methods(["GET"])
def email_log_detail_view(request, log_id):
    log = get_object_or_404(EmailLog, pk=log_id, user=request.user)
    form = EmailRemarkForm(instance=log)
    context = {'log': log, 'form': form};
    return render(request, 'jobs/partials/email_log_detail.html', context)


@login_required
@require_POST
def save_email_remark_view(request, log_id):
    log = get_object_or_404(EmailLog, pk=log_id, user=request.user)
    form = EmailRemarkForm(request.POST, instance=log)
    if form.is_valid():
        form.save()
        logging_service.create_log(request.user, "更新邮件备注", log.candidate)
        context = {'log': log, 'form': form};
        return render(request, 'jobs/partials/email_log_detail.html', context)
    return HttpResponseBadRequest("备注内容无效。")


@login_required
def load_template_view(request):
    template_id = request.GET.get('template')
    if not template_id:
        return render(request, 'jobs/partials/email_form_fields.html', {'template': None})

    template = get_object_or_404(EmailTemplate, pk=template_id)
    return render(request, 'jobs/partials/email_form_fields.html', {'template': template})


# --- AI 辅助视图 ---
@login_required
@require_POST
def ai_generate_email_view(request):
    try:
        data = json.loads(request.body)
        keywords = data.get('keywords')
        job_id = data.get('job_id')
        provider_key = data.get('provider')

        if not all([keywords, job_id, provider_key]):
            return JsonResponse({'error': '缺少必要参数 (keywords, job_id, provider)'}, status=400)

        job = get_object_or_404(Job, pk=job_id)
        job_info = {
            'title': job.title,
            'company_name': job.company.name,
            'salary_range': job.salary_range,
            'locations': ", ".join(job.locations),
        }

        result = ai_service.generate_email_draft(
            keywords=keywords,
            job=job_info,
            user_name=request.user.get_full_name() or request.user.username,
            provider_key=provider_key,
            user=request.user
        )

        if 'error' in result:
            return JsonResponse({'error': result.get('message', 'AI服务返回未知错误')}, status=500)

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON请求体'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def ai_optimize_email_view(request):
    try:
        data = json.loads(request.body)
        content = data.get('content')
        provider_key = data.get('provider')

        if not all([content, provider_key]):
            return JsonResponse({'error': '缺少必要参数 (content, provider)'}, status=400)

        result = ai_service.optimize_email_content(
            draft_content=content,
            provider_key=provider_key,
            user=request.user
        )

        if 'error' in result:
            return JsonResponse({'error': result.get('message', 'AI服务返回未知错误')}, status=500)

        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON请求体'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# --- 邮箱账户管理视图 ---
@login_required
@require_http_methods(["GET", "POST"])
def email_account_management_view(request):
    if request.method == 'POST':
        form = EmailAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.smtp_password_encrypted = encrypt_key(form.cleaned_data['smtp_password'])
            if account.is_default:
                EmailAccount.objects.filter(user=request.user).update(is_default=False)
            account.save()
            logging_service.create_log(request.user, "添加/更新邮箱账户", account)
            messages.success(request, f"成功保存邮箱账户 '{account.email_address}'。")
            return redirect('jobs:email_account_management')
    else:
        form = EmailAccountForm()
    accounts = EmailAccount.objects.filter(user=request.user)
    context = {'form': form, 'accounts': accounts}
    return render(request, 'jobs/email_account_management.html', context)


@login_required
@require_POST
def email_account_delete_view(request, account_id):
    account = get_object_or_404(EmailAccount, pk=account_id, user=request.user)
    logging_service.create_log(request.user, "删除邮箱账户", account)
    account_address = account.email_address;
    account.delete()
    messages.success(request, f"邮箱账户 '{account_address}' 已被删除。")
    return redirect('jobs:email_account_management')


# --- 任务与日志视图 ---
@login_required
def task_queue_view(request):
    email_tasks = EmailLog.objects.select_related('user', 'from_account', 'candidate').all()
    context = {'email_tasks': email_tasks}
    return render(request, 'jobs/task_queue.html', context)


@login_required
@require_POST
def cancel_email_task_view(request, log_id):
    task = get_object_or_404(EmailLog, pk=log_id)
    if task.user == request.user or request.user.is_superuser:
        if task.status == EmailLog.EmailStatus.PENDING:
            task.status = EmailLog.EmailStatus.CANCELED;
            task.save()
            logging_service.create_log(request.user, "取消邮件任务", task.candidate)
            messages.success(request, f"已取消发送给 '{task.candidate.name}' 的邮件任务。")
        else:
            messages.warning(request, "该任务已发送或已取消，无法操作。")
    else:
        messages.error(request, "您无权操作此任务。")
    email_tasks = EmailLog.objects.select_related('user', 'from_account', 'candidate').all()
    return render(request, 'jobs/partials/task_list_partial.html', {'email_tasks': email_tasks})


@login_required
def action_log_view(request):
    log_list = ActionLog.objects.select_related('user').all()
    paginator = Paginator(log_list, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, 'jobs/action_log.html', context)


# --- 邮件设置 (模板与签名) 视图 ---
@login_required
def email_settings_view(request):
    templates = EmailTemplate.objects.select_related('created_by', 'updated_by').all()
    # **核心改动**: 移除所有与 UserSignature 相关的逻辑
    context = {'templates': templates}
    return render(request, 'jobs/email_settings.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def add_template_view(request):
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.updated_by = request.user
            template.save()
            logging_service.create_log(request.user, "创建邮件模板", template)
            messages.success(request, f"邮件模板 '{template.name}' 创建成功。")
            return redirect('jobs:email_settings')
    else:
        form = EmailTemplateForm()
    # **核心改动**: 为模板添加AI模型上下文
    context = {
        'form': form,
        'action': '创建',
        'enabled_models': _get_enabled_ai_models(request.user)
    }
    return render(request, 'jobs/template_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def edit_template_view(request, template_id):
    template = get_object_or_404(EmailTemplate, pk=template_id)
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save(commit=False)
            template.updated_by = request.user
            template.save()
            logging_service.create_log(request.user, "编辑邮件模板", template)
            messages.success(request, f"邮件模板 '{template.name}' 更新成功。")
            return redirect('jobs:email_settings')
    else:
        form = EmailTemplateForm(instance=template)
    # **核心改动**: 为模板添加AI模型上下文
    context = {
        'form': form,
        'action': '编辑',
        'enabled_models': _get_enabled_ai_models(request.user)
    }
    return render(request, 'jobs/template_form.html', context)

# **新增视图**
@login_required
@require_POST
def ai_generate_template_view(request):
    try:
        data = json.loads(request.body)
        keywords = data.get('keywords')
        provider_key = data.get('provider')

        if not all([keywords, provider_key]):
            return JsonResponse({'error': '缺少必要参数 (keywords, provider)'}, status=400)

        result = ai_service.generate_template_draft(
            keywords=keywords,
            provider_key=provider_key,
            user=request.user
        )

        if 'error' in result:
             return JsonResponse({'error': result.get('message', 'AI服务返回未知错误')}, status=500)

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON请求体'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def delete_template_view(request, template_id):
    template = get_object_or_404(EmailTemplate, pk=template_id)
    logging_service.create_log(request.user, "删除邮件模板", template)
    template_name = template.name
    template.delete()
    messages.success(request, f"邮件模板 '{template_name}' 已被删除。")
    return redirect('jobs:email_settings')


# --- API密钥管理与AI解析流程视图 ---
@login_required
@require_http_methods(["GET", "POST"])
def api_key_management_view(request):
    if request.method == 'POST':
        form = ApiKeyForm(request.POST)
        if form.is_valid():
            provider = form.cleaned_data['provider'];
            api_key = form.cleaned_data['api_key']
            encrypted_key = encrypt_key(api_key)
            key_obj, created = ApiKey.objects.update_or_create(user=request.user, provider=provider,
                                                               defaults={'api_key_encrypted': encrypted_key})
            action = "添加" if created else "更新"
            messages.success(request, f"成功{action}了 {provider.upper()} 的API密钥。")
            logging_service.create_log(request.user, f"{action}API密钥", key_obj)
            return redirect('jobs:api_key_management')
    else:
        form = ApiKeyForm()
    context = {'form': form, 'saved_keys': ApiKey.objects.filter(user=request.user)};
    return render(request, 'jobs/api_key_management.html', context)


@login_required
@require_POST
def api_key_delete_view(request, key_id):
    key_obj = get_object_or_404(ApiKey, pk=key_id, user=request.user);
    logging_service.create_log(request.user, "删除API密钥", key_obj)
    provider_name = key_obj.provider.upper();
    key_obj.delete()
    messages.success(request, f"已删除 {provider_name} 的API密钥。");
    return redirect('jobs:api_key_management')


@login_required
def _preview_content(request, form_class, content_type):
    form = form_class(request.POST, request.FILES)
    if not form.is_valid(): return HttpResponseBadRequest("表单无效")
    uploaded_file = form.cleaned_data.get('file_upload');
    text_content = form.cleaned_data.get('text_content');
    texts = []
    if uploaded_file:
        texts = parsing_service.get_texts_from_file(uploaded_file)
    elif text_content:
        texts = [text_content.strip()]
    if not texts or not any(texts): return HttpResponse('<div class="alert alert-warning">未提取到任何有效文本。</div>',
                                                        status=400)
    context = {
        'full_text': "\n\n---\n\n".join(texts),
        'total_items_to_parse': len(texts),
        'enabled_models': _get_enabled_ai_models(request.user),
        'content_type': content_type
    }
    return render(request, 'jobs/partials/text_preview_and_parse_form.html', context)


@login_required
@require_POST
def preview_jobs_view(request): return _preview_content(request, JobParseForm, 'job')


@login_required
@require_POST
def preview_candidates_view(request): return _preview_content(request, CandidateParseForm, 'candidate')


@login_required
def _parse_and_show(request, content_type, parse_function, template_name):
    provider_key = request.POST.get('model_provider')
    if not provider_key: messages.error(request, "解析错误：您没有选择要使用的AI模型。"); return HttpResponse(status=204)
    full_text = request.POST.get('text_content', '')
    if not full_text: 
        messages.warning(request, "未提供任何文本内容进行解析。")
        return render(request, template_name, {'parsed_items': []})
    all_results = parse_function(full_text, provider_key, user=request.user)
    if isinstance(all_results, dict) and "error" in all_results:
        failed_results = [all_results];
        parsed_results = []
    elif isinstance(all_results, list):
        failed_results = [res for res in all_results if "error" in res];
        parsed_results = [res for res in all_results if "error" not in res]
    else:
        failed_results = []; parsed_results = [all_results] if isinstance(all_results, dict) else all_results
    if failed_results:
        first_error = failed_results[0];
        error_title = first_error.get('error', '未知错误');
        error_message = first_error.get('message', '没有更多信息。')
        messages.error(request, f"解析失败 ({error_title}): {error_message}")
    context = {'parsed_items': parsed_results, 'content_type': content_type};
    return render(request, template_name, context)


@login_required
@require_POST
def parse_and_show_jobs_view(request): return _parse_and_show(request, 'job',
                                                              parsing_service.parse_multiple_job_descriptions,
                                                              'jobs/partials/job_preview_results.html')


@login_required
@require_POST
def parse_and_show_candidates_view(request): return _parse_and_show(request, 'candidate',
                                                                    parsing_service.parse_candidate_resume,
                                                                    'jobs/partials/candidate_preview_results.html')


@login_required
@require_POST
def save_parsed_jobs_view(request):
    try:
        saved_count = 0;
        form_indexes = sorted(list(set([k.split('-')[1] for k in request.POST if k.startswith('form-')])))
        with transaction.atomic():
            for i in form_indexes:
                company, _ = Company.objects.get_or_create(name=request.POST.get(f'form-{i}-company_name', '未知公司'))
                job = Job.objects.create(
                    user=request.user, company=company, title=request.POST.get(f'form-{i}-title', ''),
                    department=request.POST.get(f'form-{i}-department', ''),
                    salary_range=request.POST.get(f'form-{i}-salary_range', ''),
                    level_set=[s.strip() for s in request.POST.get(f'form-{i}-level_set', '').split(',') if s.strip()],
                    locations=[s.strip() for s in request.POST.get(f'form-{i}-locations', '').split(',') if s.strip()],
                    keywords=[s.strip() for s in request.POST.get(f'form-{i}-keywords', '').split(',') if s.strip()],
                    job_description=request.POST.get(f'form-{i}-job_description', ''),
                    job_requirement=request.POST.get(f'form-{i}-job_requirement', ''),
                    notes=request.POST.get(f'form-{i}-notes', ''),
                );
                saved_count += 1
                logging_service.create_log(request.user, "批量创建职位", job)
        messages.success(request, f"成功保存 {saved_count} 条新职位！");
        response = HttpResponse(status=204);
        response['HX-Refresh'] = 'true';
        return response
    except Exception as e:
        messages.error(request, f"保存职位时发生严重错误: {e}"); return HttpResponse(status=500)


# --- 邮箱账户管理视图 (重构) ---
@login_required
def email_account_list_view(request):
    accounts = EmailAccount.objects.filter(user=request.user)
    context = {'accounts': accounts}
    return render(request, 'jobs/email_account_management.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def email_account_add_view(request):
    if request.method == 'POST':
        form = EmailAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            # 密码是必填的
            if not form.cleaned_data['smtp_password']:
                form.add_error('smtp_password', '新建邮箱账户时必须提供密码/授权码。')
            else:
                account.smtp_password_encrypted = encrypt_key(form.cleaned_data['smtp_password'])
                if account.is_default:
                    EmailAccount.objects.filter(user=request.user).update(is_default=False)
                account.save()
                logging_service.create_log(request.user, "添加邮箱账户", account)
                messages.success(request, f"成功添加邮箱账户 '{account.email_address}'。")
                return redirect('jobs:email_account_management')
    else:
        form = EmailAccountForm()
    return render(request, 'jobs/email_account_form.html', {'form': form, 'action': '添加'})


@login_required
@require_http_methods(["GET", "POST"])
def email_account_edit_view(request, account_id):
    account = get_object_or_404(EmailAccount, pk=account_id, user=request.user)
    if request.method == 'POST':
        form = EmailAccountForm(request.POST, instance=account)
        if form.is_valid():
            account = form.save(commit=False)
            # 只有在用户输入了新密码时才更新
            if form.cleaned_data['smtp_password']:
                account.smtp_password_encrypted = encrypt_key(form.cleaned_data['smtp_password'])

            if account.is_default:
                EmailAccount.objects.filter(user=request.user).exclude(pk=account.id).update(is_default=False)

            account.save()
            logging_service.create_log(request.user, "更新邮箱账户", account)
            messages.success(request, f"成功更新邮箱账户 '{account.email_address}'。")
            return redirect('jobs:email_account_management')
    else:
        form = EmailAccountForm(instance=account)
    return render(request, 'jobs/email_account_form.html', {'form': form, 'action': '编辑', 'account': account})


@login_required
@require_POST
def save_parsed_candidates_view(request):
    try:
        saved_count = 0;
        form_indexes = sorted(list(set([k.split('-')[1] for k in request.POST if k.startswith('form-')])))
        def sanitize_url(url_string):
            if url_string and not url_string.startswith(('http://', 'https://')): 
                return 'https://' + url_string
            return url_string

        with transaction.atomic():
            for i in form_indexes:
                homepage = sanitize_url(request.POST.get(f'form-{i}-homepage', ''));
                github_profile = sanitize_url(request.POST.get(f'form-{i}-github_profile', ''))
                linkedin_profile = sanitize_url(request.POST.get(f'form-{i}-linkedin_profile', ''));
                external_id_str = request.POST.get(f'form-{i}-external_id')
                external_id = int(external_id_str) if external_id_str and external_id_str.isdigit() else None
                candidate = Candidate.objects.create(
                    user=request.user, name=request.POST.get(f'form-{i}-name', ''),
                    emails=[s.strip() for s in request.POST.get(f'form-{i}-emails', '').split(',') if s.strip()],
                    homepage=homepage, github_profile=github_profile, linkedin_profile=linkedin_profile,
                    external_id=external_id,
                    keywords=[s.strip() for s in request.POST.get(f'form-{i}-keywords', '').split(',') if s.strip()],
                );
                saved_count += 1
                logging_service.create_log(request.user, "批量创建候选人", candidate)
        messages.success(request, f"成功保存 {saved_count} 条新候选人！");
        response = HttpResponse(status=204);
        response['HX-Refresh'] = 'true';
        return response
    except Exception as e:
        messages.error(request, f"保存候选人时发生严重错误: {e}"); return HttpResponse(status=500)
