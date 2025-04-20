"""Command-line interface for web search client."""

import sys
from typing import List, Optional

import click

from search_client import __version__
from search_client.logger import logger
from search_client.search import SearchError, run_search
from search_client.storage import cleanup, save_results
@click.command()
@click.version_option(version=__version__)
@click.argument("query", required=False)
@click.option(
    "--clean", 
    is_flag=True, 
    help="Clean up search result files older than the specified days (default: 14 days)"
)
@click.option(
    "--days", 
    type=int, 
    default=14, 
    help="Number of days to keep files when using --clean (older results will be deleted, default: 14)"
)
@click.option(
    "--all", 
    is_flag=True, 
    help="When used with --clean, removes ALL search results regardless of age"
)
@click.option(
    "--force", 
    is_flag=True, 
    help="Force cleanup without confirmation when using --clean"
)
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
@click.option(
    "--include-answer", "-a",
    type=click.Choice(["false", "basic", "advanced"]),
    default="advanced",
    help="Include an AI-generated answer in results (default: advanced)"
)
def cli(
    query: Optional[str],
    clean: bool,
    days: int,
    all: bool,
    force: bool,
    max_results: int,
    depth: str,
    raw: bool,
    include_domain: List[str],
    exclude_domain: List[str],
    retention_days: int,
    include_answer: str,
):
    """Web Search Client using Tavily API.
    
    Search the web and save results to local files.
    
    QUERY: The search query string
    
    The include_answer option can be set to:
    - 'false': No AI-generated answer
    - 'basic': A quick answer summary
    - 'advanced': A more detailed answer (default)
    """
    try:
        # Handle 'all' flag used without 'clean'
        if all and not clean:
            click.echo("Error: The --all flag can only be used with --clean.", err=True)
            click.echo("Use --help to see usage information.", err=True)
            sys.exit(1)

        # Handle cleanup mode
        if clean:
            # If 'all' flag is set, override days to 0 (clean everything)
            if all:
                days = 0
                confirmation_msg = "This will permanently delete ALL cached search results. Continue?"
            else:
                confirmation_msg = f"Clean up search result files older than {days} days?"

            if not force:
                confirm = click.confirm(confirmation_msg)
                if not confirm:
                    click.echo("Cleanup cancelled.")
                    return
            
            deleted_count = cleanup(days=days)
            
            if all:
                click.echo(f"Cleaned up {deleted_count} result file(s)")
            else:
                click.echo(f"Cleaned up {deleted_count} result file(s) older than {days} days")
            return

        # Ensure query is provided for search mode
        if query is None:
            click.echo("Error: Missing argument 'QUERY'.", err=True)
            click.echo("Use --help to see usage information.", err=True)
            sys.exit(1)
            
        # For search mode, first clean up old results
        cleanup(days=retention_days)
        
        # Run the search
        include_domains = list(include_domain) if include_domain else None
        exclude_domains = list(exclude_domain) if exclude_domain else None
        
        # Convert include_answer from string to appropriate type for the API
        include_answer_param = False if include_answer == "false" else include_answer
        
        search_results = run_search(
            query=query,
            max_results=max_results,
            search_depth=depth,
            include_raw=raw,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_answer=include_answer_param,
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
            for i, result in enumerate(search_results.get("results", []), 1):
                click.echo(f"\n{i}. {click.style(result.get('title', 'No title'), bold=True)}")
                click.echo(f"   {click.style(result.get('url', 'No URL'), fg='blue')}")
                if "content" in result:
                    # Truncate content for display
                    click.echo(f"   {result['content']}")
            # 
            # if num_results > 3:
            #     click.echo(f"\n... and {num_results - 3} more results in the saved file.")
                
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

