"""
AI Model Registry

Centralized registry for all supported AI models and their configurations.
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Type, Any, Union
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimits:
    """Rate limiting configuration for a model."""
    requests_per_minute: Optional[int] = None
    tokens_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    tokens_per_day: Optional[int] = None
    concurrent_requests: Optional[int] = None


@dataclass
class ModelConfig:
    """Configuration for a single AI model."""
    # Basic model information
    model_id: str
    name: str
    provider: str
    model_name: str
    base_url: str
    
    # Model capabilities
    max_context_tokens: int
    supports_json_mode: bool = True
    supports_streaming: bool = False
    supports_function_calling: bool = False
    
    # Performance and limits
    rate_limits: Optional[RateLimits] = None
    default_temperature: float = 0.1
    default_max_tokens: Optional[int] = None
    timeout_seconds: int = 60
    
    # Adapter configuration
    adapter_class: str = "OpenAICompatibleAdapter"
    adapter_config: Optional[Dict[str, Any]] = None
    
    # Cost information (optional)
    cost_per_1k_input_tokens: Optional[float] = None
    cost_per_1k_output_tokens: Optional[float] = None
    
    # Status and availability
    is_active: bool = True
    is_deprecated: bool = False
    deprecation_date: Optional[str] = None
    replacement_model: Optional[str] = None
    
    # Additional metadata
    description: Optional[str] = None
    documentation_url: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        """Post-initialization validation and defaults."""
        if self.tags is None:
            self.tags = []
        
        if self.rate_limits is None:
            self.rate_limits = RateLimits()
        
        # Validate required fields
        required_fields = ['model_id', 'name', 'provider', 'model_name', 'base_url', 'max_context_tokens']
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Required field '{field}' is missing or empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        # Convert RateLimits to dict if present
        if self.rate_limits:
            data['rate_limits'] = asdict(self.rate_limits)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelConfig':
        """Create ModelConfig from dictionary."""
        # Handle rate_limits
        if 'rate_limits' in data and data['rate_limits']:
            data['rate_limits'] = RateLimits(**data['rate_limits'])
        
        return cls(**data)


@dataclass
class UserPreferences:
    """User-specific AI model preferences."""
    user_id: Optional[int] = None
    preferred_model: Optional[str] = None
    fallback_models: List[str] = None
    max_retries: int = 3
    max_tokens_per_request: Optional[int] = None
    default_temperature: Optional[float] = None
    timeout_override: Optional[int] = None
    
    # User-specific rate limiting
    max_requests_per_hour: Optional[int] = None
    max_tokens_per_hour: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization defaults."""
        if self.fallback_models is None:
            self.fallback_models = []


