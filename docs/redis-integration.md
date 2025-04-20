# Redis Integration for Web Search Client

## 1. Overview and Benefits

### Introduction

This document outlines a plan to enhance the Web Search Client by integrating Redis as an alternative storage backend for search results. Currently, the application stores search results as JSON files in a local directory, which works well for individual use but has limitations for sharing results, performance at scale, and advanced querying capabilities.

### Benefits of Redis Integration

1. **Performance**: Redis is an in-memory data store that provides significantly faster read/write operations compared to file-based storage.

2. **Advanced Querying**: Redis supports complex data structures and operations that would enable more sophisticated search result querying, filtering, and aggregation.

3. **Data Expiration**: Built-in time-to-live (TTL) functionality for automatic result expiration, replacing our custom file cleanup mechanism.

4. **Sharing Capabilities**: Multiple clients can access the same Redis instance, enabling search result sharing across users or services.

5. **Reduced Disk Usage**: By using Redis as the primary or caching layer, we can reduce the need for disk storage.

6. **Scalability**: Redis can be configured in cluster mode to handle larger datasets as needs grow.

7. **Analytics**: Easier implementation of usage statistics and search analytics.

## 2. Architecture Changes

### Current Architecture

The current architecture uses a direct file-based approach:

```
┌────────────┐     ┌────────────┐    ┌────────────┐
│   Tavily   │     │   Search   │    │ File-based │
│    API     │────▶│   Module   │───▶│  Storage   │
└────────────┘     └────────────┘    └────────────┘
                          │
                          ▼
                   ┌────────────┐
                   │    CLI     │
                   │ Interface  │
                   └────────────┘
```

### Proposed Architecture

The proposed architecture introduces a storage abstraction layer and Redis as an alternative backend:

```
┌────────────┐     ┌────────────┐     ┌───────────────┐
│   Tavily   │     │   Search   │     │    Storage    │
│    API     │────▶│   Module   │────▶│  Abstraction  │
└────────────┘     └────────────┘     └───────┬───────┘
                          │                    │
                          ▼                    ▼
                   ┌────────────┐     ┌───────────────┐
                   │    CLI     │     │ ┌───────────┐ │
                   │ Interface  │     │ │File-based │ │
                   └────────────┘     │ └───────────┘ │
                                      │ ┌───────────┐ │
                                      │ │  Redis    │ │
                                      │ └───────────┘ │
                                      └───────────────┘
```

### Key Changes

1. **Storage Abstraction Layer**: Create an interface that defines storage operations, allowing implementations for both file-based and Redis-based storage.

2. **Backend Selection**: Modify the CLI to accept configuration for choosing the preferred storage backend.

3. **Redis Client Integration**: Add Redis client libraries and configuration management.

4. **Query Management**: Implement query caching and result retrieval mechanisms specific to Redis.

## 3. Implementation Details

### Storage Backend Interface

