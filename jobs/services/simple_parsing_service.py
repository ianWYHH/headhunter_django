"""
简化的解析服务
去掉复杂的回退机制，提供直接的AI解析功能
"""

import json
import logging
from typing import Dict, Any
from django.contrib.auth.models import User
from jobs.models import ApiKey

logger = logging.getLogger(__name__)


def _normalize_job_data(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    规范化职位数据格式，确保字段名与模板期待的一致
    
    Args:
        job_data: AI返回的原始职位数据
        
    Returns:
        规范化后的职位数据
    """
    # 从simple_ai_manager导入关键词列表
    from .simple_ai_manager import RESEARCH_DIRECTION_KEYWORDS
    
    normalized = job_data.copy()
    
    # 处理location -> locations的转换
    if 'location' in normalized and 'locations' not in normalized:
        location_value = normalized.pop('location')
        if isinstance(location_value, list):
            normalized['locations'] = location_value
        elif isinstance(location_value, str):
            # 如果是字符串，按逗号分割
            normalized['locations'] = [loc.strip() for loc in location_value.split(',') if loc.strip()]
        else:
            normalized['locations'] = []
    
    # 确保locations字段存在且为列表
    if 'locations' not in normalized:
        normalized['locations'] = []
    
    # 确保level_set字段存在且为列表
    if 'level_set' not in normalized:
        normalized['level_set'] = []
    
    # 确保notes字段存在且为字符串
    if 'notes' not in normalized:
        normalized['notes'] = ''
    
    # 处理并过滤关键词，严格按照RESEARCH_DIRECTION_KEYWORDS
    raw_keywords = []
    if 'keywords' in normalized:
        if isinstance(normalized['keywords'], list):
            raw_keywords = normalized['keywords']
        elif isinstance(normalized['keywords'], str):
            raw_keywords = [kw.strip() for kw in normalized['keywords'].split(',') if kw.strip()]
    
    # 过滤关键词，只保留RESEARCH_DIRECTION_KEYWORDS中包含的
    filtered_keywords = []
    for keyword in raw_keywords:
        if keyword in RESEARCH_DIRECTION_KEYWORDS:
            filtered_keywords.append(keyword)
        else:
            # 检查是否包含任何允许的关键词（不区分大小写）
            keyword_lower = keyword.lower()
            for allowed_keyword in RESEARCH_DIRECTION_KEYWORDS:
                if allowed_keyword.lower() in keyword_lower or keyword_lower in allowed_keyword.lower():
                    filtered_keywords.append(allowed_keyword)
                    break
    
    # 去重并保持顺序
    seen = set()
    normalized['keywords'] = [kw for kw in filtered_keywords if not (kw in seen or seen.add(kw))]
    
    # 确保必要的字符串字段存在
    for field in ['title', 'company_name', 'department', 'salary_range', 'job_description', 'job_requirement']:
        if field not in normalized:
            normalized[field] = ''
    
    return normalized


def parse_jobs_with_ai(text_content: str, user: User, provider_key: str = None) -> Dict[str, Any]:
    """
    使用AI解析职位信息（简化版）
    
    Args:
        text_content: 要解析的文本内容
        user: 用户对象
        provider_key: AI模型键值，如 'qwen_plus'
    
    Returns:
        解析结果字典
    """
    try:
        # 使用简化的AI管理器
        from .simple_ai_manager import simple_ai_manager
        
        # 使用默认模型（如果没有指定）
        if not provider_key:
            provider_key = 'qwen_plus'
        
        # 调用简化的AI解析
        result = simple_ai_manager.parse_with_model(
            user=user,
            model_key=provider_key, 
            content=text_content,
            parse_type='job'
        )
        
        if result['success']:
            logger.info(f"AI解析成功，使用模型: {result.get('model_used')}")
            
            # 尝试解析JSON数据
            try:
                if isinstance(result['data'], str):
                    parsed_data = json.loads(result['data'])
                else:
                    parsed_data = result['data']
                
                # 处理嵌套的jobs格式
                jobs_data = []
                if 'jobs' in parsed_data:
                    for item in parsed_data['jobs']:
                        if isinstance(item, dict):
                            # 检查是否有嵌套的jobs字段
                            if 'jobs' in item and isinstance(item['jobs'], list):
                                # 处理嵌套情况，提取内层jobs
                                for nested_job in item['jobs']:
                                    jobs_data.append(_normalize_job_data(nested_job))
                            else:
                                # 正常情况，直接添加
                                jobs_data.append(_normalize_job_data(item))
                else:
                    # 单个职位的情况
                    if isinstance(parsed_data, dict):
                        jobs_data = [_normalize_job_data(parsed_data)]
                    elif isinstance(parsed_data, list):
                        jobs_data = [_normalize_job_data(job) for job in parsed_data]
                
                return {
                    'jobs': jobs_data,
                    'model_used': result.get('model_used'),
                    'model_name': result.get('model_name')
                }
                    
            except json.JSONDecodeError:
                logger.warning("AI返回的数据不是有效JSON，直接返回")
                return {"jobs": [{"description": result['data']}]}
        
        else:
            logger.error(f"AI解析失败: {result['error']}")
            return {
                "error": "解析失败", 
                "message": result['error']
            }
            
    except Exception as e:
        logger.error(f"解析过程异常: {e}")
        return {
            "error": "系统错误",
            "message": f"解析过程出现异常: {str(e)}"
        }


def parse_candidates_with_ai(text_content: str, user: User, provider_key: str = None) -> Dict[str, Any]:
    """
    使用AI解析候选人简历（简化版）
    
    Args:
        text_content: 要解析的文本内容
        user: 用户对象
        provider_key: AI模型键值，如 'qwen_plus'
    
    Returns:
        解析结果字典
    """
    try:
        # 使用简化的AI管理器
        from .simple_ai_manager import simple_ai_manager
        
        # 使用默认模型（如果没有指定）
        if not provider_key:
            provider_key = 'qwen_plus'
        
        # 调用简化的AI解析
        result = simple_ai_manager.parse_with_model(
            user=user,
            model_key=provider_key,
            content=text_content,
            parse_type='candidate'
        )
        
        if result['success']:
            logger.info(f"AI解析成功，使用模型: {result.get('model_used')}")
            
            # 尝试解析JSON数据
            try:
                logger.info(f"原始AI响应数据类型: {type(result['data'])}")
                logger.info(f"原始AI响应内容: {str(result['data'])[:500]}...")
                
                if isinstance(result['data'], str):
                    parsed_data = json.loads(result['data'])
                    logger.info("成功解析JSON字符串")
                else:
                    parsed_data = result['data']
                    logger.info("直接使用字典数据")
                
                logger.info(f"解析后数据类型: {type(parsed_data)}")
                logger.info(f"解析后数据结构: {parsed_data}")
                
                # AI现在直接返回{"candidates": [...]}格式，无需再包装
                if isinstance(parsed_data, dict) and "candidates" in parsed_data:
                    logger.info("数据包含candidates字段，直接返回")
                    logger.info(f"candidates数量: {len(parsed_data['candidates'])}")
                    return parsed_data
                else:
                    # 如果AI没有按预期格式返回，进行兼容性处理
                    logger.warning("AI没有返回预期的candidates格式，进行兼容性处理")
                    if isinstance(parsed_data, dict):
                        wrapped_data = {"candidates": [parsed_data]}
                        logger.info(f"包装单个字典为: {wrapped_data}")
                        return wrapped_data
                    else:
                        wrapped_data = {"candidates": parsed_data if isinstance(parsed_data, list) else [parsed_data]}
                        logger.info(f"包装列表/其他为: {wrapped_data}")
                        return wrapped_data
                    
            except json.JSONDecodeError:
                logger.warning("AI返回的数据不是有效JSON，直接返回")
                return {"candidates": [{"description": result['data']}]}
        
        else:
            logger.error(f"AI解析失败: {result['error']}")
            return {
                "error": "解析失败",
                "message": result['error']
            }
            
    except Exception as e:
        logger.error(f"解析过程异常: {e}")
        return {
            "error": "系统错误", 
            "message": f"解析过程出现异常: {str(e)}"
        }


def get_available_models() -> Dict[str, Any]:
    """获取可用的AI模型列表"""
    try:
        from .simple_ai_manager import simple_ai_manager
        return simple_ai_manager.get_available_models()
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        return {}


def get_model_info(model_key: str) -> Dict[str, Any]:
    """获取指定模型的详细信息"""
    try:
        from .simple_ai_manager import simple_ai_manager
        return simple_ai_manager.get_model_info(model_key)
    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        return {}