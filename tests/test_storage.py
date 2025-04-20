"""Tests for the storage module."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from search_client.storage import (RESULT_DIR, cleanup, ensure_result_dir,
                                  generate_filename, save_results, slugify)


@pytest.fixture
def mock_result_dir():
    """Create a temporary directory for test files."""
    original_dir = RESULT_DIR
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patch the RESULT_DIR to use our temporary directory
        with patch('search_client.storage.RESULT_DIR', Path(temp_dir)):
            yield Path(temp_dir)
    # No need to restore, as the patch context manager will handle it


def test_slugify():
    """Test that the slugify function properly formats text."""
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("This is a TEST") == "this-is-a-test"
    assert slugify("Multiple   spaces") == "multiple-spaces"
    assert slugify("special@#$%^chars") == "special-chars"
    assert slugify("very" + "-" * 100 + "long") == "very" + "-" * 45 + "long"


def test_generate_filename():
    """Test that generate_filename creates properly formatted filenames."""
    filename = generate_filename("Test Query")
    
    # Check format: YYYYMMDD-HHMMSS_test-query.json
    assert filename.endswith("_test-query.json")
    assert len(filename.split("_")[0]) == 15  # YYYYMMDD-HHMMSS format
    assert "-" in filename.split("_")[0]  # Has the date-time separator


def test_ensure_result_dir(mock_result_dir):
    """Test that ensure_result_dir creates the directory if it doesn't exist."""
    # Directory should exist after calling ensure_result_dir
    ensure_result_dir()
    assert mock_result_dir.exists()
    assert mock_result_dir.is_dir()


def test_save_results(mock_result_dir):
    """Test that save_results properly saves search results to a file."""
    query = "test query"
    results = {
        "results": [
            {"title": "Test Result 1", "url": "https://example.com/1", "content": "Example content 1"},
            {"title": "Test Result 2", "url": "https://example.com/2", "content": "Example content 2"}
        ]
    }
    
    # Save the results
    file_path = save_results(query, results)
    
    # Check that the file exists
    assert file_path.exists()
    assert file_path.is_file()
    
    # Check file content
    with open(file_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    
    assert saved_data["query"] == query
    assert "timestamp" in saved_data
    assert saved_data["results"] == results


def test_cleanup_no_old_files(mock_result_dir):
    """Test cleanup when there are no old files to delete."""
    # Create the result directory
    ensure_result_dir()
    
    # No files exist yet
    deleted = cleanup(days=14)
    assert deleted == 0


def test_cleanup_with_old_files(mock_result_dir):
    """Test cleanup when there are old files to delete."""
    # Create the result directory
    ensure_result_dir()
    
    # Create some test files
    current_time = datetime.now()
    
    # Create a recent file (should not be deleted)
    recent_file = mock_result_dir / "recent_file.json"
    recent_file.touch()
    
    # Create old files (should be deleted)
    old_files = []
    for i in range(3):
        old_file = mock_result_dir / f"old_file_{i}.json"
        old_file.touch()
        old_files.append(old_file)
        
    # Modify access/modification times to make files appear old
    old_time = current_time - timedelta(days=20)
    old_timestamp = old_time.timestamp()
    
    for file in old_files:
        os.utime(file, (old_timestamp, old_timestamp))
    
    # Run cleanup (should delete the old files)
    deleted = cleanup(days=14)
    
    # Check that only the old files were deleted
    assert deleted == 3
    assert recent_file.exists()
    for file in old_files:
        assert not file.exists()

