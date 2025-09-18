"""
Base ObjectStore abstract class defining the interface for all storage backends.

This class represents the core abstraction for the 5D optical storage system,
providing a unified interface regardless of the underlying storage mechanism.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, List, Optional, Dict, Any
from pathlib import Path
import io


class ObjectStore(ABC):
    """Abstract base class for object storage implementations."""

    @abstractmethod
    def put(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store data with the given key.
        
        Args:
            key: Unique identifier for the object
            data: Binary data to store
            metadata: Optional metadata to associate with the object
        """
        pass

    @abstractmethod
    def get(self, key: str) -> bytes:
        """
        Retrieve data by key.
        
        Args:
            key: Unique identifier for the object
            
        Returns:
            Binary data associated with the key
            
        Raises:
            KeyError: If key does not exist
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if an object exists.
        
        Args:
            key: Unique identifier for the object
            
        Returns:
            True if object exists, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete an object.
        
        Args:
            key: Unique identifier for the object
            
        Raises:
            KeyError: If key does not exist
        """
        pass

    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]:
        """
        List all keys with optional prefix filter.
        
        Args:
            prefix: Optional prefix to filter keys
            
        Returns:
            List of keys matching the prefix
        """
        pass

    @abstractmethod
    def get_metadata(self, key: str) -> Dict[str, Any]:
        """
        Get metadata for an object.
        
        Args:
            key: Unique identifier for the object
            
        Returns:
            Metadata dictionary
            
        Raises:
            KeyError: If key does not exist
        """
        pass

    def put_file(self, key: str, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store a file with the given key.
        
        Args:
            key: Unique identifier for the object
            file_path: Path to the file to store
            metadata: Optional metadata to associate with the object
        """
        with open(file_path, 'rb') as f:
            self.put(key, f.read(), metadata)

    def get_file(self, key: str, file_path: Path) -> None:
        """
        Retrieve data and save to file.
        
        Args:
            key: Unique identifier for the object
            file_path: Path where to save the retrieved data
        """
        data = self.get(key)
        with open(file_path, 'wb') as f:
            f.write(data)

    def get_stream(self, key: str) -> BinaryIO:
        """
        Get data as a stream.
        
        Args:
            key: Unique identifier for the object
            
        Returns:
            Binary stream of the data
        """
        data = self.get(key)
        return io.BytesIO(data)