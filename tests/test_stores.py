"""
Unit tests for the object store implementations.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aionix_storage import FileSystemStore, ArchiveStore, create_store


class TestFileSystemStore(unittest.TestCase):
    """Test cases for FileSystemStore."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = FileSystemStore(Path(self.temp_dir))
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_put_and_get(self):
        """Test storing and retrieving data."""
        key = "test_key"
        data = b"Hello, 5D Optical Storage!"
        
        self.store.put(key, data)
        retrieved_data = self.store.get(key)
        
        self.assertEqual(data, retrieved_data)
    
    def test_put_with_metadata(self):
        """Test storing data with metadata."""
        key = "test_key_meta"
        data = b"Test data with metadata"
        metadata = {"author": "Aionix", "type": "5D_optical"}
        
        self.store.put(key, data, metadata)
        retrieved_metadata = self.store.get_metadata(key)
        
        self.assertEqual(metadata["author"], retrieved_metadata["author"])
        self.assertEqual(metadata["type"], retrieved_metadata["type"])
        self.assertEqual(len(data), retrieved_metadata["size"])
    
    def test_exists(self):
        """Test checking if objects exist."""
        key = "exists_test"
        data = b"Test data"
        
        self.assertFalse(self.store.exists(key))
        self.store.put(key, data)
        self.assertTrue(self.store.exists(key))
    
    def test_delete(self):
        """Test deleting objects."""
        key = "delete_test"
        data = b"Data to delete"
        
        self.store.put(key, data)
        self.assertTrue(self.store.exists(key))
        
        self.store.delete(key)
        self.assertFalse(self.store.exists(key))
    
    def test_delete_nonexistent(self):
        """Test deleting non-existent object raises KeyError."""
        with self.assertRaises(KeyError):
            self.store.delete("nonexistent_key")
    
    def test_get_nonexistent(self):
        """Test getting non-existent object raises KeyError."""
        with self.assertRaises(KeyError):
            self.store.get("nonexistent_key")
    
    def test_list_keys(self):
        """Test listing keys."""
        keys = ["key1", "key2", "prefix_key3"]
        data = b"test data"
        
        for key in keys:
            self.store.put(key, data)
        
        all_keys = self.store.list_keys()
        self.assertEqual(set(keys), set(all_keys))
        
        # Test prefix filtering
        prefix_keys = self.store.list_keys("prefix_")
        self.assertEqual(["prefix_key3"], prefix_keys)


class TestArchiveStore(unittest.TestCase):
    """Test cases for ArchiveStore."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.archive_path = Path(self.temp_dir) / "test_archive.tar"
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_tar_store(self):
        """Test tar archive store."""
        store = ArchiveStore(self.archive_path, "tar")
        
        key = "tar_test"
        data = b"Tar archive test data"
        store.put(key, data)
        
        retrieved_data = store.get(key)
        self.assertEqual(data, retrieved_data)
    
    def test_zip_store(self):
        """Test zip archive store."""
        zip_path = Path(self.temp_dir) / "test_archive.zip"
        store = ArchiveStore(zip_path, "zip")
        
        key = "zip_test"
        data = b"Zip archive test data"
        store.put(key, data)
        
        retrieved_data = store.get(key)
        self.assertEqual(data, retrieved_data)
    
    def test_archive_persistence(self):
        """Test that data persists when archive is reopened."""
        key = "persistence_test"
        data = b"Persistent data"
        
        # Create and store data
        store1 = ArchiveStore(self.archive_path, "tar")
        store1.put(key, data)
        
        # Open archive again and verify data exists
        store2 = ArchiveStore(self.archive_path, "tar")
        self.assertTrue(store2.exists(key))
        retrieved_data = store2.get(key)
        self.assertEqual(data, retrieved_data)


class TestFactory(unittest.TestCase):
    """Test cases for the factory function."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_create_filesystem_store(self):
        """Test creating filesystem store via factory."""
        store = create_store('filesystem', base_path=self.temp_dir)
        self.assertIsInstance(store, FileSystemStore)
    
    def test_create_archive_store(self):
        """Test creating archive store via factory."""
        archive_path = Path(self.temp_dir) / "test.tar"
        store = create_store('archive', archive_path=archive_path, archive_type='tar')
        self.assertIsInstance(store, ArchiveStore)
    
    def test_invalid_store_type(self):
        """Test that invalid store type raises ValueError."""
        with self.assertRaises(ValueError):
            create_store('invalid_type')


if __name__ == '__main__':
    unittest.main()