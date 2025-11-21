import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from datetime import datetime, timedelta
import os
from typing import Optional
import aioboto3

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "ap-south-1"),
        )
        self.bucket_name = os.getenv("AWS_S3_BUCKET")

    def get_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        """
        Generate a pre-signed URL for accessing a file in S3.

        Args:
            file_key (str): The S3 object key (path of the file in the bucket)
            expires_in (int): Expiration time in seconds (default: 1 hour)

        Returns:
            str: A pre-signed URL for viewing/downloading the file
        """
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_key},
                ExpiresIn=expires_in,  # Default 1 hour
            )
            return presigned_url

        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"Error generating pre-signed URL: {e}")

    async def upload_file(self, file: UploadFile, folder: Optional[str] = "attachments") -> str:
        """
        Upload a PDF or image file to the S3 bucket and return its file key.
        
        Supported formats: PDF, JPEG, JPG, PNG, GIF, WEBP
        """
        try:
            # Validate file type
            allowed_content_types = {
                "application/pdf": "application/pdf",
                "image/jpeg": "image/jpeg",
                "image/jpg": "image/jpeg",
                "image/png": "image/png",
                "image/gif": "image/gif",
                "image/webp": "image/webp"
            }
            
            content_type = file.content_type.lower() if file.content_type else ""
            
            # Also check by file extension if content_type is not available
            if content_type not in allowed_content_types:
                file_ext = file.filename.lower().split('.')[-1] if file.filename else ""
                ext_to_content_type = {
                    "pdf": "application/pdf",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "gif": "image/gif",
                    "webp": "image/webp"
                }
                content_type = ext_to_content_type.get(file_ext, "")
            
            if content_type not in allowed_content_types:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file type. Only PDF and images (JPEG, PNG, GIF, WEBP) are allowed."
                )
            
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            file_key = f"{folder}/{timestamp}_{file.filename}"

            session = aioboto3.Session()

            async with session.client("s3") as s3_client:

                file.file.seek(0)
                
                await s3_client.upload_fileobj(
                    file.file,
                    self.bucket_name,
                    file_key,
                    ExtraArgs={
                        "ContentType": allowed_content_types[content_type],
                        "ACL": "private",  # or "public-read" if needed
                    },
                )

            return file_key

        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"S3 Upload Error: {e}")
