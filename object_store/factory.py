"""
Factory functions for creating storage backends.
"""

from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .base import StorageBackend
from .filesystem import FileSystemStorage
from .archive import ArchiveStorage
from .s3 import S3Storage, MockS3Storage


def create_storage(storage_url: str, **kwargs) -> StorageBackend:
    """
    Create a storage backend from a URL.
    
    Supported URL formats:
    - file:///path/to/directory (FileSystemStorage)
    - tar:///path/to/archive.tar (ArchiveStorage)
    - zip:///path/to/archive.zip (ArchiveStorage)
    - s3://bucket-name (S3Storage)
    - mock-s3://bucket-name (MockS3Storage for testing)
    
    Args:
        storage_url: Storage URL
        **kwargs: Additional arguments passed to the storage backend
        
    Returns:
        StorageBackend: Configured storage backend
        
    Examples:
        >>> storage = create_storage("file:///tmp/storage")
        >>> storage = create_storage("s3://my-bucket", access_key="...", secret_key="...")
        >>> storage = create_storage("tar:///data/archive.tar")
    """
    parsed = urlparse(storage_url)
    scheme = parsed.scheme.lower()
    
    if scheme == "file":
        path = parsed.path
        return FileSystemStorage(path, **kwargs)
    
    elif scheme in ["tar", "zip"]:
        path = parsed.path
        return ArchiveStorage(path, archive_type=scheme, **kwargs)
    
    elif scheme == "s3":
        bucket_name = parsed.netloc
        if not bucket_name:
            raise ValueError("S3 URL must include bucket name: s3://bucket-name")
        return S3Storage(bucket_name, **kwargs)
    
    elif scheme == "mock-s3":
        bucket_name = parsed.netloc
        if not bucket_name:
            raise ValueError("Mock S3 URL must include bucket name: mock-s3://bucket-name")
        return MockS3Storage(bucket_name, **kwargs)
    
    else:
        raise ValueError(f"Unsupported storage scheme: {scheme}")


def create_filesystem_storage(path: str) -> FileSystemStorage:
    """Create a file system storage backend."""
    return FileSystemStorage(path)


def create_archive_storage(archive_path: str, archive_type: str = "auto") -> ArchiveStorage:
    """Create an archive storage backend."""
    return ArchiveStorage(archive_path, archive_type)


def create_s3_storage(bucket_name: str, access_key: Optional[str] = None,
                      secret_key: Optional[str] = None, endpoint_url: Optional[str] = None,
                      region: str = "us-east-1") -> S3Storage:
    """Create an S3 storage backend."""
    return S3Storage(bucket_name, access_key, secret_key, endpoint_url, region)


def create_mock_s3_storage(bucket_name: str) -> MockS3Storage:
    """Create a mock S3 storage backend for testing."""
    return MockS3Storage(bucket_name)