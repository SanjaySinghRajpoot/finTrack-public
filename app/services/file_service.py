import io
import logging
from enum import Enum
from pathlib import Path

from fastapi import UploadFile


class FileType(Enum):
    PDF = "pdf"


class ProcessingError(Exception):
    pass


class FileService:
    """Handles basic file operations, validation, and file type checking."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp'}

    def create_upload_file(self, filename: str, file_data: bytes) -> UploadFile:
        """Create an UploadFile object from filename and bytes."""
        return UploadFile(filename=filename, file=io.BytesIO(file_data))

    def generate_default_filename(self, attachment_id: str) -> str:
        """Generate a default filename for an attachment."""
        return f"attachment_{attachment_id}.pdf"

    def get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return Path(filename).suffix.lower().lstrip(".")

    def is_supported_file(self, filename: str) -> bool:
        """Check if file extension is supported."""
        return Path(filename).suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def is_pdf(self, filename: str) -> bool:
        """Check if file is a PDF."""
        return filename.lower().endswith('.pdf')
    
    def is_image(self, filename: str) -> bool:
        """Check if file is an image."""
        return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))