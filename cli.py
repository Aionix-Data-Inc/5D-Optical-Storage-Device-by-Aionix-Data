#!/usr/bin/env python3
"""
Command-line interface for 5D Optical Storage Device Encryption.

This CLI provides encryption and decryption capabilities for Aionix's
5D optical storage device with AES-256-GCM and customer-managed keys.
"""

import os
import sys
import json
import base64
from pathlib import Path
from typing import Optional

import click

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optical_encryption import OpticalStorageEncryption, EncryptionConfig, KeySource, ChunkMetadata
from config_manager import ConfigManager


@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """5D Optical Storage Device Encryption CLI."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config_manager'] = ConfigManager(config)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_dir', type=click.Path())
@click.option('--data-id', help='Unique identifier for the data')
@click.option('--key', help='Master key (base64 encoded or password)')
@click.option('--generate-key', is_flag=True, help='Generate a new master key')
@click.pass_context
def encrypt(ctx, input_file, output_dir, data_id, key, generate_key):
    """Encrypt a file for 5D optical storage."""
    verbose = ctx.obj['verbose']
    config_manager = ctx.obj['config_manager']
    
    try:
        # Validate configuration
        config_manager.validate_config()
        encryption_config = config_manager.get_encryption_config()
        
        # Initialize encryption
        encryptor = OpticalStorageEncryption(encryption_config)
        
        # Handle key management
        if generate_key:
            master_key = encryptor.generate_master_key()
            key_b64 = base64.b64encode(master_key).decode('utf-8')
            click.echo(f"Generated master key: {key_b64}")
            click.echo("IMPORTANT: Save this key securely. You'll need it for decryption.")
        elif key:
            encryptor.set_master_key(key)
        elif encryption_config.key_source == KeySource.LOCAL:
            click.echo("Error: Master key required for local encryption")
            sys.exit(1)
        
        # Read input file
        with open(input_file, 'rb') as f:
            data = f.read()
        
        if verbose:
            click.echo(f"Read {len(data)} bytes from {input_file}")
        
        # Generate data ID if not provided
        if not data_id:
            data_id = Path(input_file).stem
        
        # Encrypt data
        encrypted_chunks, metadata_list = encryptor.encrypt_data(data, data_id)
        
        if verbose:
            click.echo(f"Encrypted into {len(encrypted_chunks)} chunks")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save encrypted chunks
        chunk_files = []
        for i, chunk in enumerate(encrypted_chunks):
            chunk_file = output_path / f"{data_id}_chunk_{i}.enc"
            with open(chunk_file, 'wb') as f:
                f.write(chunk)
            chunk_files.append(str(chunk_file))
        
        # Save metadata
        metadata_dict = []
        for metadata in metadata_list:
            metadata_dict.append({
                'chunk_id': metadata.chunk_id,
                'nonce': base64.b64encode(metadata.nonce).decode('utf-8'),
                'auth_tag': base64.b64encode(metadata.auth_tag).decode('utf-8'),
                'key_derivation_salt': base64.b64encode(metadata.key_derivation_salt).decode('utf-8'),
                'chunk_size': metadata.chunk_size,
                'encryption_algorithm': metadata.encryption_algorithm
            })
        
        metadata_file = output_path / f"{data_id}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                'data_id': data_id,
                'chunk_count': len(encrypted_chunks),
                'original_size': len(data),
                'encryption_config': config_manager.get_config_summary(),
                'chunks': metadata_dict
            }, f, indent=2)
        
        click.echo(f"Encryption completed successfully!")
        click.echo(f"Encrypted chunks: {len(chunk_files)}")
        click.echo(f"Metadata file: {metadata_file}")
        click.echo(f"Total encrypted size: {sum(len(chunk) for chunk in encrypted_chunks)} bytes")
        
        if verbose:
            info = encryptor.get_encryption_info()
            click.echo("Encryption details:")
            for key, value in info.items():
                click.echo(f"  {key}: {value}")
    
    except Exception as e:
        click.echo(f"Error during encryption: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('metadata_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--key', help='Master key (base64 encoded or password)')
@click.pass_context
def decrypt(ctx, metadata_file, output_file, key):
    """Decrypt encrypted files from 5D optical storage."""
    verbose = ctx.obj['verbose']
    config_manager = ctx.obj['config_manager']
    
    try:
        # Load metadata
        with open(metadata_file, 'r') as f:
            metadata_json = json.load(f)
        
        data_id = metadata_json['data_id']
        chunk_count = metadata_json['chunk_count']
        original_size = metadata_json['original_size']
        
        if verbose:
            click.echo(f"Decrypting {data_id} with {chunk_count} chunks")
            click.echo(f"Expected output size: {original_size} bytes")
        
        # Validate configuration
        config_manager.validate_config()
        encryption_config = config_manager.get_encryption_config()
        
        # Initialize encryption
        encryptor = OpticalStorageEncryption(encryption_config)
        
        # Set master key if provided
        if key:
            encryptor.set_master_key(key)
        elif encryption_config.key_source == KeySource.LOCAL:
            click.echo("Error: Master key required for local decryption")
            sys.exit(1)
        
        # Load encrypted chunks
        metadata_path = Path(metadata_file)
        base_dir = metadata_path.parent
        
        encrypted_chunks = []
        metadata_list = []
        
        for chunk_info in metadata_json['chunks']:
            # Load chunk file
            chunk_file = base_dir / f"{chunk_info['chunk_id']}.enc"
            if not chunk_file.exists():
                raise FileNotFoundError(f"Chunk file not found: {chunk_file}")
            
            with open(chunk_file, 'rb') as f:
                encrypted_chunks.append(f.read())
            
            # Reconstruct metadata
            metadata = ChunkMetadata(
                chunk_id=chunk_info['chunk_id'],
                nonce=base64.b64decode(chunk_info['nonce']),
                auth_tag=base64.b64decode(chunk_info['auth_tag']),
                key_derivation_salt=base64.b64decode(chunk_info['key_derivation_salt']),
                chunk_size=chunk_info['chunk_size'],
                encryption_algorithm=chunk_info['encryption_algorithm']
            )
            metadata_list.append(metadata)
        
        if verbose:
            click.echo(f"Loaded {len(encrypted_chunks)} encrypted chunks")
        
        # Decrypt data
        decrypted_data = encryptor.decrypt_data(encrypted_chunks, metadata_list)
        
        if len(decrypted_data) != original_size:
            click.echo(f"Warning: Decrypted size ({len(decrypted_data)}) doesn't match expected size ({original_size})")
        
        # Save decrypted file
        with open(output_file, 'wb') as f:
            f.write(decrypted_data)
        
        click.echo(f"Decryption completed successfully!")
        click.echo(f"Output file: {output_file}")
        click.echo(f"Decrypted size: {len(decrypted_data)} bytes")
    
    except Exception as e:
        click.echo(f"Error during decryption: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def generate_key(ctx):
    """Generate a new master key for encryption."""
    config_manager = ctx.obj['config_manager']
    encryption_config = config_manager.get_encryption_config()
    
    encryptor = OpticalStorageEncryption(encryption_config)
    master_key = encryptor.generate_master_key()
    key_b64 = base64.b64encode(master_key).decode('utf-8')
    
    click.echo("Generated new master key:")
    click.echo(key_b64)
    click.echo()
    click.echo("IMPORTANT: Save this key securely in a safe location.")
    click.echo("You will need this key to decrypt your data.")


@cli.command()
@click.option('--output-dir', default='.', help='Directory to save sample configs')
@click.pass_context
def init_config(ctx, output_dir):
    """Initialize sample configuration files."""
    from config_manager import create_sample_configs
    
    configs = create_sample_configs()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    for filename, config in configs.items():
        config_file = output_path / filename
        with open(config_file, 'w') as f:
            import yaml
            yaml.dump(config, f, default_flow_style=False, indent=2)
        click.echo(f"Created: {config_file}")
    
    click.echo(f"\nSample configuration files created in {output_dir}")
    click.echo("Edit these files according to your requirements.")


@cli.command()
@click.pass_context
def config_info(ctx):
    """Display current configuration information."""
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.validate_config()
        summary = config_manager.get_config_summary()
        
        click.echo("Current Configuration:")
        click.echo("=" * 40)
        
        for key, value in summary.items():
            if isinstance(value, dict):
                click.echo(f"{key}:")
                for sub_key, sub_value in value.items():
                    click.echo(f"  {sub_key}: {sub_value}")
            else:
                click.echo(f"{key}: {value}")
    
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('test_file', type=click.Path())
@click.option('--size', default=1024, help='Test file size in bytes')
@click.pass_context
def test_encryption(ctx, test_file, size):
    """Test encryption/decryption with a sample file."""
    verbose = ctx.obj['verbose']
    config_manager = ctx.obj['config_manager']
    
    try:
        # Create test file
        test_data = os.urandom(size)
        with open(test_file, 'wb') as f:
            f.write(test_data)
        
        if verbose:
            click.echo(f"Created test file: {test_file} ({size} bytes)")
        
        # Initialize encryption
        encryption_config = config_manager.get_encryption_config()
        encryptor = OpticalStorageEncryption(encryption_config)
        
        # Generate key
        master_key = encryptor.generate_master_key()
        
        # Encrypt
        encrypted_chunks, metadata_list = encryptor.encrypt_data(test_data, "test")
        
        # Decrypt
        decrypted_data = encryptor.decrypt_data(encrypted_chunks, metadata_list)
        
        # Verify
        if test_data == decrypted_data:
            click.echo("✓ Encryption/decryption test PASSED")
            click.echo(f"✓ Original size: {len(test_data)} bytes")
            click.echo(f"✓ Encrypted chunks: {len(encrypted_chunks)}")
            click.echo(f"✓ Decrypted size: {len(decrypted_data)} bytes")
        else:
            click.echo("✗ Encryption/decryption test FAILED")
            click.echo("Original and decrypted data do not match")
            sys.exit(1)
        
        # Clean up
        os.remove(test_file)
    
    except Exception as e:
        click.echo(f"Test failed: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()