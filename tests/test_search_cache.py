"""Tests for Redis caching functionality in search_client."""

import json
import time
import unittest
from unittest import mock

import fakeredis
import pytest

from search_client.search import run_search, TavilyClient
from search_client.storage.redis import RedisStorageBackend


class TestSearchCache(unittest.TestCase):
    """Test cases for verifying search caching functionality."""

    def setUp(self):
        """Set up the test environment before each test."""
        # Create a fake Redis server for testing
        self.redis_server = fakeredis.FakeServer()
        self.fake_redis = fakeredis.FakeStrictRedis(server=self.redis_server, decode_responses=True)
        
        # Patch Redis client creation to use fakeredis
        self.redis_patcher = mock.patch('redis.Redis', return_value=self.fake_redis)
        self.mock_redis = self.redis_patcher.start()
        
        # Create Redis backend with fake Redis
        self.redis_backend = RedisStorageBackend(
            host="localhost",
            port=16379,
            prefix="test-web-search:",
            ttl_days=1
        )
        
        # Patch the global Redis backend
        self.backend_patcher = mock.patch('search_client.storage._redis_backend', self.redis_backend)
        self.mock_backend = self.backend_patcher.start()
        
        # Sample search results to be used by the mock Tavily client
        self.sample_results = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com/test",
                    "content": "This is a test result content."
                }
            ]
        }
        
        # Create a mock Tavily client - patch it directly in the search module
        self.tavily_patcher = mock.patch('search_client.search.TavilyClient')
        self.mock_tavily = self.tavily_patcher.start()
        
        # Configure the mock client instance
        self.mock_tavily_instance = mock.MagicMock()
        self.mock_tavily.return_value = self.mock_tavily_instance
        self.mock_tavily_instance.search.return_value = self.sample_results
    
    def tearDown(self):
        """Clean up after each test."""
        # Stop all patchers
        self.redis_patcher.stop()
        self.backend_patcher.stop()
        self.tavily_patcher.stop()

    def test_first_search_calls_tavily(self):
        """Test that the first search calls the Tavily API."""
        # Run the search
        query = "test query"
        results = run_search(query, max_results=1, search_depth="basic", include_raw=False, include_domains=None, exclude_domains=None, include_answer="advanced")
        
        # Verify that Tavily API was called
        self.mock_tavily_instance.search.assert_called_once()
        
        # Verify the results were returned
        self.assertEqual(results, self.sample_results)
        
        # Verify that results were stored in Redis
        keys = self.fake_redis.keys(f"{self.redis_backend.prefix}*")
        self.assertTrue(len(keys) > 0, "No keys were stored in Redis")
    
    def test_second_search_uses_cache(self):
        """Test that a second search with the same query uses the Redis cache."""
        query = "test query"
        
        # First search - should call Tavily
        run_search(query, max_results=1, search_depth="basic", include_raw=False, include_domains=None, exclude_domains=None, include_answer="advanced")
        
        # Reset the mock to track new calls
        self.mock_tavily_instance.search.reset_mock()
        
        # Second search with same query - should use cache
        results = run_search(query, max_results=1, search_depth="basic", include_raw=False, include_domains=None, exclude_domains=None, include_answer="advanced")
        
        # Verify that Tavily API was NOT called
        self.mock_tavily_instance.search.assert_not_called()
        
        # Verify that we got results 
        # For cache hits, results include _from_cache: True
        expected_results = self.sample_results.copy()
        expected_results['_from_cache'] = True
        self.assertEqual(results, expected_results)
    
    def test_expired_cache_calls_tavily_again(self):
        """Test that an expired cache entry causes a new Tavily API call."""
        query = "test query"
        
        # First search - should call Tavily
        run_search(query, max_results=1, search_depth="basic", include_raw=False, include_domains=None, exclude_domains=None, include_answer="advanced")
        
        # Reset the mock to track new calls
        self.mock_tavily_instance.search.reset_mock()
        
        # Modify cached entry to be expired (set TTL to -1)
        query_key = f"{self.redis_backend.prefix}query:{self.redis_backend._slugify(query)}"
        identifiers = self.fake_redis.zrangebyscore(query_key, 0, float('inf'))
        
        # Update the timestamp in the cached data to be expired
        for identifier in identifiers:
            result_key = f"{self.redis_backend.prefix}result:{identifier}"
            # Make sure the key exists before trying to get it
            if self.fake_redis.exists(result_key):
                data = json.loads(self.fake_redis.get(result_key))
                
                # Update the timestamp to be old
                old_time = time.time() - (2 * 24 * 60 * 60)  # 2 days ago (beyond the TTL)
                
                # Set the key with expired data with a very short TTL
                self.fake_redis.set(result_key, json.dumps(data), ex=1)
                # Force key expiration (fakeredis doesn't always respect 'ex')
                self.fake_redis.delete(result_key)
        
        # Search again
        results = run_search(query, max_results=1, search_depth="basic", include_raw=False, include_domains=None, exclude_domains=None, include_answer="advanced")
        
        # Verify that Tavily API was called again
        self.mock_tavily_instance.search.assert_called_once()
        
        # Verify that we got results
        self.assertEqual(results, self.sample_results)

    def test_cache_hit_extends_ttl(self):
        """Test that accessing a cached entry extends its TTL."""
        query = "test query for ttl extension"
        
        # First search - creates a cache entry
        run_search(query, max_results=1, search_depth="basic", include_raw=False, include_domains=None, exclude_domains=None, include_answer="advanced")
        
        # Find the cache key for the result
        query_key = f"{self.redis_backend.prefix}query:{self.redis_backend._slugify(query)}"
        identifiers = self.fake_redis.zrangebyscore(query_key, 0, float('inf'))
        self.assertTrue(len(identifiers) > 0, "No cache entry was created")
        
        # Get the result key
        result_key = f"{self.redis_backend.prefix}result:{identifiers[0]}"
        self.assertTrue(self.fake_redis.exists(result_key), "Result key does not exist")
        
        # Get the initial TTL
        initial_ttl = self.fake_redis.ttl(result_key)
        self.assertTrue(initial_ttl > 0, "Initial TTL should be positive")
        
        # Wait a short time to ensure the TTL would have decreased
        time.sleep(1)
        
        # Get a slightly decreased TTL (should be at least 1 second less)
        decreased_ttl = self.fake_redis.ttl(result_key)
        self.assertTrue(decreased_ttl < initial_ttl, "TTL should have decreased")
        
        # Access the cache entry by calling get_results directly
        self.redis_backend.get_results(identifiers[0])
        
        # Check that the TTL has been reset/extended
        extended_ttl = self.fake_redis.ttl(result_key)
        
        # The extended TTL should be approximately the original TTL (1 day in seconds)
        expected_ttl = self.redis_backend.ttl_days * 24 * 60 * 60
        
        # Allow a small margin for test execution time
        self.assertTrue(
            extended_ttl > decreased_ttl,
            f"TTL was not extended: initial={initial_ttl}, decreased={decreased_ttl}, extended={extended_ttl}"
        )
        
        # Check that the extended TTL is close to the expected full TTL
        # Allow a tolerance of 10 seconds for test execution time
        self.assertTrue(
            abs(extended_ttl - expected_ttl) < 10,
            f"Extended TTL ({extended_ttl}) is not close to expected TTL ({expected_ttl})"
        )


if __name__ == "__main__":
    unittest.main()

