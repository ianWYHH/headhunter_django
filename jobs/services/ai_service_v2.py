"""
AI Service V2

Enhanced AI service using the new adapter architecture.
This module provides the same interface as the original ai_service.py
but uses the new AIManager and adapter system underneath.
"""

from typing import Dict, Any
from django.contrib.auth.models import User

from .simple_ai_manager import SimpleAIManager

# 创建简化AI管理器实例
simple_ai_manager = SimpleAIManager()


def generate_email_draft(keywords: str, job: dict, user_name: str, provider_key: str, user: User) -> Dict[str, Any]:
    """
    根据关键词、职位信息和场景，调用AI生成邮件初稿。
    
    Args:
        keywords: 核心诉求关键词
        job: 职位信息字典
        user_name: 用户姓名
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        包含生成结果的字典
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
    3. 正文开头请使用 `{{{{candidate.salutation}}}}` 作为尊称占位符。
    4. 正文结尾请使用 `{{{{user.signature}}}}` 作为签名占位符。
    5. 邮件内容应突出职位的核心吸引力，并自然地融入核心诉求。
    6. 以邀请对方进一步沟通为结尾，引导其回复。
    7. 返回一个且仅一个符合RFC 8259标准的JSON对象，该对象必须包含 "subject" 和 "body" 两个键。不要返回任何JSON以外的解释性文字。
    """
    
    result = simple_ai_manager.parse_with_model(user, provider_key, prompt, 'candidate')
    return result


def optimize_email_content(draft_content: str, provider_key: str, user: User) -> Dict[str, Any]:
    """
    调用AI对用户输入的邮件草稿进行润色和优化。
    
    Args:
        draft_content: 待优化的邮件草稿内容
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        包含优化结果的字典
    """
    prompt = f"""
    你是一位专业的商务沟通文案专家，请将以下邮件内容进行润色和优化。

    # 优化目标
    - **语气**: 更专业、更具说服力、更自然流畅。
    - **结构**: 逻辑更清晰，重点更突出。
    - **内容**: 在保持原意不变的前提下，可以适当调整措辞，使其更具吸引力。

    # 重要约束
    - 必须完整保留原始邮件中的所有 `{{{{...}}}}` 格式的占位符，不得修改或删除它们。
    - 返回一个且仅一个符合RFC 8259标准的JSON对象，该对象必须包含一个键 "optimized_text"，其值为优化后的完整邮件内容。

    # 待优化的原始邮件:
    ---
    {draft_content}
    ---
    """
    
    result = simple_ai_manager.parse_with_model(user, provider_key, prompt, 'candidate')
    return result


def generate_template_draft(keywords: str, provider_key: str, user: User) -> Dict[str, Any]:
    """
    根据关键词，调用AI生成邮件模板。
    
    Args:
        keywords: 核心诉求关键词
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        包含生成结果的字典
    """
    from .simple_ai_manager import simple_ai_manager
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    prompt = f"""
    你是一位专业的猎头招聘文案专家，请根据以下核心诉求，为我撰写一个专业的、通用的邮件模板。

    # 核心诉求 (模板需要围绕这个主题)
    - {keywords}

    # 撰写要求
    1. 模板需包含 "name" (模板名称), "subject" (主题) 和 "body" (正文) 三个部分。
    2. "name" 应该根据核心诉求生成一个简洁、明确的模板名称。
    3. 正文内容必须包含 `{{{{candidate.salutation}}}}`, `{{{{job.title}}}}`, `{{{{job.company_name}}}}`, `{{{{user.name}}}}`, `{{{{user.signature}}}}` 等通用占位符，以确保模板的通用性。
    4. 模板内容应结构清晰、语言专业，便于用户直接使用或稍作修改。
    5. 返回一个且仅一个符合RFC 8259标准的JSON对象，该对象必须包含 "name", "subject", "body" 三个键。不要返回任何JSON以外的内容。
    """
    
    try:
        result = simple_ai_manager.parse_with_model(user, provider_key, prompt, 'template')
        
        if result.get('success'):
            # 尝试解析AI返回的JSON数据
            ai_data = result.get('data', {})
            if isinstance(ai_data, str):
                try:
                    ai_data = json.loads(ai_data)
                except json.JSONDecodeError:
                    logger.error(f"AI返回的不是有效JSON: {ai_data}")
                    return {"error": "AI返回格式错误", "message": "生成的内容不是有效的JSON格式"}
            
            # 验证必要字段
            if isinstance(ai_data, dict) and all(key in ai_data for key in ['name', 'subject', 'body']):
                return {
                    "name": ai_data.get('name', ''),
                    "subject": ai_data.get('subject', ''),
                    "body": ai_data.get('body', ''),
                    "model_used": result.get('model_used', provider_key)
                }
            else:
                logger.error(f"AI返回的数据缺少必要字段: {ai_data}")
                return {"error": "数据格式错误", "message": "AI生成的模板缺少必要字段"}
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"AI模板生成失败: {error_msg}")
            return {"error": "生成失败", "message": error_msg}
    
    except Exception as e:
        logger.error(f"模板生成异常: {str(e)}")
        return {"error": "系统错误", "message": f"生成过程中发生异常: {str(e)}"}


