"""
Aionix 5D Optical Storage - Object Store Abstraction

This package provides a unified interface for different storage backends
including local filesystem, archive formats (tar/zip), and S3-compatible storage.
"""

from .base import ObjectStore
from .filesystem import FileSystemStore
from .archive import ArchiveStore
from .s3 import S3Store
from .factory import create_store, create_store_from_config

__version__ = "1.0.0"
__all__ = [
    "ObjectStore",
    "FileSystemStore", 
    "ArchiveStore",
    "S3Store",
    "create_store",
    "create_store_from_config"
]