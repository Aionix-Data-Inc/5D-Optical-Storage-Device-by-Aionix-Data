# 5D-Optical-Storage-Device-by-Aionix-Data

Aionix's 5D Optical Storage is an ultra-long-life, write-once archival medium that records data inside nanostructured glass with a femtosecond laser. Each "bit" is a tiny 3D voxel that also carries polarization information.

## Object Store Abstraction

This repository provides a unified object store abstraction that supports multiple storage backends, designed to work seamlessly with 5D optical storage systems. The abstraction layer enables transparent data operations across different storage types.

### Supported Storage Backends

- **FileSystem Store**: Local file system storage with metadata support
- **Archive Store**: TAR and ZIP archive formats for bundled storage
- **S3 Store**: S3-compatible cloud storage integration

### Installation

```bash
# Basic installation
pip install -r requirements.txt

# For S3 support
pip install boto3
```

### Quick Start

```python
from aionix_storage import create_store

# Create a filesystem store
store = create_store('filesystem', base_path='/path/to/storage')

# Store 5D optical voxel data
voxel_data = b"5D optical voxel with polarization data"
metadata = {
    "polarization": "circular",
    "wavelength": "1030nm", 
    "power": "0.2TW/cm²"
}

store.put("voxel_001", voxel_data, metadata)

# Retrieve data
data = store.get("voxel_001")
meta = store.get_metadata("voxel_001")
```

### Examples

See the `examples/demo.py` script for comprehensive usage demonstrations.

### Storage Backend Configuration

#### FileSystem Store
```python
store = create_store('filesystem', base_path='/storage/path')
```

#### Archive Store (TAR/ZIP)
```python
# TAR archive
store = create_store('archive', 
                    archive_path='/path/data.tar.gz',
                    archive_type='tar.gz')

# ZIP archive  
store = create_store('archive',
                    archive_path='/path/data.zip', 
                    archive_type='zip')
```

#### S3-Compatible Store
```python
store = create_store('s3',
                    bucket_name='my-5d-storage',
                    aws_access_key_id='ACCESS_KEY',
                    aws_secret_access_key='SECRET_KEY',
                    region_name='us-west-2')
```

### API Reference

All storage backends implement the same `ObjectStore` interface:

- `put(key, data, metadata=None)` - Store object with optional metadata
- `get(key)` - Retrieve object data
- `exists(key)` - Check if object exists
- `delete(key)` - Delete object
- `list_keys(prefix="")` - List stored object keys
- `get_metadata(key)` - Get object metadata
- `put_file(key, file_path, metadata=None)` - Store file
- `get_file(key, file_path)` - Retrieve to file

### Testing

Run the test suite:
```bash
python tests/test_stores.py
```

Run the demo:
```bash
python examples/demo.py
```