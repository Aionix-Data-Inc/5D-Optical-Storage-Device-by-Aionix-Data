# 5D-Optical-Storage-Device-by-Aionix-Data

Aionix's 5D Optical Storage is an ultra-long-life, write-once archival medium that records data inside nanostructured glass with a femtosecond laser. Each "bit" is a tiny 3D voxel that also carries polarization information.

## Object Store Abstraction

This project includes a unified object store abstraction that provides a consistent interface for storing and retrieving data across different storage backends, perfect for managing data for 5D optical storage systems.

### Features

- **Unified Interface**: Single API for file system, archive, and cloud storage
- **Multiple Backends**: Support for local files, tar/zip archives, and S3-compatible storage
- **Metadata Support**: Rich metadata handling across all storage types
- **Flexible Storage**: Easy switching between storage backends
- **No Dependencies**: Core functionality works with Python standard library only

### Supported Storage Backends

1. **File System Storage** - Store data in local directories
2. **Archive Storage** - Store data in TAR or ZIP archives
3. **S3 Storage** - Store data in AWS S3 or S3-compatible services
4. **Mock S3** - In-memory storage for testing

### Quick Start

```python
from object_store import ObjectStore, create_storage

# Create storage backend
storage = create_storage("file:///path/to/storage")
store = ObjectStore(storage)

# Store data
metadata = store.put("my-file.txt", "Hello, 5D Optical Storage!")

# Retrieve data
content = store.get_text("my-file.txt")

# List objects
objects = store.list()
```

### Storage URL Formats

- File system: `file:///path/to/directory`
- TAR archive: `tar:///path/to/archive.tar`
- ZIP archive: `zip:///path/to/archive.zip`
- S3 bucket: `s3://bucket-name`
- Mock S3: `mock-s3://bucket-name`

### Installation

```bash
# Core functionality (no dependencies)
pip install -r requirements.txt

# For S3 support
pip install boto3
```

### Example Usage

See `example.py` for comprehensive usage examples of all storage backends.

```bash
python example.py
```

### Architecture

The object store abstraction consists of:

- `ObjectStore`: Unified client interface
- `StorageBackend`: Abstract base class for storage implementations
- `FileSystemStorage`: Local file system backend
- `ArchiveStorage`: TAR/ZIP archive backend
- `S3Storage`: AWS S3 and compatible services backend
- `ObjectMetadata`: Rich metadata for stored objects

This design allows the 5D optical storage system to seamlessly work with different storage technologies while maintaining a consistent interface for data management.