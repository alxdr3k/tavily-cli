#!/usr/bin/env python3
"""Example demonstrating the Redis storage backend for web search client.

This script shows how to use the Redis storage backend to:
1. Save search results
2. Retrieve search results
3. List stored results
4. Delete and clean up results

Note: This example uses a mock Redis implementation for demonstration purposes.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import the search_client package
sys.path.insert(0, str(Path(__file__).parent.parent))

from search_client.logger import setup_logger
from search_client.storage.redis import RedisStorageBackend, StorageError

# Set up logger
logger = setup_logger("redis_example")


def generate_mock_search_results(query, num_results=3):
    """Generate mock search results for demonstration."""
    return {
        "results": [
            {
                "title": f"Result {i} for {query}",
                "url": f"https://example.com/result/{i}",
                "content": f"This is some sample content for result {i} about {query}."
            }
            for i in range(1, num_results + 1)
        ]
    }


def format_result(result, show_content=True):
    """Format a search result for display."""
    output = []
    output.append(f"ID: {result.get('id', 'Unknown')}")
    output.append(f"Query: {result.get('query', 'Unknown')}")
    output.append(f"Timestamp: {result.get('timestamp', 'Unknown')}")
    
    if 'results' in result:
        output.append(f"Found {len(result['results'])} results:")
        
        for i, item in enumerate(result['results'], 1):
            output.append(f"  {i}. {item.get('title', 'No title')}")
            output.append(f"     URL: {item.get('url', 'No URL')}")
            
            if show_content and 'content' in item:
                content = item['content']
                if len(content) > 70:
                    content = content[:67] + "..."
                output.append(f"     {content}")
            
            output.append("")
    
    return "\n".join(output)


def main():
    """Run the Redis storage backend example."""
    try:
        print("=" * 80)
        print("Redis Storage Backend Example")
        print("=" * 80)
        
        # 1. Set up the Redis storage backend
        print("\n1. Setting up Redis storage backend...")
        redis_backend = RedisStorageBackend(
            host="localhost",
            port=6379,
            prefix="example:",
            ttl_days=14
        )
        print(f"Redis backend initialized with prefix: {redis_backend.prefix}")
        
        # 2. Perform a mock search
        print("\n2. Performing mock searches...")
        queries = [
            "Python programming",
            "Machine learning",
            "Data science"
        ]
        
        result_ids = []
        for query in queries:
            print(f"   Searching for: {query}")
            # Generate mock search results (in a real scenario, this would come from Tavily API)
            results = generate_mock_search_results(query)
            
            # 3. Save the results
            result_id = redis_backend.save_results(query, results)
            result_ids.append(result_id)
            print(f"   Results saved with ID: {result_id}")
        
        # Sleep to demonstrate time difference
        print("\n   Waiting for a moment...")
        time.sleep(1)
        
        # Add one more result that will appear as more recent
        print("   Performing one more search...")
        older_query = "Artificial intelligence"
        older_results = generate_mock_search_results(older_query, num_results=2)
        older_id = redis_backend.save_results(older_query, older_results)
        result_ids.append(older_id)
        print(f"   Results saved with ID: {older_id}")
        
        # 4. Retrieve and display results
        print("\n3. Retrieving results...")
        for result_id in result_ids:
            print(f"\nRetrieving result: {result_id}")
            result = redis_backend.get_results(result_id)
            if result:
                result["id"] = result_id  # Add ID to the result for display
                print(format_result(result))
            else:
                print(f"No results found for ID: {result_id}")
        
        # 5. List all stored results
        print("\n4. Listing all results...")
        all_results = redis_backend.list_results(limit=10)
        print(f"Found {len(all_results)} stored results:")
        for result in all_results:
            # Print a shorter summary
            print(f"- {result.get('id')}: {result.get('query')} ({len(result.get('results', {}).get('results', []))} items)")
        
        # 6. Perform cleanup
        print("\n5. Cleaning up old results...")
        # In a real scenario, we'd use a higher value like 14 days
        # For the example, we're using 0 to delete everything older than now
        deleted = redis_backend.cleanup(max_age_days=0)
        print(f"Cleaned up {deleted} result(s)")
        
        # Verify the cleanup
        print("\n6. Listing results after cleanup...")
        remaining = redis_backend.list_results()
        print(f"Found {len(remaining)} results after cleanup")
        
        # 7. Delete a specific result
        if result_ids:
            print(f"\n7. Deleting specific result: {result_ids[0]}...")
            deleted = redis_backend.delete_results(result_ids[0])
            print(f"Result deleted: {deleted}")
            
            # Verify the deletion
            all_results = redis_backend.list_results()
            print(f"Found {len(all_results)} results after deletion")
        
        print("\nExample completed successfully!")
        
    except StorageError as e:
        print(f"\nStorage error: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

