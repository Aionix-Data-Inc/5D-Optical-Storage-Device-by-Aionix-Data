"""
Base classes and interfaces for the object store abstraction.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, BinaryIO
from dataclasses import dataclass
from datetime import datetime
import hashlib


@dataclass
class ObjectMetadata:
    """Metadata for stored objects."""
    key: str
    size: int
    last_modified: datetime
    etag: str
    content_type: Optional[str] = None
    custom_metadata: Optional[Dict[str, str]] = None


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def put_object(self, key: str, data: Union[bytes, BinaryIO], 
                   metadata: Optional[Dict[str, str]] = None) -> ObjectMetadata:
        """Store an object."""
        pass
    
    @abstractmethod
    def get_object(self, key: str) -> bytes:
        """Retrieve an object."""
        pass
    
    @abstractmethod
    def delete_object(self, key: str) -> bool:
        """Delete an object."""
        pass
    
    @abstractmethod
    def list_objects(self, prefix: str = "", limit: Optional[int] = None) -> List[ObjectMetadata]:
        """List objects with optional prefix filter."""
        pass
    
    @abstractmethod
    def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        pass
    
    @abstractmethod
    def get_object_metadata(self, key: str) -> ObjectMetadata:
        """Get object metadata."""
        pass


class ObjectStore:
    """Unified object store interface."""
    
    def __init__(self, backend: StorageBackend):
        """Initialize with a storage backend."""
        self.backend = backend
    
    def put(self, key: str, data: Union[bytes, str, BinaryIO], 
            content_type: Optional[str] = None,
            metadata: Optional[Dict[str, str]] = None) -> ObjectMetadata:
        """
        Store data with the given key.
        
        Args:
            key: Unique identifier for the object
            data: Data to store (bytes, string, or file-like object)
            content_type: MIME type of the content
            metadata: Custom metadata dictionary
            
        Returns:
            ObjectMetadata: Metadata of the stored object
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        meta = metadata or {}
        if content_type:
            meta['content-type'] = content_type
            
        return self.backend.put_object(key, data, meta)
    
    def get(self, key: str) -> bytes:
        """
        Retrieve data by key.
        
        Args:
            key: Object identifier
            
        Returns:
            bytes: Object data
        """
        return self.backend.get_object(key)
    
    def get_text(self, key: str, encoding: str = 'utf-8') -> str:
        """
        Retrieve text data by key.
        
        Args:
            key: Object identifier
            encoding: Text encoding
            
        Returns:
            str: Object data as text
        """
        data = self.backend.get_object(key)
        return data.decode(encoding)
    
    def delete(self, key: str) -> bool:
        """
        Delete an object.
        
        Args:
            key: Object identifier
            
        Returns:
            bool: True if deleted successfully
        """
        return self.backend.delete_object(key)
    
    def exists(self, key: str) -> bool:
        """
        Check if an object exists.
        
        Args:
            key: Object identifier
            
        Returns:
            bool: True if object exists
        """
        return self.backend.object_exists(key)
    
    def list(self, prefix: str = "", limit: Optional[int] = None) -> List[ObjectMetadata]:
        """
        List objects with optional prefix filter.
        
        Args:
            prefix: Key prefix to filter by
            limit: Maximum number of objects to return
            
        Returns:
            List[ObjectMetadata]: List of object metadata
        """
        return self.backend.list_objects(prefix, limit)
    
    def get_metadata(self, key: str) -> ObjectMetadata:
        """
        Get object metadata.
        
        Args:
            key: Object identifier
            
        Returns:
            ObjectMetadata: Object metadata
        """
        return self.backend.get_object_metadata(key)


def calculate_etag(data: bytes) -> str:
    """Calculate ETag for data."""
    return hashlib.md5(data).hexdigest()