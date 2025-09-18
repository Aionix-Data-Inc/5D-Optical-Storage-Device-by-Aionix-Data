"""
5D Optical Storage Device Encryption Module

This module provides AES-256-GCM encryption with per-chunk keys for Aionix's 
5D optical storage device. It supports optional customer-managed keys through 
KMS/HSM integration.
"""

import os
import json
import hashlib
import secrets
from typing import Optional, Dict, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class KeySource(Enum):
    """Enumeration of supported key sources."""
    LOCAL = "local"
    AWS_KMS = "aws_kms" 
    AZURE_KEY_VAULT = "azure_key_vault"
    GOOGLE_KMS = "google_kms"
    HSM = "hsm"


@dataclass
class ChunkMetadata:
    """Metadata for an encrypted chunk."""
    chunk_id: str
    nonce: bytes
    auth_tag: bytes
    key_derivation_salt: bytes
    chunk_size: int
    encryption_algorithm: str = "AES-256-GCM"


@dataclass
class EncryptionConfig:
    """Configuration for encryption operations."""
    chunk_size: int = 1024 * 1024  # 1MB default chunk size
    key_source: KeySource = KeySource.LOCAL
    master_key_id: Optional[str] = None
    kms_config: Optional[Dict] = None
    derive_keys_per_chunk: bool = True
    compression_enabled: bool = False