class ModelRegistry:
    """
    Centralized registry for AI model configurations.
    
    Supports loading from Django settings, JSON files, or programmatic configuration.
    """
    
    def __init__(self):
        """Initialize the model registry."""
        self._models: Dict[str, ModelConfig] = {}
        self._loaded = False
        self._config_sources = []
    
    def load_from_settings(self) -> None:
        """Load model configurations from Django settings."""
        try:
            # Load from enhanced AI_MODELS setting
            models_config = getattr(settings, 'AI_MODEL_CONFIGS', {})
            
            if not models_config:
                # Fallback to legacy AI_MODELS format
                models_config = self._convert_legacy_settings()
            
            for model_id, config_data in models_config.items():
                try:
                    model_config = ModelConfig.from_dict({
                        'model_id': model_id,
                        **config_data
                    })
                    self._models[model_id] = model_config
                except Exception as e:
                    logger.error(f"Failed to load model config for '{model_id}': {e}")
            
            self._config_sources.append('settings')
            logger.info(f"Loaded {len(self._models)} models from Django settings")
            
        except Exception as e:
            logger.error(f"Failed to load models from settings: {e}")
    
    def load_from_json(self, config_path: Union[str, Path]) -> None:
        """Load model configurations from JSON file."""
        try:
            config_path = Path(config_path)
            
            if not config_path.exists():
                logger.warning(f"Config file not found: {config_path}")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            models_config = data.get('models', {})
            
            for model_id, config_data in models_config.items():
                try:
                    model_config = ModelConfig.from_dict({
                        'model_id': model_id,
                        **config_data
                    })
                    self._models[model_id] = model_config
                except Exception as e:
                    logger.error(f"Failed to load model config for '{model_id}' from JSON: {e}")
            
            self._config_sources.append(f'json:{config_path}')
            logger.info(f"Loaded {len(models_config)} models from JSON file: {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load models from JSON file '{config_path}': {e}")
    
    def _convert_legacy_settings(self) -> Dict[str, Dict[str, Any]]:
        """Convert legacy AI_MODELS format to new format."""
        legacy_models = getattr(settings, 'AI_MODELS', {})
        converted = {}
        
        for model_id, legacy_config in legacy_models.items():
            # Map legacy fields to new format
            converted[model_id] = {
                'name': legacy_config.get('name', model_id),
                'provider': legacy_config.get('provider', 'unknown'),
                'model_name': legacy_config.get('model_name', ''),
                'base_url': legacy_config.get('base_url', ''),
                'max_context_tokens': self._estimate_context_limit(model_id, legacy_config),
                'description': f"Legacy model configuration for {model_id}",
                'tags': ['legacy']
            }
        
        return converted
    
    def _estimate_context_limit(self, model_id: str, config: Dict[str, Any]) -> int:
        """Estimate context limit for legacy models."""
        model_name = config.get('model_name', '').lower()
        
        # Common context limits based on model names
        if '128k' in model_name or '128k' in model_id:
            return 131072
        elif '32k' in model_name or '32k' in model_id:
            return 32768
        elif '16k' in model_name or '16k' in model_id:
            return 16384
        elif '8k' in model_name or '8k' in model_id:
            return 8192
        elif '4k' in model_name or '4k' in model_id:
            return 4096
        elif 'qwen-max' in model_name:
            return 8192
        elif 'qwen-plus' in model_name:
            return 32768
        elif 'qwen-turbo' in model_name:
            return 8192
        elif 'moonshot' in model_name:
            return 32768
        elif 'glm-4' in model_name:
            return 128000
        elif 'abab6.5' in model_name:
            return 245760
        else:
            return 8192  # Default fallback
    
    def add_model(self, model_config: ModelConfig) -> None:
        """Add a model configuration to the registry."""
        self._models[model_config.model_id] = model_config
        logger.info(f"Added model to registry: {model_config.model_id}")
    
    def remove_model(self, model_id: str) -> bool:
        """Remove a model from the registry."""
        if model_id in self._models:
            del self._models[model_id]
            logger.info(f"Removed model from registry: {model_id}")
            return True
        return False
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get a specific model configuration."""
        return self._models.get(model_id)
    
    def get_all_models(self) -> Dict[str, ModelConfig]:
        """Get all model configurations."""
        return self._models.copy()
    
    def get_active_models(self) -> Dict[str, ModelConfig]:
        """Get only active (non-deprecated) model configurations."""
        return {
            model_id: config for model_id, config in self._models.items()
            if config.is_active and not config.is_deprecated
        }
    
    def get_models_by_provider(self, provider: str) -> Dict[str, ModelConfig]:
        """Get all models for a specific provider."""
        return {
            model_id: config for model_id, config in self._models.items()
            if config.provider == provider
        }
    
    def get_models_by_tag(self, tag: str) -> Dict[str, ModelConfig]:
        """Get all models with a specific tag."""
        return {
            model_id: config for model_id, config in self._models.items()
            if tag in config.tags
        }
    
    def search_models(self, query: str) -> Dict[str, ModelConfig]:
        """Search models by name, provider, or description."""
        query = query.lower()
        results = {}
        
        for model_id, config in self._models.items():
            if (query in model_id.lower() or
                query in config.name.lower() or
                query in config.provider.lower() or
                (config.description and query in config.description.lower())):
                results[model_id] = config
        
        return results
    
    def validate_all_models(self) -> Dict[str, List[str]]:
        """Validate all model configurations and return any errors."""
        errors = {}
        
        for model_id, config in self._models.items():
            model_errors = []
            
            # Check required fields
            if not config.base_url:
                model_errors.append("Missing base_url")
            
            if not config.model_name:
                model_errors.append("Missing model_name")
            
            if config.max_context_tokens <= 0:
                model_errors.append("Invalid max_context_tokens")
            
            # Check adapter class
            if not config.adapter_class:
                model_errors.append("Missing adapter_class")
            
            if model_errors:
                errors[model_id] = model_errors
        
        return errors
    
    def export_to_json(self, output_path: Union[str, Path]) -> None:
        """Export all model configurations to JSON file."""
        output_path = Path(output_path)
        
        data = {
            'version': '1.0',
            'generated_by': 'ModelRegistry',
            'config_sources': self._config_sources,
            'models': {
                model_id: config.to_dict()
                for model_id, config in self._models.items()
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(self._models)} models to {output_path}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total_models = len(self._models)
        active_models = len(self.get_active_models())
        
        providers = {}
        for config in self._models.values():
            providers[config.provider] = providers.get(config.provider, 0) + 1
        
        return {
            'total_models': total_models,
            'active_models': active_models,
            'deprecated_models': total_models - active_models,
            'providers': providers,
            'config_sources': self._config_sources
        }
    
    def ensure_loaded(self) -> None:
        """Ensure the registry is loaded from available sources."""
        if self._loaded:
            return
        
        # Try to load from settings first
        self.load_from_settings()
        
        # Try to load from default JSON config file
        default_config_path = Path(settings.BASE_DIR) / 'config' / 'ai_models.json'
        if default_config_path.exists():
            self.load_from_json(default_config_path)
        
        self._loaded = True


# Global registry instance
model_registry = ModelRegistry()