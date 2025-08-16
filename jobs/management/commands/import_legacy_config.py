"""
Import Legacy AI Configuration

Command to import existing AI_MODELS configuration into the new model registry system.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pathlib import Path
import json


class Command(BaseCommand):
    help = 'Import legacy AI_MODELS configuration into new model registry'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path for converted configuration (default: config/ai_models.json)'
        )
        parser.add_argument(
            '--settings-output',
            type=str,
            help='Output file for Django settings format'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be converted without writing files'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        legacy_models = getattr(settings, 'AI_MODELS', {})
        
        if not legacy_models:
            self.stdout.write(
                self.style.WARNING('No AI_MODELS found in settings')
            )
            return

        self.stdout.write(f"Found {len(legacy_models)} legacy model configurations")

        # Convert legacy format to new format
        converted_models = self.convert_legacy_models(legacy_models)

        if options['dry_run']:
            self.show_conversion_preview(converted_models)
            return

        # Write JSON configuration
        output_path = options.get('output') or 'config/ai_models.json'
        self.write_json_config(converted_models, output_path)

        # Write settings configuration if requested
        if options.get('settings_output'):
            self.write_settings_config(converted_models, options['settings_output'])

    def convert_legacy_models(self, legacy_models: dict) -> dict:
        """Convert legacy AI_MODELS format to new model registry format."""
        converted = {}

        for model_id, legacy_config in legacy_models.items():
            # Basic conversion with intelligent defaults
            converted_config = {
                'name': legacy_config.get('name', model_id),
                'provider': legacy_config.get('provider', 'unknown'),
                'model_name': legacy_config.get('model_name', ''),
                'base_url': legacy_config.get('base_url', ''),
                'max_context_tokens': self._estimate_context_limit(model_id, legacy_config),
                'supports_json_mode': True,
                'supports_streaming': self._supports_streaming(model_id, legacy_config),
                'supports_function_calling': self._supports_function_calling(model_id, legacy_config),
                'rate_limits': self._estimate_rate_limits(model_id, legacy_config),
                'default_temperature': 0.1,
                'timeout_seconds': self._estimate_timeout(model_id, legacy_config),
                'adapter_class': self._determine_adapter_class(legacy_config.get('provider')),
                'cost_per_1k_input_tokens': self._estimate_input_cost(model_id, legacy_config),
                'cost_per_1k_output_tokens': self._estimate_output_cost(model_id, legacy_config),
                'description': f"Converted from legacy configuration: {legacy_config.get('name', model_id)}",
                'tags': self._generate_tags(model_id, legacy_config),
                'is_active': True,
                'is_deprecated': False
            }

            converted[model_id] = converted_config

        return converted

    def _estimate_context_limit(self, model_id: str, config: dict) -> int:
        """Estimate context limit based on model name."""
        model_name = config.get('model_name', '').lower()
        model_id_lower = model_id.lower()
        
        # Known context limits
        context_patterns = {
            '128k': 131072,
            '32k': 32768,
            '16k': 16384,
            '8k': 8192,
            '4k': 4096
        }
        
        for pattern, limit in context_patterns.items():
            if pattern in model_name or pattern in model_id_lower:
                return limit
        
        # Provider-specific defaults
        provider = config.get('provider', '').lower()
        provider_defaults = {
            'qwen': 32768,
            'kimi': 32768,
            'doubao': 32768,
            'hunyuan': 32768,
            'chatglm': 128000,
            'minimax': 245760,
            'deepseek': 32768,
            'together': 32768
        }
        
        return provider_defaults.get(provider, 8192)

    def _supports_streaming(self, model_id: str, config: dict) -> bool:
        """Determine if model supports streaming."""
        # Most modern models support streaming
        excluded_providers = []  # Add providers that don't support streaming
        provider = config.get('provider', '').lower()
        return provider not in excluded_providers

    def _supports_function_calling(self, model_id: str, config: dict) -> bool:
        """Determine if model supports function calling."""
        model_name = config.get('model_name', '').lower()
        
        # Known function calling support
        function_calling_models = [
            'qwen-plus', 'qwen-max', 'glm-4', 'gpt-'
        ]
        
        return any(pattern in model_name for pattern in function_calling_models)

    def _estimate_rate_limits(self, model_id: str, config: dict) -> dict:
        """Estimate rate limits based on provider and model."""
        provider = config.get('provider', '').lower()
        
        # Conservative defaults by provider
        provider_limits = {
            'qwen': {
                'requests_per_minute': 60,
                'tokens_per_minute': 100000,
                'requests_per_day': 1000,
                'concurrent_requests': 5
            },
            'kimi': {
                'requests_per_minute': 60,
                'tokens_per_minute': 80000,
                'requests_per_day': 1000,
                'concurrent_requests': 5
            },
            'doubao': {
                'requests_per_minute': 50,
                'tokens_per_minute': 70000,
                'requests_per_day': 800,
                'concurrent_requests': 4
            },
            'hunyuan': {
                'requests_per_minute': 40,
                'tokens_per_minute': 60000,
                'requests_per_day': 600,
                'concurrent_requests': 3
            },
            'chatglm': {
                'requests_per_minute': 50,
                'tokens_per_minute': 75000,
                'requests_per_day': 1000,
                'concurrent_requests': 5
            },
            'deepseek': {
                'requests_per_minute': 60,
                'tokens_per_minute': 100000,
                'requests_per_day': 1200,
                'concurrent_requests': 6
            },
            'minimax': {
                'requests_per_minute': 20,
                'tokens_per_minute': 30000,
                'requests_per_day': 300,
                'concurrent_requests': 2
            },
            'together': {
                'requests_per_minute': 30,
                'tokens_per_minute': 50000,
                'requests_per_day': 500,
                'concurrent_requests': 3
            }
        }
        
        return provider_limits.get(provider, {
            'requests_per_minute': 30,
            'tokens_per_minute': 50000,
            'requests_per_day': 500,
            'concurrent_requests': 3
        })

    def _estimate_timeout(self, model_id: str, config: dict) -> int:
        """Estimate appropriate timeout based on model characteristics."""
        model_name = config.get('model_name', '').lower()
        
        if 'turbo' in model_name or 'fast' in model_name:
            return 30
        elif '128k' in model_name or 'max' in model_name:
            return 180
        else:
            return 90

    def _determine_adapter_class(self, provider: str) -> str:
        """Determine the appropriate adapter class for the provider."""
        adapter_mapping = {
            'qwen': 'QwenAdapter',
            'kimi': 'KimiAdapter',
            'doubao': 'DoubaoAdapter',
            'hunyuan': 'HunyuanAdapter',
            'chatglm': 'ChatGLMAdapter',
            'zhipu': 'ChatGLMAdapter',
            'minimax': 'MiniMaxAdapter',
            'deepseek': 'DeepSeekAdapter',
            'together': 'TogetherAdapter'
        }
        
        return adapter_mapping.get(provider.lower(), 'OpenAICompatibleAdapter')

    def _estimate_input_cost(self, model_id: str, config: dict) -> float:
        """Estimate input token cost."""
        provider = config.get('provider', '').lower()
        model_name = config.get('model_name', '').lower()
        
        # Known pricing (approximate)
        if provider == 'qwen':
            if 'turbo' in model_name:
                return 0.003
            elif 'plus' in model_name:
                return 0.008
            elif 'max' in model_name:
                return 0.02
        elif provider == 'kimi':
            return 0.012
        elif provider == 'deepseek':
            return 0.001
        elif provider == 'together':
            return 0.0009
        
        return 0.01  # Default estimate

    def _estimate_output_cost(self, model_id: str, config: dict) -> float:
        """Estimate output token cost."""
        input_cost = self._estimate_input_cost(model_id, config)
        # Output is typically 2-3x input cost
        return input_cost * 2.5

    def _generate_tags(self, model_id: str, config: dict) -> list:
        """Generate appropriate tags for the model."""
        tags = ['legacy']  # Mark as converted from legacy
        
        provider = config.get('provider', '').lower()
        model_name = config.get('model_name', '').lower()
        
        # Provider tags
        tags.append(provider)
        
        # Language tags
        chinese_providers = ['qwen', 'kimi', 'doubao', 'hunyuan', 'chatglm', 'minimax', 'deepseek']
        if provider in chinese_providers:
            tags.append('chinese')
        else:
            tags.append('english')
        
        # Capability tags
        if 'turbo' in model_name or 'fast' in model_name:
            tags.append('fast')
        
        if '128k' in model_name or 'long' in model_name:
            tags.append('long-context')
        elif '32k' in model_name:
            tags.append('medium-context')
        
        if 'coder' in model_name or 'code' in model_name:
            tags.append('coding')
        
        if 'max' in model_name or 'pro' in model_name:
            tags.append('premium')
        
        return tags

    def show_conversion_preview(self, converted_models: dict):
        """Show preview of conversion without writing files."""
        self.stdout.write(self.style.SUCCESS("\n=== Conversion Preview ==="))
        
        for model_id, config in converted_models.items():
            self.stdout.write(f"\n{model_id}:")
            self.stdout.write(f"  Name: {config['name']}")
            self.stdout.write(f"  Provider: {config['provider']}")
            self.stdout.write(f"  Context: {config['max_context_tokens']:,} tokens")
            self.stdout.write(f"  Adapter: {config['adapter_class']}")
            self.stdout.write(f"  Tags: {', '.join(config['tags'])}")

    def write_json_config(self, converted_models: dict, output_path: str):
        """Write converted configuration to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            'version': '1.0',
            'description': 'AI Model Configurations converted from legacy format',
            'conversion_timestamp': '2024-01-15T00:00:00Z',
            'models': converted_models,
            'default_preferences': {
                'preferred_model': 'qwen_plus',
                'fallback_models': ['qwen_plus', 'qwen_turbo', 'kimi_32k'],
                'max_retries': 3,
                'timeout_seconds': 90
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        self.stdout.write(
            self.style.SUCCESS(f"✓ JSON configuration written to {output_file}")
        )

    def write_settings_config(self, converted_models: dict, output_path: str):
        """Write converted configuration to Django settings format."""
        output_file = Path(output_path)
        
        lines = [
            '"""',
            'Converted AI Model Configurations',
            'Generated from legacy AI_MODELS configuration',
            '"""',
            '',
            'AI_MODEL_CONFIGS = {'
        ]
        
        for model_id, config in converted_models.items():
            lines.append(f"    '{model_id}': {{")
            for key, value in config.items():
                if isinstance(value, str):
                    lines.append(f"        '{key}': '{value}',")
                elif isinstance(value, dict):
                    lines.append(f"        '{key}': {value},")
                elif isinstance(value, list):
                    lines.append(f"        '{key}': {value},")
                else:
                    lines.append(f"        '{key}': {value},")
            lines.append("    },")
            lines.append("")
        
        lines.extend([
            '}',
            '',
            '# Default preferences',
            "AI_DEFAULT_MODEL = 'qwen_plus'",
            "AI_DEFAULT_FALLBACK_MODELS = ['qwen_plus', 'qwen_turbo', 'kimi_32k']",
            "AI_DEFAULT_MAX_RETRIES = 3",
        ])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        self.stdout.write(
            self.style.SUCCESS(f"✓ Settings configuration written to {output_file}")
        )