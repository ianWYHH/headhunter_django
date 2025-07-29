from django.template import Context, Template
from ..models import Candidate, Job, User, EmailAccount


def render_template(template_string: str, candidate: Candidate, job: Job, user: User, from_account: EmailAccount) -> str:
    """
    使用Django模板引擎渲染包含动态占位符的字符串。

    :param template_string: 包含占位符的模板字符串 (例如 "你好, {{candidate.name}}")
    :param candidate: 候选人模型实例
    :param job: 职位模型实例
    :param user: 用户模型实例
    :return: 渲染后的字符串
    """
    # 智能生成尊称
    salutation = f"尊敬的 {candidate.name}"
    if candidate.name and len(candidate.name) > 1:
        last_name = candidate.name[0]
        salutation = f"尊敬的 {last_name}先生/女士"

    # **核心改动**: 从传入的 EmailAccount 实例获取签名
    signature_content = from_account.signature or f"--\n{user.get_full_name() or user.username}"

    context = Context({
        'candidate': {'name': candidate.name, 'salutation': salutation, },
        'job': {
            'title': job.title if job else "",
            'company_name': job.company.name if job and job.company else "",
            'salary_range': job.salary_range if job else "",
            'locations': ", ".join(job.locations) if job and job.locations else "",
            'keywords': ", ".join(job.keywords) if job and job.keywords else "",
        },
        'user': {'name': user.get_full_name() or user.username, 'signature': signature_content, }
    })

    template = Template(template_string)
    return template.render(context)
