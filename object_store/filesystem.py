"""
File system storage backend implementation.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO

from .base import StorageBackend, ObjectMetadata, calculate_etag


class FileSystemStorage(StorageBackend):
    """File system storage backend."""
    
    def __init__(self, base_path: str):
        """
        Initialize file system storage.
        
        Args:
            base_path: Base directory path for storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.metadata_dir = self.base_path / ".metadata"
        self.metadata_dir.mkdir(exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a key."""
        # Ensure key doesn't contain path traversal
        safe_key = key.replace("..", "").strip("/")
        return self.base_path / safe_key
    
    def _get_metadata_path(self, key: str) -> Path:
        """Get the metadata file path for a key."""
        safe_key = key.replace("..", "").strip("/").replace("/", "_")
        return self.metadata_dir / f"{safe_key}.json"
    
    def _save_metadata(self, key: str, metadata: ObjectMetadata) -> None:
        """Save metadata to file."""
        meta_path = self._get_metadata_path(key)
        meta_data = {
            'key': metadata.key,
            'size': metadata.size,
            'last_modified': metadata.last_modified.isoformat(),
            'etag': metadata.etag,
            'content_type': metadata.content_type,
            'custom_metadata': metadata.custom_metadata
        }
        with open(meta_path, 'w') as f:
            json.dump(meta_data, f, indent=2)
    
    def _load_metadata(self, key: str) -> Optional[ObjectMetadata]:
        """Load metadata from file."""
        meta_path = self._get_metadata_path(key)
        if not meta_path.exists():
            return None
            
        try:
            with open(meta_path, 'r') as f:
                meta_data = json.load(f)
            
            return ObjectMetadata(
                key=meta_data['key'],
                size=meta_data['size'],
                last_modified=datetime.fromisoformat(meta_data['last_modified']),
                etag=meta_data['etag'],
                content_type=meta_data.get('content_type'),
                custom_metadata=meta_data.get('custom_metadata')
            )
        except (json.JSONDecodeError, KeyError):
            return None
    
    def put_object(self, key: str, data: Union[bytes, BinaryIO], 
                   metadata: Optional[Dict[str, str]] = None) -> ObjectMetadata:
        """Store an object in the file system."""
        file_path = self._get_file_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle both bytes and file-like objects
        if hasattr(data, 'read'):
            # File-like object
            content = data.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
        else:
            content = data
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Create metadata
        stat = file_path.stat()
        obj_metadata = ObjectMetadata(
            key=key,
            size=len(content),
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            etag=calculate_etag(content),
            content_type=metadata.get('content-type') if metadata else None,
            custom_metadata=metadata
        )
        
        # Save metadata
        self._save_metadata(key, obj_metadata)
        
        return obj_metadata
    
    def get_object(self, key: str) -> bytes:
        """Retrieve an object from the file system."""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Object '{key}' not found")
        
        with open(file_path, 'rb') as f:
            return f.read()
    
    def delete_object(self, key: str) -> bool:
        """Delete an object from the file system."""
        file_path = self._get_file_path(key)
        meta_path = self._get_metadata_path(key)
        
        deleted = False
        
        if file_path.exists():
            file_path.unlink()
            deleted = True
        
        if meta_path.exists():
            meta_path.unlink()
        
        return deleted
    
    def list_objects(self, prefix: str = "", limit: Optional[int] = None) -> List[ObjectMetadata]:
        """List objects with optional prefix filter."""
        objects = []
        
        # Walk through the base directory
        for root, dirs, files in os.walk(self.base_path):
            # Skip metadata directory
            if '.metadata' in root:
                continue
                
            for file in files:
                file_path = Path(root) / file
                # Get relative path from base_path
                try:
                    relative_path = file_path.relative_to(self.base_path)
                    key = str(relative_path).replace('\\', '/')
                    
                    # Apply prefix filter
                    if prefix and not key.startswith(prefix):
                        continue
                    
                    # Try to load metadata, fallback to file stats
                    metadata = self._load_metadata(key)
                    if metadata is None:
                        stat = file_path.stat()
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        
                        metadata = ObjectMetadata(
                            key=key,
                            size=stat.st_size,
                            last_modified=datetime.fromtimestamp(stat.st_mtime),
                            etag=calculate_etag(content)
                        )
                    
                    objects.append(metadata)
                    
                    # Apply limit
                    if limit and len(objects) >= limit:
                        return objects
                        
                except ValueError:
                    # Skip files outside base_path
                    continue
        
        return objects
    
    def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        file_path = self._get_file_path(key)
        return file_path.exists()
    
    def get_object_metadata(self, key: str) -> ObjectMetadata:
        """Get object metadata."""
        if not self.object_exists(key):
            raise FileNotFoundError(f"Object '{key}' not found")
        
        # Try to load saved metadata first
        metadata = self._load_metadata(key)
        if metadata:
            return metadata
        
        # Fallback to file stats
        file_path = self._get_file_path(key)
        stat = file_path.stat()
        with open(file_path, 'rb') as f:
            content = f.read()
        
        return ObjectMetadata(
            key=key,
            size=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            etag=calculate_etag(content)
        )