"""
5D Optical Storage Device Encryption Package

This package provides AES-256-GCM encryption with per-chunk keys for Aionix's
5D optical storage device. It supports optional customer-managed keys through
KMS/HSM integration.

Features:
- AES-256-GCM encryption with per-chunk unique keys
- Support for AWS KMS, Azure Key Vault, and Google Cloud KMS
- Configurable chunk sizes for optimal storage
- Command-line interface for easy operation
- Comprehensive error handling and validation
"""

from .optical_encryption import (
    OpticalStorageEncryption,
    EncryptionConfig,
    KeySource,
    ChunkMetadata
)

from .config_manager import (
    ConfigManager,
    create_sample_configs
)

__version__ = "1.0.0"
__author__ = "Aionix Data Systems"
__email__ = "support@aionix.data"

__all__ = [
    "OpticalStorageEncryption",
    "EncryptionConfig", 
    "KeySource",
    "ChunkMetadata",
    "ConfigManager",
    "create_sample_configs"
]