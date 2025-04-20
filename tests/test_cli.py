"""Tests for the CLI interface."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import click.testing
import pytest

from search_client.cli import cli


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return click.testing.CliRunner()


@pytest.fixture
def mock_search():
    """Mock the search.run_search function."""
    with patch("search_client.cli.run_search") as mock:
        # Setup mock search results
        mock.return_value = {
            "results": [
                {
                    "title": "Test Result 1",
                    "url": "https://example.com/1",
                    "content": "This is test content 1"
                },
                {
                    "title": "Test Result 2",
                    "url": "https://example.com/2",
                    "content": "This is test content 2"
                }
            ]
        }
        yield mock


@pytest.fixture
def mock_storage():
    """Mock the storage functions."""
    with patch("search_client.cli.cleanup") as mock_cleanup, \
         patch("search_client.cli.save_results") as mock_save:
        
        # Setup the save_results mock to return a file path
        mock_save.return_value = Path("search_results/20251231-120000_test-query.json")
        
        # Setup the cleanup mock to return a count of deleted files
        mock_cleanup.return_value = 0
        
        yield {
            "cleanup": mock_cleanup,
            "save_results": mock_save
        }


def test_version(cli_runner):
    """Test that the --version option works."""
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


def test_search_command_basic(cli_runner, mock_search, mock_storage):
    """Test the basic search command."""
    result = cli_runner.invoke(cli, ["search", "test query"])
    
    # Check exit code and output
    assert result.exit_code == 0
    assert "Found 2 results for query: 'test query'" in result.output
    assert "Results saved to:" in result.output
    assert "Test Result 1" in result.output
    assert "https://example.com/1" in result.output
    
    # Verify function calls
    mock_storage["cleanup"].assert_called_once_with(days=14)
    mock_search.assert_called_once()
    mock_storage["save_results"].assert_called_once()
    
    # Verify search parameters
    args, kwargs = mock_search.call_args
    assert kwargs["query"] == "test query"
    assert kwargs["max_results"] == 10  # default value
    assert kwargs["search_depth"] == "basic"  # default value
    assert not kwargs["include_raw"]  # default value


def test_search_command_with_options(cli_runner, mock_search, mock_storage):
    """Test the search command with various options."""
    result = cli_runner.invoke(cli, [
        "search", 
        "--max-results", "5",
        "--depth", "comprehensive",
        "--raw",
        "--include-domain", "example.com",
        "--exclude-domain", "spam.com",
        "--retention-days", "30",
        "advanced query"
    ])
    
    # Check exit code and output
    assert result.exit_code == 0
    assert "Found 2 results for query: 'advanced query'" in result.output
    
    # Verify function calls with correct parameters
    mock_storage["cleanup"].assert_called_once_with(days=30)
    
    args, kwargs = mock_search.call_args
    assert kwargs["query"] == "advanced query"
    assert kwargs["max_results"] == 5
    assert kwargs["search_depth"] == "comprehensive"
    assert kwargs["include_raw"] is True
    assert kwargs["include_domains"] == ["example.com"]
    assert kwargs["exclude_domains"] == ["spam.com"]


def test_clean_command(cli_runner, mock_storage):
    """Test the clean command."""
    # Setup the cleanup mock to return non-zero (some files deleted)
    mock_storage["cleanup"].return_value = 3
    
    # Test with --force to skip confirmation
    result = cli_runner.invoke(cli, ["clean", "--force"])
    
    # Check exit code and output
    assert result.exit_code == 0
    assert "Cleaned up 3 old result file(s)" in result.output
    
    # Verify function calls
    mock_storage["cleanup"].assert_called_once_with(days=14)  # default value


def test_clean_command_with_days(cli_runner, mock_storage):
    """Test the clean command with custom days."""
    # Setup the cleanup mock to return non-zero (some files deleted)
    mock_storage["cleanup"].return_value = 5
    
    # Test with --force to skip confirmation and custom days
    result = cli_runner.invoke(cli, ["clean", "--force", "--days", "7"])
    
    # Check exit code and output
    assert result.exit_code == 0
    assert "Cleaned up 5 old result file(s)" in result.output
    
    # Verify function calls with correct parameters
    mock_storage["cleanup"].assert_called_once_with(days=7)


def test_clean_command_confirmation(cli_runner, mock_storage):
    """Test the clean command confirmation prompt."""
    # Mock confirmation response (user enters 'n' to cancel)
    result = cli_runner.invoke(cli, ["clean"], input="n\n")
    
    # Should abort without calling cleanup
    assert result.exit_code != 0
    assert "Aborted" in result.output
    mock_storage["cleanup"].assert_not_called()
    
    # Reset mock and test with 'y' response
    mock_storage["cleanup"].reset_mock()
    result = cli_runner.invoke(cli, ["clean"], input="y\n")
    
    # Should proceed with cleanup
    assert result.exit_code == 0
    mock_storage["cleanup"].assert_called_once()

