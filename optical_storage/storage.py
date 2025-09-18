"""
Storage abstraction module for 5D Optical Storage System

Provides object store abstraction for files, tar/zip, and S3-like operations
with pre-encryption staging and content chunking.
"""

import os
import json
import tarfile
import zipfile
import tempfile
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, BinaryIO, Iterator, Tuple
from pathlib import Path
import hashlib
from .security import SecurityManager


class ChunkInfo:
    """Information about a data chunk."""
    
    def __init__(self, chunk_id: str, size: int, hash_sha256: str, hash_sha512: str):
        self.chunk_id = chunk_id
        self.size = size
        self.hash_sha256 = hash_sha256
        self.hash_sha512 = hash_sha512
        self.encrypted_size: Optional[int] = None
        self.nonce: Optional[bytes] = None


class ObjectMetadata:
    """Metadata for a stored object."""
    
    def __init__(self, object_id: str, original_path: str, total_size: int):
        self.object_id = object_id
        self.original_path = original_path
        self.total_size = total_size
        self.chunks: List[ChunkInfo] = []
        self.content_hash_sha256: Optional[str] = None
        self.content_hash_sha512: Optional[str] = None
        self.compression_type: Optional[str] = None
        self.created_at: Optional[str] = None


class ObjectStore(ABC):
    """Abstract base class for object storage backends."""
    
    @abstractmethod
    def put_chunk(self, chunk_id: str, data: bytes) -> None:
        """Store a data chunk."""
        pass
    
    @abstractmethod
    def get_chunk(self, chunk_id: str) -> bytes:
        """Retrieve a data chunk."""
        pass
    
    @abstractmethod
    def delete_chunk(self, chunk_id: str) -> None:
        """Delete a data chunk."""
        pass
    
    @abstractmethod
    def list_chunks(self) -> List[str]:
        """List all stored chunk IDs."""
        pass


