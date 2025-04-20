"""Tests for the Redis storage module."""

import json
import time
from unittest import mock

import fakeredis
import pytest

from search_client.storage import save_results, cleanup
from search_client.storage.redis import RedisStorageBackend
from search_client.storage.base import StorageError


@pytest.fixture
def fake_redis_setup():
    """Set up a fake Redis server for testing."""
    # Create a fake Redis server
    redis_server = fakeredis.FakeServer()
    fake_redis = fakeredis.FakeStrictRedis(server=redis_server, decode_responses=True)
    
    # Patch Redis client creation to use fakeredis
    redis_patcher = mock.patch('redis.Redis', return_value=fake_redis)
    mock_redis = redis_patcher.start()
    
    # Create Redis backend with fake Redis
    redis_backend = RedisStorageBackend(
        host="localhost",
        port=16379,
        prefix="test-web-search:",
        ttl_days=1
    )
    
    # Patch the global Redis backend in storage module
    backend_patcher = mock.patch('search_client.storage._redis_backend', redis_backend)
    mock_backend = backend_patcher.start()
    
    yield fake_redis, redis_backend
    
    # Clean up patchers
    redis_patcher.stop()
    backend_patcher.stop()


def test_redis_backend_init():
    """Test initialization of the Redis backend."""
    # Test with default parameters
    backend = RedisStorageBackend()
    assert backend.prefix == "web-search:"
    assert backend.ttl_days == 14
    
    # Test with custom parameters
    backend = RedisStorageBackend(
        host="test-host",
        port=12345,
        prefix="custom-prefix:",
        ttl_days=30
    )
    assert backend.prefix == "custom-prefix:"
    assert backend.ttl_days == 30


def test_make_key():
    """Test the _make_key method."""
    backend = RedisStorageBackend(prefix="test:")
    key = backend._make_key("result", "123456")
    assert key == "test:result:123456"


def test_slugify():
    """Test the _slugify method."""
    backend = RedisStorageBackend()
    
    # Test various text inputs
    assert backend._slugify("Hello, World!") == "hello-world"
    assert backend._slugify("This is a TEST") == "this-is-a-test"
    assert backend._slugify("Multiple   spaces") == "multiple-spaces"
    assert backend._slugify("special@#$%^chars") == "special-chars"
    
    # Test length limitation
    long_text = "very" + "-" * 100 + "long"
    assert len(backend._slugify(long_text)) <= 50


def test_save_results(fake_redis_setup):
    """Test saving results to Redis."""
    fake_redis, redis_backend = fake_redis_setup
    
    query = "test query"
    results = {
        "results": [
            {"title": "Test Result 1", "url": "https://example.com/1", "content": "Example content 1"},
            {"title": "Test Result 2", "url": "https://example.com/2", "content": "Example content 2"}
        ]
    }
    
    # Save results
    identifier = redis_backend.save_results(query, results)
    
    # Check that the key exists in Redis
    result_key = f"{redis_backend.prefix}result:{identifier}"
    assert fake_redis.exists(result_key)
    
    # Check that data was saved correctly
    saved_data = json.loads(fake_redis.get(result_key))
    assert saved_data["query"] == query
    assert "timestamp" in saved_data
    assert saved_data["results"] == results
    
    # Check that the TTL was set
    ttl = fake_redis.ttl(result_key)
    assert ttl > 0
    
    # Verify entry in index
    index_key = f"{redis_backend.prefix}index:all"
    members = fake_redis.zrange(index_key, 0, -1)
    assert identifier in members
    
    # Verify entry in query index
    query_key = f"{redis_backend.prefix}query:{redis_backend._slugify(query)}"
    members = fake_redis.zrange(query_key, 0, -1)
    assert identifier in members


def test_get_results(fake_redis_setup):
    """Test retrieving results from Redis."""
    fake_redis, redis_backend = fake_redis_setup
    
    query = "test query"
    results = {
        "results": [
            {"title": "Test Result", "url": "https://example.com/test", "content": "Test content"}
        ]
    }
    
    # Save results first
    identifier = redis_backend.save_results(query, results)
    
    # Get the results
    retrieved = redis_backend.get_results(identifier)
    
    # Check that the data matches
    assert retrieved["query"] == query
    assert retrieved["results"] == results
    
    # Check that TTL was extended
    result_key = f"{redis_backend.prefix}result:{identifier}"
    initial_ttl = fake_redis.ttl(result_key)
    
    # Artificially reduce TTL for testing
    fake_redis.expire(result_key, 1000)
    reduced_ttl = fake_redis.ttl(result_key)
    assert reduced_ttl < initial_ttl
    
    # Access again and check that TTL is extended
    redis_backend.get_results(identifier)
    extended_ttl = fake_redis.ttl(result_key)
    assert extended_ttl > reduced_ttl


def test_list_results(fake_redis_setup):
    """Test listing results from Redis."""
    fake_redis, redis_backend = fake_redis_setup
    
    # Save multiple results
    queries = ["query one", "query two", "query three"]
    identifiers = []
    
    for query in queries:
        results = {
            "results": [
                {"title": f"Result for {query}", "url": f"https://example.com/{query}", "content": f"Content for {query}"}
            ]
        }
        identifier = redis_backend.save_results(query, results)
        identifiers.append(identifier)
    
    # List all results
    all_results = redis_backend.list_results(limit=10)
    assert len(all_results) == 3
    
    # Test pagination
    paginated = redis_backend.list_results(limit=2, offset=1)
    assert len(paginated) == 2
    
    # Test filtering by query
    filtered = redis_backend.list_results(query="query one")
    assert len(filtered) == 1
    assert filtered[0]["query"] == "query one"


def test_delete_results(fake_redis_setup):
    """Test deleting results from Redis."""
    fake_redis, redis_backend = fake_redis_setup
    
    # Save a result first
    query = "delete test"
    results = {"results": [{"title": "Test", "url": "https://example.com", "content": "Content"}]}
    identifier = redis_backend.save_results(query, results)
    
    # Verify it exists
    result_key = f"{redis_backend.prefix}result:{identifier}"
    assert fake_redis.exists(result_key)
    
    # Delete it
    success = redis_backend.delete_results(identifier)
    assert success is True
    
    # Verify it's gone
    assert not fake_redis.exists(result_key)
    
    # Verify removed from indexes
    index_key = f"{redis_backend.prefix}index:all"
    query_key = f"{redis_backend.prefix}query:{redis_backend._slugify(query)}"
    
    members = fake_redis.zrange(index_key, 0, -1)
    assert identifier not in members
    
    query_members = fake_redis.zrange(query_key, 0, -1)
    assert identifier not in query_members
