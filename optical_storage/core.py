"""
Core module for 5D Optical Storage System

Provides the main OpticalStorage class that orchestrates all components
including manifest management and table of contents (TOC) generation.
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
from .security import SecurityManager
from .storage import ObjectStore, DataIngestionEngine, ObjectMetadata


class Manifest:
    """Represents a storage manifest with digital signature."""
    
    def __init__(self, manifest_id: str, version: str = "1.0"):
        self.manifest_id = manifest_id
        self.version = version
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.objects: Dict[str, ObjectMetadata] = {}
        self.total_objects = 0
        self.total_size = 0
        self.signature: Optional[bytes] = None
        self.public_key: Optional[bytes] = None
    
    def add_object(self, metadata: ObjectMetadata) -> None:
        """Add an object to the manifest."""
        self.objects[metadata.object_id] = metadata
        self.total_objects += 1
        self.total_size += metadata.total_size
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary representation."""
        return {
            'manifest_id': self.manifest_id,
            'version': self.version,
            'created_at': self.created_at,
            'total_objects': self.total_objects,
            'total_size': self.total_size,
            'objects': {
                obj_id: {
                    'object_id': obj.object_id,
                    'original_path': obj.original_path,
                    'total_size': obj.total_size,
                    'content_hash_sha256': obj.content_hash_sha256,
                    'content_hash_sha512': obj.content_hash_sha512,
                    'compression_type': obj.compression_type,
                    'created_at': obj.created_at,
                    'chunks': [
                        {
                            'chunk_id': chunk.chunk_id,
                            'size': chunk.size,
                            'hash_sha256': chunk.hash_sha256,
                            'hash_sha512': chunk.hash_sha512,
                            'encrypted_size': chunk.encrypted_size,
                            'nonce': chunk.nonce.hex() if chunk.nonce else None
                        }
                        for chunk in obj.chunks
                    ]
                }
                for obj_id, obj in self.objects.items()
            }
        }
    
    def to_json(self) -> str:
        """Convert manifest to JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Manifest':
        """Create manifest from dictionary representation."""
        manifest = cls(data['manifest_id'], data['version'])
        manifest.created_at = data['created_at']
        manifest.total_objects = data['total_objects']
        manifest.total_size = data['total_size']
        
        # Reconstruct objects
        for obj_id, obj_data in data['objects'].items():
            metadata = ObjectMetadata(
                obj_data['object_id'],
                obj_data['original_path'],
                obj_data['total_size']
            )
            metadata.content_hash_sha256 = obj_data['content_hash_sha256']
            metadata.content_hash_sha512 = obj_data['content_hash_sha512']
            metadata.compression_type = obj_data['compression_type']
            metadata.created_at = obj_data['created_at']
            
            # Reconstruct chunks
            from .storage import ChunkInfo
            for chunk_data in obj_data['chunks']:
                chunk_info = ChunkInfo(
                    chunk_data['chunk_id'],
                    chunk_data['size'],
                    chunk_data['hash_sha256'],
                    chunk_data['hash_sha512']
                )
                chunk_info.encrypted_size = chunk_data['encrypted_size']
                chunk_info.nonce = bytes.fromhex(chunk_data['nonce']) if chunk_data['nonce'] else None
                metadata.chunks.append(chunk_info)
            
            manifest.objects[obj_id] = metadata
        
        return manifest


class TableOfContents:
    """Represents a disc's Table of Contents with digital signature."""
    
    def __init__(self, disc_id: str, disc_capacity: int = 1024 * 1024 * 1024 * 1024):  # 1TB default
        self.disc_id = disc_id
        self.disc_capacity = disc_capacity
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.manifests: List[str] = []
        self.used_space = 0
        self.signature: Optional[bytes] = None
        self.public_key: Optional[bytes] = None
    
    def add_manifest(self, manifest_id: str, manifest_size: int) -> bool:
        """
        Add a manifest to the TOC if there's space.
        
        Args:
            manifest_id: Manifest identifier
            manifest_size: Size of the manifest data
            
        Returns:
            True if added successfully, False if insufficient space
        """
        if self.used_space + manifest_size > self.disc_capacity:
            return False
        
        self.manifests.append(manifest_id)
        self.used_space += manifest_size
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TOC to dictionary representation."""
        return {
            'disc_id': self.disc_id,
            'disc_capacity': self.disc_capacity,
            'created_at': self.created_at,
            'manifests': self.manifests,
            'used_space': self.used_space,
            'available_space': self.disc_capacity - self.used_space
        }
    
    def to_json(self) -> str:
        """Convert TOC to JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