Create a common interface for storage operations:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def save_results(self, query: str, results: Dict[str, Any]) -> str:
        """Save search results and return an identifier."""
        pass
        
    @abstractmethod
    def get_results(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieve results by identifier."""
        pass
        
    @abstractmethod
    def list_results(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """List available results with pagination."""
        pass
        
    @abstractmethod
    def delete_results(self, identifier: str) -> bool:
        """Delete results by identifier."""
        pass
        
    @abstractmethod
    def cleanup(self, max_age_days: int = 14) -> int:
        """Clean up old results and return count of removed items."""
        pass
```

### Redis Backend Implementation

```python
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import redis
from redis.exceptions import RedisError

from search_client.logger import logger
from search_client.storage.base import StorageBackend

class RedisStorageBackend(StorageBackend):
    """Redis-based storage backend for search results."""
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "web-search:"
    ):
        """Initialize the Redis storage backend.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Redis password if authentication is required
            prefix: Key prefix for Redis keys
        """
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        self.prefix = prefix
        
    def _make_key(self, key_type: str, identifier: str) -> str:
        """Create a Redis key with the configured prefix."""
        return f"{self.prefix}{key_type}:{identifier}"
        
    def save_results(self, query: str, results: Dict[str, Any]) -> str:
        """Save search results to Redis.
        
        Args:
            query: The search query
            results: The search results to save
            
        Returns:
            The result identifier (timestamp-based)
            
        Raises:
            StorageError: If there's an error saving to Redis
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
            self.redis_client.set(
                result_key, 
                json.dumps(results_with_metadata)
            )
            
            # Set expiration if configured
            if hasattr(self, "ttl_days") and self.ttl_days > 0:
                self.redis_client.expire(
                    result_key, 
                    timedelta(days=self.ttl_days)
                )
                
            # Add to index
            index_key = self._make_key("index", "all")
            self.redis_client.zadd(
                index_key,
                {identifier: time.time()}
            )
            
            # Add to query index
            query_key = self._make_key("query", query)
            self.redis_client.zadd(
                query_key,
                {identifier: time.time()}
            )
            
            logger.info(f"Results saved to Redis with ID: {identifier}")
            return identifier
            
        except RedisError as e:
            logger.error(f"Redis error: {e}")
            raise StorageError(f"Failed to save results to Redis: {e}")
    
    # ... other methods implementation ...
    
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
                result_key = self._make_key("result", identifier)
                
                # Get the original query
                result_data = self.redis_client.get(result_key)
                if result_data:
                    result_json = json.loads(result_data)
                    query = result_json.get("query", "")
                    
                    # Remove from query index
                    query_key = self._make_key("query", query)
                    self.redis_client.zrem(query_key, identifier)
                
                # Remove from main index and delete result
                self.redis_client.zrem(index_key, identifier)
                self.redis_client.delete(result_key)
                count += 1
                
            logger.info(f"Cleaned up {count} old result(s) from Redis")
            return count
            
        except RedisError as e:
            logger.error(f"Redis cleanup error: {e}")
            return 0
```

### CLI Changes

```python
@cli.command()
@click.argument("query", required=True)
@click.option(
    "--max-results", "-n", 
    default=10, 
    help="Maximum number of results to return (default: 10)"
)
# ... existing options ...
@click.option(
    "--storage", "-s",
    type=click.Choice(["file", "redis"]),
    default="file",
    help="Storage backend to use (default: file)"
)
@click.option(
    "--redis-host",
    default="localhost",
    help="Redis server hostname (default: localhost)"
)
@click.option(
    "--redis-port",
    default=6379,
    help="Redis server port (default: 6379)"
)
def search(
    query: str,
    max_results: int,
    depth: str,
    raw: bool,
    include_domain: List[str],
    exclude_domain: List[str],
    retention_days: int,
    storage: str,
    redis_host: str,
    redis_port: int,
):
    """Search the web and save results to a local file or Redis.
    
    QUERY: The search query string
    """
    try:
        # Create appropriate storage backend
        if storage == "redis":
            store = get_redis_backend(
                host=redis_host,
                port=redis_port,
                ttl_days=retention_days
            )
        else:
            store = get_file_backend()
            
        # Clean up old results
        store.cleanup(days=retention_days)
        
        # Run the search
        # ... existing search code ...
        
        # Save results using the selected backend
        result_id = store.save_results(query, search_results)
        
        # Display success message
        # ... existing display code ...
                
    except Exception as e:
        # ... existing error handling ...
```

### Caching Strategy

The Redis integration will implement the following caching strategies:

1. **TTL-based Expiration**: Results will automatically expire after a configurable period (default: 14 days) using Redis's built-in TTL mechanism.

2. **Query-based Indexing**: Results will be indexed by query to allow quick retrieval of previous searches for the same query.

3. **Timestamped Storage**: All results will include timestamps to support time-based queries and for maintaining consistency with the file-based approach.

4. **Sorted Sets**: Redis sorted sets will be used to maintain result ordering by timestamp for efficient retrieval and cleanup operations.

## 4. Migration and Backward Compatibility

### Backward Compatibility

1. **Default to File Storage**: The file storage backend will remain the default to maintain backward compatibility.

2. **Transparent Interface**: The storage abstraction layer will ensure that code depending on the storage functionality continues to work regardless of the backend used.

3. **Configuration Detection**: The system will automatically detect available backends and gracefully fall back to file storage if Redis is not available.

### Migration Path

For users who want to migrate from file-based storage to Redis:

1. **Import Tool**: Create a utility script to import existing JSON files into Redis:

```python
import glob
import json
import os
from pathlib import Path

from search_client.storage.redis import RedisStorageBackend

def import_files_to_redis(directory_path: str):
    """Import all JSON files from a directory into Redis."""
    redis_backend = RedisStorageBackend()
    
    # Get all JSON files
    json_files = glob.glob(os.path.join(directory_path, "*.json"))
    
    imported_count = 0
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract query and results
            query = data.get("query", "")
            results = data.get("results", {})
            
            if query and results:
                # Save to Redis
                redis_backend.save_results(query, results)
                imported_count += 1
                print(f"Imported: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error importing {file_path}: {e}")
    
    print(f"Successfully imported {imported_count} out of {len(json_files)} files")

if __name__ == "__main__":
    import_files_to_redis("search_results")
```

2. **Dual-Write Period**: Consider implementing a dual-write approach during migration, where results are written to both storage backends.

## 5. Configuration Options

### Environment Variables

Add the following environment variables to configure Redis integration:

```
WEBSEARCH_STORAGE=file|redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_PREFIX=web-search:
REDIS_TTL_DAYS=14
```

### Configuration File

Extend the configuration to support a YAML-based config file:

```yaml
storage:
  # Storage backend to use: file or redis
  backend: redis
  
  # Redis configuration (only used if backend is redis)
  redis:
    host: localhost
    port: 6379
    db: 0
    password: null  # Set to null or remove if no password
    prefix: web-search:
    ttl_days: 14
    
  # File storage configuration (only used if backend is file)
  file:
    directory: search_results
    retention_days: 14
```

### CLI Options

Add CLI options to override configuration settings:

```
--storage, -s [file|redis]  # Storage backend to use
--redis-host TEXT           # Redis server hostname
--redis-port INTEGER        # Redis server port
--redis-db INTEGER          # Redis database number
--redis-password TEXT       # Redis password
--redis-prefix TEXT         # Redis key prefix
--ttl-days INTEGER          # Default TTL for Redis keys in days
```

## 6. Examples of Usage

### Basic Usage with Redis Storage

```bash
# Search using Redis storage
web-search --storage redis "quantum computing"

# Specify Redis host and port
web-search --storage redis --redis-host myredisserver.com --redis-port 6380 "quantum computing"

# Set a custom TTL for results (30 days)
web-search --storage redis --ttl-days 30 "climate change solutions"
```

### Listing Saved Results

```bash
# List all saved results with Redis storage
web-search list --storage redis

# List results with pagination
web-search list --storage redis --limit 5 --page 2

# List results for a specific query
web-search list --storage redis --query "quantum computing"
```

### Retrieving Specific Results

```bash
# Get a specific result by ID
web-search get --storage redis 20250420-120145_quantum-computing

# Export a result to a file
web-search get --storage redis 20250420-120145_quantum-computing --export results.json
```

### Cleanup and Management

```bash
# Clean up old results with Redis storage
web-search clean --storage redis

# Clean up with specific days
web-search clean --storage redis --days 7

# Delete a specific result
web-search delete --storage redis 20250420-120145_quantum-computing
```

### Dual-Backend Usage

```bash
# Use both backends (experimental feature)
web-search --storage dual "quantum computing"

# Read from Redis, fallback to file
web-search get --storage redis-fallback 20250420-120145_quantum-computing
```

## 7. Next Steps

The following implementation tasks are proposed, in order of priority:

1. **Storage Backend Interface**
   - Create `search_client/storage/base.py` with the `StorageBackend` abstract base class
   - Define common exceptions and utility functions

2. **File Backend Migration**
   - Create `search_client/storage/file.py` to implement `FileStorageBackend`
   - Refactor existing file storage code to use the new interface
   - Ensure backward compatibility with existing file patterns

3. **Redis Backend Implementation**
   - Add Redis client dependency to `pyproject.toml`
   - Create `search_client/storage/redis.py` to implement `RedisStorageBackend`
   - Implement connection management and error handling

4. **CLI Integration**
   - Update `search_client/cli.py` to support backend selection
   - Add Redis-specific command-line options
   - Implement storage factory function

5. **Configuration Management**
   - Implement environment variable support for Redis
   - Add YAML configuration file support
   - Establish configuration precedence rules

6. **Migration Tools**
   - Create import/export utilities for moving between backends
   - Implement dual-write capability for gradual migration

7. **Documentation and Tests**
   - Update README with Redis information
   - Create unit tests for Redis storage
   - Update CLI tests to cover Redis options

## 8. Challenges and Considerations

### Dependencies

- **Redis Client**: The integration requires the `redis-py` library, which adds an external dependency to the project.
- **Optional Dependency**: Consider making Redis an optional dependency to keep the core package lightweight.

### Connection Management

- **Connection Pooling**: For repeated operations, implement connection pooling to avoid creating a new connection for each operation.
- **Connection Failures**: Implement robust error handling for cases where Redis is unavailable.
- **Graceful Degradation**: Allow the application to fall back to file storage if Redis is unreachable.

### Security

- **Authentication**: Ensure proper handling of Redis authentication credentials.
- **TLS Support**: For production deployments, consider adding TLS support for Redis connections.
- **Sensitive Data**: Be cautious of storing sensitive search data in Redis, especially in shared environments.

### Performance

- **Data Serialization**: JSON serialization/deserialization can be a bottleneck for large result sets.
- **Memory Usage**: Monitor Redis memory usage, as it can grow quickly with many search results.
- **Bulk Operations**: Use pipelining for bulk operations to improve performance.

### Migration

- **Data Loss Risk**: During migration, there's a risk of data loss if processes are interrupted.
- **Backward Compatibility**: Ensure users can still access their historical search results after migration.
- **Testing Strategy**: Develop a comprehensive testing strategy for the migration process.

### Configuration Complexity

- **Increased Options**: Adding Redis support increases the configuration complexity for users.
- **Sensible Defaults**: Provide sensible defaults to minimize required configuration.
- **Documentation**: Clearly document all configuration options and their interactions.

### Alternative Approaches

- **Redis vs. SQLite**: Consider whether SQLite might be a better fit for some use cases, especially if relational queries are needed.
- **Hybrid Storage**: Evaluate a hybrid approach where metadata is in Redis and full results in files.
- **Cloud Storage**: For some deployments, cloud object storage might be more appropriate than Redis.