class FileSystemObjectStore(ObjectStore):
    """File system-based object store implementation."""
    
    def __init__(self, base_path: str):
        """
        Initialize file system object store.
        
        Args:
            base_path: Base directory for storing chunks
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def put_chunk(self, chunk_id: str, data: bytes) -> None:
        """Store a data chunk in the file system."""
        chunk_path = self.base_path / f"{chunk_id}.chunk"
        with open(chunk_path, 'wb') as f:
            f.write(data)
    
    def get_chunk(self, chunk_id: str) -> bytes:
        """Retrieve a data chunk from the file system."""
        chunk_path = self.base_path / f"{chunk_id}.chunk"
        with open(chunk_path, 'rb') as f:
            return f.read()
    
    def delete_chunk(self, chunk_id: str) -> None:
        """Delete a data chunk from the file system."""
        chunk_path = self.base_path / f"{chunk_id}.chunk"
        if chunk_path.exists():
            chunk_path.unlink()
    
    def list_chunks(self) -> List[str]:
        """List all stored chunk IDs."""
        return [f.stem for f in self.base_path.glob("*.chunk")]


class S3ObjectStore(ObjectStore):
    """S3-compatible object store implementation."""
    
    def __init__(self, bucket_name: str, prefix: str = "chunks/"):
        """
        Initialize S3 object store.
        
        Args:
            bucket_name: S3 bucket name
            prefix: Key prefix for chunks
        """
        self.bucket_name = bucket_name
        self.prefix = prefix
        # Note: In a real implementation, you would initialize boto3 client here
        self._s3_client = None  # Placeholder for boto3.client('s3')
    
    def put_chunk(self, chunk_id: str, data: bytes) -> None:
        """Store a data chunk in S3."""
        key = f"{self.prefix}{chunk_id}.chunk"
        # Placeholder for S3 operations
        # self._s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=data)
        raise NotImplementedError("S3 integration requires boto3 configuration")
    
    def get_chunk(self, chunk_id: str) -> bytes:
        """Retrieve a data chunk from S3."""
        key = f"{self.prefix}{chunk_id}.chunk"
        # Placeholder for S3 operations
        # response = self._s3_client.get_object(Bucket=self.bucket_name, Key=key)
        # return response['Body'].read()
        raise NotImplementedError("S3 integration requires boto3 configuration")
    
    def delete_chunk(self, chunk_id: str) -> None:
        """Delete a data chunk from S3."""
        key = f"{self.prefix}{chunk_id}.chunk"
        # self._s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        raise NotImplementedError("S3 integration requires boto3 configuration")
    
    def list_chunks(self) -> List[str]:
        """List all stored chunk IDs."""
        # response = self._s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=self.prefix)
        # return [obj['Key'].replace(self.prefix, '').replace('.chunk', '') 
        #         for obj in response.get('Contents', [])]
        raise NotImplementedError("S3 integration requires boto3 configuration")


class DataIngestionEngine:
    """Handles data ingestion, chunking, and staging for encryption."""
    
    def __init__(self, security_manager: SecurityManager, object_store: ObjectStore, 
                 chunk_size: int = 4 * 1024 * 1024):  # 4MB default
        """
        Initialize data ingestion engine.
        
        Args:
            security_manager: Security manager for encryption/hashing
            object_store: Object store backend
            chunk_size: Size of data chunks (1-8 MB range)
        """
        if not (1024 * 1024 <= chunk_size <= 8 * 1024 * 1024):
            raise ValueError("Chunk size must be between 1MB and 8MB")
            
        self.security_manager = security_manager
        self.object_store = object_store
        self.chunk_size = chunk_size
        self._dedup_hashes: Dict[str, Tuple[str, bytes]] = {}  # hash -> (chunk_id, nonce) mapping
    
    def ingest_file(self, file_path: str, enable_dedup: bool = True) -> ObjectMetadata:
        """
        Ingest a single file with chunking and optional deduplication.
        
        Args:
            file_path: Path to the file to ingest
            enable_dedup: Enable content-based deduplication
            
        Returns:
            Object metadata with chunk information
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        object_id = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
        metadata = ObjectMetadata(object_id, str(file_path), file_path.stat().st_size)
        
        # Calculate file-level hashes
        with open(file_path, 'rb') as f:
            file_content = f.read()
            metadata.content_hash_sha256 = self.security_manager.hash_content(file_content, 'sha256')
            metadata.content_hash_sha512 = self.security_manager.hash_content(file_content, 'sha512')
        
        # Process file in chunks
        with open(file_path, 'rb') as f:
            chunk_index = 0
            while True:
                chunk_data = f.read(self.chunk_size)
                if not chunk_data:
                    break
                
                chunk_info = self._process_chunk(chunk_data, f"{object_id}_{chunk_index}", enable_dedup)
                metadata.chunks.append(chunk_info)
                chunk_index += 1
        
        return metadata
    
    def ingest_archive(self, archive_path: str, archive_type: str = 'auto', 
                      enable_dedup: bool = True) -> ObjectMetadata:
        """
        Ingest a tar or zip archive.
        
        Args:
            archive_path: Path to the archive file
            archive_type: Archive type ('tar', 'zip', or 'auto')
            enable_dedup: Enable content-based deduplication
            
        Returns:
            Object metadata with chunk information
        """
        archive_path = Path(archive_path)
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")
        
        if archive_type == 'auto':
            if archive_path.suffix.lower() in ['.tar', '.tar.gz', '.tar.bz2', '.tar.xz']:
                archive_type = 'tar'
            elif archive_path.suffix.lower() == '.zip':
                archive_type = 'zip'
            else:
                raise ValueError(f"Cannot auto-detect archive type for: {archive_path}")
        
        object_id = hashlib.sha256(str(archive_path).encode()).hexdigest()[:16]
        metadata = ObjectMetadata(object_id, str(archive_path), archive_path.stat().st_size)
        metadata.compression_type = archive_type
        
        # Read entire archive for processing
        with open(archive_path, 'rb') as f:
            archive_content = f.read()
            metadata.content_hash_sha256 = self.security_manager.hash_content(archive_content, 'sha256')
            metadata.content_hash_sha512 = self.security_manager.hash_content(archive_content, 'sha512')
        
        # Process archive in chunks
        chunk_index = 0
        for i in range(0, len(archive_content), self.chunk_size):
            chunk_data = archive_content[i:i + self.chunk_size]
            chunk_info = self._process_chunk(chunk_data, f"{object_id}_{chunk_index}", enable_dedup)
            metadata.chunks.append(chunk_info)
            chunk_index += 1
        
        return metadata
    
    def _process_chunk(self, chunk_data: bytes, chunk_id: str, enable_dedup: bool) -> ChunkInfo:
        """Process a single data chunk with optional deduplication."""
        # Calculate chunk hashes
        hash_sha256 = self.security_manager.hash_content(chunk_data, 'sha256')
        hash_sha512 = self.security_manager.hash_content(chunk_data, 'sha512')
        
        chunk_info = ChunkInfo(chunk_id, len(chunk_data), hash_sha256, hash_sha512)
        
        # Check for deduplication
        if enable_dedup and hash_sha256 in self._dedup_hashes:
            # Use existing chunk with stored nonce
            existing_chunk_id, existing_nonce = self._dedup_hashes[hash_sha256]
            chunk_info.chunk_id = existing_chunk_id
            chunk_info.nonce = existing_nonce
            # Set encrypted size (we would need to store this too for full dedup)
            encrypted_data, _ = self.security_manager.encrypt_chunk(chunk_data, existing_chunk_id)
            chunk_info.encrypted_size = len(encrypted_data)
            return chunk_info
        
        # Encrypt and store chunk
        encrypted_data, nonce = self.security_manager.encrypt_chunk(chunk_data, chunk_id)
        chunk_info.encrypted_size = len(encrypted_data)
        chunk_info.nonce = nonce
        
        # Store encrypted chunk
        self.object_store.put_chunk(chunk_id, encrypted_data)
        
        # Update deduplication map
        if enable_dedup:
            self._dedup_hashes[hash_sha256] = (chunk_id, nonce)
        
        return chunk_info
    
    def retrieve_object(self, metadata: ObjectMetadata) -> bytes:
        """
        Retrieve and decrypt an object from its metadata.
        
        Args:
            metadata: Object metadata with chunk information
            
        Returns:
            Decrypted object data
        """
        chunks = []
        for chunk_info in metadata.chunks:
            # Retrieve encrypted chunk
            encrypted_data = self.object_store.get_chunk(chunk_info.chunk_id)
            
            # Decrypt chunk
            decrypted_data = self.security_manager.decrypt_chunk(
                encrypted_data, chunk_info.nonce, chunk_info.chunk_id
            )
            
            # Verify chunk integrity
            chunk_hash = self.security_manager.hash_content(decrypted_data, 'sha256')
            if chunk_hash != chunk_info.hash_sha256:
                raise ValueError(f"Chunk integrity check failed for {chunk_info.chunk_id}")
            
            chunks.append(decrypted_data)
        
        # Combine chunks
        full_data = b''.join(chunks)
        
        # Verify full object integrity
        if metadata.content_hash_sha256:
            full_hash = self.security_manager.hash_content(full_data, 'sha256')
            if full_hash != metadata.content_hash_sha256:
                raise ValueError("Object integrity check failed")
        
        return full_data