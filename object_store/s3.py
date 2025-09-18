"""
S3-compatible cloud storage backend implementation.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, BinaryIO
import io

from .base import StorageBackend, ObjectMetadata, calculate_etag


class S3Storage(StorageBackend):
    """S3-compatible storage backend."""
    
    def __init__(self, bucket_name: str, access_key: Optional[str] = None, 
                 secret_key: Optional[str] = None, endpoint_url: Optional[str] = None,
                 region: str = "us-east-1"):
        """
        Initialize S3 storage.
        
        Args:
            bucket_name: Name of the S3 bucket
            access_key: AWS access key ID (optional, can use environment variables)
            secret_key: AWS secret access key (optional, can use environment variables)
            endpoint_url: Custom endpoint URL for S3-compatible services
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url
        self.region = region
        
        # Initialize S3 client
        self._init_s3_client()
    
    def _init_s3_client(self):
        """Initialize the S3 client."""
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
        except ImportError:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
        
        # Create session with optional credentials
        session = boto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )
        
        # Create S3 client
        self.s3_client = session.client(
            's3',
            endpoint_url=self.endpoint_url
        )
        
        # Store exceptions for later use
        self.NoCredentialsError = NoCredentialsError
        self.ClientError = ClientError
        
        # Verify bucket access
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except self.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Try to create bucket
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                except self.ClientError:
                    raise ConnectionError(f"Cannot access or create bucket '{self.bucket_name}'")
            else:
                raise ConnectionError(f"Cannot access bucket '{self.bucket_name}': {e}")
    
    def put_object(self, key: str, data: Union[bytes, BinaryIO], 
                   metadata: Optional[Dict[str, str]] = None) -> ObjectMetadata:
        """Store an object in S3."""
        # Handle both bytes and file-like objects
        if hasattr(data, 'read'):
            if hasattr(data, 'seek'):
                data.seek(0)  # Reset file pointer
            content = data.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
        else:
            content = data
        
        # Prepare metadata
        s3_metadata = {}
        content_type = None
        
        if metadata:
            # Separate content-type from custom metadata
            content_type = metadata.pop('content-type', None)
            s3_metadata = {k: v for k, v in metadata.items() if isinstance(v, str)}
        
        # Upload to S3
        try:
            put_args = {
                'Bucket': self.bucket_name,
                'Key': key,
                'Body': content,
                'Metadata': s3_metadata
            }
            
            if content_type:
                put_args['ContentType'] = content_type
            
            response = self.s3_client.put_object(**put_args)
            
            # Create metadata object
            obj_metadata = ObjectMetadata(
                key=key,
                size=len(content),
                last_modified=datetime.now(),
                etag=response['ETag'].strip('"'),
                content_type=content_type,
                custom_metadata=s3_metadata
            )
            
            return obj_metadata
            
        except self.ClientError as e:
            raise RuntimeError(f"Failed to store object '{key}': {e}")
    
    def get_object(self, key: str) -> bytes:
        """Retrieve an object from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except self.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"Object '{key}' not found")
            else:
                raise RuntimeError(f"Failed to retrieve object '{key}': {e}")
    
    def delete_object(self, key: str) -> bool:
        """Delete an object from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return False
            else:
                raise RuntimeError(f"Failed to delete object '{key}': {e}")
    
    def list_objects(self, prefix: str = "", limit: Optional[int] = None) -> List[ObjectMetadata]:
        """List objects with optional prefix filter."""
        objects = []
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                PaginationConfig={'PageSize': min(limit or 1000, 1000)}
            )
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Get additional metadata
                        try:
                            head_response = self.s3_client.head_object(
                                Bucket=self.bucket_name,
                                Key=obj['Key']
                            )
                            content_type = head_response.get('ContentType')
                            custom_metadata = head_response.get('Metadata', {})
                        except self.ClientError:
                            content_type = None
                            custom_metadata = {}
                        
                        metadata = ObjectMetadata(
                            key=obj['Key'],
                            size=obj['Size'],
                            last_modified=obj['LastModified'].replace(tzinfo=None),
                            etag=obj['ETag'].strip('"'),
                            content_type=content_type,
                            custom_metadata=custom_metadata
                        )
                        
                        objects.append(metadata)
                        
                        if limit and len(objects) >= limit:
                            return objects
                            
                if limit and len(objects) >= limit:
                    break
            
            return objects
            
        except self.ClientError as e:
            raise RuntimeError(f"Failed to list objects: {e}")
    
    def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                raise RuntimeError(f"Failed to check object existence '{key}': {e}")
    
    def get_object_metadata(self, key: str) -> ObjectMetadata:
        """Get object metadata."""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            
            return ObjectMetadata(
                key=key,
                size=response['ContentLength'],
                last_modified=response['LastModified'].replace(tzinfo=None),
                etag=response['ETag'].strip('"'),
                content_type=response.get('ContentType'),
                custom_metadata=response.get('Metadata', {})
            )
            
        except self.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise FileNotFoundError(f"Object '{key}' not found")
            else:
                raise RuntimeError(f"Failed to get object metadata '{key}': {e}")


class MockS3Storage(StorageBackend):
    """Mock S3 storage for testing without AWS dependencies."""
    
    def __init__(self, bucket_name: str):
        """Initialize mock S3 storage."""
        self.bucket_name = bucket_name
        self._objects = {}  # key -> (data, metadata)
    
    def put_object(self, key: str, data: Union[bytes, BinaryIO], 
                   metadata: Optional[Dict[str, str]] = None) -> ObjectMetadata:
        """Store an object in mock S3."""
        if hasattr(data, 'read'):
            content = data.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
        else:
            content = data
        
        obj_metadata = ObjectMetadata(
            key=key,
            size=len(content),
            last_modified=datetime.now(),
            etag=calculate_etag(content),
            content_type=metadata.get('content-type') if metadata else None,
            custom_metadata=metadata
        )
        
        self._objects[key] = (content, obj_metadata)
        return obj_metadata
    
    def get_object(self, key: str) -> bytes:
        """Retrieve an object from mock S3."""
        if key not in self._objects:
            raise FileNotFoundError(f"Object '{key}' not found")
        return self._objects[key][0]
    
    def delete_object(self, key: str) -> bool:
        """Delete an object from mock S3."""
        if key in self._objects:
            del self._objects[key]
            return True
        return False
    
    def list_objects(self, prefix: str = "", limit: Optional[int] = None) -> List[ObjectMetadata]:
        """List objects with optional prefix filter."""
        objects = []
        for key, (_, metadata) in self._objects.items():
            if prefix and not key.startswith(prefix):
                continue
            objects.append(metadata)
            if limit and len(objects) >= limit:
                break
        return objects
    
    def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        return key in self._objects
    
    def get_object_metadata(self, key: str) -> ObjectMetadata:
        """Get object metadata."""
        if key not in self._objects:
            raise FileNotFoundError(f"Object '{key}' not found")
        return self._objects[key][1]