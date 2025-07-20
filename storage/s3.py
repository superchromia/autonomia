import boto3
from storage.base import StorageBackend
import os
from botocore.exceptions import NoCredentialsError

class S3StorageBackend(StorageBackend):
    def __init__(self, bucket_name: str, region_name: str , base_url: str):
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.base_url = base_url
        self.s3 = boto3.client(
            's3',
            region_name=region_name,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        )

    async def save_image(self, file_bytes: bytes, file_name: str = None) -> str:
        hashed_name = self.hash_filename(file_bytes)
        # Check if such object already exists in the bucket
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=hashed_name)
            return self.base_url + hashed_name
        except self.s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] != '404':
                raise
        self.s3.put_object(Bucket=self.bucket_name, Key=hashed_name, Body=file_bytes, ContentType='image/jpeg')
        return self.base_url + hashed_name
