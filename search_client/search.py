"""Tavily search functionality for web-search-client."""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from dotenv import load_dotenv
from tavily import TavilyClient

from search_client.logger import logger
from search_client.storage import _get_redis_backend, save_results
# Load environment variables from .env file
load_dotenv()

# Get Tavily API key from environment
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Configure cache TTL (default 24 hours = 86400 seconds)
SEARCH_CACHE_TTL_SECONDS = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "86400"))


class SearchError(Exception):
    """Exception raised for errors in the search process."""
    pass


def validate_api_key() -> None:
    """Validate that the Tavily API key is available.
    
    Raises:
        SearchError: If the API key is not found
    """
    if not TAVILY_API_KEY:
        logger.error("Tavily API key not found in environment variables")
        logger.error("Please set TAVILY_API_KEY in your .env file")
        raise SearchError("Tavily API key not found")


def get_cached_results(
    query: str,
    search_depth: str,
    max_results: int,
    include_raw: bool ,
    include_domains: Optional[List[str]],
    exclude_domains: Optional[List[str]],
    include_answer: Union[bool, str],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if results for this query are already cached in Redis.
    
    Args:
        query: The search query string
        search_depth: Search depth, either "basic" or "advanced"
        max_results: Maximum number of results to return
        include_raw: Whether to include raw content in results
        include_domains: Optional list of domains to include in search
        exclude_domains: Optional list of domains to exclude from search
        include_answer: Whether to include an AI-generated answer in results.
                        "false": No answer, "basic": Quick answer, 
                        "advanced": Detailed answer
        
    Returns:
        Tuple of (found, results), where found is a boolean indicating if
        results were found in cache, and results is the cached data if found
    """
    try:
        # Get Redis backend
        redis_backend = _get_redis_backend()
        
        # Get the most recent result for this query
        cached_results = redis_backend.list_results(query=query, limit=1)
        
        if cached_results and len(cached_results) > 0:
            # We found a cached result
            cached_data = cached_results[0]
            
            # Extract the actual search results from the cached data
            if "results" in cached_data and "results" in cached_data["results"]:
                logger.info(f"Cache HIT for query: {query}")
                # Add a flag to indicate this came from cache
                result = cached_data["results"]
                result["_from_cache"] = True
                return True, result
        
        logger.info(f"Cache MISS for query: {query}")
        return False, None
            
    except Exception as e:
        # If there's any error accessing the cache, log it but don't fail the search
        logger.warning(f"Error checking Redis cache: {e}")
        return False, None


def run_search(
    query: str, 
    max_results: int, 
    search_depth: str,
    include_raw: bool,
    include_domains: Optional[List[str]],
    exclude_domains: Optional[List[str]],
    include_answer: Union[bool, str],
) -> Dict[str, Any]:
    """Run a web search using Tavily API.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return
        search_depth: Search depth, either "basic" or "advanced"
        include_raw: Whether to include raw content in results
        include_domains: Optional list of domains to include in search
        exclude_domains: Optional list of domains to exclude from search
        include_answer: Whether to include an AI-generated answer in results.
                        False: No answer, "basic": Quick answer, 
                        "advanced": Detailed answer
        
    Returns:
        List of search result dictionaries
        
    Raises:
        SearchError: If there's an error with the search request
    """
    try:
        logger.info(f"Searching for: {query}")
        logger.info(f"Max results: {max_results}, depth: {search_depth}")

        # Check if results are already in Redis cache
        found_in_cache, cached_results = get_cached_results(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_raw=include_raw,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_answer=include_answer
        )
        
        # If found in cache, return cached results
        if found_in_cache and cached_results is not None:
            # Ensure the format matches what would be returned from Tavily API
            return cached_results
        
        # If not in cache, we need to make an API call
        validate_api_key()

        # Initialize Tavily client
        client = TavilyClient(api_key=TAVILY_API_KEY)
        
        # Prepare search parameters
        search_params = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": include_raw,
            "include_answer": include_answer,
        }
        
        # Add optional domain filters if provided
        if include_domains:
            search_params["include_domains"] = include_domains
        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains
            
        # Execute search
        response = client.search(**search_params)
        # Extract and return results
        if "results" in response:
            logger.info(f"Found {len(response['results'])} results")
            # Mark that these results are fresh from the API (not from cache)
            response["_from_cache"] = False
            
            # Save the results to Redis cache
            try:
                save_results(query, response)
                logger.info(f"Saved search results to cache for query: {query}")
            except Exception as e:
                logger.warning(f"Failed to save results to cache: {e}")
                
            return response
        else:
            logger.warning("No results field in API response")
            return response
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        raise SearchError(f"Network error: {e}")
    except Exception as e:
        logger.error(f"Error performing search: {e}")
        raise SearchError(f"Search failed: {e}")

