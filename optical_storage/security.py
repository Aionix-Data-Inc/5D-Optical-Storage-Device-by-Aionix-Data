"""
Security module for 5D Optical Storage System

Handles encryption, decryption, and digital signatures using:
- AES-256-GCM for per-chunk encryption
- Ed25519 for digital signatures
- SHA-256/SHA-512 for content hashing
"""

import hashlib
import secrets
from typing import Dict, Optional, Tuple, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


class SecurityManager:
    """Manages encryption, hashing, and digital signatures for the storage system."""
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize security manager.
        
        Args:
            master_key: Optional master key for deterministic key derivation
        """
        self.master_key = master_key or secrets.token_bytes(32)
        self._signing_key = Ed25519PrivateKey.generate()
        
    def generate_chunk_key(self, chunk_id: str) -> bytes:
        """Generate a unique AES-256 key for a specific chunk."""
        # Use HMAC-based key derivation for deterministic per-chunk keys
        key_material = self.master_key + chunk_id.encode('utf-8')
        return hashlib.sha256(key_material).digest()
    
    def encrypt_chunk(self, data: bytes, chunk_id: str) -> Tuple[bytes, bytes]:
        """
        Encrypt a data chunk using AES-256-GCM.
        
        Args:
            data: Raw data to encrypt
            chunk_id: Unique identifier for this chunk
            
        Returns:
            Tuple of (encrypted_data, nonce)
        """
        chunk_key = self.generate_chunk_key(chunk_id)
        aesgcm = AESGCM(chunk_key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return ciphertext, nonce
    
    def decrypt_chunk(self, encrypted_data: bytes, nonce: bytes, chunk_id: str) -> bytes:
        """
        Decrypt a data chunk using AES-256-GCM.
        
        Args:
            encrypted_data: Encrypted chunk data
            nonce: Nonce used for encryption
            chunk_id: Unique identifier for this chunk
            
        Returns:
            Decrypted data
        """
        chunk_key = self.generate_chunk_key(chunk_id)
        aesgcm = AESGCM(chunk_key)
        return aesgcm.decrypt(nonce, encrypted_data, None)
    
    def hash_content(self, data: bytes, algorithm: str = 'sha256') -> str:
        """
        Generate content hash using specified algorithm.
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm ('sha256' or 'sha512')
            
        Returns:
            Hexadecimal hash string
        """
        if algorithm == 'sha256':
            return hashlib.sha256(data).hexdigest()
        elif algorithm == 'sha512':
            return hashlib.sha512(data).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    def sign_manifest(self, manifest_data: bytes) -> bytes:
        """
        Sign manifest data using Ed25519.
        
        Args:
            manifest_data: Manifest data to sign
            
        Returns:
            Digital signature
        """
        return self._signing_key.sign(manifest_data)
    
    def verify_signature(self, signature: bytes, data: bytes, public_key_bytes: bytes) -> bool:
        """
        Verify an Ed25519 signature.
        
        Args:
            signature: Digital signature to verify
            data: Original data that was signed
            public_key_bytes: Public key for verification
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature, data)
            return True
        except Exception:
            return False
    
    def get_public_key(self) -> bytes:
        """Get the public key for signature verification."""
        return self._signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def export_private_key(self) -> bytes:
        """Export the private key for backup/storage."""
        return self._signing_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    @classmethod
    def from_private_key(cls, private_key_bytes: bytes, master_key: Optional[bytes] = None) -> 'SecurityManager':
        """
        Create SecurityManager from existing private key.
        
        Args:
            private_key_bytes: Raw private key bytes
            master_key: Optional master key for encryption
            
        Returns:
            SecurityManager instance
        """
        instance = cls(master_key)
        instance._signing_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        return instance


class KMSSecurityManager(SecurityManager):
    """Extended security manager with KMS/HSM support for customer-managed keys."""
    
    def __init__(self, kms_key_id: Optional[str] = None, master_key: Optional[bytes] = None):
        """
        Initialize KMS-enabled security manager.
        
        Args:
            kms_key_id: External key management system key identifier
            master_key: Optional master key (can be derived from KMS)
        """
        super().__init__(master_key)
        self.kms_key_id = kms_key_id
        # In a real implementation, this would integrate with AWS KMS, Azure Key Vault, etc.
    
    def generate_chunk_key(self, chunk_id: str) -> bytes:
        """Generate chunk key using KMS-derived master key."""
        if self.kms_key_id:
            # Placeholder for KMS integration
            # In practice, this would call KMS to derive the key
            kms_derived_key = self._simulate_kms_derive_key(self.kms_key_id, chunk_id)
            return kms_derived_key
        return super().generate_chunk_key(chunk_id)
    
    def _simulate_kms_derive_key(self, kms_key_id: str, chunk_id: str) -> bytes:
        """Simulate KMS key derivation (placeholder for real KMS integration)."""
        # This would be replaced with actual KMS API calls
        combined = f"{kms_key_id}:{chunk_id}:{self.master_key.hex()}"
        return hashlib.sha256(combined.encode()).digest()