"""
Test AI Fallback System

Command to test the AI fallback and retry functionality.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import time


class Command(BaseCommand):
    help = 'Test AI fallback and retry functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Username to test with (default: admin)'
        )
        parser.add_argument(
            '--primary-model',
            type=str,
            help='Primary model to test (e.g., qwen_plus)'
        )
        parser.add_argument(
            '--fallback-models',
            type=str,
            nargs='+',
            help='Fallback models to test'
        )
        parser.add_argument(
            '--prompt',
            type=str,
            default='请返回一个包含"status": "ok"的简单JSON对象。',
            help='Test prompt to send'
        )
        parser.add_argument(
            '--batch-test',
            action='store_true',
            help='Test batch processing with fallback'
        )
        parser.add_argument(
            '--show-logs',
            action='store_true',
            help='Show detailed human-readable logs'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        try:
            # Get user
            user = User.objects.get(username=options['user'])
        except User.DoesNotExist:
            raise CommandError(f"User '{options['user']}' does not exist")

        if options['batch_test']:
            self.test_batch_processing(user, options)
        else:
            self.test_single_request(user, options)

    def test_single_request(self, user, options):
        """Test a single AI request with fallback."""
        try:
            from jobs.services.ai_manager import ai_manager
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'AI manager not available: {e}'))
            return

        self.stdout.write(f"\n=== Testing AI Fallback for user '{user.username}' ===")

        # Get fallback status first
        fallback_status = ai_manager.get_fallback_status(user)
        self.stdout.write(f"\n--- Fallback Configuration ---")
        self.stdout.write(f"Primary Model: {fallback_status.get('primary_model', 'None')}")
        self.stdout.write(f"Accessible Models: {fallback_status.get('accessible_models', 0)}")
        self.stdout.write(f"Fallback Health: {fallback_status.get('fallback_health', 'Unknown')}")
        
        if fallback_status.get('recommendations'):
            self.stdout.write("Recommendations:")
            for rec in fallback_status['recommendations']:
                self.stdout.write(f"  - {rec}")

        # Test the request
        self.stdout.write(f"\n--- Testing Request ---")
        self.stdout.write(f"Prompt: {options['prompt']}")
        
        start_time = time.time()
        
        result = ai_manager.call_model_with_fallback(
            prompt=options['prompt'],
            user=user,
            primary_model=options.get('primary_model'),
            fallback_models=options.get('fallback_models')
        )
        
        execution_time = time.time() - start_time

        # Display results
        self.stdout.write(f"\n--- Results ---")
        if result.get('success'):
            self.stdout.write(self.style.SUCCESS(f"✓ Success with {result.get('final_model')}"))
            self.stdout.write(f"Models Tried: {result.get('models_tried', 1)}")
            self.stdout.write(f"Total Retries: {result.get('total_retries', 0)}")
            self.stdout.write(f"Fallback Used: {'Yes' if result.get('fallback_used') else 'No'}")
            self.stdout.write(f"Execution Time: {execution_time:.2f}s")
            
            if result.get('summary'):
                self.stdout.write(f"Summary: {result['summary']}")
        else:
            self.stdout.write(self.style.ERROR(f"✗ Failed: {result.get('message', 'Unknown error')}"))
            self.stdout.write(f"Models Tried: {result.get('models_tried', 0)}")
            self.stdout.write(f"Total Retries: {result.get('total_retries', 0)}")
            self.stdout.write(f"Execution Time: {execution_time:.2f}s")

        # Show human-readable logs if requested
        if options.get('show_logs') and result.get('human_readable_log'):
            self.stdout.write(f"\n--- Execution Log ---")
            for log_entry in result['human_readable_log']:
                self.stdout.write(f"  {log_entry}")

        # Show detailed attempt information
        if result.get('attempts'):
            self.stdout.write(f"\n--- Detailed Attempts ---")
            for attempt in result['attempts']:
                status = "✓" if not attempt.get('error') else "✗"
                self.stdout.write(f"  {status} {attempt['model_id']}: {attempt.get('error', 'Success')}")
                if attempt.get('retries', 0) > 0:
                    self.stdout.write(f"    Retries: {attempt['retries']}")

    def test_batch_processing(self, user, options):
        """Test batch processing with fallback."""
        try:
            from jobs.services.batch_processing import BatchProcessor
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'Batch processor not available: {e}'))
            return

        self.stdout.write(f"\n=== Testing Batch Processing for user '{user.username}' ===")

        # Create test items
        test_prompts = [
            "请返回包含'item': 1的JSON对象。",
            "请返回包含'item': 2的JSON对象。", 
            "请返回包含'item': 3的JSON对象。",
            "这是一个故意很长的提示词，用来测试上下文长度限制的处理..." + "很长的内容 " * 100,
            "请返回包含'item': 5的JSON对象。"
        ]

        self.stdout.write(f"Processing {len(test_prompts)} test items...")

        # Create batch processor
        processor = BatchProcessor(user, continue_on_failure=True)

        # Define processing function
        def process_item(prompt, user):
            from jobs.services.ai_manager import ai_manager
            return ai_manager.call_model_with_fallback(
                prompt=prompt,
                user=user,
                primary_model=options.get('primary_model')
            )

        # Progress callback
        def show_progress(current, total):
            self.stdout.write(f"  Progress: {current}/{total}")

        # Process batch
        start_time = time.time()
        result = processor.process_batch(
            items=test_prompts,
            process_func=process_item,
            item_id_func=lambda p: f"prompt_{test_prompts.index(p)+1}",
            progress_callback=show_progress
        )
        execution_time = time.time() - start_time

        # Display batch results
        self.stdout.write(f"\n--- Batch Results ---")
        self.stdout.write(f"Total Items: {result.total_items}")
        self.stdout.write(f"Successful: {result.successful_items}")
        self.stdout.write(f"Failed: {result.failed_items}")
        self.stdout.write(f"Success Rate: {result.success_rate:.1%}")
        self.stdout.write(f"Total Execution Time: {execution_time:.2f}s")
        self.stdout.write(f"Average Time/Item: {result.average_execution_time:.2f}s")
        self.stdout.write(f"Total Models Tried: {result.total_models_tried}")
        self.stdout.write(f"Fallbacks Used: {result.total_fallbacks_used}")

        # Show error summary
        if result.error_summary:
            self.stdout.write(f"\n--- Error Summary ---")
            for error_type, count in result.error_summary.items():
                self.stdout.write(f"  {error_type}: {count}")

        # Show individual item results if requested
        if options.get('show_logs'):
            self.stdout.write(f"\n--- Individual Results ---")
            for item in result.items:
                status = "✓" if item.success else "✗"
                self.stdout.write(f"  {status} {item.id}: {item.error or 'Success'}")
                if item.fallback_used:
                    self.stdout.write(f"    Fallback used, {item.models_tried} models tried")
                if item.human_log:
                    for log_entry in item.human_log:
                        self.stdout.write(f"      {log_entry}")

        # Get batch summary
        summary = processor.get_batch_summary(result)
        self.stdout.write(f"\n--- Summary ---")
        self.stdout.write(summary)

        # Test retry functionality if there are failures
        failed_items = processor.get_failed_items(result)
        if failed_items:
            self.stdout.write(f"\n--- Testing Retry Functionality ---")
            self.stdout.write(f"Retrying {len(failed_items)} failed items...")
            
            retry_result = processor.retry_failed_items(result, process_item, max_retries=1)
            
            self.stdout.write(f"After retry: {retry_result.successful_items}/{retry_result.total_items} successful")
            retry_summary = processor.get_batch_summary(retry_result)
            self.stdout.write(f"Retry summary: {retry_summary}")