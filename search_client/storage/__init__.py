"""Storage backends for web search client results."""

from search_client.storage.base import StorageBackend, StorageError
from search_client.storage.redis import RedisStorageBackend

__all__ = ["StorageBackend", "StorageError", "RedisStorageBackend"]


def get_storage_backend(backend_type: str = "file", **kwargs):
    """Factory function to get the appropriate storage backend.
    
    Args:
        backend_type: Type of storage backend to use ("file" or "redis")
        **kwargs: Additional arguments to pass to the storage backend
        
    Returns:
        An initialized storage backend instance
        
    Raises:
        ValueError: If the backend type is not recognized
    """
    if backend_type == "file":
        from search_client.storage.file import FileStorageBackend
        return FileStorageBackend(**kwargs)
    elif backend_type == "redis":
        from search_client.storage.redis import RedisStorageBackend
        return RedisStorageBackend(**kwargs)
    else:
        raise ValueError(f"Unknown storage backend type: {backend_type}")

