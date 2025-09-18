"""
Configuration management for 5D Optical Storage Encryption.

This module provides configuration management for different encryption
scenarios including local keys and customer-managed keys.
"""

import os
import json
import yaml
from typing import Dict, Optional, Any
from pathlib import Path

try:
    from .optical_encryption import EncryptionConfig, KeySource
except ImportError:
    from optical_encryption import EncryptionConfig, KeySource


class ConfigManager:
    """Manages encryption configuration for the 5D optical storage device."""
    
    DEFAULT_CONFIG = {
        "encryption": {
            "chunk_size": 1048576,  # 1MB
            "key_source": "local",
            "derive_keys_per_chunk": True,
            "compression_enabled": False
        },
        "kms": {
            "aws": {
                "region": "us-east-1",
                "key_spec": "AES_256"
            },
            "azure": {
                "vault_url": None,
                "key_name": None
            },
            "google": {
                "project_id": None,
                "location": "global",
                "key_ring": None,
                "key_name": None
            }
        },
        "security": {
            "key_rotation_days": 90,
            "audit_logging": True,
            "fail_on_key_unavailable": True
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_path and Path(config_path).exists():
            self.load_config(config_path)
        
        # Load from environment variables
        self._load_from_env()
    
    def load_config(self, config_path: str) -> None:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file (JSON or YAML)
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() in ['.yml', '.yaml']:
                    loaded_config = yaml.safe_load(f)
                else:
                    loaded_config = json.load(f)
            
            # Merge with default configuration
            self._merge_config(self.config, loaded_config)
            
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")
    
    def _merge_config(self, base: Dict, update: Dict) -> None:
        """Recursively merge configuration dictionaries."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Encryption settings
        if chunk_size := os.getenv('OPTICAL_CHUNK_SIZE'):
            self.config['encryption']['chunk_size'] = int(chunk_size)
        
        if key_source := os.getenv('OPTICAL_KEY_SOURCE'):
            self.config['encryption']['key_source'] = key_source
        
        if per_chunk := os.getenv('OPTICAL_PER_CHUNK_KEYS'):
            self.config['encryption']['derive_keys_per_chunk'] = per_chunk.lower() == 'true'
        
        # AWS KMS settings
        if aws_region := os.getenv('AWS_DEFAULT_REGION'):
            self.config['kms']['aws']['region'] = aws_region
        
        if aws_key_id := os.getenv('OPTICAL_AWS_KMS_KEY_ID'):
            self.config['kms']['aws']['key_id'] = aws_key_id
        
        # Azure Key Vault settings
        if azure_vault := os.getenv('OPTICAL_AZURE_VAULT_URL'):
            self.config['kms']['azure']['vault_url'] = azure_vault
        
        if azure_key := os.getenv('OPTICAL_AZURE_KEY_NAME'):
            self.config['kms']['azure']['key_name'] = azure_key
        
        # Google KMS settings
        if gcp_project := os.getenv('OPTICAL_GCP_PROJECT_ID'):
            self.config['kms']['google']['project_id'] = gcp_project
        
        if gcp_location := os.getenv('OPTICAL_GCP_LOCATION'):
            self.config['kms']['google']['location'] = gcp_location
        
        if gcp_key_ring := os.getenv('OPTICAL_GCP_KEY_RING'):
            self.config['kms']['google']['key_ring'] = gcp_key_ring
        
        if gcp_key := os.getenv('OPTICAL_GCP_KEY_NAME'):
            self.config['kms']['google']['key_name'] = gcp_key
    
    def get_encryption_config(self) -> EncryptionConfig:
        """
        Create EncryptionConfig from current configuration.
        
        Returns:
            EncryptionConfig instance
        """
        enc_config = self.config['encryption']
        kms_config = self._get_kms_config()
        
        return EncryptionConfig(
            chunk_size=enc_config['chunk_size'],
            key_source=KeySource(enc_config['key_source']),
            master_key_id=kms_config.get('key_id'),
            kms_config=kms_config,
            derive_keys_per_chunk=enc_config['derive_keys_per_chunk'],
            compression_enabled=enc_config['compression_enabled']
        )
    
    def _get_kms_config(self) -> Dict[str, Any]:
        """Get KMS configuration based on key source."""
        key_source = self.config['encryption']['key_source']
        
        if key_source == 'aws_kms':
            aws_config = self.config['kms']['aws']
            return {
                'region_name': aws_config.get('region', 'us-east-1'),
                'key_id': aws_config.get('key_id')
            }
        
        elif key_source == 'azure_key_vault':
            azure_config = self.config['kms']['azure']
            return {
                'vault_url': azure_config.get('vault_url'),
                'key_name': azure_config.get('key_name')
            }
        
        elif key_source == 'google_kms':
            gcp_config = self.config['kms']['google']
            project_id = gcp_config.get('project_id')
            location = gcp_config.get('location', 'global')
            key_ring = gcp_config.get('key_ring')
            key_name = gcp_config.get('key_name')
            
            if all([project_id, key_ring, key_name]):
                key_path = f"projects/{project_id}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{key_name}"
                return {'key_id': key_path}
        
        return {}
    
    def save_config(self, output_path: str) -> None:
        """
        Save current configuration to file.
        
        Args:
            output_path: Path to save configuration
        """
        output_file = Path(output_path)
        
        try:
            with open(output_file, 'w') as f:
                if output_file.suffix.lower() in ['.yml', '.yaml']:
                    yaml.dump(self.config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(self.config, f, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to save configuration: {e}")
    
    def validate_config(self) -> bool:
        """
        Validate the current configuration.
        
        Returns:
            True if configuration is valid
        
        Raises:
            ValueError: If configuration is invalid
        """
        enc_config = self.config['encryption']
        
        # Validate chunk size
        if enc_config['chunk_size'] <= 0:
            raise ValueError("Chunk size must be positive")
        
        # Validate key source
        try:
            KeySource(enc_config['key_source'])
        except ValueError:
            raise ValueError(f"Invalid key source: {enc_config['key_source']}")
        
        # Validate KMS configuration if needed
        key_source = enc_config['key_source']
        
        if key_source == 'aws_kms':
            aws_config = self.config['kms']['aws']
            if not aws_config.get('key_id'):
                raise ValueError("AWS KMS key ID is required")
        
        elif key_source == 'azure_key_vault':
            azure_config = self.config['kms']['azure']
            if not azure_config.get('vault_url'):
                raise ValueError("Azure Key Vault URL is required")
            if not azure_config.get('key_name'):
                raise ValueError("Azure Key Vault key name is required")
        
        elif key_source == 'google_kms':
            gcp_config = self.config['kms']['google']
            required_fields = ['project_id', 'key_ring', 'key_name']
            for field in required_fields:
                if not gcp_config.get(field):
                    raise ValueError(f"Google KMS {field} is required")
        
        return True
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current configuration.
        
        Returns:
            Configuration summary
        """
        enc_config = self.config['encryption']
        
        summary = {
            "encryption_algorithm": "AES-256-GCM",
            "chunk_size_mb": enc_config['chunk_size'] / (1024 * 1024),
            "key_source": enc_config['key_source'],
            "per_chunk_keys": enc_config['derive_keys_per_chunk'],
            "compression": enc_config['compression_enabled']
        }
        
        # Add KMS-specific info
        key_source = enc_config['key_source']
        if key_source != 'local':
            kms_config = self._get_kms_config()
            summary['kms_configuration'] = {
                'provider': key_source,
                'key_configured': bool(kms_config.get('key_id'))
            }
        
        return summary


def create_sample_configs():
    """Create sample configuration files for different scenarios."""
    
    # Local encryption config
    local_config = {
        "encryption": {
            "chunk_size": 1048576,
            "key_source": "local",
            "derive_keys_per_chunk": True,
            "compression_enabled": False
        }
    }
    
    # AWS KMS config
    aws_config = {
        "encryption": {
            "chunk_size": 2097152,  # 2MB
            "key_source": "aws_kms",
            "derive_keys_per_chunk": True,
            "compression_enabled": True
        },
        "kms": {
            "aws": {
                "region": "us-west-2",
                "key_id": "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
            }
        }
    }
    
    # Azure Key Vault config
    azure_config = {
        "encryption": {
            "chunk_size": 1048576,
            "key_source": "azure_key_vault",
            "derive_keys_per_chunk": True,
            "compression_enabled": False
        },
        "kms": {
            "azure": {
                "vault_url": "https://your-vault.vault.azure.net/",
                "key_name": "optical-storage-key"
            }
        }
    }
    
    # Google KMS config
    google_config = {
        "encryption": {
            "chunk_size": 1048576,
            "key_source": "google_kms",
            "derive_keys_per_chunk": True,
            "compression_enabled": False
        },
        "kms": {
            "google": {
                "project_id": "your-project-id",
                "location": "us-central1",
                "key_ring": "optical-storage-ring",
                "key_name": "optical-storage-key"
            }
        }
    }
    
    configs = {
        "config_local.yaml": local_config,
        "config_aws.yaml": aws_config,
        "config_azure.yaml": azure_config,
        "config_google.yaml": google_config
    }
    
    return configs