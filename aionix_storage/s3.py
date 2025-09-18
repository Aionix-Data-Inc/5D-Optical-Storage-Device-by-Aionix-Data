"""
S3Store implementation for S3-compatible cloud storage.

This implementation provides integration with AWS S3 and S3-compatible
object storage services using the boto3 library.
"""

import json
from typing import Dict, List, Optional, Any

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

from .base import ObjectStore


class S3Store(ObjectStore):
    """Object store implementation using S3-compatible storage."""
    
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = 'us-east-1',
        endpoint_url: Optional[str] = None
    ):
        """
        Initialize S3 store.
        
        Args:
            bucket_name: Name of the S3 bucket
            aws_access_key_id: AWS access key ID (optional, can use environment)
            aws_secret_access_key: AWS secret access key (optional, can use environment)
            region_name: AWS region name
            endpoint_url: Custom endpoint URL for S3-compatible services
        """
        if boto3 is None:
            raise ImportError("boto3 is required for S3Store. Install with: pip install boto3")
        
        self.bucket_name = bucket_name
        
        # Create S3 client
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        
        self.s3_client = session.client('s3', endpoint_url=endpoint_url)
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                except ClientError as create_error:
                    raise RuntimeError(f"Failed to create bucket {self.bucket_name}: {create_error}")
            else:
                raise RuntimeError(f"Failed to access bucket {self.bucket_name}: {e}")
    
    def _get_metadata_key(self, key: str) -> str:
        """Get the metadata key for an object key."""
        return f"{key}.meta"
    
    def put(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store data with the given key."""
        try:
            # Store object data
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data
            )
            
            # Store metadata as a separate object
            if metadata:
                meta_data = metadata.copy()
                meta_data.update({
                    'size': len(data),
                    'key': key
                })
                
                metadata_json = json.dumps(meta_data, indent=2)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=self._get_metadata_key(key),
                    Body=metadata_json.encode('utf-8'),
                    ContentType='application/json'
                )
        
        except ClientError as e:
            raise RuntimeError(f"Failed to store object '{key}': {e}")
    
    def get(self, key: str) -> bytes:
        """Retrieve data by key."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise KeyError(f"Object with key '{key}' not found")
            else:
                raise RuntimeError(f"Failed to retrieve object '{key}': {e}")
    
    def exists(self, key: str) -> bool:
        """Check if an object exists."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                raise RuntimeError(f"Failed to check object '{key}': {e}")
    
    def delete(self, key: str) -> None:
        """Delete an object."""
        if not self.exists(key):
            raise KeyError(f"Object with key '{key}' not found")
        
        try:
            # Delete object
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            
            # Delete metadata if it exists
            metadata_key = self._get_metadata_key(key)
            if self.exists(metadata_key):
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=metadata_key)
        
        except ClientError as e:
            raise RuntimeError(f"Failed to delete object '{key}': {e}")
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with optional prefix filter."""
        try:
            keys = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        # Skip metadata files
                        if not key.endswith('.meta'):
                            keys.append(key)
            
            return sorted(keys)
        
        except ClientError as e:
            raise RuntimeError(f"Failed to list objects: {e}")
    
    def get_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata for an object."""
        if not self.exists(key):
            raise KeyError(f"Object with key '{key}' not found")
        
        metadata_key = self._get_metadata_key(key)
        
        try:
            # Try to get stored metadata
            if self.exists(metadata_key):
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                metadata_json = response['Body'].read().decode('utf-8')
                return json.loads(metadata_json)
            else:
                # Return minimal metadata from object info
                response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                return {
                    'size': response['ContentLength'],
                    'key': key,
                    'last_modified': response['LastModified'].isoformat(),
                    'etag': response['ETag'].strip('"')
                }
        
        except ClientError as e:
            raise RuntimeError(f"Failed to get metadata for '{key}': {e}")