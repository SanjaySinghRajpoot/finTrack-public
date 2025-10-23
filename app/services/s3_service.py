import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from datetime import datetime, timedelta
import os
from typing import Optional


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

    def upload_pdf(self, file: UploadFile, folder: Optional[str] = "attachments") -> str:
        """
        Upload a PDF file to the S3 bucket and return its file key.
        """
        try:
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Only PDF files are allowed")

            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            file_key = f"{folder}/{timestamp}_{file.filename}"

            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                file_key,
                ExtraArgs={
                    "ContentType": "application/pdf",
                    "ACL": "private"  # use "public-read" if you want direct access
                },
            )

            return file_key

        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"S3 Upload Error: {e}")
