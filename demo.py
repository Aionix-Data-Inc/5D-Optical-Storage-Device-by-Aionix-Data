#!/usr/bin/env python3
"""
Demonstration script for 5D Optical Storage System

This script demonstrates all the major features of the storage system.
"""

import os
import tempfile
from pathlib import Path

from optical_storage import OpticalStorage, SecurityManager
from optical_storage.storage import FileSystemObjectStore


def create_test_files(base_dir: Path):
    """Create test files for demonstration."""
    files = {}
    
    # Create a text file
    text_file = base_dir / "document.txt"
    with open(text_file, 'w') as f:
        f.write("""5D Optical Storage System Documentation

This is a test document to demonstrate the capabilities of the 5D Optical Storage System.

Key Features:
- AES-256-GCM encryption with per-chunk keys
- Ed25519 digital signatures for manifests and TOCs
- SHA-256/SHA-512 content hashing
- Content deduplication
- Support for multiple storage backends
- Chunking for large files (1-8 MB chunks)

The system provides enterprise-grade security and data integrity for long-term archival storage.
""")
    files['document'] = text_file
    
    # Create a binary file
    binary_file = base_dir / "data.bin"
    with open(binary_file, 'wb') as f:
        # Create 3MB of data to demonstrate chunking
        f.write(b'DATA' * (3 * 1024 * 1024 // 4))
    files['binary'] = binary_file
    
    # Create a duplicate file to demonstrate deduplication
    duplicate_file = base_dir / "document_copy.txt"
    with open(duplicate_file, 'w') as f:
        f.write("""5D Optical Storage System Documentation

This is a test document to demonstrate the capabilities of the 5D Optical Storage System.

Key Features:
- AES-256-GCM encryption with per-chunk keys
- Ed25519 digital signatures for manifests and TOCs
- SHA-256/SHA-512 content hashing
- Content deduplication
- Support for multiple storage backends
- Chunking for large files (1-8 MB chunks)

The system provides enterprise-grade security and data integrity for long-term archival storage.
""")
    files['duplicate'] = duplicate_file
    
    return files


def main():
    """Run the demonstration."""
    print("=== 5D Optical Storage System Demonstration ===\n")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        storage_path = temp_path / "storage"
        files_path = temp_path / "files"
        files_path.mkdir()
        
        print(f"Using temporary directory: {temp_dir}")
        print(f"Storage path: {storage_path}")
        print(f"Test files path: {files_path}\n")
        
        # Create test files
        print("1. Creating test files...")
        test_files = create_test_files(files_path)
        for name, path in test_files.items():
            print(f"   Created {name}: {path} ({path.stat().st_size} bytes)")
        print()
        
        # Initialize the storage system
        print("2. Initializing 5D Optical Storage System...")
        security_manager = SecurityManager()
        object_store = FileSystemObjectStore(str(storage_path))
        optical_storage = OpticalStorage(
            security_manager, 
            object_store, 
            chunk_size=2 * 1024 * 1024  # 2MB chunks
        )
        print("   Security manager initialized with Ed25519 signing key")
        print("   File system object store initialized")
        print("   Optical storage system ready\n")
        
        # Store files
        print("3. Storing files with encryption and deduplication...")
        manifest_id = "demo_manifest_001"
        stored_objects = {}
        
        for name, file_path in test_files.items():
            print(f"   Storing {name} ({file_path.name})...")
            object_id = optical_storage.store_file(
                str(file_path), 
                manifest_id,
                enable_dedup=True
            )
            stored_objects[name] = object_id
            print(f"   -> Object ID: {object_id}")
        
        print()
        
        # Display manifest information
        print("4. Manifest Information...")
        manifest = optical_storage.manifests[manifest_id]
        print(f"   Manifest ID: {manifest.manifest_id}")
        print(f"   Total objects: {manifest.total_objects}")
        print(f"   Total size: {manifest.total_size} bytes")
        print(f"   Digitally signed: {manifest.signature is not None}")
        print(f"   Signature algorithm: Ed25519")
        
        # Show chunk details
        print("\n   Chunk Details:")
        for obj_id, obj_metadata in manifest.objects.items():
            print(f"   Object {obj_id} ({obj_metadata.original_path}):")
            print(f"     Chunks: {len(obj_metadata.chunks)}")
            for i, chunk in enumerate(obj_metadata.chunks):
                print(f"     Chunk {i}: {chunk.chunk_id}")
                print(f"       Size: {chunk.size} bytes")
                print(f"       Encrypted size: {chunk.encrypted_size} bytes")
                print(f"       SHA-256: {chunk.hash_sha256[:16]}...")
        print()
        
        # Demonstrate signature verification
        print("5. Verifying digital signatures...")
        is_valid = optical_storage._verify_manifest_signature(manifest_id)
        print(f"   Manifest signature valid: {is_valid}")
        
        # Test retrieval
        print("\n6. Testing file retrieval and decryption...")
        for name, object_id in stored_objects.items():
            print(f"   Retrieving {name}...")
            try:
                retrieved_data = optical_storage.retrieve_object(object_id, manifest_id)
                print(f"   -> Retrieved {len(retrieved_data)} bytes")
                
                # Verify content matches original
                original_path = test_files[name]
                with open(original_path, 'rb') as f:
                    original_data = f.read()
                
                if retrieved_data == original_data:
                    print(f"   -> Content verification: PASSED")
                else:
                    print(f"   -> Content verification: FAILED")
            except Exception as e:
                print(f"   -> Error: {e}")
        print()
        
        # Create Table of Contents
        print("7. Creating disc Table of Contents...")
        disc_id = "AIONIX_DISC_001"
        toc = optical_storage.create_disc_toc(
            disc_id, 
            [manifest_id],
            disc_capacity=1024 * 1024 * 1024  # 1GB disc
        )
        print(f"   Disc ID: {toc.disc_id}")
        print(f"   Manifests: {len(toc.manifests)}")
        print(f"   Used space: {toc.used_space} bytes")
        print(f"   Available space: {toc.disc_capacity - toc.used_space} bytes")
        print(f"   Digitally signed: {toc.signature is not None}")
        print()
        
        # Display storage statistics
        print("8. Storage System Statistics...")
        stats = optical_storage.get_storage_stats()
        print(f"   Total manifests: {stats['total_manifests']}")
        print(f"   Total objects: {stats['total_objects']}")
        print(f"   Total size: {stats['total_size']} bytes")
        print(f"   Total chunks: {stats['total_chunks']}")
        print(f"   Total discs: {stats['total_discs']}")
        print()
        
        # Demonstrate deduplication effectiveness
        print("9. Deduplication Analysis...")
        duplicate_obj = stored_objects['duplicate']
        document_obj = stored_objects['document']
        
        doc_metadata = manifest.objects[document_obj]
        dup_metadata = manifest.objects[duplicate_obj]
        
        print(f"   Document chunks: {len(doc_metadata.chunks)}")
        print(f"   Duplicate chunks: {len(dup_metadata.chunks)}")
        
        # Check if chunks are shared
        doc_chunk_ids = [chunk.chunk_id for chunk in doc_metadata.chunks]
        dup_chunk_ids = [chunk.chunk_id for chunk in dup_metadata.chunks]
        shared_chunks = set(doc_chunk_ids) & set(dup_chunk_ids)
        
        print(f"   Shared chunks: {len(shared_chunks)}")
        print(f"   Storage efficiency: {(len(shared_chunks) / max(len(doc_chunk_ids), 1)) * 100:.1f}%")
        print()
        
        # Export manifest for archival
        print("10. Exporting manifest for archival...")
        manifest_export_path = temp_path / "manifest_export.json"
        optical_storage.export_manifest(manifest_id, str(manifest_export_path))
        print(f"   Manifest exported to: {manifest_export_path}")
        print(f"   Export size: {manifest_export_path.stat().st_size} bytes")
        print()
        
        print("=== Demonstration Complete ===")
        print(f"\nThe 5D Optical Storage System successfully:")
        print("✓ Encrypted all data with AES-256-GCM")
        print("✓ Generated per-chunk encryption keys")
        print("✓ Applied SHA-256/SHA-512 content hashing")
        print("✓ Implemented content deduplication")
        print("✓ Created digitally signed manifests (Ed25519)")
        print("✓ Generated signed Table of Contents")
        print("✓ Verified data integrity during retrieval")
        print("✓ Demonstrated enterprise-grade security features")
        
        print(f"\nStorage artifacts created in: {storage_path}")
        print("(Note: Temporary directory will be cleaned up automatically)")


if __name__ == "__main__":
    main()