class OpticalStorage:
    """Main 5D Optical Storage System class."""
    
    def __init__(self, security_manager: SecurityManager, object_store: ObjectStore,
                 chunk_size: int = 4 * 1024 * 1024):
        """
        Initialize the optical storage system.
        
        Args:
            security_manager: Security manager for encryption/signatures
            object_store: Object store backend
            chunk_size: Data chunk size in bytes (1-8 MB)
        """
        self.security_manager = security_manager
        self.object_store = object_store
        self.ingestion_engine = DataIngestionEngine(
            security_manager, object_store, chunk_size
        )
        self.manifests: Dict[str, Manifest] = {}
        self.table_of_contents: Dict[str, TableOfContents] = {}
    
    def store_file(self, file_path: str, manifest_id: Optional[str] = None,
                   enable_dedup: bool = True) -> str:
        """
        Store a single file in the optical storage system.
        
        Args:
            file_path: Path to the file to store
            manifest_id: Optional manifest ID (creates new if not provided)
            enable_dedup: Enable content deduplication
            
        Returns:
            Object ID of the stored file
        """
        # Ingest the file
        metadata = self.ingestion_engine.ingest_file(file_path, enable_dedup)
        metadata.created_at = datetime.now(timezone.utc).isoformat()
        
        # Get or create manifest
        if manifest_id is None:
            manifest_id = f"manifest_{int(time.time())}"
        
        if manifest_id not in self.manifests:
            self.manifests[manifest_id] = Manifest(manifest_id)
        
        # Add to manifest
        self.manifests[manifest_id].add_object(metadata)
        
        # Sign the manifest
        self._sign_manifest(manifest_id)
        
        return metadata.object_id
    
    def store_archive(self, archive_path: str, archive_type: str = 'auto',
                     manifest_id: Optional[str] = None, enable_dedup: bool = True) -> str:
        """
        Store an archive file in the optical storage system.
        
        Args:
            archive_path: Path to the archive file
            archive_type: Archive type ('tar', 'zip', or 'auto')
            manifest_id: Optional manifest ID (creates new if not provided)
            enable_dedup: Enable content deduplication
            
        Returns:
            Object ID of the stored archive
        """
        # Ingest the archive
        metadata = self.ingestion_engine.ingest_archive(archive_path, archive_type, enable_dedup)
        metadata.created_at = datetime.now(timezone.utc).isoformat()
        
        # Get or create manifest
        if manifest_id is None:
            manifest_id = f"manifest_{int(time.time())}"
        
        if manifest_id not in self.manifests:
            self.manifests[manifest_id] = Manifest(manifest_id)
        
        # Add to manifest
        self.manifests[manifest_id].add_object(metadata)
        
        # Sign the manifest
        self._sign_manifest(manifest_id)
        
        return metadata.object_id
    
    def retrieve_object(self, object_id: str, manifest_id: str) -> bytes:
        """
        Retrieve and decrypt an object from storage.
        
        Args:
            object_id: Object identifier
            manifest_id: Manifest containing the object
            
        Returns:
            Decrypted object data
        """
        if manifest_id not in self.manifests:
            raise ValueError(f"Manifest not found: {manifest_id}")
        
        manifest = self.manifests[manifest_id]
        if object_id not in manifest.objects:
            raise ValueError(f"Object not found: {object_id}")
        
        # Verify manifest signature before retrieval
        if not self._verify_manifest_signature(manifest_id):
            raise ValueError(f"Manifest signature verification failed: {manifest_id}")
        
        metadata = manifest.objects[object_id]
        return self.ingestion_engine.retrieve_object(metadata)
    
    def create_disc_toc(self, disc_id: str, manifest_ids: List[str],
                       disc_capacity: int = 1024 * 1024 * 1024 * 1024) -> TableOfContents:
        """
        Create a Table of Contents for a disc.
        
        Args:
            disc_id: Unique disc identifier
            manifest_ids: List of manifest IDs to include
            disc_capacity: Disc capacity in bytes
            
        Returns:
            Table of Contents object
        """
        toc = TableOfContents(disc_id, disc_capacity)
        
        for manifest_id in manifest_ids:
            if manifest_id not in self.manifests:
                raise ValueError(f"Manifest not found: {manifest_id}")
            
            manifest = self.manifests[manifest_id]
            manifest_size = manifest.total_size
            
            if not toc.add_manifest(manifest_id, manifest_size):
                raise ValueError(f"Insufficient disc capacity for manifest: {manifest_id}")
        
        # Sign the TOC
        self._sign_toc(disc_id, toc)
        
        self.table_of_contents[disc_id] = toc
        return toc
    
    def export_manifest(self, manifest_id: str, output_path: str) -> None:
        """Export a signed manifest to a file."""
        if manifest_id not in self.manifests:
            raise ValueError(f"Manifest not found: {manifest_id}")
        
        manifest = self.manifests[manifest_id]
        with open(output_path, 'w') as f:
            f.write(manifest.to_json())
    
    def import_manifest(self, manifest_path: str) -> str:
        """Import a manifest from a file."""
        with open(manifest_path, 'r') as f:
            data = json.load(f)
        
        manifest = Manifest.from_dict(data)
        self.manifests[manifest.manifest_id] = manifest
        return manifest.manifest_id
    
    def _sign_manifest(self, manifest_id: str) -> None:
        """Sign a manifest with Ed25519."""
        manifest = self.manifests[manifest_id]
        manifest_data = manifest.to_json().encode('utf-8')
        manifest.signature = self.security_manager.sign_manifest(manifest_data)
        manifest.public_key = self.security_manager.get_public_key()
    
    def _verify_manifest_signature(self, manifest_id: str) -> bool:
        """Verify a manifest's digital signature."""
        manifest = self.manifests[manifest_id]
        if not manifest.signature or not manifest.public_key:
            return False
        
        # Create manifest data without signature for verification
        manifest_copy = Manifest(manifest.manifest_id, manifest.version)
        manifest_copy.created_at = manifest.created_at
        manifest_copy.objects = manifest.objects
        manifest_copy.total_objects = manifest.total_objects
        manifest_copy.total_size = manifest.total_size
        
        manifest_data = manifest_copy.to_json().encode('utf-8')
        return self.security_manager.verify_signature(
            manifest.signature, manifest_data, manifest.public_key
        )
    
    def _sign_toc(self, disc_id: str, toc: TableOfContents) -> None:
        """Sign a Table of Contents with Ed25519."""
        toc_data = toc.to_json().encode('utf-8')
        toc.signature = self.security_manager.sign_manifest(toc_data)
        toc.public_key = self.security_manager.get_public_key()
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        total_objects = sum(manifest.total_objects for manifest in self.manifests.values())
        total_size = sum(manifest.total_size for manifest in self.manifests.values())
        total_chunks = len(self.object_store.list_chunks())
        
        return {
            'total_manifests': len(self.manifests),
            'total_objects': total_objects,
            'total_size': total_size,
            'total_chunks': total_chunks,
            'total_discs': len(self.table_of_contents),
            'manifests': {
                mid: {
                    'objects': manifest.total_objects,
                    'size': manifest.total_size,
                    'signed': manifest.signature is not None
                }
                for mid, manifest in self.manifests.items()
            }
        }