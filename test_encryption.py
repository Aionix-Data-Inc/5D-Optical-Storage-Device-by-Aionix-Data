"""
Unit tests for 5D Optical Storage Device Encryption.

This module contains comprehensive tests for the encryption functionality
including local and customer-managed key scenarios.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optical_encryption import (
    OpticalStorageEncryption, 
    EncryptionConfig, 
    KeySource, 
    ChunkMetadata
)
from config_manager import ConfigManager


class TestOpticalStorageEncryption(unittest.TestCase):
    """Test cases for OpticalStorageEncryption class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = b"This is test data for 5D optical storage encryption. " * 100
        self.config = EncryptionConfig(
            chunk_size=512,  # Small chunk size for testing
            key_source=KeySource.LOCAL,
            derive_keys_per_chunk=True
        )
        self.encryptor = OpticalStorageEncryption(self.config)
        self.master_key = self.encryptor.generate_master_key()
    
    def test_key_generation(self):
        """Test master key generation."""
        key1 = self.encryptor.generate_master_key()
        key2 = self.encryptor.generate_master_key()
        
        # Keys should be 32 bytes for AES-256
        self.assertEqual(len(key1), 32)
        self.assertEqual(len(key2), 32)
        
        # Keys should be different
        self.assertNotEqual(key1, key2)
    
    def test_key_export_import(self):
        """Test key export and import functionality."""
        # Export key
        exported_key = self.encryptor.export_key()
        self.assertIsInstance(exported_key, str)
        
        # Create new encryptor and import key
        new_encryptor = OpticalStorageEncryption(self.config)
        new_encryptor.set_master_key(exported_key)
        
        # Both should have the same key
        self.assertEqual(self.encryptor._master_key, new_encryptor._master_key)
    
    def test_chunk_encryption_decryption(self):
        """Test single chunk encryption and decryption."""
        chunk_data = b"Test chunk data"
        chunk_id = "test_chunk_001"
        
        # Encrypt chunk
        encrypted_data, metadata = self.encryptor.encrypt_chunk(chunk_data, chunk_id)
        
        # Verify metadata
        self.assertEqual(metadata.chunk_id, chunk_id)
        self.assertEqual(metadata.chunk_size, len(chunk_data))
        self.assertEqual(metadata.encryption_algorithm, "AES-256-GCM")
        self.assertEqual(len(metadata.nonce), 12)  # GCM nonce size
        self.assertEqual(len(metadata.auth_tag), 16)  # GCM auth tag size
        
        # Decrypt chunk
        decrypted_data = self.encryptor.decrypt_chunk(encrypted_data, metadata)
        
        # Verify decryption
        self.assertEqual(chunk_data, decrypted_data)
    
    def test_data_encryption_decryption(self):
        """Test full data encryption and decryption."""
        data_id = "test_data_001"
        
        # Encrypt data
        encrypted_chunks, metadata_list = self.encryptor.encrypt_data(self.test_data, data_id)
        
        # Verify chunking
        expected_chunks = (len(self.test_data) + self.config.chunk_size - 1) // self.config.chunk_size
        self.assertEqual(len(encrypted_chunks), expected_chunks)
        self.assertEqual(len(metadata_list), expected_chunks)
        
        # Verify chunk IDs
        for i, metadata in enumerate(metadata_list):
            expected_id = f"{data_id}_chunk_{i}"
            self.assertEqual(metadata.chunk_id, expected_id)
        
        # Decrypt data
        decrypted_data = self.encryptor.decrypt_data(encrypted_chunks, metadata_list)
        
        # Verify decryption
        self.assertEqual(self.test_data, decrypted_data)
    
    def test_per_chunk_keys(self):
        """Test that different chunks use different keys."""
        chunk_data1 = b"First chunk data"
        chunk_data2 = b"Second chunk data"
        
        # Encrypt both chunks
        encrypted1, metadata1 = self.encryptor.encrypt_chunk(chunk_data1, "chunk1")
        encrypted2, metadata2 = self.encryptor.encrypt_chunk(chunk_data2, "chunk2")
        
        # Same data with different chunk IDs should produce different encrypted data
        if chunk_data1 == chunk_data2:
            self.assertNotEqual(encrypted1, encrypted2)
        
        # Different salts should be used
        self.assertNotEqual(metadata1.key_derivation_salt, metadata2.key_derivation_salt)
        
        # Both should decrypt correctly
        decrypted1 = self.encryptor.decrypt_chunk(encrypted1, metadata1)
        decrypted2 = self.encryptor.decrypt_chunk(encrypted2, metadata2)
        
        self.assertEqual(chunk_data1, decrypted1)
        self.assertEqual(chunk_data2, decrypted2)
    
    def test_wrong_key_fails(self):
        """Test that decryption fails with wrong key."""
        chunk_data = b"Test data"
        chunk_id = "test_chunk"
        
        # Encrypt with first key
        encrypted_data, metadata = self.encryptor.encrypt_chunk(chunk_data, chunk_id)
        
        # Try to decrypt with different key
        new_encryptor = OpticalStorageEncryption(self.config)
        new_encryptor.generate_master_key()  # Different key
        
        with self.assertRaises(ValueError):
            new_encryptor.decrypt_chunk(encrypted_data, metadata)
    
    def test_encryption_info(self):
        """Test encryption information retrieval."""
        info = self.encryptor.get_encryption_info()
        
        self.assertEqual(info['algorithm'], 'AES-256-GCM')
        self.assertEqual(info['chunk_size'], self.config.chunk_size)
        self.assertEqual(info['key_source'], KeySource.LOCAL.value)
        self.assertTrue(info['per_chunk_keys'])
        self.assertTrue(info['master_key_set'])
        self.assertFalse(info['compression_enabled'])
    
    def test_empty_data(self):
        """Test encryption of empty data."""
        empty_data = b""
        data_id = "empty_test"
        
        encrypted_chunks, metadata_list = self.encryptor.encrypt_data(empty_data, data_id)
        
        # Should have one empty chunk
        self.assertEqual(len(encrypted_chunks), 1)
        self.assertEqual(len(metadata_list), 1)
        
        # Decrypt should return empty data
        decrypted_data = self.encryptor.decrypt_data(encrypted_chunks, metadata_list)
        self.assertEqual(empty_data, decrypted_data)
    
    def test_large_data(self):
        """Test encryption of large data that spans multiple chunks."""
        large_data = b"X" * (self.config.chunk_size * 3 + 100)  # 3.1 chunks
        data_id = "large_test"
        
        encrypted_chunks, metadata_list = self.encryptor.encrypt_data(large_data, data_id)
        
        # Should have 4 chunks
        self.assertEqual(len(encrypted_chunks), 4)
        self.assertEqual(len(metadata_list), 4)
        
        # Verify chunk sizes
        for i, metadata in enumerate(metadata_list):
            if i < 3:
                self.assertEqual(metadata.chunk_size, self.config.chunk_size)
            else:
                self.assertEqual(metadata.chunk_size, 100)  # Last chunk
        
        # Decrypt should return original data
        decrypted_data = self.encryptor.decrypt_data(encrypted_chunks, metadata_list)
        self.assertEqual(large_data, decrypted_data)


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.yaml")
        
        # Clear optical environment variables
        self.original_env = {}
        for key in list(os.environ.keys()):
            if key.startswith('OPTICAL_'):
                self.original_env[key] = os.environ.pop(key)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        
        # Restore original environment variables
        for key, value in self.original_env.items():
            os.environ[key] = value
    
    def test_default_config(self):
        """Test default configuration loading."""
        manager = ConfigManager()
        config = manager.get_encryption_config()
        
        # Just test that it's a valid configuration
        self.assertIsInstance(config.chunk_size, int)
        self.assertTrue(config.chunk_size > 0)
        self.assertIsInstance(config.key_source, KeySource)
        self.assertIsInstance(config.derive_keys_per_chunk, bool)
        self.assertIsInstance(config.compression_enabled, bool)
    
    def test_config_validation(self):
        """Test configuration validation."""
        manager = ConfigManager()
        
        # Valid config should pass
        self.assertTrue(manager.validate_config())
        
        # Invalid chunk size
        manager.config['encryption']['chunk_size'] = -1
        with self.assertRaises(ValueError):
            manager.validate_config()
        
        # Reset chunk size and test invalid key source
        manager.config['encryption']['chunk_size'] = 1024
        manager.config['encryption']['key_source'] = 'invalid'
        with self.assertRaises(ValueError):
            manager.validate_config()
        
        # Reset to valid config for next test
        manager.config['encryption']['key_source'] = 'local'
    
    def test_config_summary(self):
        """Test configuration summary generation."""
        manager = ConfigManager()
        summary = manager.get_config_summary()
        
        self.assertIn('encryption_algorithm', summary)
        self.assertIn('chunk_size_mb', summary)
        self.assertIn('key_source', summary)
        self.assertEqual(summary['encryption_algorithm'], 'AES-256-GCM')
    
    def test_environment_variables(self):
        """Test loading configuration from environment variables."""
        # Set environment variables
        os.environ['OPTICAL_CHUNK_SIZE'] = '2048'
        os.environ['OPTICAL_KEY_SOURCE'] = 'aws_kms'
        os.environ['OPTICAL_PER_CHUNK_KEYS'] = 'false'
        
        try:
            manager = ConfigManager()
            config = manager.get_encryption_config()
            
            self.assertEqual(config.chunk_size, 2048)
            self.assertEqual(config.key_source, KeySource.AWS_KMS)
            self.assertFalse(config.derive_keys_per_chunk)
        
        finally:
            # Clean up environment variables
            for var in ['OPTICAL_CHUNK_SIZE', 'OPTICAL_KEY_SOURCE', 'OPTICAL_PER_CHUNK_KEYS']:
                os.environ.pop(var, None)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data = b"Integration test data for 5D optical storage " * 50
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_encryption(self):
        """Test complete encryption/decryption workflow."""
        # Create configuration
        config = EncryptionConfig(
            chunk_size=256,
            key_source=KeySource.LOCAL,
            derive_keys_per_chunk=True
        )
        
        # Initialize encryptor
        encryptor = OpticalStorageEncryption(config)
        master_key = encryptor.generate_master_key()
        
        # Encrypt data
        data_id = "integration_test"
        encrypted_chunks, metadata_list = encryptor.encrypt_data(self.test_data, data_id)
        
        # Save encrypted chunks to files (simulating storage)
        chunk_files = []
        for i, chunk in enumerate(encrypted_chunks):
            chunk_file = os.path.join(self.temp_dir, f"{data_id}_chunk_{i}.enc")
            with open(chunk_file, 'wb') as f:
                f.write(chunk)
            chunk_files.append(chunk_file)
        
        # Load encrypted chunks from files
        loaded_chunks = []
        for chunk_file in chunk_files:
            with open(chunk_file, 'rb') as f:
                loaded_chunks.append(f.read())
        
        # Decrypt data
        decrypted_data = encryptor.decrypt_data(loaded_chunks, metadata_list)
        
        # Verify
        self.assertEqual(self.test_data, decrypted_data)
    
    def test_different_chunk_sizes(self):
        """Test encryption with different chunk sizes."""
        chunk_sizes = [128, 512, 1024, 2048]
        
        for chunk_size in chunk_sizes:
            with self.subTest(chunk_size=chunk_size):
                config = EncryptionConfig(
                    chunk_size=chunk_size,
                    key_source=KeySource.LOCAL,
                    derive_keys_per_chunk=True
                )
                
                encryptor = OpticalStorageEncryption(config)
                encryptor.generate_master_key()
                
                # Encrypt and decrypt
                encrypted_chunks, metadata_list = encryptor.encrypt_data(self.test_data, "test")
                decrypted_data = encryptor.decrypt_data(encrypted_chunks, metadata_list)
                
                self.assertEqual(self.test_data, decrypted_data)


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(TestOpticalStorageEncryption))
    suite.addTest(unittest.makeSuite(TestConfigManager))
    suite.addTest(unittest.makeSuite(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)