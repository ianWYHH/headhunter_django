"""
AI Manager (Simplified)

简化的AI管理器，直接使用simple_ai_manager。
保持向后兼容性，重定向到简化的实现。
"""

import logging
from typing import Dict, Any, Optional, List
from django.contrib.auth.models import User
from django.conf import settings

from .simple_ai_manager import SimpleAIManager

logger = logging.getLogger(__name__)


class AIManager:
    """
    简化的AI管理器，重定向到SimpleAIManager。
    保持API兼容性。
    """
    
    def __init__(self):
        """Initialize the simplified AI manager."""
        self.simple_manager = SimpleAIManager()
        
    def get_available_models(self, user: User) -> Dict[str, Any]:
        """获取可用的AI模型列表"""
        return self.simple_manager.get_available_models(user)
    
    def get_model_info(self, model_key: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        return self.simple_manager.get_model_info(model_key)
    
    def call_model_with_fallback(self, user: User, primary_model: str, 
                                content: str, parse_type: str = 'candidate') -> Dict[str, Any]:
        """
        调用AI模型（简化版，无回退机制）
        
        Args:
            user: 用户对象
            primary_model: 主要模型键值
            content: 要解析的内容
            parse_type: 解析类型 ('candidate' 或 'job')
        
        Returns:
            解析结果字典
        """
        logger.info(f"使用简化AI管理器调用模型: {primary_model}")
        
        # 直接调用简化管理器，无回退机制
        result = self.simple_manager.parse_with_model(
            user=user,
            model_key=primary_model,
            content=content,
            parse_type=parse_type
        )
        
        if result['success']:
            return {
                'success': True,
                'data': result['data'],
                'model_used': result.get('model_used', primary_model),
                'model_name': result.get('model_name', primary_model)
            }
        else:
            return {
                'success': False,
                'error': result.get('error', '解析失败'),
                'data': None
            }
    
    def check_user_access(self, user: User, model_key: str) -> bool:
        """检查用户是否有权限使用指定模型"""
        # 简化版：检查是否有对应的API密钥
        try:
            from jobs.models import ApiKey
            model_info = self.get_model_info(model_key)
            if not model_info:
                return False
            
            provider = model_info.get('provider')
            if not provider:
                return False
            
            return ApiKey.objects.filter(user=user, provider=provider).exists()
        except Exception as e:
            logger.error(f"检查用户权限失败: {e}")
            return False


# 创建全局实例（保持向后兼容）
ai_manager = AIManager()