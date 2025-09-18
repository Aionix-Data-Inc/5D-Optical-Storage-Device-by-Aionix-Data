"""
FileSystemStore implementation for local file system storage.

This implementation stores objects as files in a local directory structure,
with metadata stored in accompanying .meta files.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import ObjectStore


class FileSystemStore(ObjectStore):
    """Object store implementation using local filesystem."""
    
    def __init__(self, base_path: Path):
        """
        Initialize filesystem store.
        
        Args:
            base_path: Base directory for storing objects
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_object_path(self, key: str) -> Path:
        """Get the file path for an object key."""
        # Sanitize key to create a safe file path
        safe_key = key.replace('/', '_').replace('\\', '_').replace('..', '_')
        return self.base_path / safe_key
    
    def _get_metadata_path(self, key: str) -> Path:
        """Get the metadata file path for an object key."""
        return self._get_object_path(key).with_suffix('.meta')
    
    def put(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store data with the given key."""
        object_path = self._get_object_path(key)
        metadata_path = self._get_metadata_path(key)
        
        # Write object data
        with open(object_path, 'wb') as f:
            f.write(data)
        
        # Write metadata
        meta_data = metadata or {}
        meta_data.update({
            'size': len(data),
            'key': key
        })
        
        with open(metadata_path, 'w') as f:
            json.dump(meta_data, f, indent=2)
    
    def get(self, key: str) -> bytes:
        """Retrieve data by key."""
        object_path = self._get_object_path(key)
        
        if not object_path.exists():
            raise KeyError(f"Object with key '{key}' not found")
        
        with open(object_path, 'rb') as f:
            return f.read()
    
    def exists(self, key: str) -> bool:
        """Check if an object exists."""
        return self._get_object_path(key).exists()
    
    def delete(self, key: str) -> None:
        """Delete an object."""
        object_path = self._get_object_path(key)
        metadata_path = self._get_metadata_path(key)
        
        if not object_path.exists():
            raise KeyError(f"Object with key '{key}' not found")
        
        object_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with optional prefix filter."""
        keys = []
        
        for file_path in self.base_path.iterdir():
            if file_path.is_file() and not file_path.name.endswith('.meta'):
                # Convert file name back to key
                key = file_path.name
                if key.startswith(prefix):
                    keys.append(key)
        
        return sorted(keys)
    
    def get_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata for an object."""
        metadata_path = self._get_metadata_path(key)
        
        if not self.exists(key):
            raise KeyError(f"Object with key '{key}' not found")
        
        if not metadata_path.exists():
            # Return minimal metadata if no metadata file exists
            object_path = self._get_object_path(key)
            return {
                'size': object_path.stat().st_size,
                'key': key
            }
        
        with open(metadata_path, 'r') as f:
            return json.load(f)