"""
Batch Processing with AI Fallback

Enhanced batch processing that continues even when individual AI requests fail.
"""

import time
import logging
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from django.contrib.auth.models import User

from .simple_ai_manager import SimpleAIManager

# 创建简化AI管理器实例
simple_ai_manager = SimpleAIManager()

logger = logging.getLogger(__name__)


@dataclass
class BatchItem:
    """Individual item in a batch processing operation."""
    id: str  # Unique identifier for this item
    data: Any  # The data to process
    result: Optional[Any] = None
    success: bool = False
    error: Optional[str] = None
    models_tried: int = 0
    execution_time: float = 0
    fallback_used: bool = False
    human_log: List[str] = field(default_factory=list)


@dataclass
class BatchResult:
    """Result of a batch processing operation."""
    total_items: int
    successful_items: int
    failed_items: int
    items: List[BatchItem]
    
    # Aggregated metrics
    total_execution_time: float = 0
    total_models_tried: int = 0
    total_fallbacks_used: int = 0
    
    # Error summary
    error_summary: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of the batch."""
        return self.successful_items / self.total_items if self.total_items > 0 else 0.0
    
    @property
    def average_execution_time(self) -> float:
        """Calculate average execution time per item."""
        return self.total_execution_time / self.total_items if self.total_items > 0 else 0.0


class BatchProcessor:
    """Processes batches of items using AI with fallback support."""
    
    def __init__(self, user: User, continue_on_failure: bool = True):
        """
        Initialize the batch processor.
        
        Args:
            user: The user performing the batch operation
            continue_on_failure: Whether to continue processing if individual items fail
        """
        self.user = user
        self.continue_on_failure = continue_on_failure
    
    def process_batch(self, items: List[Dict[str, Any]], 
                     process_func: Callable[[Any, User], Dict[str, Any]],
                     item_id_func: Callable[[Any], str] = None,
                     progress_callback: Callable[[int, int], None] = None) -> BatchResult:
        """
        Process a batch of items using AI with fallback support.
        
        Args:
            items: List of items to process
            process_func: Function to process each item (item, user) -> result
            item_id_func: Function to generate ID for each item (optional)
            progress_callback: Callback for progress updates (current, total)
            
        Returns:
            BatchResult with detailed results for each item
        """
        if not items:
            return BatchResult(total_items=0, successful_items=0, failed_items=0, items=[])
        
        batch_items = []
        start_time = time.time()
        
        logger.info(f"Starting batch processing of {len(items)} items for user {self.user.username}")
        
        for i, item in enumerate(items):
            # Generate item ID
            if item_id_func:
                item_id = item_id_func(item)
            else:
                item_id = f"item_{i+1}"
            
            batch_item = BatchItem(id=item_id, data=item)
            
            try:
                # Process the item
                item_start_time = time.time()
                result = process_func(item, self.user)
                batch_item.execution_time = time.time() - item_start_time
                
                # Check if the result indicates success
                if isinstance(result, dict):
                    if result.get('success'):
                        batch_item.success = True
                        batch_item.result = result.get('data', result)
                        batch_item.models_tried = result.get('models_tried', 1)
                        batch_item.fallback_used = result.get('fallback_used', False)
                        batch_item.human_log = result.get('human_readable_log', [])
                        
                        logger.debug(f"Batch item {item_id} processed successfully")
                    else:
                        batch_item.error = result.get('message', '处理失败')
                        batch_item.models_tried = result.get('models_tried', 0)
                        batch_item.human_log = result.get('human_readable_log', [])
                        
                        logger.warning(f"Batch item {item_id} failed: {batch_item.error}")
                        
                        if not self.continue_on_failure:
                            logger.error(f"Stopping batch processing due to failure in item {item_id}")
                            break
                else:
                    # Non-dict result, assume success
                    batch_item.success = True
                    batch_item.result = result
                    batch_item.models_tried = 1
            
            except Exception as e:
                batch_item.error = str(e)
                batch_item.execution_time = time.time() - item_start_time
                
                logger.exception(f"Unexpected error processing batch item {item_id}: {e}")
                
                if not self.continue_on_failure:
                    logger.error(f"Stopping batch processing due to exception in item {item_id}")
                    break
            
            finally:
                batch_items.append(batch_item)
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, len(items))
        
        # Calculate batch result
        total_execution_time = time.time() - start_time
        successful_items = sum(1 for item in batch_items if item.success)
        failed_items = len(batch_items) - successful_items
        
        # Aggregate metrics
        total_models_tried = sum(item.models_tried for item in batch_items)
        total_fallbacks_used = sum(1 for item in batch_items if item.fallback_used)
        
        # Error summary
        error_summary = {}
        for item in batch_items:
            if item.error:
                error_type = self._classify_error(item.error)
                error_summary[error_type] = error_summary.get(error_type, 0) + 1
        
        result = BatchResult(
            total_items=len(items),
            successful_items=successful_items,
            failed_items=failed_items,
            items=batch_items,
            total_execution_time=total_execution_time,
            total_models_tried=total_models_tried,
            total_fallbacks_used=total_fallbacks_used,
            error_summary=error_summary
        )
        
        logger.info(f"Batch processing completed: {successful_items}/{len(items)} successful "
                   f"({result.success_rate:.1%}) in {total_execution_time:.2f}s")
        
        return result
    
    def _classify_error(self, error_message: str) -> str:
        """Classify error message into categories."""
        error_lower = error_message.lower()
        
        if any(keyword in error_lower for keyword in ['timeout', '超时']):
            return 'timeout'
        elif any(keyword in error_lower for keyword in ['rate limit', '频率', '限制']):
            return 'rate_limit'
        elif any(keyword in error_lower for keyword in ['auth', '认证', '密钥']):
            return 'auth_error'
        elif any(keyword in error_lower for keyword in ['quota', '配额', 'balance', '余额']):
            return 'quota_error'
        elif any(keyword in error_lower for keyword in ['context', '上下文', 'too long', '过长']):
            return 'context_error'
        elif any(keyword in error_lower for keyword in ['network', '网络', 'connection', '连接']):
            return 'network_error'
        else:
            return 'other'
    
    def get_batch_summary(self, result: BatchResult) -> str:
        """Get a human-readable summary of the batch processing result."""
        if result.total_items == 0:
            return "没有处理任何项目"
        
        summary = f"批处理完成: {result.successful_items}/{result.total_items} 成功 " \
                 f"({result.success_rate:.1%})"
        
        if result.total_fallbacks_used > 0:
            summary += f"，{result.total_fallbacks_used} 次模型切换"
        
        if result.failed_items > 0:
            top_errors = sorted(result.error_summary.items(), key=lambda x: x[1], reverse=True)[:3]
            error_desc = "，主要错误: " + "、".join(f"{error}({count})" for error, count in top_errors)
            summary += error_desc
        
        return summary
    
    def get_failed_items(self, result: BatchResult) -> List[BatchItem]:
        """Get all failed items from the batch result."""
        return [item for item in result.items if not item.success]
    
    def retry_failed_items(self, result: BatchResult, 
                          process_func: Callable[[Any, User], Dict[str, Any]],
                          max_retries: int = 1) -> BatchResult:
        """
        Retry processing of failed items.
        
        Args:
            result: Previous batch result
            process_func: Function to process each item
            max_retries: Maximum number of retry attempts
            
        Returns:
            New BatchResult with retry attempts
        """
        failed_items = self.get_failed_items(result)
        
        if not failed_items:
            logger.info("No failed items to retry")
            return result
        
        logger.info(f"Retrying {len(failed_items)} failed items (max {max_retries} attempts)")
        
        # Convert failed BatchItems back to raw data for retry
        retry_data = [item.data for item in failed_items]
        
        # Process the retry batch
        retry_result = self.process_batch(
            retry_data,
            process_func,
            lambda item: f"retry_{failed_items[retry_data.index(item)].id}"
        )
        
        # Merge results
        merged_items = []
        retry_index = 0
        
        for item in result.items:
            if item.success:
                # Keep successful items as-is
                merged_items.append(item)
            else:
                # Replace with retry result
                retry_item = retry_result.items[retry_index]
                retry_index += 1
                
                if retry_item.success:
                    # Update original item with retry success
                    item.success = True
                    item.result = retry_item.result
                    item.error = None
                    item.models_tried += retry_item.models_tried
                    item.execution_time += retry_item.execution_time
                    item.fallback_used = item.fallback_used or retry_item.fallback_used
                    item.human_log.extend(retry_item.human_log)
                else:
                    # Update with retry failure info
                    item.models_tried += retry_item.models_tried
                    item.execution_time += retry_item.execution_time
                    item.human_log.extend(retry_item.human_log)
                
                merged_items.append(item)
        
        # Create merged result
        successful_items = sum(1 for item in merged_items if item.success)
        failed_items = len(merged_items) - successful_items
        
        merged_result = BatchResult(
            total_items=result.total_items,
            successful_items=successful_items,
            failed_items=failed_items,
            items=merged_items,
            total_execution_time=result.total_execution_time + retry_result.total_execution_time,
            total_models_tried=result.total_models_tried + retry_result.total_models_tried,
            total_fallbacks_used=result.total_fallbacks_used + retry_result.total_fallbacks_used
        )
        
        logger.info(f"Retry completed: {retry_result.successful_items}/{len(failed_items)} "
                   f"originally failed items now successful")
        
        return merged_result


# Utility functions for common batch processing tasks
def parse_job_batch(job_texts: List[str], user: User, provider_key: str = None) -> BatchResult:
    """
    Parse a batch of job descriptions using AI with fallback support.
    
    Args:
        job_texts: List of job description texts
        user: User performing the parsing
        provider_key: Preferred AI model (optional)
        
    Returns:
        BatchResult with parsing results
    """
    from .parsing_service_v2 import parse_job_from_text
    
    processor = BatchProcessor(user, continue_on_failure=True)
    
    def parse_job(text: str, user: User) -> Dict[str, Any]:
        return parse_job_from_text(text, provider_key, user)
    
    def get_item_id(text: str) -> str:
        # Use first 50 characters as ID
        return f"job_{hash(text[:50]) % 10000}"
    
    return processor.process_batch(
        items=job_texts,
        process_func=parse_job,
        item_id_func=get_item_id
    )