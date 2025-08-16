"""
AI Configuration Manager

Manages user preferences, model selection, and configuration overrides.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from django.contrib.auth.models import User
from django.core.cache import cache
from django.conf import settings

from .model_registry import ModelRegistry, ModelConfig, UserPreferences, model_registry

logger = logging.getLogger(__name__)


class AIConfigManager:
    """
    Manages AI model configurations and user preferences.
    
    Handles model selection, fallback logic, user preferences, and configuration overrides.
    """
    
    def __init__(self, registry: Optional[ModelRegistry] = None):
        """Initialize the configuration manager."""
        self.registry = registry or model_registry
        self.cache_timeout = getattr(settings, 'AI_CONFIG_CACHE_TIMEOUT', 300)  # 5 minutes
    
    def get_user_preferences(self, user: User) -> UserPreferences:
        """Get user-specific AI preferences."""
        cache_key = f"ai_preferences_{user.id}"
        preferences = cache.get(cache_key)
        
        if preferences is None:
            preferences = self._load_user_preferences(user)
            cache.set(cache_key, preferences, self.cache_timeout)
        
        return preferences
    
    def _load_user_preferences(self, user: User) -> UserPreferences:
        """Load user preferences from database or use defaults."""
        try:
            # Try to load from UserProfile or AIPreferences model if it exists
            from ...models import User as UserModel
            
            # For now, use default preferences
            # TODO: Implement UserAIPreferences model to store in database
            preferences = UserPreferences(
                user_id=user.id,
                preferred_model=self._get_default_preferred_model(),
                fallback_models=self._get_default_fallback_models(),
                max_retries=getattr(settings, 'AI_DEFAULT_MAX_RETRIES', 3),
                max_tokens_per_request=getattr(settings, 'AI_DEFAULT_MAX_TOKENS', None)
            )
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error loading user preferences for {user.username}: {e}")
            return UserPreferences(user_id=user.id)
    
    def _get_default_preferred_model(self) -> Optional[str]:
        """Get the default preferred model from settings."""
        return getattr(settings, 'AI_DEFAULT_MODEL', 'qwen_plus')
    
    def _get_default_fallback_models(self) -> List[str]:
        """Get default fallback models from settings."""
        return getattr(settings, 'AI_DEFAULT_FALLBACK_MODELS', [
            'qwen_plus', 'qwen_turbo', 'kimi_32k'
        ])
    
    def update_user_preferences(self, user: User, preferences: UserPreferences) -> None:
        """Update user preferences."""
        preferences.user_id = user.id
        
        # TODO: Save to database when UserAIPreferences model is implemented
        
        # Update cache
        cache_key = f"ai_preferences_{user.id}"
        cache.set(cache_key, preferences, self.cache_timeout)
        
        logger.info(f"Updated AI preferences for user {user.username}")
    
    def get_available_models_for_user(self, user: User) -> Dict[str, ModelConfig]:
        """Get models available to a specific user (based on API keys)."""
        try:
            from ...models import ApiKey
            
            # Get user's configured providers
            user_providers = set(
                ApiKey.objects.filter(user=user).values_list('provider', flat=True)
            )
            
            # Filter models by available providers
            available_models = {}
            for model_id, config in self.registry.get_active_models().items():
                if config.provider in user_providers:
                    available_models[model_id] = config
            
            return available_models
            
        except Exception as e:
            logger.error(f"Error getting available models for user {user.username}: {e}")
            return {}
    
    def select_model_for_user(self, user: User, requested_model: Optional[str] = None) -> Optional[ModelConfig]:
        """
        Select the best available model for a user.
        
        Selection priority:
        1. Requested model (if available and user has access)
        2. User's preferred model
        3. User's fallback models (in order)
        4. System default models
        """
        available_models = self.get_available_models_for_user(user)
        
        if not available_models:
            logger.warning(f"No models available for user {user.username}")
            return None
        
        preferences = self.get_user_preferences(user)
        
        # Try requested model first
        if requested_model and requested_model in available_models:
            return available_models[requested_model]
        
        # Try preferred model
        if preferences.preferred_model and preferences.preferred_model in available_models:
            return available_models[preferences.preferred_model]
        
        # Try fallback models in order
        for fallback_model in preferences.fallback_models:
            if fallback_model in available_models:
                return available_models[fallback_model]
        
        # Use first available model as last resort
        first_available = next(iter(available_models.values()))
        logger.info(f"Using first available model {first_available.model_id} for user {user.username}")
        return first_available
    
    def get_model_with_preferences(self, user: User, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model configuration merged with user preferences."""
        model_config = self.registry.get_model(model_id)
        if not model_config:
            return None
        
        preferences = self.get_user_preferences(user)
        
        # Merge model config with user preferences
        merged_config = {
            'model_config': model_config,
            'max_retries': preferences.max_retries,
            'timeout': preferences.timeout_override or model_config.timeout_seconds,
            'max_tokens': preferences.max_tokens_per_request or model_config.default_max_tokens,
            'temperature': preferences.default_temperature or model_config.default_temperature,
        }
        
        return merged_config
    
    def validate_user_model_access(self, user: User, model_id: str) -> Dict[str, Any]:
        """Validate that a user has access to a specific model."""
        model_config = self.registry.get_model(model_id)
        
        if not model_config:
            return {
                'has_access': False,
                'reason': 'model_not_found',
                'message': f'模型 {model_id} 不存在'
            }
        
        if not model_config.is_active:
            return {
                'has_access': False,
                'reason': 'model_inactive',
                'message': f'模型 {model_id} 当前不可用'
            }
        
        if model_config.is_deprecated:
            replacement = model_config.replacement_model
            return {
                'has_access': False,
                'reason': 'model_deprecated',
                'message': f'模型 {model_id} 已弃用' + (f'，请使用 {replacement}' if replacement else ''),
                'replacement_model': replacement
            }
        
        # Check if user has API key for this provider
        try:
            from ...models import ApiKey
            
            if not ApiKey.objects.filter(user=user, provider=model_config.provider).exists():
                return {
                    'has_access': False,
                    'reason': 'missing_api_key',
                    'message': f'缺少 {model_config.provider.upper()} 的API密钥',
                    'provider': model_config.provider
                }
            
            return {
                'has_access': True,
                'model_config': model_config
            }
            
        except Exception as e:
            logger.error(f"Error validating user model access: {e}")
            return {
                'has_access': False,
                'reason': 'validation_error',
                'message': '验证模型访问权限时出错'
            }
    
    def get_rate_limit_info(self, user: User, model_id: str) -> Dict[str, Any]:
        """Get rate limiting information for a user and model."""
        model_config = self.registry.get_model(model_id)
        if not model_config or not model_config.rate_limits:
            return {}
        
        preferences = self.get_user_preferences(user)
        rate_limits = model_config.rate_limits
        
        # Apply user-specific overrides
        effective_limits = {
            'requests_per_minute': rate_limits.requests_per_minute,
            'tokens_per_minute': rate_limits.tokens_per_minute,
            'requests_per_day': rate_limits.requests_per_day,
            'tokens_per_day': rate_limits.tokens_per_day,
            'concurrent_requests': rate_limits.concurrent_requests
        }
        
        # Apply user preferences (if more restrictive)
        if preferences.max_requests_per_hour:
            rpm_from_hourly = preferences.max_requests_per_hour // 60
            if not effective_limits['requests_per_minute'] or rpm_from_hourly < effective_limits['requests_per_minute']:
                effective_limits['requests_per_minute'] = rpm_from_hourly
        
        if preferences.max_tokens_per_hour:
            tpm_from_hourly = preferences.max_tokens_per_hour // 60
            if not effective_limits['tokens_per_minute'] or tpm_from_hourly < effective_limits['tokens_per_minute']:
                effective_limits['tokens_per_minute'] = tpm_from_hourly
        
        return effective_limits
    
    def get_fallback_chain(self, user: User, primary_model: str) -> List[str]:
        """Get the complete fallback chain for a user and primary model."""
        preferences = self.get_user_preferences(user)
        available_models = self.get_available_models_for_user(user)
        
        # Build fallback chain
        chain = []
        
        # Add primary model if available
        if primary_model in available_models:
            chain.append(primary_model)
        
        # Add user's fallback models
        for model_id in preferences.fallback_models:
            if model_id in available_models and model_id not in chain:
                chain.append(model_id)
        
        # Add system defaults
        for model_id in self._get_default_fallback_models():
            if model_id in available_models and model_id not in chain:
                chain.append(model_id)
        
        return chain
    
    def get_model_usage_stats(self, user: User, days: int = 30) -> Dict[str, Any]:
        """Get model usage statistics for a user."""
        # TODO: Implement when usage tracking is added
        return {
            'total_requests': 0,
            'total_tokens': 0,
            'models_used': [],
            'most_used_model': None,
            'period_days': days
        }
    
    def clear_user_cache(self, user: User) -> None:
        """Clear cached data for a user."""
        cache_key = f"ai_preferences_{user.id}"
        cache.delete(cache_key)
        logger.info(f"Cleared AI cache for user {user.username}")
    
    def clear_all_cache(self) -> None:
        """Clear all AI-related cache data."""
        # This would require a cache key pattern, implementing basic version
        logger.info("Cleared all AI configuration cache")


# Global configuration manager instance
config_manager = AIConfigManager()