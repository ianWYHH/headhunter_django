from . import parsing_service # 复用底层的AI调用逻辑

def generate_email_draft(keywords: str, job: dict, user_name: str, provider_key: str, user):
    """
    根据关键词、职位信息和场景，调用AI生成邮件初稿。
    """
    prompt = f"""
    你是一位顶尖的猎头顾问，请根据以下信息，撰写一封专业、简洁且富有吸引力的中文职位推荐邮件。

    # 我的身份
    - 姓名: {user_name}

    # 核心诉求 (邮件需要围绕这些点展开)
    - {keywords}

    # 职位信息
    - 职位名称: {job.get('title', 'N/A')}
    - 公司: {job.get('company_name', 'N/A')}
    - 薪资: {job.get('salary_range', 'N/A')}
    - 地点: {job.get('locations', 'N/A')}

    # 撰写要求
    1. 邮件需包含 "subject" (主题) 和 "body" (正文) 两个部分。
    2. 语气必须专业、尊重，体现出你对候选人背景的了解和职位的深刻洞察。
    3. 正文开头请使用 `{{candidate.salutation}}` 作为尊称占位符。
    4. 正文结尾请使用 `{{user.signature}}` 作为签名占位符。
    5. 邮件内容应突出职位的核心吸引力，并自然地融入核心诉求。
    6. 以邀请对方进一步沟通为结尾，引导其回复。
    7. 返回一个且仅一个符合RFC 8259标准的JSON对象，该对象必须包含 "subject" 和 "body" 两个键。不要返回任何JSON以外的解释性文字。
    """
    # 复用已有的、经过用户隔离和错误处理的AI调用函数
    return parsing_service._call_ai_model(prompt, provider_key, user)

def optimize_email_content(draft_content: str, provider_key: str, user):
    """
    调用AI对用户输入的邮件草稿进行润色和优化。
    """
    prompt = f"""
    你是一位专业的商务沟通文案专家，请将以下邮件内容进行润色和优化。

    # 优化目标
    - **语气**: 更专业、更具说服力、更自然流畅。
    - **结构**: 逻辑更清晰，重点更突出。
    - **内容**: 在保持原意不变的前提下，可以适当调整措辞，使其更具吸引力。

    # 重要约束
    - 必须完整保留原始邮件中的所有 `{{...}}` 格式的占位符，不得修改或删除它们。
    - 返回一个且仅一个符合RFC 8259标准的JSON对象，该对象必须包含一个键 "optimized_text"，其值为优化后的完整邮件内容。

    # 待优化的原始邮件:
    ---
    {draft_content}
    ---
    """
    return parsing_service._call_ai_model(prompt, provider_key, user)
