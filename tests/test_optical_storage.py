"""
Test suite for 5D Optical Storage System

Tests all major components including security, storage, and core functionality.
"""

import os
import tempfile
import pytest
from pathlib import Path
import json

from optical_storage import OpticalStorage, SecurityManager, ObjectStore
from optical_storage.storage import FileSystemObjectStore, DataIngestionEngine
from optical_storage.core import Manifest, TableOfContents


class TestSecurityManager:
    """Test the security manager functionality."""
    
    def setup_method(self):
        """Set up test security manager."""
        self.security_manager = SecurityManager()
    
    def test_chunk_key_generation(self):
        """Test chunk key generation is deterministic."""
        chunk_id = "test_chunk_001"
        key1 = self.security_manager.generate_chunk_key(chunk_id)
        key2 = self.security_manager.generate_chunk_key(chunk_id)
        
        assert key1 == key2
        assert len(key1) == 32  # 256-bit key
    
    def test_encryption_decryption(self):
        """Test chunk encryption and decryption."""
        chunk_id = "test_chunk_001"
        original_data = b"This is test data for encryption testing."
        
        # Encrypt
        encrypted_data, nonce = self.security_manager.encrypt_chunk(original_data, chunk_id)
        
        # Decrypt
        decrypted_data = self.security_manager.decrypt_chunk(encrypted_data, nonce, chunk_id)
        
        assert decrypted_data == original_data
        assert len(nonce) == 12  # 96-bit nonce for GCM
    
    def test_content_hashing(self):
        """Test content hashing with different algorithms."""
        test_data = b"Test data for hashing"
        
        sha256_hash = self.security_manager.hash_content(test_data, 'sha256')
        sha512_hash = self.security_manager.hash_content(test_data, 'sha512')
        
        assert len(sha256_hash) == 64  # 256-bit hash in hex
        assert len(sha512_hash) == 128  # 512-bit hash in hex
        
        # Test deterministic hashing
        assert sha256_hash == self.security_manager.hash_content(test_data, 'sha256')
    
    def test_digital_signatures(self):
        """Test Ed25519 digital signature creation and verification."""
        test_data = b"Test data for signature verification"
        
        # Sign the data
        signature = self.security_manager.sign_manifest(test_data)
        public_key = self.security_manager.get_public_key()
        
        # Verify signature
        is_valid = self.security_manager.verify_signature(signature, test_data, public_key)
        assert is_valid
        
        # Test with tampered data
        tampered_data = b"Tampered data for signature verification"
        is_valid_tampered = self.security_manager.verify_signature(signature, tampered_data, public_key)
        assert not is_valid_tampered


