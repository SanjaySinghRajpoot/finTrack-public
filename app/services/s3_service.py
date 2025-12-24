import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from datetime import datetime, timedelta
from typing import Optional
import aioboto3
import logging

from app.core.config import settings

# Configure logger
logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket_name = settings.AWS_S3_BUCKET
        
        # Log S3 configuration (without sensitive data)
        logger.info(f"S3Service initialized - Bucket: {self.bucket_name}, Region: {settings.AWS_REGION}")

    async def generate_upload_presigned_url(
        self, 
        file_key: str, 
        content_type: str,
        expires_in: int = 3600
    ) -> str:
        """
        Generate a pre-signed URL for uploading a file directly to S3.

        Args:
            file_key (str): The S3 object key (path where file will be stored in the bucket)
            content_type (str): The MIME type of the file being uploaded
            expires_in (int): Expiration time in seconds (default: 1 hour)

        Returns:
            str: A pre-signed URL for uploading the file directly to S3
        """
        try:
            logger.info(f"Generating presigned upload URL - Key: {file_key}, ContentType: {content_type}, ExpiresIn: {expires_in}")
            
            # Run sync boto3 call in executor to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Generate presigned URL without ACL (many buckets have ACLs disabled)
            params = {
                "Bucket": self.bucket_name, 
                "Key": file_key,
                "ContentType": content_type
            }
            
            logger.debug(f"Presigned URL params: {params}")
            
            presigned_url = await loop.run_in_executor(
                None,
                lambda: self.s3_client.generate_presigned_url(
                    "put_object",
                    Params=params,
                    ExpiresIn=expires_in,
                    HttpMethod="PUT"
                )
            )
            
            logger.info(f"✅ Presigned URL generated successfully for: {file_key}")
            logger.debug(f"Generated URL (first 100 chars): {presigned_url[:100]}...")
            
            return presigned_url

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"❌ AWS ClientError generating presigned URL: Code={error_code}, Message={error_message}")
            logger.error(f"Failed params: Bucket={self.bucket_name}, Key={file_key}, ContentType={content_type}")
            raise HTTPException(status_code=500, detail=f"Error generating upload pre-signed URL: {error_code} - {error_message}")
        except Exception as e:
            logger.error(f"❌ Unexpected error generating presigned URL: {type(e).__name__} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating upload pre-signed URL: {str(e)}")

    async def get_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        """
        Generate a pre-signed URL for accessing a file in S3.

        Args:
            file_key (str): The S3 object key (path of the file in the bucket)
            expires_in (int): Expiration time in seconds (default: 1 hour)

        Returns:
            str: A pre-signed URL for viewing/downloading the file
        """
        try:
            logger.info(f"Generating presigned URL for access - Key: {file_key}, ExpiresIn: {expires_in}")
            
            # Run sync boto3 call in executor to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            
            presigned_url = await loop.run_in_executor(
                None,
                lambda: self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": file_key},
                    ExpiresIn=expires_in,  # Default 1 hour
                )
            )
            
            logger.info(f"✅ Presigned URL generated successfully for: {file_key}")
            logger.debug(f"Generated URL (first 100 chars): {presigned_url[:100]}...")
            
            return presigned_url

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"❌ AWS ClientError generating presigned URL: Code={error_code}, Message={error_message}")
            logger.error(f"Failed params: Bucket={self.bucket_name}, Key={file_key}")
            raise HTTPException(status_code=500, detail=f"Error generating pre-signed URL: {error_code} - {error_message}")
        except Exception as e:
            logger.error(f"❌ Unexpected error generating presigned URL: {type(e).__name__} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating pre-signed URL: {str(e)}")

    async def upload_file(self, file: UploadFile, folder: Optional[str] = "attachments") -> str:
        """
        Upload a PDF or image file to the S3 bucket and return its file key.
        
        Supported formats: PDF, JPEG, JPG, PNG, GIF, WEBP
        """
        try:
            logger.info(f"Uploading file - Filename: {file.filename}, Folder: {folder}")
            
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
                logger.error(f"❌ Invalid file type: {file.content_type} - Filename: {file.filename}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file type. Only PDF and images (JPEG, PNG, GIF, WEBP) are allowed."
                )
            
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            file_key = f"{folder}/{timestamp}_{file.filename}"

            session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )

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
            
            logger.info(f"✅ File uploaded successfully - Key: {file_key}")
            return file_key

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"❌ AWS ClientError uploading file: Code={error_code}, Message={error_message}")
            logger.error(f"Failed params: Bucket={self.bucket_name}, Key={file_key}")
            raise HTTPException(status_code=500, detail=f"S3 Upload Error: {error_code} - {error_message}")
        except Exception as e:
            logger.error(f"❌ Unexpected error uploading file: {type(e).__name__} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"S3 Upload Error: {str(e)}")

    async def download_file_from_s3(self, s3_key: str) -> bytes:
        """
        Download file from S3 and return as bytes.
        
        Args:
            s3_key: The S3 object key (path of the file in the bucket)
            
        Returns:
            bytes: File content as bytes
        """
        try:
            logger.info(f"Downloading file from S3 - Key: {s3_key}")
            
            session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )

            async with session.client("s3") as s3_client:
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                async with response['Body'] as stream:
                    file_content = await stream.read()
                    
            logger.info(f"✅ File downloaded successfully - Key: {s3_key}")
            return file_content
                    
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"❌ AWS ClientError downloading file: Code={error_code}, Message={error_message}")
            logger.error(f"Failed params: Bucket={self.bucket_name}, Key={s3_key}")
            raise HTTPException(status_code=500, detail=f"S3 Download Error: {error_code} - {error_message}")
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading file: {type(e).__name__} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"S3 Download Error: {str(e)}")
