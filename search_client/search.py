"""Tavily search functionality for web-search-client."""

import os
import sys
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from tavily import TavilyClient

from search_client.logger import logger

# Load environment variables from .env file
load_dotenv()

# Get Tavily API key from environment
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


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


def run_search(
    query: str, 
    max_results: int = 10, 
    search_depth: str = "basic",
    include_raw: bool = False,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Run a web search using Tavily API.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 10)
        search_depth: Search depth, either "basic" or "comprehensive" (default: "basic")
        include_raw: Whether to include raw content in results (default: False)
        include_domains: Optional list of domains to include in search
        exclude_domains: Optional list of domains to exclude from search
        
    Returns:
        List of search result dictionaries
        
    Raises:
        SearchError: If there's an error with the search request
    """
    try:
        validate_api_key()

        logger.info(f"Searching for: {query}")
        logger.info(f"Max results: {max_results}, depth: {search_depth}")

        # Initialize Tavily client
        client = TavilyClient(api_key=TAVILY_API_KEY)
        
        # Prepare search parameters
        search_params = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": include_raw,
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

