#!/usr/bin/env python3
"""
Command-line interface for 5D Optical Storage System

Provides a CLI for interacting with the storage system.
"""

import argparse
import json
import sys
from pathlib import Path
from optical_storage import OpticalStorage, SecurityManager
from optical_storage.storage import FileSystemObjectStore


def create_storage_system(storage_path: str, master_key: str = None) -> OpticalStorage:
    """Create and initialize the optical storage system."""
    # Initialize security manager
    if master_key:
        master_key_bytes = master_key.encode('utf-8')[:32].ljust(32, b'\0')
    else:
        master_key_bytes = None
    
    security_manager = SecurityManager(master_key_bytes)
    
    # Initialize object store
    object_store = FileSystemObjectStore(storage_path)
    
    # Initialize optical storage system
    return OpticalStorage(security_manager, object_store)


def cmd_store_file(args):
    """Store a file in the optical storage system."""
    storage = create_storage_system(args.storage_path, args.master_key)
    
    try:
        object_id = storage.store_file(
            args.file_path, 
            args.manifest_id, 
            enable_dedup=not args.no_dedup
        )
        print(f"Successfully stored file: {args.file_path}")
        print(f"Object ID: {object_id}")
        
        # Print manifest information
        manifest_id = args.manifest_id or list(storage.manifests.keys())[-1]
        manifest = storage.manifests[manifest_id]
        print(f"Manifest ID: {manifest_id}")
        print(f"Total objects in manifest: {manifest.total_objects}")
        print(f"Total size: {manifest.total_size} bytes")
        
    except Exception as e:
        print(f"Error storing file: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_store_archive(args):
    """Store an archive in the optical storage system."""
    storage = create_storage_system(args.storage_path, args.master_key)
    
    try:
        object_id = storage.store_archive(
            args.archive_path,
            args.archive_type,
            args.manifest_id,
            enable_dedup=not args.no_dedup
        )
        print(f"Successfully stored archive: {args.archive_path}")
        print(f"Object ID: {object_id}")
        
        # Print manifest information
        manifest_id = args.manifest_id or list(storage.manifests.keys())[-1]
        manifest = storage.manifests[manifest_id]
        print(f"Manifest ID: {manifest_id}")
        print(f"Total objects in manifest: {manifest.total_objects}")
        print(f"Total size: {manifest.total_size} bytes")
        
    except Exception as e:
        print(f"Error storing archive: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_retrieve_object(args):
    """Retrieve an object from the optical storage system."""
    storage = create_storage_system(args.storage_path, args.master_key)
    
    try:
        # Load manifest if needed
        if args.manifest_file:
            manifest_id = storage.import_manifest(args.manifest_file)
        else:
            manifest_id = args.manifest_id
        
        if not manifest_id:
            print("Error: Manifest ID or manifest file required", file=sys.stderr)
            sys.exit(1)
        
        # Retrieve object
        data = storage.retrieve_object(args.object_id, manifest_id)
        
        # Output to file or stdout
        if args.output_file:
            with open(args.output_file, 'wb') as f:
                f.write(data)
            print(f"Object retrieved and saved to: {args.output_file}")
        else:
            # Output to stdout (for text files)
            try:
                print(data.decode('utf-8'))
            except UnicodeDecodeError:
                print("Binary data retrieved (use --output-file to save)", file=sys.stderr)
                sys.exit(1)
        
    except Exception as e:
        print(f"Error retrieving object: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_create_toc(args):
    """Create a Table of Contents for a disc."""
    storage = create_storage_system(args.storage_path, args.master_key)
    
    try:
        # Load manifests if needed
        manifest_ids = []
        if args.manifest_files:
            for manifest_file in args.manifest_files:
                manifest_id = storage.import_manifest(manifest_file)
                manifest_ids.append(manifest_id)
        elif args.manifest_ids:
            manifest_ids = args.manifest_ids
        else:
            # Use all available manifests
            manifest_ids = list(storage.manifests.keys())
        
        if not manifest_ids:
            print("Error: No manifests available", file=sys.stderr)
            sys.exit(1)
        
        # Create TOC
        toc = storage.create_disc_toc(args.disc_id, manifest_ids, args.disc_capacity)
        
        print(f"Successfully created TOC for disc: {args.disc_id}")
        print(f"Manifests included: {len(toc.manifests)}")
        print(f"Used space: {toc.used_space} bytes")
        print(f"Available space: {toc.disc_capacity - toc.used_space} bytes")
        
        # Export TOC if requested
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(toc.to_json())
            print(f"TOC exported to: {args.output_file}")
        
    except Exception as e:
        print(f"Error creating TOC: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_export_manifest(args):
    """Export a manifest to a file."""
    storage = create_storage_system(args.storage_path, args.master_key)
    
    try:
        storage.export_manifest(args.manifest_id, args.output_file)
        print(f"Manifest exported to: {args.output_file}")
        
    except Exception as e:
        print(f"Error exporting manifest: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stats(args):
    """Show storage system statistics."""
    storage = create_storage_system(args.storage_path, args.master_key)
    
    try:
        stats = storage.get_storage_stats()
        
        print("=== 5D Optical Storage Statistics ===")
        print(f"Total Manifests: {stats['total_manifests']}")
        print(f"Total Objects: {stats['total_objects']}")
        print(f"Total Size: {stats['total_size']} bytes")
        print(f"Total Chunks: {stats['total_chunks']}")
        print(f"Total Discs: {stats['total_discs']}")
        
        if args.detailed:
            print("\n=== Manifest Details ===")
            for manifest_id, info in stats['manifests'].items():
                print(f"Manifest {manifest_id}:")
                print(f"  Objects: {info['objects']}")
                print(f"  Size: {info['size']} bytes")
                print(f"  Signed: {info['signed']}")
        
    except Exception as e:
        print(f"Error getting statistics: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="5D Optical Storage System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Store a file
  python cli.py store-file /path/to/file.txt --storage-path ./storage

  # Store an archive
  python cli.py store-archive /path/to/archive.tar.gz --storage-path ./storage

  # Retrieve an object
  python cli.py retrieve --object-id abc123 --manifest-id manifest_001 --storage-path ./storage

  # Create disc TOC
  python cli.py create-toc --disc-id disc_001 --storage-path ./storage

  # Show statistics
  python cli.py stats --storage-path ./storage --detailed
        """
    )
    
    parser.add_argument('--storage-path', required=True,
                       help='Path to storage directory')
    parser.add_argument('--master-key', 
                       help='Master encryption key (optional)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Store file command
    store_file_parser = subparsers.add_parser('store-file', help='Store a file')
    store_file_parser.add_argument('file_path', help='Path to file to store')
    store_file_parser.add_argument('--manifest-id', help='Manifest ID (auto-generated if not provided)')
    store_file_parser.add_argument('--no-dedup', action='store_true', 
                                  help='Disable content deduplication')
    store_file_parser.set_defaults(func=cmd_store_file)
    
    # Store archive command
    store_archive_parser = subparsers.add_parser('store-archive', help='Store an archive')
    store_archive_parser.add_argument('archive_path', help='Path to archive to store')
    store_archive_parser.add_argument('--archive-type', default='auto',
                                     choices=['auto', 'tar', 'zip'],
                                     help='Archive type')
    store_archive_parser.add_argument('--manifest-id', help='Manifest ID (auto-generated if not provided)')
    store_archive_parser.add_argument('--no-dedup', action='store_true',
                                     help='Disable content deduplication')
    store_archive_parser.set_defaults(func=cmd_store_archive)
    
    # Retrieve object command
    retrieve_parser = subparsers.add_parser('retrieve', help='Retrieve an object')
    retrieve_parser.add_argument('object_id', help='Object ID to retrieve')
    retrieve_parser.add_argument('--manifest-id', help='Manifest ID containing the object')
    retrieve_parser.add_argument('--manifest-file', help='Path to manifest file')
    retrieve_parser.add_argument('--output-file', help='Output file path (stdout if not provided)')
    retrieve_parser.set_defaults(func=cmd_retrieve_object)
    
    # Create TOC command
    toc_parser = subparsers.add_parser('create-toc', help='Create disc Table of Contents')
    toc_parser.add_argument('disc_id', help='Disc identifier')
    toc_parser.add_argument('--manifest-ids', nargs='+', help='Manifest IDs to include')
    toc_parser.add_argument('--manifest-files', nargs='+', help='Manifest files to include')
    toc_parser.add_argument('--disc-capacity', type=int, 
                           default=1024*1024*1024*1024,  # 1TB
                           help='Disc capacity in bytes')
    toc_parser.add_argument('--output-file', help='Export TOC to file')
    toc_parser.set_defaults(func=cmd_create_toc)
    
    # Export manifest command
    export_parser = subparsers.add_parser('export-manifest', help='Export a manifest')
    export_parser.add_argument('manifest_id', help='Manifest ID to export')
    export_parser.add_argument('output_file', help='Output file path')
    export_parser.set_defaults(func=cmd_export_manifest)
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show storage statistics')
    stats_parser.add_argument('--detailed', action='store_true',
                             help='Show detailed manifest information')
    stats_parser.set_defaults(func=cmd_stats)
    
    # Parse arguments and execute command
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()