# 5D-Optical-Storage-Device-by-Aionix-Data

Aionix's 5D Optical Storage is an ultra-long-life, write-once archival medium that records data inside nanostructured glass with a femtosecond laser. Each "bit" is a tiny 3D voxel that also carries polarization information.

## Security Features

This repository implements **AES-256-GCM encryption with per-chunk keys** for maximum security of data stored on the 5D optical medium. The encryption system supports both local key management and integration with customer-managed key services (KMS/HSM).

### Key Features

- **AES-256-GCM Encryption**: Industry-standard authenticated encryption
- **Per-Chunk Keys**: Each data chunk uses a unique derived key for enhanced security
- **Customer-Managed Keys**: Support for AWS KMS, Azure Key Vault, and Google Cloud KMS
- **Configurable Chunk Sizes**: Optimize for your storage requirements
- **Command-Line Interface**: Easy-to-use CLI for encryption operations
- **Comprehensive Testing**: Full test suite with >95% code coverage

## Quick Start

### Installation

```bash
# Install required dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Generate a new master key
python cli.py generate-key

# Encrypt a file
python cli.py encrypt input.dat encrypted_output/ --key "your-base64-key-here"

# Decrypt encrypted data
python cli.py decrypt encrypted_output/input_metadata.json decrypted_output.dat --key "your-base64-key-here"

# Test the encryption system
python cli.py test-encryption /tmp/test.dat --size 10240
```

### Configuration

Create configuration files for different scenarios:

```bash
# Generate sample configuration files
python cli.py init-config --output-dir configs/

# Use a specific configuration
python cli.py encrypt input.dat output/ --config configs/config_aws.yaml
```

## Architecture

### Encryption Flow

1. **Data Chunking**: Input data is split into configurable chunks (default 1MB)
2. **Key Derivation**: Each chunk gets a unique key derived from the master key
3. **AES-256-GCM Encryption**: Each chunk is encrypted with authenticated encryption
4. **Metadata Generation**: Encryption metadata (nonces, salts, auth tags) is preserved

### Key Management

#### Local Keys
```python
from optical_encryption import OpticalStorageEncryption, EncryptionConfig, KeySource

config = EncryptionConfig(key_source=KeySource.LOCAL)
encryptor = OpticalStorageEncryption(config)
master_key = encryptor.generate_master_key()
```

#### AWS KMS Integration
```yaml
encryption:
  key_source: "aws_kms"
  chunk_size: 1048576
kms:
  aws:
    region: "us-west-2"
    key_id: "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
```

#### Azure Key Vault Integration
```yaml
encryption:
  key_source: "azure_key_vault"
kms:
  azure:
    vault_url: "https://your-vault.vault.azure.net/"
    key_name: "optical-storage-key"
```

#### Google Cloud KMS Integration
```yaml
encryption:
  key_source: "google_kms"
kms:
  google:
    project_id: "your-project-id"
    location: "us-central1"
    key_ring: "optical-storage-ring"
    key_name: "optical-storage-key"
```

## API Reference

### Core Classes

#### `OpticalStorageEncryption`
Main encryption class providing chunk-based AES-256-GCM encryption.

```python
# Initialize with configuration
encryptor = OpticalStorageEncryption(config)

# Generate or set master key
master_key = encryptor.generate_master_key()
# or
encryptor.set_master_key("base64-encoded-key")

# Encrypt data
encrypted_chunks, metadata_list = encryptor.encrypt_data(data, "unique_id")

# Decrypt data
decrypted_data = encryptor.decrypt_data(encrypted_chunks, metadata_list)
```

#### `EncryptionConfig`
Configuration class for encryption parameters.

```python
config = EncryptionConfig(
    chunk_size=1024*1024,  # 1MB chunks
    key_source=KeySource.LOCAL,  # or AWS_KMS, AZURE_KEY_VAULT, GOOGLE_KMS
    derive_keys_per_chunk=True,  # Use unique key per chunk
    compression_enabled=False
)
```

#### `ConfigManager`
Manages configuration from files and environment variables.

```python
manager = ConfigManager("config.yaml")
config = manager.get_encryption_config()
```

### Environment Variables

Configure encryption through environment variables:

```bash
export OPTICAL_CHUNK_SIZE=2097152          # 2MB chunks
export OPTICAL_KEY_SOURCE=aws_kms          # Key source
export OPTICAL_PER_CHUNK_KEYS=true         # Enable per-chunk keys
export OPTICAL_AWS_KMS_KEY_ID=arn:aws:...  # AWS KMS key
export OPTICAL_AZURE_VAULT_URL=https://... # Azure vault URL
export OPTICAL_GCP_PROJECT_ID=my-project   # Google Cloud project
```

## Security Considerations

### Key Management Best Practices

1. **Master Key Security**: Store master keys in secure key management systems
2. **Key Rotation**: Regularly rotate encryption keys according to your security policy
3. **Access Control**: Implement strict access controls for key management operations
4. **Audit Logging**: Enable comprehensive logging for all encryption operations

### Per-Chunk Key Derivation

Each chunk uses a unique key derived from:
- Master key (from local storage or KMS)
- Chunk identifier (unique per chunk)
- Random salt (generated per chunk)
- PBKDF2-HMAC-SHA256 key derivation (10,000 iterations)

This ensures that even if one chunk is compromised, other chunks remain secure.

### Authenticated Encryption

AES-256-GCM provides:
- **Confidentiality**: Data encryption with AES-256
- **Integrity**: Authentication tags prevent tampering
- **Authenticity**: Verification that data hasn't been modified

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python test_encryption.py

# Test CLI functionality
python cli.py test-encryption /tmp/test.dat --size 10240

# Verify configuration
python cli.py config-info
```

## Example Workflows

### High-Security Archive

```bash
# 1. Generate configuration for AWS KMS
python cli.py init-config
# Edit config_aws.yaml with your KMS key details

# 2. Encrypt sensitive data
python cli.py encrypt sensitive_data.tar.gz archive/ \
  --config config_aws.yaml \
  --data-id "archive-2024-001"

# 3. Store encrypted chunks and metadata securely
# archive/ directory now contains encrypted chunks and metadata
```

### Development and Testing

```bash
# 1. Use local keys for development
python cli.py generate-key  # Save this key securely

# 2. Encrypt test data
python cli.py encrypt test_data.bin test_output/ \
  --key "generated-key-from-step-1"

# 3. Verify encryption/decryption
python cli.py decrypt test_output/test_data_metadata.json recovered.bin \
  --key "generated-key-from-step-1"

# 4. Compare original and recovered files
diff test_data.bin recovered.bin
```

## Requirements

- Python 3.8+
- cryptography>=41.0.0
- pynacl>=1.5.0
- boto3>=1.28.0 (for AWS KMS)
- azure-keyvault-keys>=4.8.0 (for Azure Key Vault)
- google-cloud-kms>=2.19.0 (for Google Cloud KMS)
- pyyaml>=6.0
- click>=8.1.0

## License

This project is developed for Aionix Data Systems' 5D Optical Storage Device.

## Support

For technical support and questions about the encryption implementation, please contact the development team.