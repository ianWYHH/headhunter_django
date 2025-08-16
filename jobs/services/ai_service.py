# 使用新的适配器架构，同时保持向后兼容性
try:
    from .ai_service_v2 import (
        generate_email_draft, 
        optimize_email_content, 
        generate_template_draft,
        get_available_models_for_user,
        check_model_access,
        get_model_info,
        get_supported_providers
    )
    # 标记使用新系统
    _using_new_architecture = True
except ImportError:
    # 如果新系统不可用，回退到旧实现
    from . import parsing_service # 复用底层的AI调用逻辑
    _using_new_architecture = False
    
    def generate_email_draft(keywords: str, job: dict, user_name: str, provider_key: str, user):
        """
        根据关键词、职位信息和场景，调用AI生成邮件初稿。
        """
        prompt = f"""你是一位顶尖的猎头顾问，请根据以下信息，撰写一封专业、简洁且富有吸引力的中文职位推荐邮件。

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
3. 正文开头请使用 `{{{{candidate.salutation}}}}` 作为尊称占位符。
4. 正文结尾请使用 `{{{{user.signature}}}}` 作为签名占位符。
5. 邮件内容应突出职位的核心吸引力，并自然地融入核心诉求。
6. 以邀请对方进一步沟通为结尾，引导其回复。
7. 返回一个且仅一个符合RFC 8259标准的JSON对象，该对象必须包含 "subject" 和 "body" 两个键。不要返回任何JSON以外的解释性文字。

示例输出格式:
{{"subject": "关于Code大模型算法工程师职位的推荐", "body": "{{{{candidate.salutation}}}}，\\n\\n我是{user_name}，专业猎头顾问。根据您的技术背景，我认为这个职位非常适合您...\\n\\n期待您的回复！\\n\\n{{{{user.signature}}}}"}}"""
        
        print(f"📤 发送给AI的prompt长度: {len(prompt)} 字符")
        print(f"🎯 职位信息详情: {job}")
        
        result = parsing_service._call_ai_model(prompt, provider_key, user)
        print(f"📥 AI原始返回: {result}")
        
        return result

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

    def generate_template_draft(keywords: str, provider_key: str, user):
        """
        **新增函数**: 根据关键词，调用AI生成邮件模板。
        """
        prompt = f"""
        你是一位专业的猎头招聘文案专家，请根据以下核心诉求，为我撰写一个专业的、通用的邮件模板。

        # 核心诉求 (模板需要围绕这个主题)
        - {keywords}

        # 撰写要求
        1. 模板需包含 "name" (模板名称), "subject" (主题) 和 "body" (正文) 三个部分。
        2. "name" 应该根据核心诉求生成一个简洁、明确的模板名称。
        3. 正文内容必须包含 `{{candidate.salutation}}`, `{{job.title}}`, `{{job.company_name}}`, `{{user.name}}`, `{{user.signature}}` 等通用占位符，以确保模板的通用性。
        4. 模板内容应结构清晰、语言专业，便于用户直接使用或稍作修改。
        5. 返回一个且仅一个符合RFC 8259标准的JSON对象，该对象必须包含 "name", "subject", "body" 三个键。
        """
        return parsing_service._call_ai_model(prompt, provider_key, user)
    
    # 如果使用旧系统，提供占位符函数
    def get_available_models_for_user(user):
        """获取用户可用的AI模型列表（旧系统占位符）"""
        from django.conf import settings
        return getattr(settings, 'AI_MODELS', {})
    
    def check_model_access(user, provider_key):
        """检查模型访问权限（旧系统占位符）"""
        return {"has_access": True, "reason": "legacy_system"}
    
    def get_model_info(provider_key):
        """获取模型信息（旧系统占位符）"""
        from django.conf import settings
        return getattr(settings, 'AI_MODELS', {}).get(provider_key, {})
    
    def get_supported_providers():
        """获取支持的提供商（旧系统占位符）"""
        return {}
