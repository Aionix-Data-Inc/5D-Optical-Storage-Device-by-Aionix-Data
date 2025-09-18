#!/usr/bin/env python3
"""
Simple tests for the object store abstraction.

Run with: python3 test_object_store.py
"""

import os
import tempfile
import shutil
from object_store import ObjectStore, create_storage


def test_filesystem_storage():
    """Test file system storage."""
    print("Testing FileSystem Storage...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create storage
        storage = create_storage(f"file://{temp_dir}")
        store = ObjectStore(storage)
        
        # Test basic operations
        test_data = "Hello, World!"
        metadata = store.put("test.txt", test_data)
        assert metadata.size == len(test_data)
        
        # Test retrieval
        retrieved = store.get_text("test.txt")
        assert retrieved == test_data
        
        # Test existence
        assert store.exists("test.txt")
        assert not store.exists("nonexistent.txt")
        
        # Test listing
        objects = store.list()
        assert len(objects) == 1
        assert objects[0].key == "test.txt"
        
        # Test deletion
        assert store.delete("test.txt")
        assert not store.exists("test.txt")
        
    print("✓ FileSystem Storage tests passed")


def test_archive_storage():
    """Test archive storage."""
    print("Testing Archive Storage...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        tar_path = os.path.join(temp_dir, "test.tar")
        
        # Create TAR storage
        storage = create_storage(f"tar://{tar_path}")
        store = ObjectStore(storage)
        
        # Test basic operations
        test_data = "Archive test data"
        metadata = store.put("archive/test.txt", test_data)
        assert metadata.size == len(test_data)
        
        # Test retrieval
        retrieved = store.get_text("archive/test.txt")
        assert retrieved == test_data
        
        # Test existence
        assert store.exists("archive/test.txt")
        
        # Test listing
        objects = store.list()
        assert len(objects) == 1
        assert objects[0].key == "archive/test.txt"
        
    print("✓ Archive Storage tests passed")


def test_mock_s3_storage():
    """Test mock S3 storage."""
    print("Testing Mock S3 Storage...")
    
    # Create mock S3 storage
    storage = create_storage("mock-s3://test-bucket")
    store = ObjectStore(storage)
    
    # Test basic operations
    test_data = b"Binary test data"
    metadata = store.put("data/binary.bin", test_data)
    assert metadata.size == len(test_data)
    
    # Test retrieval
    retrieved = store.get("data/binary.bin")
    assert retrieved == test_data
    
    # Test existence
    assert store.exists("data/binary.bin")
    
    # Test listing with prefix
    objects = store.list(prefix="data/")
    assert len(objects) == 1
    assert objects[0].key == "data/binary.bin"
    
    # Test deletion
    assert store.delete("data/binary.bin")
    assert not store.exists("data/binary.bin")
    
    print("✓ Mock S3 Storage tests passed")


def test_metadata():
    """Test metadata functionality."""
    print("Testing Metadata...")
    
    storage = create_storage("mock-s3://metadata-test")
    store = ObjectStore(storage)
    
    # Store with metadata
    test_data = "Data with metadata"
    metadata = store.put(
        "meta/test.txt", 
        test_data,
        content_type="text/plain",
        metadata={"author": "test", "version": "1.0"}
    )
    
    # Verify metadata
    assert metadata.content_type == "text/plain"
    assert metadata.custom_metadata["author"] == "test"
    assert metadata.custom_metadata["version"] == "1.0"
    
    # Get metadata
    retrieved_meta = store.get_metadata("meta/test.txt")
    assert retrieved_meta.key == "meta/test.txt"
    assert retrieved_meta.size == len(test_data)
    
    print("✓ Metadata tests passed")


def main():
    """Run all tests."""
    print("Running Object Store Tests...")
    print("=" * 40)
    
    try:
        test_filesystem_storage()
        test_archive_storage()
        test_mock_s3_storage()
        test_metadata()
        
        print("=" * 40)
        print("✓ All tests passed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()