"""Base classes for storage backends."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class StorageError(Exception):
    """Exception raised for errors in the storage backend."""
    pass


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def save_results(self, query: str, results: Dict[str, Any]) -> str:
        """Save search results and return an identifier.
        
        Args:
            query: The search query
            results: The search results to save
            
        Returns:
            A unique identifier for the saved results
            
        Raises:
            StorageError: If there's an error saving the results
        """
        pass
        
    @abstractmethod
    def get_results(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieve results by identifier.
        
        Args:
            identifier: The unique identifier for the results
            
        Returns:
            The search results, or None if not found
            
        Raises:
            StorageError: If there's an error retrieving the results
        """
        pass
        
    @abstractmethod
    def list_results(
        self, 
        limit: int = 10, 
        offset: int = 0,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List available results with pagination.
        
        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip
            query: Optional query string to filter results
            
        Returns:
            A list of search result metadata
            
        Raises:
            StorageError: If there's an error listing the results
        """
        pass
        
    @abstractmethod
    def delete_results(self, identifier: str) -> bool:
        """Delete results by identifier.
        
        Args:
            identifier: The unique identifier for the results
            
        Returns:
            True if the results were deleted, False if not found
            
        Raises:
            StorageError: If there's an error deleting the results
        """
        pass
        
    @abstractmethod
    def cleanup(self, max_age_days: int = 14) -> int:
        """Clean up old results and return count of removed items.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of results removed
            
        Raises:
            StorageError: If there's an error during cleanup
        """
        pass

