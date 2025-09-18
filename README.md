# 5D-Optical-Storage-Device-by-Aionix-Data

Aionix's 5D Optical Storage is an ultra-long-life, write-once archival medium that records data inside nanostructured glass with a femtosecond laser. Each "bit" is a tiny 3D voxel that also carries polarization information.

## Implementation

This repository contains a comprehensive implementation of a 5D Optical Storage System with advanced security and data integrity features.

### Features

#### Ingest & Packaging
- **Object store abstraction**: Support for files, tar/zip archives, and S3-like operations
- **Pre-encryption staging**: Optional content deduplication and chunking (1-8 MB chunks)
- **Content hashing**: SHA-256/SHA-512 hashing at both file-level and chunk-level
- **Chunking**: Efficient handling of large files with configurable chunk sizes

#### Security
- **Encryption**: AES-256-GCM with per-chunk keys for maximum security
- **Customer-managed keys**: Optional integration with KMS/HSM systems
- **Digital signatures**: Ed25519 signatures for manifests and per-disc Table of Contents (TOC)
- **Data integrity**: Comprehensive hash verification and signature validation

### Architecture

The system consists of several key components:

1. **SecurityManager**: Handles encryption, decryption, hashing, and digital signatures
2. **ObjectStore**: Abstraction layer for storage backends (filesystem, S3-compatible)
3. **DataIngestionEngine**: Manages chunking, deduplication, and encryption
4. **OpticalStorage**: Main orchestration class with manifest and TOC management

### Quick Start

```python
from optical_storage import OpticalStorage, SecurityManager
from optical_storage.storage import FileSystemObjectStore

# Initialize the storage system
security_manager = SecurityManager()
object_store = FileSystemObjectStore("./storage")
storage = OpticalStorage(security_manager, object_store)

# Store a file
object_id = storage.store_file("document.pdf")

# Retrieve the file
manifest_id = list(storage.manifests.keys())[0]
data = storage.retrieve_object(object_id, manifest_id)
```

### Command Line Interface

The system includes a CLI for easy interaction:

```bash
# Store a file
python cli.py --storage-path ./storage store-file document.pdf

# Store an archive
python cli.py --storage-path ./storage store-archive backup.tar.gz

# Show statistics
python cli.py --storage-path ./storage stats --detailed

# Create disc Table of Contents
python cli.py --storage-path ./storage create-toc disc_001
```

### Running the Demo

See the complete system in action:

```bash
python demo.py
```

This will demonstrate:
- File ingestion with chunking
- AES-256-GCM encryption with per-chunk keys
- Content deduplication
- Digital signature creation and verification
- Manifest and TOC generation
- Data integrity verification

### Testing

Run the comprehensive test suite:

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

### Installation

```bash
pip install -r requirements.txt
# Or install in development mode
pip install -e .
```

### Requirements

- Python 3.8+
- cryptography >= 41.0.0
- boto3 >= 1.28.0 (for S3 support)
- pynacl >= 1.5.0 (for Ed25519 signatures)

### Security Features

- **AES-256-GCM**: Industry-standard authenticated encryption
- **Per-chunk keys**: Unique encryption keys for each data chunk
- **Ed25519**: Modern elliptic curve digital signatures
- **Content hashing**: SHA-256/SHA-512 for data integrity
- **Deduplication**: Content-based deduplication to save storage space
- **Signed manifests**: Tamper-evident storage catalogs
- **Signed TOCs**: Per-disc verification of contents

### Use Cases

- **Long-term archival**: Ultra-durable storage for critical data
- **Compliance**: Tamper-evident storage for regulatory requirements
- **Data centers**: Secure backup and archival solutions
- **Research**: Preservation of scientific data and research results
- **Enterprise**: High-security document and data archival