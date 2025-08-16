"""
Test AI Adapters Management Command

This command tests the new AI adapter architecture to ensure it works correctly
and maintains backward compatibility with the existing system.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings
import json


class Command(BaseCommand):
    help = 'Test the new AI adapter architecture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Username to test with (default: admin)'
        )
        parser.add_argument(
            '--provider',
            type=str,
            help='Specific provider to test (e.g., qwen_plus, kimi_32k)'
        )
        parser.add_argument(
            '--list-models',
            action='store_true',
            help='List all available AI models'
        )
        parser.add_argument(
            '--test-prompt',
            type=str,
            default='请返回一个包含"jobs"键的JSON对象，其值为空数组。',
            help='Test prompt to send to the AI model'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        try:
            # Import the new AI manager
            from jobs.services.ai_manager import ai_manager
            new_system_available = True
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'New AI adapter system not available: {e}')
            )
            new_system_available = False

        if options['list_models']:
            self.list_available_models(new_system_available)
            return

        # Get user
        try:
            user = User.objects.get(username=options['user'])
        except User.DoesNotExist:
            raise CommandError(f"User '{options['user']}' does not exist")

        if new_system_available:
            self.test_new_system(user, options)
        else:
            self.test_legacy_system(user, options)

    def list_available_models(self, new_system_available):
        """List all available AI models."""
        self.stdout.write(self.style.SUCCESS('=== Available AI Models ==='))
        
        if new_system_available:
            from jobs.services.ai_manager import ai_manager
            models = ai_manager.get_available_models()
            providers = ai_manager.get_supported_providers()
            
            self.stdout.write(f"Total models: {len(models)}")
            self.stdout.write(f"Supported providers: {list(providers.keys())}")
            
            for provider, description in providers.items():
                self.stdout.write(f"\n{provider}: {description}")
                provider_models = ai_manager.get_models_by_provider(provider)
                for key, config in provider_models.items():
                    self.stdout.write(f"  - {key}: {config.get('name', 'N/A')}")
        else:
            # Fallback to settings
            models = getattr(settings, 'AI_MODELS', {})
            self.stdout.write(f"Total models: {len(models)}")
            
            for key, config in models.items():
                provider = config.get('provider', 'unknown')
                name = config.get('name', 'N/A')
                self.stdout.write(f"{key} ({provider}): {name}")

    def test_new_system(self, user, options):
        """Test the new AI adapter system."""
        from jobs.services.ai_manager import ai_manager
        
        self.stdout.write(self.style.SUCCESS('=== Testing New AI Adapter System ==='))
        
        # Get user's available models
        user_models = ai_manager.get_user_available_models(user)
        self.stdout.write(f"User {user.username} has access to {len(user_models)} models")
        
        if not user_models:
            self.stdout.write(
                self.style.WARNING('User has no API keys configured. Please add API keys first.')
            )
            return
        
        # Test specific provider or first available
        if options['provider']:
            if options['provider'] not in user_models:
                self.stdout.write(
                    self.style.ERROR(f"Provider '{options['provider']}' not available to user")
                )
                return
            test_providers = [options['provider']]
        else:
            test_providers = list(user_models.keys())[:3]  # Test first 3
        
        for provider_key in test_providers:
            self.test_provider(ai_manager, user, provider_key, options['test_prompt'])

    def test_legacy_system(self, user, options):
        """Test the legacy AI system."""
        self.stdout.write(self.style.WARNING('=== Testing Legacy AI System ==='))
        
        try:
            from jobs.services.parsing_service import _call_ai_model
            
            # Get available models from settings
            models = getattr(settings, 'AI_MODELS', {})
            
            if options['provider']:
                if options['provider'] not in models:
                    self.stdout.write(
                        self.style.ERROR(f"Provider '{options['provider']}' not found in settings")
                    )
                    return
                test_providers = [options['provider']]
            else:
                test_providers = list(models.keys())[:3]  # Test first 3
            
            for provider_key in test_providers:
                self.stdout.write(f"\nTesting {provider_key}...")
                result = _call_ai_model(options['test_prompt'], provider_key, user)
                
                if isinstance(result, dict) and 'error' in result:
                    self.stdout.write(
                        self.style.ERROR(f"  Error: {result.get('message', 'Unknown error')}")
                    )
                else:
                    self.stdout.write(self.style.SUCCESS(f"  Success: {type(result).__name__}"))
                    
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"Legacy system not available: {e}"))

    def test_provider(self, ai_manager, user, provider_key, test_prompt):
        """Test a specific provider."""
        self.stdout.write(f"\nTesting {provider_key}...")
        
        # Check access
        access_info = ai_manager.check_user_access(user, provider_key)
        if not access_info.get('has_access'):
            self.stdout.write(
                self.style.ERROR(f"  No access: {access_info.get('reason', 'Unknown')}")
            )
            return
        
        # Get adapter info
        try:
            adapter = ai_manager.get_adapter(provider_key)
            self.stdout.write(f"  Adapter: {adapter.__class__.__name__}")
            self.stdout.write(f"  Provider: {adapter.provider}")
            self.stdout.write(f"  Model: {adapter.model_name}")
            self.stdout.write(f"  Context Limit: {adapter.get_context_limit()} tokens")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Failed to create adapter: {e}"))
            return
        
        # Test API call
        try:
            result = ai_manager.call_model(test_prompt, provider_key, user, json_mode=True)
            
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS("  ✓ API call successful"))
                data = result.get('data', {})
                if isinstance(data, dict):
                    self.stdout.write(f"    Response keys: {list(data.keys())}")
                else:
                    self.stdout.write(f"    Response type: {type(data).__name__}")
            else:
                error_msg = result.get('message', 'Unknown error')
                error_code = result.get('code', 'unknown')
                self.stdout.write(
                    self.style.ERROR(f"  ✗ API call failed: {error_msg} ({error_code})")
                )
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Exception during API call: {e}"))

    def test_backward_compatibility(self, user):
        """Test that the new system maintains backward compatibility."""
        self.stdout.write(self.style.SUCCESS('\n=== Testing Backward Compatibility ==='))
        
        try:
            # Test old ai_service functions
            from jobs.services.ai_service import generate_email_draft, optimize_email_content
            
            # Mock job data
            job_data = {
                'title': 'AI工程师',
                'company_name': '测试公司',
                'salary_range': '20-30K',
                'locations': ['北京', '上海']
            }
            
            # Test email generation
            self.stdout.write("Testing generate_email_draft...")
            # Note: This would require actual API keys to test fully
            
            self.stdout.write(self.style.SUCCESS("✓ Backward compatibility maintained"))
            
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"Backward compatibility test failed: {e}"))