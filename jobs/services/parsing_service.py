"""
解析服务 (简化版)

重定向到简化的解析服务，保持向后兼容性。
"""

import logging
import re
import pandas as pd
import docx
from typing import Dict, Any, List
from django.contrib.auth.models import User

# 导入简化的解析服务
from .simple_parsing_service import parse_candidates_with_ai, parse_jobs_with_ai

logger = logging.getLogger(__name__)


def parse_candidate_resume(text_content: str, user: User, provider_key: str = None) -> Dict[str, Any]:
    """
    解析候选人简历（兼容旧接口）
    
    重定向到简化的解析服务
    """
    logger.info("调用简化的候选人解析服务")
    return parse_candidates_with_ai(text_content, user, provider_key)


def parse_multiple_job_descriptions(text_content: str, user: User, provider_key: str = None) -> List[Dict[str, Any]]:
    """
    解析多个职位描述（兼容旧接口）
    
    重定向到简化的解析服务
    """
    logger.info("调用简化的职位解析服务")
    result = parse_jobs_with_ai(text_content, user, provider_key)
    
    # 如果有错误，返回空列表（保持向后兼容）
    if 'error' in result:
        logger.error(f"职位解析失败: {result['error']}")
        return []
    
    # 返回jobs数组（兼容旧接口）
    return result.get('jobs', [])


def parse_job_description(text_content: str, user: User, provider_key: str = None) -> Dict[str, Any]:
    """
    解析单个职位描述（兼容旧接口）
    
    重定向到简化的解析服务
    """
    logger.info("调用简化的职位解析服务（单个）")
    result = parse_jobs_with_ai(text_content, user, provider_key)
    
    # 如果有错误，返回错误信息
    if 'error' in result:
        return {'error': result['error']}
    
    # 返回第一个职位（如果有的话）
    jobs = result.get('jobs', [])
    if jobs:
        return jobs[0]
    else:
        return {'error': '未能解析出任何职位信息'}


# 文件解析功能
def get_texts_from_file(file):
    """
    从上传的文件中提取文本列表 (支持TXT, XLSX, DOCX)
    
    Args:
        file: 上传的文件对象
        
    Returns:
        文本内容列表
    """
    try:
        if file.name.endswith('.txt'):
            content = file.read().decode("utf-8")
            return [j.strip() for j in re.split(r'\n\s*\n|\n---\n', content) if j.strip()]
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file, engine='openpyxl').fillna('')
            return [", ".join(f"{c}: {v}" for c, v in row.items() if str(v).strip()) for _, row in df.iterrows()]
        elif file.name.endswith('.docx'):
            doc = docx.Document(file)
            return ["\n".join([p.text for p in doc.paragraphs])]
        return []
    except Exception as e:
        logger.error(f"解析文件 {file.name} 时出错: {e}")
        return []


# 保持向后兼容的函数别名
parse_resume = parse_candidate_resume
parse_job = parse_job_description
parse_jobs = parse_multiple_job_descriptions