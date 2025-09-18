"""
Factory function for creating object store instances.

This module provides a convenient way to create different types of object stores
based on configuration parameters.
"""

from pathlib import Path
from typing import Dict, Any, Union

from .base import ObjectStore
from .filesystem import FileSystemStore
from .archive import ArchiveStore
from .s3 import S3Store


def create_store(store_type: str, **kwargs) -> ObjectStore:
    """
    Create an object store instance based on type and configuration.
    
    Args:
        store_type: Type of store ('filesystem', 'archive', 's3')
        **kwargs: Configuration parameters specific to each store type
    
    Returns:
        Configured ObjectStore instance
    
    Raises:
        ValueError: If store_type is not supported
        
    Examples:
        # Create filesystem store
        store = create_store('filesystem', base_path='/path/to/storage')
        
        # Create archive store
        store = create_store('archive', archive_path='/path/to/archive.tar.gz', 
                           archive_type='tar.gz')
        
        # Create S3 store
        store = create_store('s3', bucket_name='my-bucket', region_name='us-west-2')
    """
    store_type = store_type.lower()
    
    if store_type == 'filesystem':
        return _create_filesystem_store(**kwargs)
    elif store_type == 'archive':
        return _create_archive_store(**kwargs)
    elif store_type == 's3':
        return _create_s3_store(**kwargs)
    else:
        raise ValueError(f"Unsupported store type: {store_type}")


def _create_filesystem_store(**kwargs) -> FileSystemStore:
    """Create a filesystem store."""
    base_path = kwargs.get('base_path')
    if not base_path:
        raise ValueError("base_path is required for filesystem store")
    
    return FileSystemStore(base_path=Path(base_path))


def _create_archive_store(**kwargs) -> ArchiveStore:
    """Create an archive store."""
    archive_path = kwargs.get('archive_path')
    if not archive_path:
        raise ValueError("archive_path is required for archive store")
    
    archive_type = kwargs.get('archive_type', 'tar')
    
    return ArchiveStore(
        archive_path=Path(archive_path),
        archive_type=archive_type
    )


def _create_s3_store(**kwargs) -> S3Store:
    """Create an S3 store."""
    bucket_name = kwargs.get('bucket_name')
    if not bucket_name:
        raise ValueError("bucket_name is required for S3 store")
    
    return S3Store(
        bucket_name=bucket_name,
        aws_access_key_id=kwargs.get('aws_access_key_id'),
        aws_secret_access_key=kwargs.get('aws_secret_access_key'),
        region_name=kwargs.get('region_name', 'us-east-1'),
        endpoint_url=kwargs.get('endpoint_url')
    )


def create_store_from_config(config: Dict[str, Any]) -> ObjectStore:
    """
    Create an object store from a configuration dictionary.
    
    Args:
        config: Configuration dictionary with 'type' key and other parameters
        
    Returns:
        Configured ObjectStore instance
        
    Example:
        config = {
            'type': 'filesystem',
            'base_path': '/path/to/storage'
        }
        store = create_store_from_config(config)
    """
    store_type = config.get('type')
    if not store_type:
        raise ValueError("Configuration must include 'type' key")
    
    # Extract all other parameters
    params = {k: v for k, v in config.items() if k != 'type'}
    
    return create_store(store_type, **params)