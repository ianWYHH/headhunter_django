from django.template import Context, Template
from ..models import Candidate, Job, User, UserSignature

def render_template(template_string: str, candidate: Candidate, job: Job, user: User) -> str:
    """
    渲染邮件模板中的占位符。

    :param template_string: 包含占位符的模板字符串
    :param candidate: 候选人实例
    :param job: 职位实例
    :param user: 当前用户实例
    :return: 渲染后的字符串
    """
    # 智能生成尊称
    salutation = f"尊敬的 {candidate.name}"
    # 这是一个简化的示例，您可以根据需要扩展更复杂的逻辑
    if candidate.name and len(candidate.name) > 1:
        last_name = candidate.name[0]
        salutation = f"尊敬的 {last_name} 先生/女士"

    # 获取用户签名
    try:
        signature_content = user.signature.content
    except UserSignature.DoesNotExist:
        signature_content = f"--\n{user.get_full_name() or user.username}"

    context = Context({
        'candidate': {
            'name': candidate.name,
            'salutation': salutation,
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
        }
    })

    template = Template(template_string)
    return template.render(context)
