"""
Manage AI Models Command

Command for managing AI model configurations, user preferences, and system settings.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings
import json
from pathlib import Path
from typing import Dict, Any, Optional


class Command(BaseCommand):
    help = 'Manage AI model configurations and user preferences'

    def add_arguments(self, parser):
        # Subcommands
        subparsers = parser.add_subparsers(dest='subcommand', help='Available subcommands')

        # List models
        list_parser = subparsers.add_parser('list', help='List available models')
        list_parser.add_argument('--provider', type=str, help='Filter by provider')
        list_parser.add_argument('--active-only', action='store_true', help='Show only active models')
        list_parser.add_argument('--user', type=str, help='Show models available to specific user')

        # Show model details
        show_parser = subparsers.add_parser('show', help='Show detailed model information')
        show_parser.add_argument('model_id', type=str, help='Model ID to show')

        # Test model
        test_parser = subparsers.add_parser('test', help='Test model configuration')
        test_parser.add_argument('model_id', type=str, help='Model ID to test')
        test_parser.add_argument('--user', type=str, default='admin', help='Username to test with')

        # Export configuration
        export_parser = subparsers.add_parser('export', help='Export model configurations')
        export_parser.add_argument('--output', type=str, help='Output file path')
        export_parser.add_argument('--format', choices=['json', 'settings'], default='json', help='Export format')

        # Import configuration
        import_parser = subparsers.add_parser('import', help='Import model configurations')
        import_parser.add_argument('input_file', type=str, help='Input file path')

        # Validate configuration
        validate_parser = subparsers.add_parser('validate', help='Validate model configurations')

        # User preferences
        prefs_parser = subparsers.add_parser('preferences', help='Manage user preferences')
        prefs_parser.add_argument('username', type=str, help='Username')
        prefs_parser.add_argument('--preferred-model', type=str, help='Set preferred model')
        prefs_parser.add_argument('--fallback-models', type=str, nargs='+', help='Set fallback models')
        prefs_parser.add_argument('--max-retries', type=int, help='Set max retries')
        prefs_parser.add_argument('--show', action='store_true', help='Show current preferences')

        # Statistics
        stats_parser = subparsers.add_parser('stats', help='Show system statistics')

    def handle(self, *args, **options):
        """Main command handler."""
        subcommand = options.get('subcommand')
        
        if not subcommand:
            self.print_help('manage_ai_models', '')
            return

        # Import here to avoid issues if new system not available
        try:
            from jobs.services.ai_config import model_registry, config_manager
            model_registry.ensure_loaded()
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'AI configuration system not available: {e}')
            )
            return

        # Dispatch to appropriate handler
        handler_name = f'handle_{subcommand}'
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            handler(options)
        else:
            self.stdout.write(
                self.style.ERROR(f'Unknown subcommand: {subcommand}')
            )

    def handle_list(self, options):
        """Handle list subcommand."""
        from jobs.services.ai_config import model_registry

        if options.get('user'):
            # Show models for specific user
            try:
                user = User.objects.get(username=options['user'])
                models = config_manager.get_available_models_for_user(user)
                self.stdout.write(f"Models available to user '{options['user']}':")
            except User.DoesNotExist:
                raise CommandError(f"User '{options['user']}' does not exist")
        else:
            # Show all models
            if options.get('active_only'):
                models = model_registry.get_active_models()
                self.stdout.write("Active AI Models:")
            else:
                models = model_registry.get_all_models()
                self.stdout.write("All AI Models:")

        # Filter by provider if specified
        if options.get('provider'):
            models = {
                model_id: config for model_id, config in models.items()
                if config.provider == options['provider']
            }

        if not models:
            self.stdout.write("No models found.")
            return

        # Display models
        for model_id, config in models.items():
            status = "✓" if config.is_active else "✗"
            deprecated = " (DEPRECATED)" if config.is_deprecated else ""
            self.stdout.write(
                f"  {status} {model_id}: {config.name} ({config.provider}){deprecated}"
            )
            if config.description:
                self.stdout.write(f"    {config.description}")

    def handle_show(self, options):
        """Handle show subcommand."""
        from jobs.services.ai_config import model_registry

        model_id = options['model_id']
        config = model_registry.get_model(model_id)

        if not config:
            raise CommandError(f"Model '{model_id}' not found")

        self.stdout.write(f"\n=== Model: {model_id} ===")
        self.stdout.write(f"Name: {config.name}")
        self.stdout.write(f"Provider: {config.provider}")
        self.stdout.write(f"Model Name: {config.model_name}")
        self.stdout.write(f"Base URL: {config.base_url}")
        self.stdout.write(f"Max Context: {config.max_context_tokens:,} tokens")
        self.stdout.write(f"Active: {'Yes' if config.is_active else 'No'}")
        self.stdout.write(f"Deprecated: {'Yes' if config.is_deprecated else 'No'}")
        self.stdout.write(f"Adapter: {config.adapter_class}")
        self.stdout.write(f"Temperature: {config.default_temperature}")
        self.stdout.write(f"Timeout: {config.timeout_seconds}s")

        if config.description:
            self.stdout.write(f"Description: {config.description}")

        if config.tags:
            self.stdout.write(f"Tags: {', '.join(config.tags)}")

        if config.rate_limits:
            self.stdout.write("\n--- Rate Limits ---")
            rl = config.rate_limits
            if rl.requests_per_minute:
                self.stdout.write(f"Requests/minute: {rl.requests_per_minute}")
            if rl.tokens_per_minute:
                self.stdout.write(f"Tokens/minute: {rl.tokens_per_minute:,}")
            if rl.requests_per_day:
                self.stdout.write(f"Requests/day: {rl.requests_per_day:,}")

        if config.cost_per_1k_input_tokens:
            self.stdout.write(f"\n--- Pricing ---")
            self.stdout.write(f"Input: ${config.cost_per_1k_input_tokens:.4f}/1K tokens")
            if config.cost_per_1k_output_tokens:
                self.stdout.write(f"Output: ${config.cost_per_1k_output_tokens:.4f}/1K tokens")

    def handle_test(self, options):
        """Handle test subcommand."""
        from jobs.services.ai_manager import ai_manager

        model_id = options['model_id']
        username = options['user']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        self.stdout.write(f"Testing model '{model_id}' for user '{username}'...")

        # Check access
        access_info = ai_manager.check_user_access(user, model_id)
        if not access_info.get('has_access'):
            self.stdout.write(
                self.style.ERROR(f"❌ Access denied: {access_info.get('message', 'Unknown reason')}")
            )
            return

        self.stdout.write(self.style.SUCCESS("✓ Access granted"))

        # Test adapter creation
        try:
            adapter = ai_manager.get_adapter(model_id)
            self.stdout.write(f"✓ Adapter: {adapter.__class__.__name__}")
            self.stdout.write(f"✓ Context limit: {adapter.get_context_limit():,} tokens")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Adapter creation failed: {e}"))
            return

        # Test API call (simple test)
        test_prompt = "请返回一个包含'status': 'ok'的JSON对象。"
        try:
            result = ai_manager.call_model(test_prompt, model_id, user, json_mode=True)
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS("✓ API call successful"))
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ API call failed: {result.get('message', 'Unknown error')}")
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ API test failed: {e}"))

    def handle_export(self, options):
        """Handle export subcommand."""
        from jobs.services.ai_config import model_registry

        output_file = options.get('output')
        format_type = options.get('format', 'json')

        if not output_file:
            output_file = f"ai_models.{format_type}"

        output_path = Path(output_file)

        if format_type == 'json':
            model_registry.export_to_json(output_path)
        elif format_type == 'settings':
            self._export_to_settings(output_path)

        self.stdout.write(
            self.style.SUCCESS(f"Exported model configurations to {output_path}")
        )

    def _export_to_settings(self, output_path: Path):
        """Export configurations as Django settings format."""
        from jobs.services.ai_config import model_registry

        models = model_registry.get_all_models()
        
        settings_content = [
            "# AI Model Configurations",
            "# Generated by manage_ai_models export command",
            "",
            "AI_MODEL_CONFIGS = {"
        ]

        for model_id, config in models.items():
            settings_content.append(f"    '{model_id}': {{")
            
            # Basic fields
            for field, value in config.to_dict().items():
                if field in ['model_id']:
                    continue
                if isinstance(value, str):
                    settings_content.append(f"        '{field}': '{value}',")
                elif isinstance(value, (int, float, bool)):
                    settings_content.append(f"        '{field}': {value},")
                elif isinstance(value, list):
                    settings_content.append(f"        '{field}': {value},")
                elif isinstance(value, dict):
                    settings_content.append(f"        '{field}': {value},")
            
            settings_content.append("    },")
            settings_content.append("")

        settings_content.append("}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(settings_content))

    def handle_import(self, options):
        """Handle import subcommand."""
        from jobs.services.ai_config import model_registry

        input_file = Path(options['input_file'])
        
        if not input_file.exists():
            raise CommandError(f"Input file '{input_file}' does not exist")

        model_registry.load_from_json(input_file)
        
        self.stdout.write(
            self.style.SUCCESS(f"Imported model configurations from {input_file}")
        )

    def handle_validate(self, options):
        """Handle validate subcommand."""
        from jobs.services.ai_config import model_registry

        self.stdout.write("Validating model configurations...")
        
        errors = model_registry.validate_all_models()
        
        if not errors:
            self.stdout.write(self.style.SUCCESS("✓ All model configurations are valid"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Found {len(errors)} models with errors:"))
            for model_id, model_errors in errors.items():
                self.stdout.write(f"  {model_id}:")
                for error in model_errors:
                    self.stdout.write(f"    - {error}")

    def handle_preferences(self, options):
        """Handle preferences subcommand."""
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        if options.get('show'):
            self._show_user_preferences(user)
        else:
            self._update_user_preferences(user, options)

    def _show_user_preferences(self, user: User):
        """Show current user preferences."""
        preferences = config_manager.get_user_preferences(user)
        
        self.stdout.write(f"\n=== AI Preferences for {user.username} ===")
        self.stdout.write(f"Preferred Model: {preferences.preferred_model or 'Not set'}")
        self.stdout.write(f"Fallback Models: {preferences.fallback_models or 'Not set'}")
        self.stdout.write(f"Max Retries: {preferences.max_retries}")
        self.stdout.write(f"Max Tokens/Request: {preferences.max_tokens_per_request or 'Default'}")
        
        if preferences.default_temperature:
            self.stdout.write(f"Default Temperature: {preferences.default_temperature}")

    def _update_user_preferences(self, user: User, options: Dict[str, Any]):
        """Update user preferences."""
        preferences = config_manager.get_user_preferences(user)
        updated = False

        if options.get('preferred_model'):
            preferences.preferred_model = options['preferred_model']
            updated = True

        if options.get('fallback_models'):
            preferences.fallback_models = options['fallback_models']
            updated = True

        if options.get('max_retries') is not None:
            preferences.max_retries = options['max_retries']
            updated = True

        if updated:
            config_manager.update_user_preferences(user, preferences)
            self.stdout.write(
                self.style.SUCCESS(f"Updated preferences for user '{user.username}'")
            )
        else:
            self.stdout.write("No preferences specified to update")

    def handle_stats(self, options):
        """Handle stats subcommand."""
        from jobs.services.ai_config import model_registry

        stats = model_registry.get_statistics()
        
        self.stdout.write("\n=== AI System Statistics ===")
        self.stdout.write(f"Total Models: {stats['total_models']}")
        self.stdout.write(f"Active Models: {stats['active_models']}")
        self.stdout.write(f"Deprecated Models: {stats['deprecated_models']}")
        
        self.stdout.write(f"\nProviders:")
        for provider, count in stats['providers'].items():
            self.stdout.write(f"  {provider}: {count} models")
        
        self.stdout.write(f"\nConfiguration Sources: {', '.join(stats['config_sources'])}")
        
        # User statistics
        total_users = User.objects.count()
        users_with_keys = User.objects.filter(apikey__isnull=False).distinct().count()
        
        self.stdout.write(f"\nUser Statistics:")
        self.stdout.write(f"  Total Users: {total_users}")
        self.stdout.write(f"  Users with API Keys: {users_with_keys}")
        self.stdout.write(f"  Usage Coverage: {users_with_keys/total_users*100:.1f}%" if total_users > 0 else "  Usage Coverage: 0%")