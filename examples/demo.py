#!/usr/bin/env python3
"""
Example usage of the Aionix 5D Optical Storage Object Store abstraction.

This script demonstrates how to use different storage backends
with a unified interface.
"""

import json
import tempfile
from pathlib import Path
import sys
import os

# Add the parent directory to the path to import aionix_storage
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aionix_storage import create_store, FileSystemStore, ArchiveStore


def demonstrate_filesystem_store():
    """Demonstrate filesystem store usage."""
    print("=== FileSystem Store Demo ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a filesystem store
        store = create_store('filesystem', base_path=temp_dir)
        
        # Store some 5D optical data
        voxel_data = b"5D optical voxel data with polarization info"
        metadata = {
            "polarization": "circular",
            "wavelength": "1030nm",
            "power": "0.2TW/cm²",
            "type": "5D_optical_voxel"
        }
        
        store.put("voxel_001", voxel_data, metadata)
        store.put("voxel_002", b"Another voxel with different properties")
        
        # Retrieve and display
        retrieved_data = store.get("voxel_001")
        retrieved_metadata = store.get_metadata("voxel_001")
        
        print(f"Stored data: {retrieved_data}")
        print(f"Metadata: {json.dumps(retrieved_metadata, indent=2)}")
        
        # List all keys
        keys = store.list_keys()
        print(f"All stored voxels: {keys}")
        
        print()


def demonstrate_archive_store():
    """Demonstrate archive store usage."""
    print("=== Archive Store Demo ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        archive_path = Path(temp_dir) / "5d_optical_data.tar.gz"
        
        # Create a compressed tar archive store
        store = create_store('archive', archive_path=archive_path, archive_type='tar.gz')
        
        # Store multiple voxels in the archive
        voxel_collection = {
            "layer_1_voxel_001": b"First layer voxel data",
            "layer_1_voxel_002": b"Second voxel in first layer",
            "layer_2_voxel_001": b"First voxel in second layer",
        }
        
        for key, data in voxel_collection.items():
            metadata = {
                "layer": key.split('_')[1],
                "position": key.split('_')[3],
                "type": "5D_optical_layer"
            }
            store.put(key, data, metadata)
        
        # Verify data persistence by reopening the archive
        store2 = ArchiveStore(archive_path, 'tar.gz')
        keys = store2.list_keys()
        print(f"Voxels in archive: {keys}")
        
        # Retrieve a specific voxel
        layer_1_data = store2.get("layer_1_voxel_001")
        layer_1_metadata = store2.get_metadata("layer_1_voxel_001")
        
        print(f"Layer 1 voxel data: {layer_1_data}")
        print(f"Layer 1 metadata: {json.dumps(layer_1_metadata, indent=2)}")
        
        print(f"Archive size: {archive_path.stat().st_size} bytes")
        print()


def demonstrate_unified_interface():
    """Demonstrate using the same interface for different stores."""
    print("=== Unified Interface Demo ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create different store types
        stores = {
            "filesystem": create_store('filesystem', base_path=temp_dir + "/fs"),
            "tar_archive": create_store('archive', 
                                     archive_path=Path(temp_dir) / "data.tar",
                                     archive_type='tar'),
            "zip_archive": create_store('archive', 
                                     archive_path=Path(temp_dir) / "data.zip",
                                     archive_type='zip')
        }
        
        # Same operations on all stores
        test_data = b"Universal 5D optical storage test"
        test_metadata = {"format": "5D_optical", "test": True}
        
        for store_name, store in stores.items():
            print(f"Testing {store_name} store:")
            
            # Store data
            store.put("test_voxel", test_data, test_metadata)
            
            # Verify storage
            assert store.exists("test_voxel")
            retrieved_data = store.get("test_voxel")
            assert retrieved_data == test_data
            
            # Get metadata
            metadata = store.get_metadata("test_voxel")
            print(f"  Stored successfully, size: {metadata['size']} bytes")
        
        print("All stores work with the same interface!")
        print()


def demonstrate_file_operations():
    """Demonstrate file-based operations."""
    print("=== File Operations Demo ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        store = create_store('filesystem', base_path=temp_dir + "/files")
        
        # Create a test file
        test_file = Path(temp_dir) / "5d_sample.dat"
        test_file.write_bytes(b"5D optical storage sample file content")
        
        # Store the file
        store.put_file("sample_file", test_file, {"source": "lab_experiment"})
        
        # Retrieve to a new file
        output_file = Path(temp_dir) / "retrieved_sample.dat"
        store.get_file("sample_file", output_file)
        
        # Verify content matches
        original_content = test_file.read_bytes()
        retrieved_content = output_file.read_bytes()
        
        assert original_content == retrieved_content
        print("File operations successful!")
        print(f"Original size: {len(original_content)} bytes")
        print(f"Retrieved size: {len(retrieved_content)} bytes")
        print()


def main():
    """Run all demonstrations."""
    print("Aionix 5D Optical Storage - Object Store Abstraction Demo")
    print("=" * 60)
    print()
    
    try:
        demonstrate_filesystem_store()
        demonstrate_archive_store()
        demonstrate_unified_interface()
        demonstrate_file_operations()
        
        print("All demonstrations completed successfully!")
        print("The object store abstraction provides a unified interface")
        print("for different storage backends suitable for 5D optical storage systems.")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())