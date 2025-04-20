"""Redis storage backend for web search client."""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# Import real Redis
import redis

from search_client.logger import logger
from search_client.storage.base import StorageBackend, StorageError

# Mock Redis implementation - kept for reference but not used
class MockRedisClient:
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 16379, 
        db: int = 0,
        key_prefix: str = "search:",
        **kwargs
    ):
        """Initialize the Redis storage backend.
        
        Args:
            host: Redis host (default: localhost)
            port: Redis port (default: 16379)
            db: Redis database number (default: 0)
            key_prefix: Prefix for Redis keys (default: "search:")
        """
        self.data = {}
        self.expiry = {}
        self.sorted_sets = {}
        
    def ping(self):
        """Test connection, always returns True for mock."""
        return True
        
    def set(self, key, value, ex=None):
        """Set a string value in the mock Redis."""
        self.data[key] = value
        if ex:  # Set expiration if provided
            self.expire(key, ex)
        return True
        
    def get(self, key):
        """Get a string value from the mock Redis."""
        # Check if key exists and hasn't expired
        if key in self.data:
            if key in self.expiry and time.time() > self.expiry[key]:
                # Key has expired
                del self.data[key]
                del self.expiry[key]
                return None
            return self.data[key]
        return None
        
    def delete(self, key):
        """Delete a key."""
        if key in self.data:
            del self.data[key]
            if key in self.expiry:
                del self.expiry[key]
            return 1
        return 0
        
    def expire(self, key, seconds):
        """Set an expiry time for a key."""
        if key in self.data:
            self.expiry[key] = time.time() + seconds
            return True
        return False
        
    def zadd(self, key, mapping):
        """Add to a sorted set."""
        if key not in self.sorted_sets:
            self.sorted_sets[key] = {}
        self.sorted_sets[key].update(mapping)
        return len(mapping)
        
    def zrangebyscore(self, key, min_score, max_score):
        """Get members from a sorted set by score."""
        if key not in self.sorted_sets:
            return []
        return [
            member for member, score in self.sorted_sets[key].items()
            if min_score <= score <= max_score
        ]
        
    def zrem(self, key, *members):
        """Remove members from a sorted set."""
        if key not in self.sorted_sets:
            return 0
        count = 0
        for member in members:
            if member in self.sorted_sets[key]:
                del self.sorted_sets[key][member]
                count += 1
        return count


