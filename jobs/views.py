import json
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db import models
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
    ActionLog, EmailTemplate, ScheduledEmailTask, Contact, ContactGroup, ContactOperationLog
)
from .forms import (
    JobForm, JobParseForm, ApiKeyForm, CandidateForm,
    CandidateParseForm, CandidateGroupForm, EmailComposeForm, EmailRemarkForm,
    CustomAuthenticationForm, CustomUserCreationForm, EmailAccountForm,
    EmailTemplateForm, ScheduledEmailTaskForm
)
from .services import parsing_service, matching_service, mailing_service, logging_service, ai_service
from .services.contact_service import ContactService, ContactGroupService, ContactOperationLogger
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
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    search_keyword = request.GET.get('search', '');
    company_id = request.GET.get('company', '');
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    query = Job.objects.select_related('company').all()
    if search_keyword: query = query.filter(
        Q(title__icontains=search_keyword) | Q(company__name__icontains=search_keyword))
    if company_id: query = query.filter(company_id=company_id)
    if status: query = query.filter(status=status)
    
    # Add pagination
    paginator = Paginator(query, 100)  # 100 records per page
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)
    
    return render(request, 'jobs/partials/job_list_table.html', {'jobs': jobs, 'page_obj': jobs})


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
    context = {
        'parse_form': CandidateParseForm(), 
        'groups': CandidateGroup.objects.all(),
        'education_choices': Candidate.EducationLevel.choices,
        'gender_choices': Candidate.Gender.choices,
    }
    return render(request, 'jobs/candidate_dashboard.html', context)


