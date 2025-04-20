"""Command-line interface for web search client."""

import sys
from typing import List, Optional

import click

from search_client import __version__
from search_client.logger import logger
from search_client.search import SearchError, run_search
from search_client.storage import cleanup, save_results


@click.group()
@click.version_option(version=__version__)
def cli():
    """Web Search Client using Tavily API.
    
    Search the web and save results to local files.
    """
    pass


@cli.command()
@click.argument("query", required=True)
@click.option(
    "--max-results", "-n", 
    default=10, 
    help="Maximum number of results to return (default: 10)"
)
@click.option(
    "--depth", "-d", 
    type=click.Choice(["basic", "comprehensive"]), 
    default="basic",
    help="Search depth (basic is faster, comprehensive is more thorough)"
)
@click.option(
    "--raw/--no-raw", 
    default=False, 
    help="Include raw content in results"
)
@click.option(
    "--include-domain", "-i",
    multiple=True,
    help="Domain to include in search (can be used multiple times)"
)
@click.option(
    "--exclude-domain", "-e",
    multiple=True,
    help="Domain to exclude from search (can be used multiple times)"
)
@click.option(
    "--retention-days", "-r",
    default=14,
    help="Number of days to keep result files (default: 14)"
)
def search(
    query: str,
    max_results: int,
    depth: str,
    raw: bool,
    include_domain: List[str],
    exclude_domain: List[str],
    retention_days: int,
):
    """Search the web and save results to a local file.
    
    QUERY: The search query string
    """
    try:
        # First clean up old results
        cleanup(days=retention_days)
        
        # Run the search
        include_domains = list(include_domain) if include_domain else None
        exclude_domains = list(exclude_domain) if exclude_domain else None
        
        search_results = run_search(
            query=query,
            max_results=max_results,
            search_depth=depth,
            include_raw=raw,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
        
        # Only save results if they didn't come from cache
        if not search_results.get("_from_cache", False):
            logger.info("Saving fresh results to Redis")
            file_path = save_results(query, search_results)
        else:
            # For cache hits, we can retrieve the existing file path
            # This avoids the duplicate "Results saved to Redis with ID: xyz" message
            logger.info("Using cached results, not saving again")
            file_path = f"Using cached results for: {query}"
        
        # Display success message
        num_results = len(search_results.get("results", []))
        click.echo(f"Found {num_results} results for query: '{query}'")
        click.echo(f"Results saved to: {file_path}")
        
        # Show top results in the terminal
        if num_results > 0:
            click.echo("\nTop results:")
            for i, result in enumerate(search_results.get("results", [])[:3], 1):
                click.echo(f"\n{i}. {click.style(result.get('title', 'No title'), bold=True)}")
                click.echo(f"   {click.style(result.get('url', 'No URL'), fg='blue')}")
                if "content" in result:
                    # Truncate content for display
                    content = result["content"]
                    if len(content) > 200:
                        content = content[:197] + "..."
                    click.echo(f"   {content}")
            
            if num_results > 3:
                click.echo(f"\n... and {num_results - 3} more results in the saved file.")
                
    except SearchError as e:
        logger.error(f"Search error: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)



if __name__ == "__main__":
    cli()

