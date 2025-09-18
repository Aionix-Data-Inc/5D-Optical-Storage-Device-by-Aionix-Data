#!/usr/bin/env python3
"""
Example usage of the 5D Optical Storage Object Store abstraction.

This example demonstrates how to use the unified object store interface
with different storage backends: file system, archives, and S3-compatible storage.
"""

import os
import tempfile
from object_store import ObjectStore, create_storage


def main():
    """Demonstrate object store usage with different backends."""
    
    print("=== 5D Optical Storage Object Store Demo ===\n")
    
    # Create temporary directory for examples
    with tempfile.TemporaryDirectory() as temp_dir:
        
        # Example 1: File System Storage
        print("1. File System Storage Example")
        print("-" * 40)
        
        fs_path = os.path.join(temp_dir, "filesystem")
        fs_backend = create_storage(f"file://{fs_path}")
        fs_store = ObjectStore(fs_backend)
        
        # Store some data
        data1 = "Hello from 5D Optical Storage!"
        metadata1 = fs_store.put("documents/readme.txt", data1, content_type="text/plain")
        print(f"Stored: {metadata1.key} ({metadata1.size} bytes)")
        
        # Store binary data
        binary_data = b"Binary data for optical storage simulation"
        metadata2 = fs_store.put("data/optical_data.bin", binary_data, content_type="application/octet-stream")
        print(f"Stored: {metadata2.key} ({metadata2.size} bytes)")
        
        # Retrieve and display
        retrieved_text = fs_store.get_text("documents/readme.txt")
        print(f"Retrieved text: {retrieved_text}")
        
        # List objects
        objects = fs_store.list()
        print(f"Objects in store: {[obj.key for obj in objects]}")
        print()
        
        # Example 2: Archive Storage (TAR)
        print("2. Archive Storage (TAR) Example")
        print("-" * 40)
        
        tar_path = os.path.join(temp_dir, "storage.tar")
        tar_backend = create_storage(f"tar://{tar_path}")
        tar_store = ObjectStore(tar_backend)
        
        # Store data in archive
        tar_store.put("config/settings.json", '{"version": "1.0", "storage": "5D Optical"}')
        tar_store.put("logs/access.log", "2024-01-01 10:00:00 - Access granted to optical storage")
        
        # List archive contents
        archive_objects = tar_store.list()
        print(f"Archive contents: {[obj.key for obj in archive_objects]}")
        
        # Retrieve from archive
        config = tar_store.get_text("config/settings.json")
        print(f"Config from archive: {config}")
        print()
        
        # Example 3: Archive Storage (ZIP)
        print("3. Archive Storage (ZIP) Example")
        print("-" * 40)
        
        zip_path = os.path.join(temp_dir, "storage.zip")
        zip_backend = create_storage(f"zip://{zip_path}")
        zip_store = ObjectStore(zip_backend)
        
        # Store data in ZIP
        zip_store.put("backup/data1.txt", "Backup data for 5D storage")
        zip_store.put("backup/data2.txt", "More backup data")
        
        # List ZIP contents
        zip_objects = zip_store.list()
        print(f"ZIP contents: {[obj.key for obj in zip_objects]}")
        print()
        
        # Example 4: Mock S3 Storage (for testing)
        print("4. Mock S3 Storage Example")
        print("-" * 40)
        
        mock_s3_backend = create_storage("mock-s3://test-bucket")
        s3_store = ObjectStore(mock_s3_backend)
        
        # Store data in mock S3
        s3_store.put("images/optical_storage.jpg", b"Simulated image data for 5D optical storage")
        s3_store.put("docs/manual.pdf", b"PDF manual for 5D optical storage device")
        
        # List S3 objects
        s3_objects = s3_store.list()
        print(f"S3 objects: {[obj.key for obj in s3_objects]}")
        
        # Demonstrate prefix filtering
        image_objects = s3_store.list(prefix="images/")
        print(f"Image objects: {[obj.key for obj in image_objects]}")
        print()
        
        # Example 5: Object operations
        print("5. Object Operations Example")
        print("-" * 40)
        
        store = ObjectStore(fs_backend)  # Use file system store
        
        # Check existence
        print(f"readme.txt exists: {store.exists('documents/readme.txt')}")
        print(f"nonexistent.txt exists: {store.exists('nonexistent.txt')}")
        
        # Get metadata
        meta = store.get_metadata("documents/readme.txt")
        print(f"Metadata - Size: {meta.size}, ETag: {meta.etag}, Modified: {meta.last_modified}")
        
        # Delete object
        deleted = store.delete("data/optical_data.bin")
        print(f"Deleted optical_data.bin: {deleted}")
        
        # List remaining objects
        remaining = store.list()
        print(f"Remaining objects: {[obj.key for obj in remaining]}")
        print()
        
        print("=== Demo Complete ===")
        print("\nThe 5D Optical Storage Object Store abstraction provides:")
        print("- Unified interface across file system, archive, and cloud storage")
        print("- Metadata support for all storage types")
        print("- Efficient operations for data archival and retrieval")
        print("- Perfect for long-term data storage in optical storage devices")


if __name__ == "__main__":
    main()