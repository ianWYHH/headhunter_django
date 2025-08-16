from django.template import Context, Template
from django.contrib.auth.models import User
from ..models import Candidate, Job, EmailAccount, Contact
from datetime import datetime
from typing import Union


def render_template(template_string: str, recipient: Union[Candidate, Contact], job: Job, user: User, from_account: EmailAccount) -> str:
    """
    使用Django模板引擎渲染包含动态占位符的字符串。

    :param template_string: 包含占位符的模板字符串 (例如 "你好, {{candidate.name}}")
    :param recipient: 收件人模型实例（候选人或联系人）
    :param job: 职位模型实例
    :param user: 用户模型实例
    :param from_account: 发件邮箱账户
    :return: 渲染后的字符串
    """
    # 智能生成尊称 - 基于性别精确生成
    def get_smart_salutation(person):
        """基于性别和姓名智能生成尊称"""
        if not person:
            return "您"
        
        # 安全获取姓名
        name = getattr(person, 'name', None)
        if not name:
            return "您"
        
        # 判断是候选人还是联系人
        if isinstance(person, Candidate):
            gender = getattr(person, 'gender', None)
            if gender == '男':
                return f"{name}先生"
            elif gender == '女':
                return f"{name}女士"
            else:
                # 性别未知时，根据姓名长度处理
                if len(name) > 1:
                    return f"{name[0]}先生/女士"
                return name
        
        elif isinstance(person, Contact):
            gender = getattr(person, 'gender', None)
            if gender == Contact.Gender.MALE:
                return f"{name}先生"
            elif gender == Contact.Gender.FEMALE:
                return f"{name}女士"
            else:
                # 性别未知时，根据姓名长度处理
                if len(name) > 1:
                    return f"{name[0]}先生/女士"
                return name
        
        # 处理其他类型的对象（如SimpleNamespace）
        else:
            gender = getattr(person, 'gender', None)
            if gender in ['男', 'male', Contact.Gender.MALE]:
                return f"{name}先生"
            elif gender in ['女', 'female', Contact.Gender.FEMALE]:
                return f"{name}女士"
            else:
                # 默认处理
                if len(name) > 1:
                    return f"{name[0]}先生/女士"
                return name

    # 获取收件人信息
    recipient_name = recipient.name if recipient else ""
    recipient_salutation = get_smart_salutation(recipient)
    
    # 智能获取邮箱地址
    recipient_email = ""
    if isinstance(recipient, Candidate):
        # 候选人使用emails字段（列表），取第一个邮箱
        emails_list = getattr(recipient, 'emails', [])
        recipient_email = emails_list[0] if emails_list else ""
    elif isinstance(recipient, Contact):
        # 联系人使用email字段
        recipient_email = getattr(recipient, 'email', '')
    
    recipient_location = getattr(recipient, 'location', '')

    # 获取签名内容
    signature_content = from_account.signature if from_account else f"--\n{user.get_full_name() or user.username}"

    # 获取当前时间信息
    now = datetime.now()
    today = now.strftime('%Y年%m月%d日')
    current_time = now.strftime('%H:%M')

    # 构建模板上下文
    context = Context({
        'candidate': {
            'name': recipient_name,
            'salutation': recipient_salutation,
            'email': recipient_email,
            'location': recipient_location,
        },
        # 为了向后兼容，也提供contact变量
        'contact': {
            'name': recipient_name,
            'salutation': recipient_salutation,
            'email': recipient_email,
            'location': recipient_location,
        },
        'job': {
            'title': job.title if job else "",
            'company_name': job.company.name if job and job.company else "",
            'salary_range': job.salary_range if job else "",
            'locations': ", ".join(job.locations) if job and job.locations else "",
            'keywords': ", ".join(job.keywords) if job and job.keywords else "",
        },
        'user': {
            'name': user.get_full_name() or user.username,
            'signature': signature_content,
        },
        'today': today,
        'current_time': current_time,
    })

    template = Template(template_string)
    return template.render(context)
