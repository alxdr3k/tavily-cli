"""Storage backends for web search client."""

import os
from typing import Dict, Any, Optional

from search_client.storage.base import StorageBackend, StorageError
from search_client.storage.redis import RedisStorageBackend

__all__ = [
    "StorageBackend", 
    "StorageError", 
    "RedisStorageBackend",
    "save_results",
    "cleanup"
]

# Global Redis storage backend instance
_redis_backend = None


def get_storage_backend(backend_type: str = "redis", **kwargs):
    """Factory function to get the Redis storage backend.
    
    Args:
        backend_type: Parameter kept for backward compatibility but ignored
        **kwargs: Additional arguments to pass to the Redis storage backend
        
    Returns:
        An initialized Redis storage backend instance
    """
    # Set default Redis port if not specified
    if 'port' not in kwargs:
        kwargs['port'] = 16379
        
    # Always return Redis storage backend regardless of the backend_type
    return RedisStorageBackend(**kwargs)


def _get_redis_backend():
    """Get or initialize the Redis backend singleton.
    
    Returns:
        Initialized Redis storage backend
    """
    global _redis_backend
    if _redis_backend is None:
        # Initialize with environment variables if available
        host = os.environ.get("REDIS_HOST", "localhost")
        port = int(os.environ.get("REDIS_PORT", "16379"))
        _redis_backend = RedisStorageBackend(host=host, port=port)
    return _redis_backend


def save_results(query: str, results: Dict[str, Any]) -> str:
    """Save search results using the Redis backend.
    
    Args:
        query: The search query
        results: The search results to save
        
    Returns:
        Identifier for the saved results
        
    Raises:
        StorageError: If there is an error saving the results
    """
    backend = _get_redis_backend()
    return backend.save_results(query, results)


def cleanup(days: int = 14) -> int:
    """Clean up old search results.
    
    Args:
        days: Remove results older than this many days
        
    Returns:
        Number of results removed
    """
    backend = _get_redis_backend()
    return backend.cleanup(max_age_days=days)

