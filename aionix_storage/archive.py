"""
ArchiveStore implementation for tar and zip archive storage.

This implementation stores objects within tar or zip archives,
providing a way to bundle multiple objects into archive files.
"""

import json
import tarfile
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import io

from .base import ObjectStore


class ArchiveStore(ObjectStore):
    """Object store implementation using tar or zip archives."""
    
    def __init__(self, archive_path: Path, archive_type: str = "tar"):
        """
        Initialize archive store.
        
        Args:
            archive_path: Path to the archive file
            archive_type: Type of archive ('tar', 'tar.gz', 'tar.bz2', 'zip')
        """
        self.archive_path = Path(archive_path)
        self.archive_type = archive_type.lower()
        self._objects = {}  # In-memory cache of objects
        self._metadata = {}  # In-memory cache of metadata
        
        # Validate archive type
        if self.archive_type not in ['tar', 'tar.gz', 'tar.bz2', 'zip']:
            raise ValueError(f"Unsupported archive type: {archive_type}")
        
        # Load existing archive if it exists
        if self.archive_path.exists():
            self._load_archive()
    
    def _load_archive(self) -> None:
        """Load objects from existing archive."""
        if self.archive_type == 'zip':
            self._load_zip_archive()
        else:
            self._load_tar_archive()
    
    def _load_zip_archive(self) -> None:
        """Load objects from zip archive."""
        with zipfile.ZipFile(self.archive_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.meta'):
                    # Load metadata
                    key = name[:-5]  # Remove .meta extension
                    with zf.open(name) as f:
                        self._metadata[key] = json.load(f)
                else:
                    # Load object data
                    with zf.open(name) as f:
                        self._objects[name] = f.read()
    
    def _load_tar_archive(self) -> None:
        """Load objects from tar archive."""
        mode = 'r'
        if self.archive_type == 'tar.gz':
            mode = 'r:gz'
        elif self.archive_type == 'tar.bz2':
            mode = 'r:bz2'
        
        with tarfile.open(self.archive_path, mode) as tf:
            for member in tf.getmembers():
                if member.isfile():
                    if member.name.endswith('.meta'):
                        # Load metadata
                        key = member.name[:-5]  # Remove .meta extension
                        f = tf.extractfile(member)
                        if f:
                            self._metadata[key] = json.load(f)
                    else:
                        # Load object data
                        f = tf.extractfile(member)
                        if f:
                            self._objects[member.name] = f.read()
    
    def _save_archive(self) -> None:
        """Save all objects to archive."""
        if self.archive_type == 'zip':
            self._save_zip_archive()
        else:
            self._save_tar_archive()
    
    def _save_zip_archive(self) -> None:
        """Save objects to zip archive."""
        with zipfile.ZipFile(self.archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Save objects
            for key, data in self._objects.items():
                zf.writestr(key, data)
            
            # Save metadata
            for key, metadata in self._metadata.items():
                metadata_str = json.dumps(metadata, indent=2)
                zf.writestr(f"{key}.meta", metadata_str)
    
    def _save_tar_archive(self) -> None:
        """Save objects to tar archive."""
        mode = 'w'
        if self.archive_type == 'tar.gz':
            mode = 'w:gz'
        elif self.archive_type == 'tar.bz2':
            mode = 'w:bz2'
        
        with tarfile.open(self.archive_path, mode) as tf:
            # Save objects
            for key, data in self._objects.items():
                tarinfo = tarfile.TarInfo(name=key)
                tarinfo.size = len(data)
                tf.addfile(tarinfo, io.BytesIO(data))
            
            # Save metadata
            for key, metadata in self._metadata.items():
                metadata_str = json.dumps(metadata, indent=2)
                metadata_bytes = metadata_str.encode('utf-8')
                tarinfo = tarfile.TarInfo(name=f"{key}.meta")
                tarinfo.size = len(metadata_bytes)
                tf.addfile(tarinfo, io.BytesIO(metadata_bytes))
    
    def put(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store data with the given key."""
        self._objects[key] = data
        
        meta_data = metadata or {}
        meta_data.update({
            'size': len(data),
            'key': key
        })
        self._metadata[key] = meta_data
        
        # Save archive
        self._save_archive()
    
    def get(self, key: str) -> bytes:
        """Retrieve data by key."""
        if key not in self._objects:
            raise KeyError(f"Object with key '{key}' not found")
        
        return self._objects[key]
    
    def exists(self, key: str) -> bool:
        """Check if an object exists."""
        return key in self._objects
    
    def delete(self, key: str) -> None:
        """Delete an object."""
        if key not in self._objects:
            raise KeyError(f"Object with key '{key}' not found")
        
        del self._objects[key]
        if key in self._metadata:
            del self._metadata[key]
        
        # Save archive
        self._save_archive()
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with optional prefix filter."""
        keys = [key for key in self._objects.keys() if key.startswith(prefix)]
        return sorted(keys)
    
    def get_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata for an object."""
        if key not in self._objects:
            raise KeyError(f"Object with key '{key}' not found")
        
        return self._metadata.get(key, {
            'size': len(self._objects[key]),
            'key': key
        })