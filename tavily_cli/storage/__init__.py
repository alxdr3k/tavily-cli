"""Storage backends for Tavily CLI."""

import os
from typing import Dict, Any, Optional

from tavily_cli.storage.base import StorageBackend, StorageError
from tavily_cli.storage.redis import RedisStorageBackend

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
    # Check environment variables first
    host = os.environ.get("REDIS_HOST", kwargs.get('host', 'localhost'))
    
    # Handle port configuration with Docker awareness
    in_docker = os.environ.get("IN_DOCKER", "").lower() == "true"
    env_port = os.environ.get("REDIS_PORT")
    
    if env_port:
        port = int(env_port)
    elif in_docker and 'port' not in kwargs:
        # In Docker, use the container port (6379)
        port = 6379
    elif 'port' not in kwargs:
        # Default to host port when not in Docker
        port = 16379
    else:
        port = kwargs.get('port')
    
    # Handle other Redis parameters
    password = os.environ.get("REDIS_PASSWORD", kwargs.get('password'))
    ssl = kwargs.get('ssl', False)
    
    # Set updated values in kwargs
    kwargs['host'] = host
    kwargs['port'] = port
    if password:
        kwargs['password'] = password
    
    # Always return Redis storage backend regardless of the backend_type
    return RedisStorageBackend(**kwargs)


def _get_redis_backend():
    """Get or initialize the Redis backend singleton.
    
    Returns:
        Initialized Redis storage backend
    """
    global _redis_backend
    if _redis_backend is None:
        # Use the factory function to ensure consistent configuration
        _redis_backend = get_storage_backend()
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

