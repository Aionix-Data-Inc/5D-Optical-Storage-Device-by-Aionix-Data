"""
5D Optical Storage Object Store Abstraction

This module provides a unified interface for storing and retrieving data
across different storage backends including file systems, archives, and
cloud storage services.
"""

from .base import ObjectStore, StorageBackend
from .filesystem import FileSystemStorage
from .archive import ArchiveStorage
from .s3 import S3Storage
from .factory import create_storage

__version__ = "1.0.0"
__all__ = [
    "ObjectStore",
    "StorageBackend", 
    "FileSystemStorage",
    "ArchiveStorage",
    "S3Storage",
    "create_storage"
]