class TestObjectStore:
    """Test object store implementations."""
    
    def setup_method(self):
        """Set up test object store."""
        self.temp_dir = tempfile.mkdtemp()
        self.object_store = FileSystemObjectStore(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test object store."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_chunk_operations(self):
        """Test basic chunk operations."""
        chunk_id = "test_chunk_001"
        test_data = b"This is test chunk data"
        
        # Store chunk
        self.object_store.put_chunk(chunk_id, test_data)
        
        # List chunks
        chunks = self.object_store.list_chunks()
        assert chunk_id in chunks
        
        # Retrieve chunk
        retrieved_data = self.object_store.get_chunk(chunk_id)
        assert retrieved_data == test_data
        
        # Delete chunk
        self.object_store.delete_chunk(chunk_id)
        chunks = self.object_store.list_chunks()
        assert chunk_id not in chunks


class TestDataIngestionEngine:
    """Test data ingestion and chunking."""
    
    def setup_method(self):
        """Set up test ingestion engine."""
        self.temp_dir = tempfile.mkdtemp()
        self.security_manager = SecurityManager()
        self.object_store = FileSystemObjectStore(self.temp_dir)
        self.ingestion_engine = DataIngestionEngine(
            self.security_manager, self.object_store, chunk_size=1024*1024  # 1MB chunk for testing
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_file_ingestion(self):
        """Test file ingestion with chunking."""
        # Create a test file
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_content = b"A" * (2 * 1024 * 1024)  # 2MB file, should create 2 chunks with 1MB chunk size
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Ingest the file
        metadata = self.ingestion_engine.ingest_file(str(test_file))
        
        assert metadata.total_size == 2 * 1024 * 1024
        assert len(metadata.chunks) == 2  # Should be split into 2 chunks
        assert metadata.content_hash_sha256 is not None
        assert metadata.content_hash_sha512 is not None
        
        # Test retrieval
        retrieved_data = self.ingestion_engine.retrieve_object(metadata)
        assert retrieved_data == test_content
    
    def test_deduplication(self):
        """Test content deduplication."""
        # Create two files with same content
        test_file1 = Path(self.temp_dir) / "test_file1.txt"
        test_file2 = Path(self.temp_dir) / "test_file2.txt"
        test_content = b"Duplicate content for deduplication testing"
        
        for test_file in [test_file1, test_file2]:
            with open(test_file, 'wb') as f:
                f.write(test_content)
        
        # Ingest both files with deduplication enabled
        metadata1 = self.ingestion_engine.ingest_file(str(test_file1), enable_dedup=True)
        metadata2 = self.ingestion_engine.ingest_file(str(test_file2), enable_dedup=True)
        
        # Should use same chunk for identical content
        assert metadata1.chunks[0].hash_sha256 == metadata2.chunks[0].hash_sha256
        
        # Check that only one physical chunk is stored
        stored_chunks = self.object_store.list_chunks()
        assert len(stored_chunks) == 1  # Only one physical chunk despite two files


class TestOpticalStorage:
    """Test the main optical storage system."""
    
    def setup_method(self):
        """Set up test optical storage system."""
        self.temp_dir = tempfile.mkdtemp()
        self.security_manager = SecurityManager()
        self.object_store = FileSystemObjectStore(self.temp_dir)
        self.optical_storage = OpticalStorage(
            self.security_manager, self.object_store, chunk_size=1024*1024  # 1MB chunk for testing
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_file_storage_and_retrieval(self):
        """Test end-to-end file storage and retrieval."""
        # Create a test file
        test_file = Path(self.temp_dir) / "test_document.txt"
        test_content = b"This is a test document for the 5D optical storage system."
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Store the file
        object_id = self.optical_storage.store_file(str(test_file))
        
        # Verify manifest was created and signed
        assert len(self.optical_storage.manifests) == 1
        manifest_id = list(self.optical_storage.manifests.keys())[0]
        manifest = self.optical_storage.manifests[manifest_id]
        assert manifest.signature is not None
        assert manifest.public_key is not None
        
        # Retrieve the file
        retrieved_content = self.optical_storage.retrieve_object(object_id, manifest_id)
        assert retrieved_content == test_content
    
    def test_manifest_signature_verification(self):
        """Test manifest signature verification."""
        # Create and store a test file
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_content = b"Test content for signature verification"
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        object_id = self.optical_storage.store_file(str(test_file))
        manifest_id = list(self.optical_storage.manifests.keys())[0]
        
        # Verify signature is valid
        assert self.optical_storage._verify_manifest_signature(manifest_id)
        
        # Tamper with manifest and verify signature fails
        manifest = self.optical_storage.manifests[manifest_id]
        original_size = manifest.total_size
        manifest.total_size = 99999  # Tamper with data
        
        assert not self.optical_storage._verify_manifest_signature(manifest_id)
        
        # Restore original data
        manifest.total_size = original_size
        assert self.optical_storage._verify_manifest_signature(manifest_id)
    
    def test_disc_toc_creation(self):
        """Test Table of Contents creation for discs."""
        # Store some test files
        test_files = []
        manifest_ids = []
        
        for i in range(3):
            test_file = Path(self.temp_dir) / f"test_file_{i}.txt"
            test_content = f"Test content for file {i}".encode()
            
            with open(test_file, 'wb') as f:
                f.write(test_content)
            
            manifest_id = f"manifest_{i}"
            object_id = self.optical_storage.store_file(str(test_file), manifest_id)
            manifest_ids.append(manifest_id)
        
        # Create TOC
        disc_id = "disc_001"
        toc = self.optical_storage.create_disc_toc(disc_id, manifest_ids)
        
        assert toc.disc_id == disc_id
        assert len(toc.manifests) == 3
        assert toc.signature is not None
        assert toc.public_key is not None
        assert toc.used_space > 0
    
    def test_storage_statistics(self):
        """Test storage statistics reporting."""
        # Store some test files
        for i in range(2):
            test_file = Path(self.temp_dir) / f"stats_test_{i}.txt"
            test_content = f"Statistics test content {i}".encode()
            
            with open(test_file, 'wb') as f:
                f.write(test_content)
            
            self.optical_storage.store_file(str(test_file))
        
        # Get statistics
        stats = self.optical_storage.get_storage_stats()
        
        assert stats['total_manifests'] >= 1
        assert stats['total_objects'] >= 2
        assert stats['total_size'] > 0
        assert stats['total_chunks'] > 0


def test_manifest_serialization():
    """Test manifest serialization and deserialization."""
    # Create a manifest
    manifest = Manifest("test_manifest")
    
    # Convert to dict and back
    manifest_dict = manifest.to_dict()
    reconstructed = Manifest.from_dict(manifest_dict)
    
    assert reconstructed.manifest_id == manifest.manifest_id
    assert reconstructed.version == manifest.version
    assert reconstructed.created_at == manifest.created_at


def test_toc_serialization():
    """Test TOC serialization."""
    toc = TableOfContents("test_disc")
    toc.add_manifest("manifest_001", 1024)
    toc.add_manifest("manifest_002", 2048)
    
    toc_dict = toc.to_dict()
    
    assert toc_dict['disc_id'] == "test_disc"
    assert len(toc_dict['manifests']) == 2
    assert toc_dict['used_space'] == 3072
    assert toc_dict['available_space'] == toc.disc_capacity - 3072


if __name__ == "__main__":
    pytest.main([__file__, "-v"])