def parse_job_text(text: str, provider_key: str, user: User) -> Dict[str, Any]:
    """
    解析职位文本，提取结构化信息。
    
    Args:
        text: 待解析的职位文本
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        包含解析结果的字典
    """
    from ..services.parsing_service import RESEARCH_DIRECTION_KEYWORDS
    
    keywords_str = "、".join(RESEARCH_DIRECTION_KEYWORDS)
    
    prompt = f"""
请解析以下职位信息，提取关键字段，并返回JSON格式数据。

# 标准化关键词列表 (请从中选择匹配的关键词)
{keywords_str}

# 任务要求
1. 提取职位标题、公司名称、薪资范围、工作地点、职位描述、职位要求等信息
2. 从原始技能中识别并匹配标准化关键词
3. 返回标准的JSON数组格式

# 待解析文本:
---
{text}
---

# 返回格式 (JSON数组，每个对象包含以下字段):
- title: 职位名称
- company_name: 公司名称
- salary_range: 薪资范围
- locations: 工作地点数组
- job_description: 职位描述
- job_requirement: 职位要求
- raw_skills: 原始技能数组
- keywords: 匹配的标准化关键词数组
- level_set: 职级要求数组

请返回一个且仅一个符合RFC 8259标准的JSON对象，该对象必须包含 "jobs" 键，其值为职位信息数组。
"""
    
    result = simple_ai_manager.parse_with_model(user, provider_key, prompt, 'candidate')
    return result


# Utility functions for the new architecture
def get_available_models_for_user(user: User) -> Dict[str, Dict[str, Any]]:
    """
    获取用户可用的AI模型列表。
    
    Args:
        user: 用户对象
        
    Returns:
        用户可用的模型字典
    """
    return simple_ai_manager.get_available_models(user)


def check_model_access(user: User, provider_key: str) -> Dict[str, Any]:
    """
    检查用户是否有权限使用指定的AI模型。
    
    Args:
        user: 用户对象
        provider_key: 模型标识符
        
    Returns:
        访问检查结果
    """
    return simple_ai_manager.get_model_info(provider_key) is not None


def get_model_info(provider_key: str) -> Dict[str, Any]:
    """
    获取指定模型的信息。
    
    Args:
        provider_key: 模型标识符
        
    Returns:
        模型信息字典
    """
    return simple_ai_manager.get_model_info(provider_key) or {}


def get_supported_providers() -> Dict[str, str]:
    """
    获取所有支持的AI服务提供商。
    
    Returns:
        提供商名称到描述的映射
    """
    # 返回支持的提供商列表
    from django.conf import settings
    models = settings.AI_MODELS
    providers = set(model.get('provider') for model in models.values() if model.get('provider'))
    return list(providers)