class OpticalStorageEncryption:
    """
    AES-256-GCM encryption for 5D optical storage with per-chunk keys.
    
    This class provides encryption and decryption functionality for data
    stored on Aionix's 5D optical storage medium. Each chunk of data is
    encrypted with its own derived key for maximum security.
    """
    
    def __init__(self, config: EncryptionConfig):
        """
        Initialize the encryption module.
        
        Args:
            config: Encryption configuration
        """
        self.config = config
        self._master_key: Optional[bytes] = None
        self._kms_client = None
        
        # Initialize KMS client if needed
        if config.key_source != KeySource.LOCAL:
            self._initialize_kms_client()
    
    def _initialize_kms_client(self):
        """Initialize the appropriate KMS client based on configuration."""
        if self.config.key_source == KeySource.AWS_KMS:
            try:
                import boto3
                self._kms_client = boto3.client('kms', **self.config.kms_config or {})
            except ImportError:
                raise ImportError("boto3 is required for AWS KMS support")
        
        elif self.config.key_source == KeySource.AZURE_KEY_VAULT:
            try:
                from azure.keyvault.keys import KeyClient
                from azure.identity import DefaultAzureCredential
                
                vault_url = self.config.kms_config.get('vault_url')
                if not vault_url:
                    raise ValueError("vault_url is required for Azure Key Vault")
                
                credential = DefaultAzureCredential()
                self._kms_client = KeyClient(vault_url=vault_url, credential=credential)
            except ImportError:
                raise ImportError("azure-keyvault-keys and azure-identity are required for Azure Key Vault support")
        
        elif self.config.key_source == KeySource.GOOGLE_KMS:
            try:
                from google.cloud import kms
                self._kms_client = kms.KeyManagementServiceClient()
            except ImportError:
                raise ImportError("google-cloud-kms is required for Google KMS support")
    
    def set_master_key(self, key: Union[bytes, str]) -> None:
        """
        Set the master key for encryption operations.
        
        Args:
            key: Master key as bytes or base64 string
        """
        if isinstance(key, str):
            try:
                self._master_key = base64.b64decode(key)
            except Exception:
                # If not base64, treat as password and derive key
                self._master_key = self._derive_master_key_from_password(key)
        else:
            self._master_key = key
        
        if len(self._master_key) != 32:  # AES-256 requires 32-byte key
            raise ValueError("Master key must be 32 bytes for AES-256")
    
    def generate_master_key(self) -> bytes:
        """
        Generate a new random master key.
        
        Returns:
            32-byte master key
        """
        key = secrets.token_bytes(32)
        self._master_key = key
        return key
    
    def _derive_master_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Derive a master key from a password using PBKDF2.
        
        Args:
            password: Password string
            salt: Optional salt (generated if not provided)
            
        Returns:
            Derived 32-byte key
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode('utf-8'))
    
    def _derive_chunk_key(self, chunk_id: str, salt: bytes) -> bytes:
        """
        Derive a unique key for a specific chunk.
        
        Args:
            chunk_id: Unique identifier for the chunk
            salt: Random salt for key derivation
            
        Returns:
            32-byte chunk key
        """
        if not self._master_key:
            raise ValueError("Master key not set")
        
        # Combine master key with chunk ID and salt
        key_material = self._master_key + chunk_id.encode('utf-8') + salt
        
        # Use PBKDF2 for key derivation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=10000,
        )
        return kdf.derive(key_material)
    
    def _get_customer_managed_key(self) -> bytes:
        """
        Retrieve or derive key from customer-managed key service.
        
        Returns:
            32-byte key from KMS/HSM
        """
        if self.config.key_source == KeySource.AWS_KMS:
            response = self._kms_client.decrypt(
                KeyId=self.config.master_key_id,
                CiphertextBlob=base64.b64decode(self.config.master_key_id)
            )
            return response['Plaintext'][:32]
        
        elif self.config.key_source == KeySource.AZURE_KEY_VAULT:
            # In a real implementation, you'd retrieve and decrypt the key
            # This is a simplified example
            key = self._kms_client.get_key(self.config.master_key_id)
            # Extract key material (implementation depends on key type)
            return hashlib.sha256(str(key.key).encode()).digest()
        
        elif self.config.key_source == KeySource.GOOGLE_KMS:
            # Decrypt data encrypted with the KMS key
            response = self._kms_client.decrypt(
                request={
                    "name": self.config.master_key_id,
                    "ciphertext": base64.b64decode(self.config.master_key_id)
                }
            )
            return response.plaintext[:32]
        
        else:
            raise ValueError(f"Unsupported key source: {self.config.key_source}")
    
    def encrypt_chunk(self, data: bytes, chunk_id: str) -> Tuple[bytes, ChunkMetadata]:
        """
        Encrypt a chunk of data using AES-256-GCM.
        
        Args:
            data: Data to encrypt
            chunk_id: Unique identifier for this chunk
            
        Returns:
            Tuple of (encrypted_data, metadata)
        """
        # Generate random salt and nonce
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        
        # Derive chunk-specific key
        if self.config.derive_keys_per_chunk:
            if self.config.key_source == KeySource.LOCAL:
                chunk_key = self._derive_chunk_key(chunk_id, salt)
            else:
                # For customer-managed keys, derive from CMK
                master_key = self._get_customer_managed_key()
                # Temporarily set master key for derivation
                original_key = self._master_key
                self._master_key = master_key
                chunk_key = self._derive_chunk_key(chunk_id, salt)
                self._master_key = original_key
        else:
            chunk_key = self._master_key or self._get_customer_managed_key()
        
        # Encrypt using AES-256-GCM
        aesgcm = AESGCM(chunk_key)
        encrypted_data = aesgcm.encrypt(nonce, data, None)
        
        # Extract auth tag (last 16 bytes)
        ciphertext = encrypted_data[:-16]
        auth_tag = encrypted_data[-16:]
        
        # Create metadata
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            nonce=nonce,
            auth_tag=auth_tag,
            key_derivation_salt=salt,
            chunk_size=len(data)
        )
        
        return ciphertext, metadata
    
    def decrypt_chunk(self, encrypted_data: bytes, metadata: ChunkMetadata) -> bytes:
        """
        Decrypt a chunk of data using AES-256-GCM.
        
        Args:
            encrypted_data: Encrypted data
            metadata: Chunk metadata containing nonce, salt, etc.
            
        Returns:
            Decrypted data
        """
        # Derive the same chunk key used for encryption
        if self.config.derive_keys_per_chunk:
            if self.config.key_source == KeySource.LOCAL:
                chunk_key = self._derive_chunk_key(metadata.chunk_id, metadata.key_derivation_salt)
            else:
                # For customer-managed keys, derive from CMK
                master_key = self._get_customer_managed_key()
                # Temporarily set master key for derivation
                original_key = self._master_key
                self._master_key = master_key
                chunk_key = self._derive_chunk_key(metadata.chunk_id, metadata.key_derivation_salt)
                self._master_key = original_key
        else:
            chunk_key = self._master_key or self._get_customer_managed_key()
        
        # Reconstruct the full encrypted data with auth tag
        full_encrypted_data = encrypted_data + metadata.auth_tag
        
        # Decrypt using AES-256-GCM
        aesgcm = AESGCM(chunk_key)
        try:
            decrypted_data = aesgcm.decrypt(metadata.nonce, full_encrypted_data, None)
            return decrypted_data
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def encrypt_data(self, data: bytes, data_id: str) -> Tuple[List[bytes], List[ChunkMetadata]]:
        """
        Encrypt data by splitting it into chunks.
        
        Args:
            data: Data to encrypt
            data_id: Unique identifier for this data
            
        Returns:
            Tuple of (encrypted_chunks, metadata_list)
        """
        chunks = []
        metadata_list = []
        
        # Handle empty data case
        if len(data) == 0:
            chunk_id = f"{data_id}_chunk_0"
            encrypted_chunk, metadata = self.encrypt_chunk(data, chunk_id)
            chunks.append(encrypted_chunk)
            metadata_list.append(metadata)
            return chunks, metadata_list
        
        # Split data into chunks
        for i in range(0, len(data), self.config.chunk_size):
            chunk_data = data[i:i + self.config.chunk_size]
            chunk_id = f"{data_id}_chunk_{i // self.config.chunk_size}"
            
            encrypted_chunk, metadata = self.encrypt_chunk(chunk_data, chunk_id)
            chunks.append(encrypted_chunk)
            metadata_list.append(metadata)
        
        return chunks, metadata_list
    
    def decrypt_data(self, encrypted_chunks: List[bytes], metadata_list: List[ChunkMetadata]) -> bytes:
        """
        Decrypt data from encrypted chunks.
        
        Args:
            encrypted_chunks: List of encrypted chunks
            metadata_list: List of chunk metadata
            
        Returns:
            Decrypted data
        """
        if len(encrypted_chunks) != len(metadata_list):
            raise ValueError("Number of chunks must match number of metadata entries")
        
        decrypted_data = b""
        
        for encrypted_chunk, metadata in zip(encrypted_chunks, metadata_list):
            chunk_data = self.decrypt_chunk(encrypted_chunk, metadata)
            decrypted_data += chunk_data
        
        return decrypted_data
    
    def export_key(self) -> str:
        """
        Export the master key as base64 string.
        
        Returns:
            Base64 encoded master key
        """
        if not self._master_key:
            raise ValueError("No master key set")
        return base64.b64encode(self._master_key).decode('utf-8')
    
    def get_encryption_info(self) -> Dict:
        """
        Get information about the current encryption configuration.
        
        Returns:
            Dictionary with encryption information
        """
        return {
            "algorithm": "AES-256-GCM",
            "chunk_size": self.config.chunk_size,
            "key_source": self.config.key_source.value,
            "per_chunk_keys": self.config.derive_keys_per_chunk,
            "master_key_set": self._master_key is not None,
            "compression_enabled": self.config.compression_enabled
        }