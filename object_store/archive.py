"""
Archive storage backend implementation for tar/zip files.
"""

import io
import tarfile
import zipfile
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO

from .base import StorageBackend, ObjectMetadata, calculate_etag


class ArchiveStorage(StorageBackend):
    """Archive storage backend for tar and zip files."""
    
    def __init__(self, archive_path: str, archive_type: str = "auto"):
        """
        Initialize archive storage.
        
        Args:
            archive_path: Path to the archive file
            archive_type: Type of archive ('tar', 'zip', or 'auto' for auto-detection)
        """
        self.archive_path = Path(archive_path)
        
        # Auto-detect archive type
        if archive_type == "auto":
            if self.archive_path.suffix.lower() in ['.tar', '.tar.gz', '.tar.bz2', '.tar.xz']:
                self.archive_type = "tar"
            elif self.archive_path.suffix.lower() in ['.zip']:
                self.archive_type = "zip"
            else:
                raise ValueError(f"Cannot auto-detect archive type for {archive_path}")
        else:
            self.archive_type = archive_type
        
        self._metadata_cache = {}
        self._load_archive_index()
    
    def _load_archive_index(self) -> None:
        """Load the archive index to memory for fast access."""
        if not self.archive_path.exists():
            return
        
        try:
            if self.archive_type == "tar":
                with tarfile.open(self.archive_path, 'r') as tar:
                    for member in tar.getmembers():
                        if member.isfile():
                            self._metadata_cache[member.name] = ObjectMetadata(
                                key=member.name,
                                size=member.size,
                                last_modified=datetime.fromtimestamp(member.mtime),
                                etag="",  # Will be calculated when needed
                            )
            elif self.archive_type == "zip":
                with zipfile.ZipFile(self.archive_path, 'r') as zf:
                    for info in zf.infolist():
                        if not info.is_dir():
                            # Convert zip date_time to datetime
                            dt = datetime(*info.date_time)
                            self._metadata_cache[info.filename] = ObjectMetadata(
                                key=info.filename,
                                size=info.file_size,
                                last_modified=dt,
                                etag="",  # Will be calculated when needed
                            )
        except (tarfile.TarError, zipfile.BadZipFile):
            # Archive doesn't exist or is corrupted, start fresh
            self._metadata_cache = {}
    
    def _write_archive(self, updates: Dict[str, bytes]) -> None:
        """Write updates to the archive."""
        # For archives, we need to rewrite the entire archive with updates
        # This is a limitation of the tar/zip formats
        
        # Read existing data
        existing_data = {}
        if self.archive_path.exists():
            try:
                if self.archive_type == "tar":
                    with tarfile.open(self.archive_path, 'r') as tar:
                        for member in tar.getmembers():
                            if member.isfile():
                                f = tar.extractfile(member)
                                if f:
                                    existing_data[member.name] = f.read()
                elif self.archive_type == "zip":
                    with zipfile.ZipFile(self.archive_path, 'r') as zf:
                        for name in zf.namelist():
                            if not name.endswith('/'):
                                existing_data[name] = zf.read(name)
            except (tarfile.TarError, zipfile.BadZipFile):
                # Corrupted archive, start fresh
                existing_data = {}
        
        # Merge updates
        existing_data.update(updates)
        
        # Create parent directory if needed
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write new archive
        if self.archive_type == "tar":
            with tarfile.open(self.archive_path, 'w') as tar:
                for name, data in existing_data.items():
                    tarinfo = tarfile.TarInfo(name=name)
                    tarinfo.size = len(data)
                    tarinfo.mtime = int(datetime.now().timestamp())
                    tar.addfile(tarinfo, io.BytesIO(data))
        elif self.archive_type == "zip":
            with zipfile.ZipFile(self.archive_path, 'w') as zf:
                for name, data in existing_data.items():
                    zf.writestr(name, data)
        
        # Reload index
        self._load_archive_index()
    
    def put_object(self, key: str, data: Union[bytes, BinaryIO], 
                   metadata: Optional[Dict[str, str]] = None) -> ObjectMetadata:
        """Store an object in the archive."""
        # Handle both bytes and file-like objects
        if hasattr(data, 'read'):
            content = data.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
        else:
            content = data
        
        # Write to archive
        self._write_archive({key: content})
        
        # Create metadata
        obj_metadata = ObjectMetadata(
            key=key,
            size=len(content),
            last_modified=datetime.now(),
            etag=calculate_etag(content),
            content_type=metadata.get('content-type') if metadata else None,
            custom_metadata=metadata
        )
        
        # Update cache
        self._metadata_cache[key] = obj_metadata
        
        return obj_metadata
    
    def get_object(self, key: str) -> bytes:
        """Retrieve an object from the archive."""
        if not self.archive_path.exists():
            raise FileNotFoundError(f"Archive '{self.archive_path}' not found")
        
        try:
            if self.archive_type == "tar":
                with tarfile.open(self.archive_path, 'r') as tar:
                    member = tar.getmember(key)
                    f = tar.extractfile(member)
                    if f:
                        return f.read()
                    else:
                        raise FileNotFoundError(f"Object '{key}' not found in archive")
            elif self.archive_type == "zip":
                with zipfile.ZipFile(self.archive_path, 'r') as zf:
                    return zf.read(key)
        except (KeyError, tarfile.TarError, zipfile.BadZipFile):
            raise FileNotFoundError(f"Object '{key}' not found in archive")
    
    def delete_object(self, key: str) -> bool:
        """Delete an object from the archive."""
        if key not in self._metadata_cache:
            return False
        
        # Read all data except the key to delete
        existing_data = {}
        if self.archive_path.exists():
            try:
                if self.archive_type == "tar":
                    with tarfile.open(self.archive_path, 'r') as tar:
                        for member in tar.getmembers():
                            if member.isfile() and member.name != key:
                                f = tar.extractfile(member)
                                if f:
                                    existing_data[member.name] = f.read()
                elif self.archive_type == "zip":
                    with zipfile.ZipFile(self.archive_path, 'r') as zf:
                        for name in zf.namelist():
                            if not name.endswith('/') and name != key:
                                existing_data[name] = zf.read(name)
            except (tarfile.TarError, zipfile.BadZipFile):
                return False
        
        # Rewrite archive without the deleted key
        if self.archive_type == "tar":
            with tarfile.open(self.archive_path, 'w') as tar:
                for name, data in existing_data.items():
                    tarinfo = tarfile.TarInfo(name=name)
                    tarinfo.size = len(data)
                    tarinfo.mtime = int(datetime.now().timestamp())
                    tar.addfile(tarinfo, io.BytesIO(data))
        elif self.archive_type == "zip":
            with zipfile.ZipFile(self.archive_path, 'w') as zf:
                for name, data in existing_data.items():
                    zf.writestr(name, data)
        
        # Remove from cache and reload
        del self._metadata_cache[key]
        self._load_archive_index()
        
        return True
    
    def list_objects(self, prefix: str = "", limit: Optional[int] = None) -> List[ObjectMetadata]:
        """List objects with optional prefix filter."""
        objects = []
        
        for key, metadata in self._metadata_cache.items():
            if prefix and not key.startswith(prefix):
                continue
            
            # Calculate ETag if not already done
            if not metadata.etag:
                try:
                    data = self.get_object(key)
                    metadata.etag = calculate_etag(data)
                except FileNotFoundError:
                    continue
            
            objects.append(metadata)
            
            if limit and len(objects) >= limit:
                break
        
        return objects
    
    def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        return key in self._metadata_cache
    
    def get_object_metadata(self, key: str) -> ObjectMetadata:
        """Get object metadata."""
        if key not in self._metadata_cache:
            raise FileNotFoundError(f"Object '{key}' not found")
        
        metadata = self._metadata_cache[key]
        
        # Calculate ETag if not already done
        if not metadata.etag:
            try:
                data = self.get_object(key)
                metadata.etag = calculate_etag(data)
            except FileNotFoundError:
                raise FileNotFoundError(f"Object '{key}' not found")
        
        return metadata