class RedisStorageBackend(StorageBackend):
    """Redis-based storage backend for search results."""
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 16379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "web-search:",
        ttl_days: int = 14,
        ssl: bool = False
    ):
        """Initialize the Redis storage backend.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Redis password if authentication is required
            prefix: Key prefix for Redis keys
            ttl_days: Default TTL for keys in days
            ssl: Whether to use SSL for Redis connection
        """
        # Initialize with environment variables if available
        host = os.environ.get("REDIS_HOST", host)
        
        # Check if running inside Docker to use the correct port
        in_docker = os.environ.get("IN_DOCKER", "").lower() == "true"
        env_port = os.environ.get("REDIS_PORT")
        if env_port:
            port = int(env_port)
        elif in_docker:
            # If in Docker, use the container port (6379)
            port = 6379
        
        # Get password from environment if available
        env_password = os.environ.get("REDIS_PASSWORD")
        if env_password:
            password = env_password
            
        # Using real Redis client with proper parameters
        try:
            self.redis_client = redis.Redis(
                host=host, 
                port=port, 
                db=db,
                password=password,
                ssl=ssl,
                decode_responses=True
            )
            
            # Test connection
            self.redis_client.ping()
            is_mock = False
            logger.info(f"Initialized Redis storage backend at {host}:{port} with prefix: {prefix}")
        except redis.exceptions.RedisError as e:
            logger.warning(f"Failed to connect to Redis at {host}:{port}: {e}")
            logger.warning("Falling back to mock Redis implementation")
            self.redis_client = MockRedisClient()
            is_mock = True
            logger.info(f"Initialized Mock Redis storage backend with prefix: {prefix}")
        
        self.prefix = prefix
        self.ttl_days = ttl_days
        self.is_mock = is_mock
        
    def _make_key(self, key_type: str, identifier: str) -> str:
        """Create a Redis key with the configured prefix."""
        return f"{self.prefix}{key_type}:{identifier}"
        
    def _slugify(self, text: str) -> str:
        """Convert text to a Redis-safe slug."""
        # Simple implementation for the proof of concept
        return text.lower().replace(" ", "-")[:50]
        
    def save_results(self, query: str, results: Dict[str, Any]) -> str:
        """Save search results to Redis.
        
        Args:
            query: The search query
            results: The search results to save
            
        Returns:
            The result identifier (timestamp-based)
            
        Raises:
            StorageError: If there is an error saving to Redis
        """
        try:
            # Generate a timestamp-based identifier
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            identifier = f"{timestamp}_{self._slugify(query)}"
            
            # Add metadata
            results_with_metadata = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            # Save to Redis
            result_key = self._make_key("result", identifier)
            try:
                self.redis_client.set(
                    result_key, 
                    json.dumps(results_with_metadata)
                )
                
                # Set expiration
                if self.ttl_days > 0:
                    seconds = self.ttl_days * 24 * 60 * 60
                    self.redis_client.expire(result_key, seconds)
                    
                # Add to index
                index_key = self._make_key("index", "all")
                self.redis_client.zadd(
                    index_key,
                    {identifier: time.time()}
                )
                
                # Add to query index
                query_key = self._make_key("query", self._slugify(query))
                self.redis_client.zadd(
                    query_key,
                    {identifier: time.time()}
                )
                
                logger.info(f"Results saved to Redis with ID: {identifier}")
                return identifier
                
            except redis.exceptions.RedisError as re:
                logger.error(f"Redis operation error: {re}")
                # If using mock, the error is not from connection
                if not self.is_mock:
                    logger.error(f"Check Redis connection settings (host: {os.environ.get('REDIS_HOST', 'localhost')}, port: {os.environ.get('REDIS_PORT', '16379')})")
                raise StorageError(f"Failed to perform Redis operation: {re}")
                
        except Exception as e:
            logger.error(f"Redis error: {e}")
            raise StorageError(f"Failed to save results to Redis: {e}")
    
    def get_results(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieve results by identifier.
        
        Args:
            identifier: The unique identifier for the results
            
        Returns:
            The search results, or None if not found
        """
        try:
            result_key = self._make_key("result", identifier)
            result_data = self.redis_client.get(result_key)
            
            if not result_data:
                return None
                
            return json.loads(result_data)
            
        except Exception as e:
            logger.error(f"Error retrieving results: {e}")
            raise StorageError(f"Failed to retrieve results: {e}")
    
    def list_results(
        self, 
        limit: int = 10, 
        offset: int = 0,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List available results with pagination.
        
        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip
            query: Optional query string to filter results
            
        Returns:
            A list of search result metadata
        """
        try:
            # Determine which index to use
            if query:
                index_key = self._make_key("query", self._slugify(query))
            else:
                index_key = self._make_key("index", "all")
            
            # Get identifiers from the index (in a real implementation, this would use zrevrange with offset/limit)
            identifiers = self.redis_client.zrangebyscore(index_key, 0, float('inf'))
            
            # Apply offset and limit
            identifiers = identifiers[offset:offset + limit]
            
            # Get result data for each identifier
            results = []
            for identifier in identifiers:
                result_data = self.get_results(identifier)
                if result_data:
                    # Add the identifier to the metadata
                    result_data["id"] = identifier
                    results.append(result_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error listing results: {e}")
            raise StorageError(f"Failed to list results: {e}")
    
    def delete_results(self, identifier: str) -> bool:
        """Delete results by identifier.
        
        Args:
            identifier: The unique identifier for the results
            
        Returns:
            True if the results were deleted, False if not found
        """
        try:
            # Get the result to extract the query
            result_data = self.get_results(identifier)
            if not result_data:
                return False
                
            # Get the query for removing from the query index
            query = result_data.get("query", "")
            
            # Remove from indexes
            index_key = self._make_key("index", "all")
            self.redis_client.zrem(index_key, identifier)
            
            if query:
                query_key = self._make_key("query", self._slugify(query))
                self.redis_client.zrem(query_key, identifier)
            
            # Delete the result
            result_key = self._make_key("result", identifier)
            deleted = self.redis_client.delete(result_key)
            
            return deleted > 0
            
        except Exception as e:
            logger.error(f"Error deleting result: {e}")
            raise StorageError(f"Failed to delete result: {e}")
    
    def cleanup(self, max_age_days: int = 14) -> int:
        """Remove results older than the specified number of days.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of results removed
        """
        try:
            # Calculate cutoff timestamp
            cutoff = time.time() - (max_age_days * 24 * 60 * 60)
            
            # Get keys older than cutoff
            index_key = self._make_key("index", "all")
            old_results = self.redis_client.zrangebyscore(
                index_key, 
                0, 
                cutoff
            )
            
            if not old_results:
                return 0
                
            # Remove each result
            count = 0
            for identifier in old_results:
                if self.delete_results(identifier):
                    count += 1
                
            logger.info(f"Cleaned up {count} old result(s) from Redis")
            return count
            
        except Exception as e:
            logger.error(f"Redis cleanup error: {e}")
            return 0

