from . import parsing_service # 复用底层的AI调用逻辑

def generate_email_draft(keywords: str, job: dict, user_name: str, provider_key: str, user):
    """
    使用AI生成邮件初稿。
    """
    prompt = f"""
    你是一位顶尖的猎头顾问，请根据以下信息，撰写一封专业、简洁且富有吸引力的中文职位推荐邮件。

    我的身份: {user_name}
    核心诉求: "{keywords}"

    职位信息:
    - 职位名称: {job.get('title', 'N/A')}
    - 公司: {job.get('company_name', 'N/A')}
    - 薪资: {job.get('salary_range', 'N/A')}
    - 地点: {job.get('locations', 'N/A')}

    要求:
    1. 邮件需包含主题(subject)和正文(body)。
    2. 语气专业、尊重，体现出你对候选人背景的了解。
    3. 突出职位的核心吸引力。
    4. 以邀请对方进一步沟通为结尾。
    5. 使用 `{{candidate.name}}`, `{{user.signature}}` 等占位符。
    6. 返回一个只包含 "subject" 和 "body" 两个键的JSON对象。
    """
    # 注意：parsing_service._call_ai_model 需要 user 参数
    return parsing_service._call_ai_model(prompt, provider_key, user)

def optimize_email_content(draft_content: str, provider_key: str, user):
    """
    使用AI优化邮件内容。
    """
    prompt = f"""
    请将以下邮件内容进行润色，使其语气更专业、表达更流畅、更具说服力，同时保持核心信息和占位符不变。

    原始邮件:
    ---
    {draft_content}
    ---
    返回一个只包含 "optimized_text" 键的JSON对象。
    """
    return parsing_service._call_ai_model(prompt, provider_key, user)