@login_required
def candidate_list_partial(request):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from datetime import date
    
    # Get filter parameters
    search_keyword = request.GET.get('search', '')
    location = request.GET.get('location', '')
    education = request.GET.get('education', '')
    gender = request.GET.get('gender', '')
    age_min = request.GET.get('age_min', '')
    age_max = request.GET.get('age_max', '')
    page = request.GET.get('page', 1)
    
    query = Candidate.objects.all()
    
    # General keyword search across multiple fields
    if search_keyword:
        keyword_query = Q(name__icontains=search_keyword) | \
                       Q(emails__icontains=search_keyword) | \
                       Q(keywords__icontains=search_keyword) | \
                       Q(predicted_position__icontains=search_keyword) | \
                       Q(location__icontains=search_keyword)
        query = query.filter(keyword_query)
    
    # Location filter
    if location:
        query = query.filter(location__icontains=location)
    
    # Education filter
    if education and education != 'all':
        query = query.filter(education_level=education)
    
    # Gender filter
    if gender and gender != 'all':
        query = query.filter(gender=gender)
    
    # Age range filter
    if age_min or age_max:
        current_year = date.today().year
        
        if age_min:
            try:
                min_age = int(age_min)
                max_birth_year = current_year - min_age
                query = query.filter(birthday__year__lte=max_birth_year)
            except ValueError:
                pass
        
        if age_max:
            try:
                max_age = int(age_max)
                min_birth_year = current_year - max_age
                query = query.filter(birthday__year__gte=min_birth_year)
            except ValueError:
                pass
    
    # Add pagination
    paginator = Paginator(query, 100)  # 100 records per page
    try:
        candidates = paginator.page(page)
    except PageNotAnInteger:
        candidates = paginator.page(1)
    except EmptyPage:
        candidates = paginator.page(paginator.num_pages)
    
    # Pass search parameters back to template for highlighting and form preservation
    context = {
        'candidates': candidates, 
        'page_obj': candidates,
        'search_keyword': search_keyword,
        'location_filter': location,
        'education_filter': education,
        'gender_filter': gender,
        'age_min_filter': age_min,
        'age_max_filter': age_max,
    }
    
    return render(request, 'jobs/partials/candidate_list_table.html', context)


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
        
        # 添加调试日志
        print(f"🔍 AI邮件生成请求数据: {data}")
        print(f"📝 关键词: '{keywords}', 职位ID: {job_id}, AI模型: {provider_key}")

        if not all([keywords, job_id, provider_key]):
            missing_params = []
            if not keywords: missing_params.append('keywords')
            if not job_id: missing_params.append('job_id') 
            if not provider_key: missing_params.append('provider')
            error_msg = f'缺少必要参数: {", ".join(missing_params)}'
            print(f"❌ 参数检查失败: {error_msg}")
            return JsonResponse({'error': error_msg}, status=400)

        job = get_object_or_404(Job, pk=job_id)
        job_info = {
            'title': job.title,
            'company_name': job.company.name,
            'salary_range': job.salary_range or '面议',
            'locations': ", ".join(job.locations) if job.locations else '多个城市',
        }
        
        user_name = request.user.get_full_name() or request.user.username
        print(f"🏢 职位信息: {job_info}")
        print(f"👤 用户信息: {user_name}")

        result = ai_service.generate_email_draft(
            keywords=keywords,
            job=job_info,
            user_name=user_name,
            provider_key=provider_key,
            user=request.user
        )
        
        print(f"🤖 AI生成结果: {result}")

        if 'error' in result:
            error_msg = result.get('message', 'AI服务返回未知错误')
            print(f"❌ AI生成失败: {error_msg}")
            return JsonResponse({'error': error_msg}, status=500)
        
        # 检查返回的结果
        if not result.get('subject') and not result.get('body'):
            print(f"⚠️ AI返回了空内容: {result}")
            return JsonResponse({
                'error': 'AI生成的内容为空',
                'debug_info': f'返回数据: {result}'
            }, status=500)

        print(f"✅ AI生成成功，主题长度: {len(result.get('subject', ''))}, 内容长度: {len(result.get('body', ''))}")
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
        account_id = request.POST.get('account_id')
        
        if account_id:
            # Editing existing account
            try:
                # Validate account_id is a valid integer
                account_id = int(account_id)
                account = get_object_or_404(EmailAccount, pk=account_id, user=request.user)
                form = EmailAccountForm(request.POST, instance=account)
                action = "编辑"
            except (ValueError, TypeError):
                messages.error(request, "无效的账户ID。")
                return redirect('jobs:email_account_management')
            except Exception as e:
                messages.error(request, "找不到指定的邮箱账户。")
                return redirect('jobs:email_account_management')
        else:
            # Adding new account
            form = EmailAccountForm(request.POST)
            action = "添加"
        
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            
            # Only update password if provided (for editing) or if new account
            smtp_password = form.cleaned_data.get('smtp_password')
            if smtp_password or not account_id:
                if smtp_password:
                    account.smtp_password_encrypted = encrypt_key(smtp_password)
                else:
                    # For new accounts, password is required
                    messages.error(request, "新建邮箱账户时必须提供密码。")
                    accounts = EmailAccount.objects.filter(user=request.user)
                    context = {'form': form, 'accounts': accounts}
                    return render(request, 'jobs/email_account_management.html', context)
            
            # Handle default account setting
            if account.is_default:
                EmailAccount.objects.filter(user=request.user).exclude(pk=account.pk).update(is_default=False)
            
            account.save()
            logging_service.create_log(request.user, f"{action}邮箱账户", account)
            
            if action == "编辑":
                messages.success(request, f"成功更新邮箱账户 '{account.email_address}'。")
            else:
                messages.success(request, f"成功添加邮箱账户 '{account.email_address}'。")
            
            return redirect('jobs:email_account_management')
        else:
            # Form validation failed
            if account_id:
                messages.error(request, "编辑邮箱账户时出现错误，请检查表单字段。")
            else:
                messages.error(request, "添加邮箱账户时出现错误，请检查表单字段。")
    else:
        form = EmailAccountForm()
    
    accounts = EmailAccount.objects.filter(user=request.user).order_by('-updated_at')
    context = {'form': form, 'accounts': accounts}
    return render(request, 'jobs/email_account_management.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def email_account_edit_view(request, account_id):
    """编辑邮箱账户"""
    account = get_object_or_404(EmailAccount, pk=account_id, user=request.user)
    
    if request.method == 'POST':
        form = EmailAccountForm(request.POST, instance=account)
        if form.is_valid():
            # 保存账户信息
            updated_account = form.save(commit=False)
            updated_account.user = request.user
            
            # 只有在提供了新密码时才更新加密密码
            if form.cleaned_data.get('smtp_password'):
                updated_account.smtp_password_encrypted = encrypt_key(form.cleaned_data['smtp_password'])
            
            # 如果设为默认，取消其他账户的默认状态
            if updated_account.is_default:
                EmailAccount.objects.filter(user=request.user).exclude(pk=account.id).update(is_default=False)
            
            updated_account.save()
            logging_service.create_log(request.user, "编辑邮箱账户", updated_account)
            messages.success(request, f"邮箱账户 '{updated_account.email_address}' 更新成功！")
            
            # AJAX请求返回成功状态
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': '邮箱账户更新成功！'})
            
            return redirect('jobs:email_account_management')
        else:
            # AJAX请求返回表单错误
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        # GET 请求：返回预填充的编辑表单
        form = EmailAccountForm(instance=account)
        
        # 为AJAX请求返回表单HTML
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(request, 'jobs/partials/email_account_edit_form.html', {
                'form': form, 
                'account': account,
                'action_url': f'/email-accounts/{account.id}/edit/',
                'is_edit_mode': True,  # 明确标识为编辑模式
                'current_values': {
                    'email_address': account.email_address,
                    'sender_name': account.sender_name or '',
                    'daily_send_limit': account.daily_send_limit,
                    'is_default': account.is_default,
                    'smtp_host': account.smtp_host,
                    'smtp_port': account.smtp_port,
                    'use_ssl': account.use_ssl,
                    'imap_host': account.imap_host or '',
                    'imap_port': account.imap_port or '',
                    'imap_use_ssl': account.imap_use_ssl,
                }
            })
    
    # 非AJAX请求的fallback - 重定向到邮箱管理页面
    messages.info(request, f"请在邮箱管理页面中点击编辑按钮来修改 '{account.email_address}' 的设置。")
    return redirect('jobs:email_account_management')


@login_required
@require_POST
def email_account_delete_view(request, account_id):
    account = get_object_or_404(EmailAccount, pk=account_id, user=request.user)
    logging_service.create_log(request.user, "删除邮箱账户", account)
    account_address = account.email_address;
    account.delete()
    messages.success(request, f"邮箱账户 '{account_address}' 已被删除。")
    return redirect('jobs:email_account_management')


@login_required
@require_http_methods(["GET"])
def check_email_account_status_view(request, account_id):
    """检查邮箱账户SMTP连接状态"""
    account = get_object_or_404(EmailAccount, pk=account_id, user=request.user)
    
    from .services.smtp_status_checker import SMTPStatusChecker
    
    # 执行状态检查
    status_result = SMTPStatusChecker.check_smtp_connection(account)
    
    # 记录检查日志
    logging_service.create_log(
        request.user, 
        f"SMTP状态检查: {account.email_address} - {status_result['message']}"
    )
    
    # 为HTMX请求返回状态badge HTML
    if request.headers.get('HX-Request'):
        badge_class = SMTPStatusChecker.get_status_badge_class(status_result['status'])
        status_icon = SMTPStatusChecker.get_status_icon(status_result['status'])
        
        badge_html = f'''
        <span class="badge {badge_class} me-2" 
              data-bs-toggle="tooltip" 
              data-bs-placement="top" 
              title="{status_result['details']}"
              id="status-badge-{account.id}">
            {status_icon} {status_result['message']}
        </span>
        '''
        
        return HttpResponse(badge_html)
    
    # 非HTMX请求返回JSON
    return JsonResponse(status_result)


@login_required
@require_POST
def test_email_account_view(request, account_id):
    """测试邮箱账户连接"""
    account = get_object_or_404(EmailAccount, pk=account_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        test_recipient = data.get('test_recipient', '').strip()
        
        if not test_recipient:
            return JsonResponse({
                'success': False,
                'message': '请输入测试收件人邮箱地址'
            }, status=400)
        
        # 调用测试服务
        from .services.multi_email_service import test_email_account
        test_result = test_email_account(
            account=account,
            test_recipient=test_recipient,
            test_subject="邮箱配置测试",
            test_content="这是一封测试邮件，用于验证您的邮箱配置是否正确。如果您收到这封邮件，说明邮箱配置成功！"
        )
        
        # 记录测试日志
        if test_result['success']:
            logging_service.create_log(
                request.user, 
                f"邮箱测试成功: {account.email_address} -> {test_recipient}"
            )
        else:
            logging_service.create_log(
                request.user, 
                f"邮箱测试失败: {account.email_address}, 错误: {test_result['message']}"
            )
        
        return JsonResponse(test_result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"测试邮箱账户时发生错误: {e}", exc_info=True)
        
        return JsonResponse({
            'success': False,
            'message': f'测试过程中发生错误: {str(e)}'
        }, status=500)


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
            
            # 确定收件人信息用于日志和消息
            recipient_info = None
            if task.candidate:
                recipient_info = task.candidate
                recipient_name = task.candidate.name
            elif task.contact:
                recipient_info = task.contact
                recipient_name = task.contact.name
            else:
                recipient_name = "未知收件人"
            
            logging_service.create_log(request.user, "取消邮件任务", recipient_info)
            messages.success(request, f"已取消发送给 '{recipient_name}' 的邮件任务。")
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
    if not form.is_valid(): 
        return HttpResponseBadRequest("表单无效")
        
    uploaded_file = form.cleaned_data.get('file_upload')
    text_content = form.cleaned_data.get('text_content')
    texts = []
    
    if uploaded_file:
        texts = parsing_service.get_texts_from_file(uploaded_file)
    elif text_content:
        texts = [text_content.strip()]
        
    if not texts or not any(texts): 
        return HttpResponse('<div class="alert alert-warning">未提取到任何有效文本。</div>', status=400)
    
    context = {
        'preview_texts': texts,  # 预览文本列表
        'full_text': "\n\n---\n\n".join(texts),  # 合并的完整文本
        'total_items_to_parse': len(texts),
        'enabled_models': _get_enabled_ai_models(request.user),
        'content_type': content_type
    }
    
    # 根据内容类型选择模板
    if content_type == 'job':
        template_name = 'jobs/partials/job_content_preview.html'
    else:
        template_name = 'jobs/partials/candidate_content_preview.html'
    
    return render(request, template_name, context)


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
    # 修复参数顺序：(text_content, user, provider_key)
    all_results = parse_function(full_text, request.user, provider_key)
    
    # 添加详细日志
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== 视图层调试信息 ===")
    logger.info(f"解析函数返回数据类型: {type(all_results)}")
    logger.info(f"解析函数返回内容: {all_results}")
    
    if isinstance(all_results, dict) and "error" in all_results:
        failed_results = [all_results];
        parsed_results = []
        logger.info("检测到错误结果")
    elif isinstance(all_results, list):
        failed_results = [res for res in all_results if "error" in res];
        parsed_results = [res for res in all_results if "error" not in res]
        logger.info(f"列表结果 - 失败: {len(failed_results)}, 成功: {len(parsed_results)}")
    else:
        failed_results = []; 
        # 特殊处理candidates结构
        if isinstance(all_results, dict) and "candidates" in all_results:
            parsed_results = all_results["candidates"]
            logger.info(f"提取candidates字段，数量: {len(parsed_results)}")
        else:
            parsed_results = [all_results] if isinstance(all_results, dict) else all_results
            logger.info(f"其他情况处理，结果: {parsed_results}")
    if failed_results:
        first_error = failed_results[0];
        error_title = first_error.get('error', '未知错误');
        error_message = first_error.get('message', '没有更多信息。')
        messages.error(request, f"解析失败 ({error_title}): {error_message}")
    context = {'parsed_items': parsed_results, 'content_type': content_type};
    logger.info(f"=== 最终模板上下文 ===")
    logger.info(f"parsed_items类型: {type(parsed_results)}")
    logger.info(f"parsed_items长度: {len(parsed_results) if hasattr(parsed_results, '__len__') else 'N/A'}")
    logger.info(f"parsed_items内容: {parsed_results}")
    logger.info(f"模板名称: {template_name}")
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


# --- 邮箱账户管理视图删除了重复的拆分视图，恢复单页面管理 ---


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
                external_id = None
                if external_id_str and external_id_str.strip():
                    try:
                        external_id = int(external_id_str.strip())
                    except (ValueError, TypeError):
                        logging_service.create_log(request.user, f"外部ID格式错误: {external_id_str}")
                        external_id = None
                
                # 处理新字段
                birthday_str = request.POST.get(f'form-{i}-birthday', '')
                birthday = None
                if birthday_str:
                    try:
                        # 处理不同的日期格式
                        if len(birthday_str) == 4:  # YYYY
                            birthday = f"{birthday_str}-01-01"
                        elif len(birthday_str) == 7:  # YYYY-MM
                            birthday = f"{birthday_str}-01"
                        else:  # YYYY-MM-DD
                            birthday = birthday_str
                        from datetime import datetime
                        birthday = datetime.strptime(birthday, '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        logging_service.create_log(request.user, f"日期格式错误: {birthday_str}, 错误: {e}")
                        birthday = None
                
                candidate = Candidate.objects.create(
                    user=request.user, name=request.POST.get(f'form-{i}-name', ''),
                    emails=[s.strip() for s in request.POST.get(f'form-{i}-emails', '').split(',') if s.strip()],
                    homepage=homepage, github_profile=github_profile, linkedin_profile=linkedin_profile,
                    external_id=external_id,
                    birthday=birthday,
                    gender=request.POST.get(f'form-{i}-gender', '未知'),
                    location=request.POST.get(f'form-{i}-location', ''),
                    education_level=request.POST.get(f'form-{i}-education_level', '未知'),
                    predicted_position=request.POST.get(f'form-{i}-predicted_position', ''),  # 新增字段
                    keywords=[s.strip() for s in request.POST.get(f'form-{i}-keywords', '').split(',') if s.strip()],
                );
                saved_count += 1
                logging_service.create_log(request.user, "批量创建候选人", candidate)
        messages.success(request, f"成功保存 {saved_count} 条新候选人！");
        response = HttpResponse(status=204);
        response['HX-Refresh'] = 'true';
        return response
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"保存候选人时发生严重错误: {e}", exc_info=True)
        messages.error(request, f"保存候选人时发生严重错误: {e}")
        return HttpResponse(status=500)

# --- 定时邮件任务管理视图 ---
@login_required
def scheduled_task_list_view(request):
    """定时任务列表视图"""
    tasks = ScheduledEmailTask.objects.filter(user=request.user).order_by('-created_at')
    context = {'tasks': tasks}
    return render(request, 'jobs/scheduled_task_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def scheduled_task_add_view(request):
    """添加定时任务视图"""
    if request.method == 'POST':
        form = ScheduledEmailTaskForm(request.user, request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            form.save(commit=True)  # 使用form.save来处理多对多关系
            
            # 添加到调度器
            from jobs.services.mail_scheduler import mail_scheduler
            mail_scheduler.add_task(task)
            
            logging_service.create_log(request.user, "创建定时邮件任务", task)
            messages.success(request, f"定时任务 '{task.name}' 创建成功。")
            return redirect('jobs:scheduled_task_list')
    else:
        form = ScheduledEmailTaskForm(request.user)
    
    context = {'form': form, 'action': '添加'}
    return render(request, 'jobs/scheduled_task_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def scheduled_task_edit_view(request, task_id):
    """编辑定时任务视图"""
    task = get_object_or_404(ScheduledEmailTask, pk=task_id, user=request.user)
    
    if request.method == 'POST':
        form = ScheduledEmailTaskForm(request.user, request.POST, instance=task)
        if form.is_valid():
            task = form.save()
            
            # 更新调度器中的任务
            from jobs.services.mail_scheduler import mail_scheduler
            mail_scheduler.remove_task(task.id)
            if task.is_enabled and task.status == ScheduledEmailTask.TaskStatus.ACTIVE:
                mail_scheduler.add_task(task)
            
            logging_service.create_log(request.user, "更新定时邮件任务", task)
            messages.success(request, f"定时任务 '{task.name}' 更新成功。")
            return redirect('jobs:scheduled_task_list')
    else:
        form = ScheduledEmailTaskForm(request.user, instance=task)
    
    context = {'form': form, 'action': '编辑', 'task': task}
    return render(request, 'jobs/scheduled_task_form.html', context)


@login_required
@require_POST
def scheduled_task_delete_view(request, task_id):
    """删除定时任务视图"""
    task = get_object_or_404(ScheduledEmailTask, pk=task_id, user=request.user)
    
    # 从调度器中移除任务
    from jobs.services.mail_scheduler import mail_scheduler
    mail_scheduler.remove_task(task.id)
    
    task_name = task.name
    task.delete()
    
    logging_service.create_log(request.user, "删除定时邮件任务", task)
    messages.success(request, f"定时任务 '{task_name}' 已删除。")
    return redirect('jobs:scheduled_task_list')


@login_required
@require_POST
def scheduled_task_toggle_view(request, task_id):
    """切换定时任务启用状态"""
    task = get_object_or_404(ScheduledEmailTask, pk=task_id, user=request.user)
    
    from jobs.services.mail_scheduler import mail_scheduler
    
    if task.is_enabled:
        task.is_enabled = False
        mail_scheduler.remove_task(task.id)
        action = "禁用"
    else:
        task.is_enabled = True
        if task.status == ScheduledEmailTask.TaskStatus.ACTIVE:
            mail_scheduler.add_task(task)
        action = "启用"
    
    task.save()
    
    logging_service.create_log(request.user, f"{action}定时邮件任务", task)
    messages.success(request, f"定时任务 '{task.name}' 已{action}。")
    
    response = HttpResponse(status=204)
    response['HX-Refresh'] = 'true'
    return response


@login_required
def scheduled_task_detail_view(request, task_id):
    """定时任务详情视图"""
    task = get_object_or_404(ScheduledEmailTask, pk=task_id, user=request.user)
    
    # 获取调度器中的任务状态
    from jobs.services.mail_scheduler import mail_scheduler
    job_status = mail_scheduler.get_job_status(task.id)
    
    # 获取最近的执行记录
    recent_logs = EmailLog.objects.filter(
        group=task.group,
        trigger_type=EmailLog.TriggerType.AUTO
    ).order_by('-sent_at')[:10]
    
    context = {
        'task': task,
        'job_status': job_status,
        'recent_logs': recent_logs
    }
    return render(request, 'jobs/scheduled_task_detail.html', context)


@login_required
@require_POST
def scheduled_task_preview_view(request, task_id):
    """预览定时任务邮件内容"""
    task = get_object_or_404(ScheduledEmailTask, pk=task_id, user=request.user)
    
    # 根据目标类型获取收件人
    recipients = []
    recipient_type = "未知"
    
    if task.target_type == ScheduledEmailTask.TargetType.CANDIDATE_GROUP:
        if not task.group:
            messages.error(request, "候选人分组不存在。")
            return redirect('jobs:scheduled_task_detail', task_id=task_id)
        
        candidates = task.group.candidates.filter(emails__isnull=False).exclude(emails=[])
        recipients = list(candidates)
        recipient_type = "候选人"
        
    elif task.target_type == ScheduledEmailTask.TargetType.CONTACT_GROUP:
        if not task.contact_group:
            messages.error(request, "联系人分组不存在。")
            return redirect('jobs:scheduled_task_detail', task_id=task_id)
        
        contacts = task.contact_group.get_active_contacts()
        recipients = list(contacts)
        recipient_type = "联系人"
    
    if not recipients:
        messages.warning(request, f"该分组中没有有效邮箱的{recipient_type}。")
        return redirect('jobs:scheduled_task_detail', task_id=task_id)
    
    # 渲染邮件内容
    from jobs.services.email_renderer import EmailRenderer
    rendered_emails = EmailRenderer.render_batch_emails(
        template_content=task.template.body,
        template_subject=task.template.subject,
        recipients=recipients[:5],  # 只预览前5个
        user=request.user
    )
    
    context = {
        'task': task,
        'rendered_emails': rendered_emails,
        'total_recipients': len(recipients),
        'recipient_type': recipient_type
    }
    return render(request, 'jobs/scheduled_task_preview.html', context)


# --- 多邮箱管理视图 ---
@login_required
def multi_email_accounts_view(request):
    """多邮箱账户管理页面"""
    from .services.multi_email_service import get_multi_email_sender
    
    accounts = request.user.email_accounts.all().order_by('-is_default', 'email_address')
    
    # 获取邮箱状态信息
    sender = get_multi_email_sender(request.user)
    accounts_status = sender.get_accounts_status()
    
    context = {
        'accounts': accounts,
        'accounts_status': accounts_status
    }
    return render(request, 'jobs/multi_email_accounts.html', context)


@login_required
def multi_email_send_view(request):
    """多邮箱批量发送页面"""
    from .forms import MultiEmailSendForm
    from .services.multi_email_service import get_multi_email_sender
    
    if request.method == 'POST':
        form = MultiEmailSendForm(request.user, request.POST)
        if form.is_valid():
            candidate_group = form.cleaned_data['candidate_group']
            template = form.cleaned_data['template']
            send_mode = form.cleaned_data['send_mode']
            selected_accounts = form.cleaned_data.get('selected_accounts', [])
            single_account = form.cleaned_data.get('single_account')
            send_immediately = form.cleaned_data['send_immediately']
            
            candidates = list(candidate_group.candidates.all())
            
            if send_immediately:
                try:
                    sender = get_multi_email_sender(request.user)
                    
                    if send_mode == 'auto_multi':
                        # 自动分配多邮箱发送
                        result = sender.send_batch_emails(
                            candidates=candidates,
                            template_subject=template.subject,
                            template_content=template.body,
                            group=candidate_group
                        )
                    elif send_mode == 'selected_accounts':
                        # 使用指定的多个邮箱发送
                        result = sender.send_batch_emails(
                            candidates=candidates,
                            template_subject=template.subject,
                            template_content=template.body,
                            selected_accounts=list(selected_accounts),
                            group=candidate_group
                        )
                    elif send_mode == 'single_account':
                        # 使用单个邮箱发送
                        result = sender.send_batch_emails(
                            candidates=candidates,
                            template_subject=template.subject,
                            template_content=template.body,
                            selected_accounts=[single_account],
                            group=candidate_group
                        )
                    
                    messages.success(request, 
                        f"邮件发送完成！成功: {result['success']}封, 失败: {result['failed']}封")
                    
                    # 记录日志
                    logging_service.create_log(
                        user=request.user,
                        action_description=f"多邮箱批量发送邮件到分组 {candidate_group.name}，"
                                         f"成功 {result['success']} 封，失败 {result['failed']} 封",
                        related_object=candidate_group
                    )
                    
                except Exception as e:
                    messages.error(request, f"发送失败: {str(e)}")
                    
            else:
                messages.info(request, "邮件任务已创建，稍后可手动触发发送")
            
            return redirect('jobs:multi_email_send')
    else:
        form = MultiEmailSendForm(request.user)
    
    context = {'form': form}
    return render(request, 'jobs/multi_email_send.html', context)


@login_required  
def email_account_stats_view(request):
    """邮箱发送统计页面"""
    from .forms import EmailAccountStatsForm
    from .models import EmailAccountStats
    from django.db.models import Q
    from datetime import date, timedelta
    
    form = EmailAccountStatsForm(request.user, request.GET)
    stats_queryset = EmailAccountStats.objects.filter(
        email_account__user=request.user
    )
    
    if form.is_valid():
        email_account = form.cleaned_data.get('email_account')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        if email_account:
            stats_queryset = stats_queryset.filter(email_account=email_account)
        
        if date_from:
            stats_queryset = stats_queryset.filter(date__gte=date_from)
        
        if date_to:
            stats_queryset = stats_queryset.filter(date__lte=date_to)
    
    # 默认显示最近30天的数据
    if not form.is_valid() or not any([form.cleaned_data.get('date_from'), form.cleaned_data.get('date_to')]):
        thirty_days_ago = date.today() - timedelta(days=30)
        stats_queryset = stats_queryset.filter(date__gte=thirty_days_ago)
    
    stats = stats_queryset.order_by('-date', 'email_account__email_address')
    
    # 分页
    paginator = Paginator(stats, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'total_stats': stats.count()
    }
    return render(request, 'jobs/email_account_stats.html', context)


@login_required
def incoming_emails_view(request):
    """收件邮件管理页面"""
    from .forms import IncomingEmailFilterForm
    from .models import IncomingEmail
    from .services.imap_service import IMAPService
    
    form = IncomingEmailFilterForm(request.user, request.GET)
    emails_queryset = IncomingEmail.objects.filter(
        received_account__user=request.user
    )
    
    if form.is_valid():
        received_account = form.cleaned_data.get('received_account')
        candidate = form.cleaned_data.get('candidate')
        email_type = form.cleaned_data.get('email_type')
        is_read = form.cleaned_data.get('is_read')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        if received_account:
            emails_queryset = emails_queryset.filter(received_account=received_account)
        
        if candidate:
            emails_queryset = emails_queryset.filter(candidate=candidate)
        
        if email_type:
            emails_queryset = emails_queryset.filter(email_type=email_type)
        
        if is_read:
            emails_queryset = emails_queryset.filter(is_read=(is_read == 'true'))
        
        if date_from:
            emails_queryset = emails_queryset.filter(received_at__date__gte=date_from)
        
        if date_to:
            emails_queryset = emails_queryset.filter(received_at__date__lte=date_to)
    
    emails = emails_queryset.order_by('-received_at')
    
    # 分页
    paginator = Paginator(emails, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 统计信息
    unread_count = emails_queryset.filter(is_read=False).count()
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'unread_count': unread_count,
        'total_emails': emails.count()
    }
    return render(request, 'jobs/incoming_emails.html', context)


@login_required
def incoming_email_detail_view(request, email_id):
    """收件邮件详情页面"""
    from .models import IncomingEmail
    from .services.imap_service import IMAPService
    
    try:
        email = IncomingEmail.objects.get(
            id=email_id,
            received_account__user=request.user
        )
        
        # 标记为已读
        if not email.is_read:
            email.is_read = True
            email.save()
        
        # 统计信息
        same_sender_count = IncomingEmail.objects.filter(
            sender_email=email.sender_email,
            received_account__user=request.user
        ).count()
        
        same_type_count = IncomingEmail.objects.filter(
            email_type=email.email_type,
            received_account__user=request.user
        ).count()
        
        context = {
            'email': email,
            'same_sender_count': same_sender_count,
            'same_type_count': same_type_count
        }
        return render(request, 'jobs/incoming_email_detail.html', context)
        
    except IncomingEmail.DoesNotExist:
        messages.error(request, "邮件不存在或无权访问")
        return redirect('jobs:incoming_emails')


@login_required
def fetch_emails_view(request):
    """手动收取邮件"""
    from .services.imap_service import create_imap_fetch_task
    
    if request.method == 'POST':
        try:
            days_back = int(request.POST.get('days_back', 1))
            if days_back < 1 or days_back > 365:  # Reasonable bounds
                days_back = 1
        except (ValueError, TypeError):
            days_back = 1
        
        try:
            result = create_imap_fetch_task(request.user, days_back)
            
            if result['success']:
                messages.success(request, 
                    f"邮件收取完成！共收取到 {result['total_emails']} 封新邮件")
                
                # 显示详细结果
                for account, count in result['results'].items():
                    if count > 0:
                        messages.info(request, f"邮箱 {account}: {count} 封新邮件")
            else:
                messages.error(request, f"邮件收取失败: {result['error']}")
                
        except Exception as e:
            messages.error(request, f"邮件收取异常: {str(e)}")
    
    return redirect('jobs:incoming_emails')


@login_required
def email_account_test_view(request, account_id):
    """测试邮箱连接"""
    from .models import EmailAccount
    from .services.imap_service import IMAPEmailReceiver
    import smtplib
    from django.http import JsonResponse
    
    try:
        account = EmailAccount.objects.get(id=account_id, user=request.user)
        
        results = {'smtp': False, 'imap': False, 'errors': []}
        
        # 测试SMTP
        try:
            from ..utils import decrypt_key
            password = decrypt_key(account.smtp_password_encrypted)
            
            if account.use_ssl:
                server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port)
            else:
                server = smtplib.SMTP(account.smtp_host, account.smtp_port)
                server.starttls()
            
            server.login(account.email_address, password)
            server.quit()
            results['smtp'] = True
            
        except Exception as e:
            results['errors'].append(f"SMTP连接失败: {str(e)}")
        
        # 测试IMAP
        if account.imap_host:
            try:
                receiver = IMAPEmailReceiver(account)
                if receiver.connect():
                    receiver.disconnect()
                    results['imap'] = True
                else:
                    results['errors'].append("IMAP连接失败")
                    
            except Exception as e:
                results['errors'].append(f"IMAP连接失败: {str(e)}")
        
        return JsonResponse(results)
        
    except EmailAccount.DoesNotExist:
        return JsonResponse({'error': '邮箱账户不存在'}, status=404)


# --- 联系人管理视图 ---
@login_required
def contact_list_view(request):
    """联系人列表页面"""
    from .forms import ContactSearchForm
    
    form = ContactSearchForm(user=request.user, data=request.GET)
    contacts_queryset = Contact.objects.filter(is_active=True)
    
    if form.is_valid():
        search_query = form.cleaned_data.get('search_query')
        company = form.cleaned_data.get('company')
        position = form.cleaned_data.get('position')
        department = form.cleaned_data.get('department')
        contact_group = form.cleaned_data.get('contact_group')
        is_active = form.cleaned_data.get('is_active')
        
        # 转换is_active字符串为布尔值
        if is_active == 'true':
            is_active = True
        elif is_active == 'false':
            is_active = False
        else:
            is_active = None
        
        contacts_queryset = ContactService.search_contacts(
            search_query=search_query,
            company=company,
            position=position,
            department=department,
            contact_group=contact_group,
            is_active=is_active
        )
    
    # 分页
    paginator = Paginator(contacts_queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 统计信息
    stats = ContactService.get_contact_statistics()
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'stats': stats,
        'total_contacts': contacts_queryset.count()
    }
    return render(request, 'jobs/contact_list.html', context)


@login_required
def contact_add_view(request):
    """添加联系人页面"""
    from .forms import ContactForm
    
    if request.method == 'POST':
        form = ContactForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                contact_data = form.cleaned_data
                contact = ContactService.create_contact(
                    contact_data=contact_data,
                    operator=request.user,
                    request=request
                )
                
                messages.success(request, f"联系人 '{contact.name}' 添加成功！")
                return redirect('jobs:contact_detail', contact_id=contact.id)
                
            except Exception as e:
                messages.error(request, f"添加联系人失败: {str(e)}")
    else:
        form = ContactForm(user=request.user)
    
    context = {'form': form, 'action': '添加'}
    return render(request, 'jobs/contact_form.html', context)


@login_required
def contact_edit_view(request, contact_id):
    """编辑联系人页面"""
    from .forms import ContactForm
    
    contact = get_object_or_404(Contact, id=contact_id, is_active=True)
    
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact, user=request.user)
        if form.is_valid():
            try:
                update_data = form.cleaned_data
                ContactService.update_contact(
                    contact=contact,
                    update_data=update_data,
                    operator=request.user,
                    request=request
                )
                
                messages.success(request, f"联系人 '{contact.name}' 更新成功！")
                return redirect('jobs:contact_detail', contact_id=contact.id)
                
            except Exception as e:
                messages.error(request, f"更新联系人失败: {str(e)}")
    else:
        form = ContactForm(instance=contact, user=request.user)
    
    context = {'form': form, 'contact': contact, 'action': '编辑'}
    return render(request, 'jobs/contact_form.html', context)


@login_required
def contact_detail_view(request, contact_id):
    """联系人详情页面"""
    contact = get_object_or_404(Contact, id=contact_id, is_active=True)
    
    # 获取联系人的分组
    contact_groups = contact.contact_groups.all()
    
    # 获取操作日志
    operation_logs = contact.operation_logs.all()[:10]
    
    context = {
        'contact': contact,
        'contact_groups': contact_groups,
        'operation_logs': operation_logs
    }
    return render(request, 'jobs/contact_detail.html', context)


@login_required
@require_POST
def contact_delete_view(request, contact_id):
    """删除联系人"""
    contact = get_object_or_404(Contact, id=contact_id, is_active=True)
    
    try:
        ContactService.delete_contact(
            contact=contact,
            operator=request.user,
            request=request
        )
        
        messages.success(request, f"联系人 '{contact.name}' 已删除")
        
    except Exception as e:
        messages.error(request, f"删除联系人失败: {str(e)}")
    
    return redirect('jobs:contact_list')


# --- 联系人分组管理视图 ---
@login_required
def contact_group_list_view(request):
    """联系人分组列表页面"""
    groups = ContactGroup.objects.filter(user=request.user).annotate(
        contact_count=models.Count('contacts', filter=models.Q(contacts__is_active=True))
    ).order_by('name')
    
    # 分页
    paginator = Paginator(groups, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'page_obj': page_obj}
    return render(request, 'jobs/contact_group_list.html', context)


@login_required
def contact_group_add_view(request):
    """添加联系人分组页面"""
    from .forms import ContactGroupForm
    
    if request.method == 'POST':
        form = ContactGroupForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                group_data = {
                    'name': form.cleaned_data['name'],
                    'description': form.cleaned_data['description'],
                }
                
                group = ContactGroupService.create_group(
                    group_data=group_data,
                    operator=request.user,
                    request=request
                )
                
                # 处理联系人关联
                selected_contacts = form.cleaned_data.get('selected_contacts', [])
                if selected_contacts:
                    ContactGroupService.add_contacts_to_group(
                        group=group,
                        contacts=list(selected_contacts),
                        operator=request.user,
                        request=request
                    )
                
                messages.success(request, f"联系人分组 '{group.name}' 创建成功！")
                return redirect('jobs:contact_group_detail', group_id=group.id)
                
            except Exception as e:
                messages.error(request, f"创建分组失败: {str(e)}")
    else:
        form = ContactGroupForm(user=request.user)
    
    context = {'form': form, 'action': '添加'}
    return render(request, 'jobs/contact_group_form.html', context)


@login_required
def contact_group_edit_view(request, group_id):
    """编辑联系人分组页面"""
    from .forms import ContactGroupForm
    
    group = get_object_or_404(ContactGroup, id=group_id, user=request.user)
    
    if request.method == 'POST':
        form = ContactGroupForm(request.POST, instance=group, user=request.user)
        if form.is_valid():
            try:
                update_data = {
                    'name': form.cleaned_data['name'],
                    'description': form.cleaned_data['description'],
                }
                
                ContactGroupService.update_group(
                    group=group,
                    update_data=update_data,
                    operator=request.user,
                    request=request
                )
                
                # 处理联系人关联变更
                new_contacts = set(form.cleaned_data.get('selected_contacts', []))
                current_contacts = set(group.contacts.all())
                
                # 添加新联系人
                contacts_to_add = new_contacts - current_contacts
                if contacts_to_add:
                    ContactGroupService.add_contacts_to_group(
                        group=group,
                        contacts=list(contacts_to_add),
                        operator=request.user,
                        request=request
                    )
                
                # 移除不再属于分组的联系人
                contacts_to_remove = current_contacts - new_contacts
                if contacts_to_remove:
                    ContactGroupService.remove_contacts_from_group(
                        group=group,
                        contacts=list(contacts_to_remove),
                        operator=request.user,
                        request=request
                    )
                
                messages.success(request, f"联系人分组 '{group.name}' 更新成功！")
                return redirect('jobs:contact_group_detail', group_id=group.id)
                
            except Exception as e:
                messages.error(request, f"更新分组失败: {str(e)}")
    else:
        form = ContactGroupForm(instance=group, user=request.user)
    
    context = {'form': form, 'group': group, 'action': '编辑'}
    return render(request, 'jobs/contact_group_form.html', context)


@login_required
def contact_group_detail_view(request, group_id):
    """联系人分组详情页面"""
    group = get_object_or_404(ContactGroup, id=group_id, user=request.user)
    
    # 获取分组中的联系人
    contacts = group.get_active_contacts()
    
    # 分页
    paginator = Paginator(contacts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取操作日志
    operation_logs = group.operation_logs.all()[:10]
    
    context = {
        'group': group,
        'page_obj': page_obj,
        'operation_logs': operation_logs,
        'total_contacts': contacts.count()
    }
    return render(request, 'jobs/contact_group_detail.html', context)


@login_required
@require_POST
def contact_group_delete_view(request, group_id):
    """删除联系人分组"""
    group = get_object_or_404(ContactGroup, id=group_id, user=request.user)
    
    try:
        # 删除分组
        group_name = group.name
        group.delete()
        
        # 记录操作日志
        ContactOperationLogger.log_operation(
            operation_type=ContactOperationLog.OperationType.DELETE,
            operator=request.user,
            description=f"删除联系人分组: {group_name}",
            request=request
        )
        
        messages.success(request, f"联系人分组 '{group_name}' 已删除")
        
    except Exception as e:
        messages.error(request, f"删除分组失败: {str(e)}")
    
    return redirect('jobs:contact_group_list')


# --- 联系人邮件发送视图 ---
@login_required
def contact_email_send_view(request):
    """给联系人发送邮件页面"""
    from .forms import ContactEmailForm
    from .services.multi_email_service import get_multi_email_sender
    from .services.email_renderer import EmailRenderer
    
    if request.method == 'POST':
        form = ContactEmailForm(request.user, request.POST)
        if form.is_valid():
            try:
                # 获取所有目标联系人
                contacts = list(form.cleaned_data.get('contacts', []))
                contact_groups = form.cleaned_data.get('contact_groups', [])
                
                # 从分组中获取联系人
                group_contacts = ContactService.get_contacts_by_groups(list(contact_groups))
                
                # 合并联系人列表并去重
                all_contacts = list(set(contacts + group_contacts))
                
                if not all_contacts:
                    messages.error(request, "没有找到要发送邮件的联系人")
                    return redirect('jobs:contact_email_send')
                
                # 转换联系人为候选人格式（用于邮件渲染）
                candidates = []
                for contact in all_contacts:
                    # 创建临时候选人对象用于邮件渲染
                    from types import SimpleNamespace
                    candidate = SimpleNamespace()
                    candidate.name = contact.name
                    candidate.email = contact.email
                    candidate.emails = [contact.email]
                    candidate.company = contact.company if contact.company else ""
                    candidate.position = contact.position
                    candidates.append(candidate)
                
                # 发送邮件
                if form.cleaned_data['send_immediately']:
                    from_account = form.cleaned_data.get('from_account')
                    if not from_account:
                        messages.error(request, "请选择发件邮箱")
                        return redirect('jobs:contact_email_send')
                    
                    sender = get_multi_email_sender(request.user)
                    
                    result = sender.send_batch_emails(
                        candidates=candidates,
                        template_subject=form.cleaned_data['subject'],
                        template_content=form.cleaned_data['content'],
                        selected_accounts=[from_account] if from_account else None
                    )
                    
                    # 记录操作日志
                    for contact in all_contacts:
                        ContactOperationLogger.log_operation(
                            operation_type=ContactOperationLog.OperationType.EMAIL_SENT,
                            operator=request.user,
                            contact=contact,
                            description=f"发送邮件: {form.cleaned_data['subject']}",
                            request=request
                        )
                    
                    messages.success(request, 
                        f"邮件发送完成！成功: {result['success']}封, 失败: {result['failed']}封")
                else:
                    messages.info(request, "邮件任务已创建，稍后将发送")
                
                return redirect('jobs:contact_list')
                
            except Exception as e:
                messages.error(request, f"发送邮件失败: {str(e)}")
    else:
        # 支持URL参数预设
        initial_data = {}
        
        # 预设联系人
        contact_id = request.GET.get('contact')
        if contact_id:
            try:
                contact = Contact.objects.get(id=contact_id, is_active=True)
                initial_data['contacts'] = [contact]
            except Contact.DoesNotExist:
                pass
        
        # 预设联系人分组
        contact_group_id = request.GET.get('contact_group')
        if contact_group_id:
            try:
                contact_group = ContactGroup.objects.get(id=contact_group_id, user=request.user)
                initial_data['contact_groups'] = [contact_group]
            except ContactGroup.DoesNotExist:
                pass
        
        form = ContactEmailForm(request.user, initial=initial_data)
    
    context = {'form': form}
    return render(request, 'jobs/contact_email_send.html', context)


@login_required
def get_template_data_view(request):
    """HTMX endpoint to fetch template data"""
    from django.http import JsonResponse
    from .models import EmailTemplate
    
    template_id = request.GET.get('template_id')
    if not template_id:
        return JsonResponse({'error': 'No template ID provided'}, status=400)
    
    try:
        template = EmailTemplate.objects.get(id=template_id)
        return JsonResponse({
            'subject': template.subject,
            'content': template.body,
            'success': True
        })
    except EmailTemplate.DoesNotExist:
        return JsonResponse({'error': 'Template not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_group_members_view(request):
    """获取分组成员信息的API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Only GET method allowed'})
    
    group_type = request.GET.get('type')  # 'candidate' or 'contact'
    group_id = request.GET.get('group_id')
    
    if not group_type or not group_id:
        return JsonResponse({'success': False, 'error': 'Missing parameters'})
    
    try:
        if group_type == 'candidate':
            group = get_object_or_404(CandidateGroup, pk=group_id, user=request.user)
            members = []
            for candidate in group.candidates.all():
                members.append({
                    'id': candidate.id,
                    'name': candidate.name,
                    'emails': candidate.emails,
                    'company': getattr(candidate, 'company', ''),
                    'position': getattr(candidate, 'predicted_position', ''),
                })
        elif group_type == 'contact':
            group = get_object_or_404(ContactGroup, pk=group_id, user=request.user)
            members = []
            for contact in group.contacts.filter(is_active=True):
                members.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'company': contact.company,
                    'position': contact.position,
                })
        else:
            return JsonResponse({'success': False, 'error': 'Invalid group type'})
        
        return JsonResponse({
            'success': True,
            'members': members,
            'count': len(members)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def unified_email_send_view(request):
    """统一的邮件发送页面 - 支持候选人分组和联系人发送"""
    from .forms import UnifiedEmailSendForm
    from .services.multi_email_service import get_multi_email_sender
    
    if request.method == 'POST':
        form = UnifiedEmailSendForm(request.user, request.POST)
        if form.is_valid():
            try:
                send_type = form.cleaned_data['send_type']
                template = form.cleaned_data.get('template')
                subject = form.cleaned_data['subject']
                content = form.cleaned_data['content']
                from_account = form.cleaned_data.get('from_account')
                send_immediately = form.cleaned_data['send_immediately']
                
                candidates = []
                target_description = ""
                
                if send_type == 'candidate_group':
                    # 候选人分组发送
                    candidate_group = form.cleaned_data['candidate_group']
                    candidates = list(candidate_group.candidates.all())
                    target_description = f"候选人分组: {candidate_group.name}"
                    
                elif send_type == 'contact_group':
                    # 联系人分组发送
                    contact_group = form.cleaned_data['contact_group']
                    contacts = list(contact_group.contacts.filter(is_active=True))
                    
                    # 转换联系人为候选人格式（用于邮件渲染）
                    for contact in contacts:
                        from types import SimpleNamespace
                        candidate = SimpleNamespace()
                        candidate.name = contact.name
                        candidate.email = contact.email
                        candidate.emails = [contact.email]
                        candidate.company = contact.company if contact.company else ""
                        candidate.position = contact.position
                        # 添加gender属性以避免模板渲染错误
                        candidate.gender = getattr(contact, 'gender', 'unknown')
                        candidates.append(candidate)
                    
                    target_description = f"联系人分组: {contact_group.name}"
                    

                
                if not candidates:
                    messages.error(request, "没有找到要发送邮件的收件人")
                    return redirect('jobs:unified_email_send')
                
                # 发送邮件
                if send_immediately:
                    if not from_account:
                        messages.error(request, "请选择发件邮箱")
                        return redirect('jobs:unified_email_send')
                    
                    sender = get_multi_email_sender(request.user)
                    
                    # 根据邮件数量选择发送模式
                    async_mode = len(candidates) > 5  # 超过5封邮件使用异步模式
                    
                    result = sender.send_batch_emails(
                        candidates=candidates,
                        template_subject=subject,
                        template_content=content,
                        selected_accounts=[from_account],
                        async_mode=async_mode
                    )
                    
                    if result.get('mode') == 'async':
                        # 异步模式 - 任务已创建
                        messages.success(request, 
                            f"批量邮件任务已创建！目标: {target_description}, 共 {result['total_count']} 封邮件正在后台发送中...")
                        # 可以在这里添加任务ID到session中，用于前端轮询
                        request.session['last_batch_task_ids'] = result['task_ids']
                    else:
                        # 同步模式 - 立即完成
                        messages.success(request, 
                            f"邮件发送完成！目标: {target_description}, 成功: {result['success']}封, 失败: {result['failed']}封")
                    
                    # 记录日志
                    if result.get('mode') == 'async':
                        logging_service.create_log(
                            user=request.user,
                            action_description=f"统一邮件发送任务创建 - {target_description}, 创建 {result['created_count']} 个任务"
                        )
                    else:
                        logging_service.create_log(
                            user=request.user,
                            action_description=f"统一邮件发送 - {target_description}, 成功 {result['success']} 封，失败 {result['failed']} 封"
                    )
                else:
                    messages.info(request, "邮件任务已创建，稍后将发送")
                
                return redirect('jobs:unified_email_send')
                
            except Exception as e:
                messages.error(request, f"发送邮件失败: {str(e)}")
    else:
        form = UnifiedEmailSendForm(request.user)
    
    context = {'form': form}
    return render(request, 'jobs/unified_email_send.html', context)


@login_required
def incoming_email_mark_read_view(request, email_id):
    """标记邮件为已读"""
    if request.method == 'POST':
        try:
            email = IncomingEmail.objects.get(
                id=email_id,
                received_account__user=request.user
            )
            email.is_read = True
            email.save()
            return JsonResponse({'success': True})
        except IncomingEmail.DoesNotExist:
            return JsonResponse({'success': False, 'error': '邮件不存在'})
    return JsonResponse({'success': False, 'error': '无效请求'})


@login_required
def incoming_email_toggle_important_view(request, email_id):
    """切换邮件重要状态"""
    if request.method == 'POST':
        try:
            email = IncomingEmail.objects.get(
                id=email_id,
                received_account__user=request.user
            )
            email.is_important = not email.is_important
            email.save()
            return JsonResponse({'success': True, 'is_important': email.is_important})
        except IncomingEmail.DoesNotExist:
            return JsonResponse({'success': False, 'error': '邮件不存在'})
    return JsonResponse({'success': False, 'error': '无效请求'})


@login_required
def incoming_email_delete_view(request, email_id):
    """删除邮件"""
    if request.method == 'DELETE':
        try:
            email = IncomingEmail.objects.get(
                id=email_id,
                received_account__user=request.user
            )
            email.delete()
            return JsonResponse({'success': True})
        except IncomingEmail.DoesNotExist:
            return JsonResponse({'success': False, 'error': '邮件不存在'})
    return JsonResponse({'success': False, 'error': '无效请求'})


@login_required
def incoming_emails_mark_all_read_view(request):
    """标记所有邮件为已读"""
    if request.method == 'POST':
        updated_count = IncomingEmail.objects.filter(
            received_account__user=request.user,
            is_read=False
        ).update(is_read=True)
        return JsonResponse({'success': True, 'updated_count': updated_count})
    return JsonResponse({'success': False, 'error': '无效请求'})


@login_required
def incoming_emails_batch_operations_view(request):
    """批量操作邮件"""
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            email_ids = data.get('email_ids', [])
            operation = data.get('operation')
            
            if not email_ids:
                return JsonResponse({'success': False, 'error': '未选择邮件'})
            
            emails = IncomingEmail.objects.filter(
                id__in=email_ids,
                received_account__user=request.user
            )
            
            if operation == 'mark_read':
                updated_count = emails.update(is_read=True)
                return JsonResponse({'success': True, 'updated_count': updated_count})
            
            elif operation == 'toggle_important':
                # 切换重要状态比较复杂，需要逐个处理
                updated_count = 0
                for email in emails:
                    email.is_important = not email.is_important
                    email.save()
                    updated_count += 1
                return JsonResponse({'success': True, 'updated_count': updated_count})
            
            elif operation == 'delete':
                deleted_count = emails.count()
                emails.delete()
                return JsonResponse({'success': True, 'deleted_count': deleted_count})
            
            else:
                return JsonResponse({'success': False, 'error': '未知操作'})
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': '无效的JSON数据'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效请求'})


@login_required
def get_batch_email_status_view(request):
    """获取批量邮件发送状态API"""
    from .services.multi_email_service import get_multi_email_sender
    import json
    
    task_ids_str = request.GET.get('task_ids', '')
    if not task_ids_str:
        return JsonResponse({'error': '请提供任务ID列表'}, status=400)
    
    try:
        # 解析任务ID列表
        task_ids = [int(id.strip()) for id in task_ids_str.split(',') if id.strip()]
        
        if not task_ids:
            return JsonResponse({'error': '无效的任务ID列表'}, status=400)
        
        # 获取状态
        sender = get_multi_email_sender(request.user)
        status = sender.get_batch_sending_status(task_ids)
        
        return JsonResponse(status)
        
    except ValueError:
        return JsonResponse({'error': '任务ID格式错误'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'查询状态失败: {str(e)}'}, status=500)
