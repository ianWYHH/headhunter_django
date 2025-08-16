"""
Enhanced AI Model Configurations

This file contains the centralized model registry configuration that replaces
the legacy AI_MODELS setting with a more comprehensive structure.
"""

# AI Configuration Settings - 简化版，只保留原始的三个千问大模型
AI_MODEL_CONFIGS = {
    'qwen_plus': {
        'name': '通义千问-Plus (推荐)',
        'provider': 'qwen',
        'model_name': 'qwen-plus',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'max_context_tokens': 32768,
        'supports_json_mode': True,
        'supports_streaming': True,
        'supports_function_calling': True,
        'rate_limits': {
            'requests_per_minute': 60,
            'tokens_per_minute': 100000,
            'requests_per_day': 1000,
            'concurrent_requests': 5
        },
        'default_temperature': 0.1,
        'timeout_seconds': 60,
        'adapter_class': 'QwenAdapter',
        'cost_per_1k_input_tokens': 0.008,
        'cost_per_1k_output_tokens': 0.02,
        'description': '阿里云通义千问Plus模型，平衡性能和成本的推荐选择',
        'tags': ['recommended', 'balanced', 'chinese'],
        'is_active': True,
        'is_deprecated': False
    },
    
    'qwen_turbo': {
        'name': '通义千问-Turbo (高速)',
        'provider': 'qwen',
        'model_name': 'qwen-turbo',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'max_context_tokens': 8192,
        'supports_json_mode': True,
        'supports_streaming': True,
        'rate_limits': {
            'requests_per_minute': 120,
            'tokens_per_minute': 200000,
            'requests_per_day': 2000,
            'concurrent_requests': 10
        },
        'default_temperature': 0.1,
        'timeout_seconds': 30,
        'adapter_class': 'QwenAdapter',
        'cost_per_1k_input_tokens': 0.003,
        'cost_per_1k_output_tokens': 0.006,
        'description': '快速响应的通义千问模型，适合简单任务',
        'tags': ['fast', 'cost-effective', 'chinese'],
        'is_active': True,
        'is_deprecated': False
    },
    
    'qwen_max': {
        'name': '通义千问-Max (长文本)',
        'provider': 'qwen',
        'model_name': 'qwen-max',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'max_context_tokens': 8192,
        'supports_json_mode': True,
        'supports_streaming': True,
        'supports_function_calling': True,
        'rate_limits': {
            'requests_per_minute': 30,
            'tokens_per_minute': 50000,
            'requests_per_day': 500,
            'concurrent_requests': 3
        },
        'default_temperature': 0.1,
        'timeout_seconds': 120,
        'adapter_class': 'QwenAdapter',
        'cost_per_1k_input_tokens': 0.02,
        'cost_per_1k_output_tokens': 0.06,
        'description': '通义千问最强模型，适合复杂推理任务',
        'tags': ['premium', 'complex-reasoning', 'chinese'],
        'is_active': True,
        'is_deprecated': False
    }
}

# Default User Preferences
AI_DEFAULT_MODEL = 'qwen_plus'
AI_DEFAULT_FALLBACK_MODELS = ['qwen_plus', 'qwen_turbo', 'qwen_max']
AI_DEFAULT_MAX_RETRIES = 3
AI_DEFAULT_MAX_TOKENS = None
AI_DEFAULT_TEMPERATURE = 0.1
AI_DEFAULT_TIMEOUT = 90

# Cache Configuration
AI_CONFIG_CACHE_TIMEOUT = 300  # 5 minutes

# Rate Limiting Configuration
AI_ENABLE_RATE_LIMITING = True
AI_RATE_LIMIT_BACKEND = 'django_ratelimit'

# Legacy Support - for backward compatibility
# This maintains the old AI_MODELS format for existing code
AI_MODELS = {
    'qwen_plus': {
        'name': '通义千问-Plus (推荐)',
        'provider': 'qwen',
        'model_name': 'qwen-plus',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'max_context_tokens': 32768,
        'supports_json_mode': True,
        'supports_streaming': True,
        'supports_function_calling': True,
        'rate_limits': {'requests_per_minute': 60, 'tokens_per_minute': 100000, 'requests_per_day': 1000, 'concurrent_requests': 5},
        'default_temperature': 0.1,
        'timeout_seconds': 60,
        'adapter_class': 'QwenAdapter',
        'cost_per_1k_input_tokens': 0.008,
        'cost_per_1k_output_tokens': 0.02,
        'description': '阿里云通义千问Plus模型，平衡性能和成本的推荐选择',
        'tags': ['recommended', 'balanced', 'chinese'],
        'is_active': True,
        'is_deprecated': False,
    },
    'qwen_turbo': {
        'name': '通义千问-Turbo (高速)',
        'provider': 'qwen',
        'model_name': 'qwen-turbo',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'max_context_tokens': 8192,
        'supports_json_mode': True,
        'supports_streaming': True,
        'rate_limits': {'requests_per_minute': 120, 'tokens_per_minute': 200000, 'requests_per_day': 2000, 'concurrent_requests': 10},
        'default_temperature': 0.1,
        'timeout_seconds': 30,
        'adapter_class': 'QwenAdapter',
        'cost_per_1k_input_tokens': 0.003,
        'cost_per_1k_output_tokens': 0.006,
        'description': '快速响应的通义千问模型，适合简单任务',
        'tags': ['fast', 'cost-effective', 'chinese'],
        'is_active': True,
        'is_deprecated': False,
    },
    'qwen_max': {
        'name': '通义千问-Max (长文本)',
        'provider': 'qwen',
        'model_name': 'qwen-max',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'max_context_tokens': 8192,
        'supports_json_mode': True,
        'supports_streaming': True,
        'supports_function_calling': True,
        'rate_limits': {'requests_per_minute': 30, 'tokens_per_minute': 50000, 'requests_per_day': 500, 'concurrent_requests': 3},
        'default_temperature': 0.1,
        'timeout_seconds': 120,
        'adapter_class': 'QwenAdapter',
        'cost_per_1k_input_tokens': 0.02,
        'cost_per_1k_output_tokens': 0.06,
        'description': '通义千问最强模型，适合复杂推理任务',
        'tags': ['premium', 'complex-reasoning', 'chinese'],
        'is_active': True,
        'is_deprecated': False,
    }
}