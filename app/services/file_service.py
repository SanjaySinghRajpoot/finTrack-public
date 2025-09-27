import base64
import datetime
import json
import mimetypes
import csv
import io
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging
import PyPDF2


import requests

from app.models.models import Attachment

# Required imports for different file types
try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    from openpyxl import load_workbook
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

try:
    import xlrd
    XLS_AVAILABLE = True
except ImportError:
    XLS_AVAILABLE = False

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False


class FileProcessor:
    """
    A comprehensive file processing class for extracting text content from various file formats.
    
    Supports: TXT, CSV, PDF, DOCX, DOC, XLSX, XLS, PPTX, and other text-based files.
    """
    
    # Supported file extensions mapping
    SUPPORTED_EXTENSIONS = {
        'text': ['.txt', '.log', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml'],
        'csv': ['.csv'],
        'pdf': ['.pdf'],
        'word': ['.docx', '.doc'],
        'excel': ['.xlsx', '.xls'],
        'powerpoint': ['.pptx', '.ppt']
    }
    
    def __init__(self, download_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the FileProcessor.
        
        Args:
            download_dir (str or Path, optional): Directory to save downloaded files
        """
        # Default to /data directory
        self.download_dir = Path.cwd() / "metadata"
        self.download_dir.mkdir(exist_ok=True, parents=True)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Check available libraries
        self._check_dependencies()
    
    def _check_dependencies(self) -> Dict[str, bool]:
        """Check which file processing libraries are available."""
        dependencies = {
            'pdf': PDF_AVAILABLE,
            'docx': DOCX_AVAILABLE,
            'xlsx': XLSX_AVAILABLE,
            'xls': XLS_AVAILABLE,
            'pptx': PPTX_AVAILABLE
        }
        
        missing = [lib for lib, available in dependencies.items() if not available]
        if missing:
            print(f"Warning: Missing libraries for {', '.join(missing)} processing")
        
        return dependencies
    
    def get_file_type(self, file_path: Union[str, Path]) -> str:
        """
        Determine the file type based on extension and MIME type.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: File type category
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Check each category
        for category, extensions in self.SUPPORTED_EXTENSIONS.items():
            if extension in extensions:
                return category
        
        # Check by MIME type as fallback
        if mime_type:
            if 'text' in mime_type:
                return 'text'
            elif 'csv' in mime_type:
                return 'csv'
            elif 'pdf' in mime_type:
                return 'pdf'
            elif 'word' in mime_type or 'document' in mime_type:
                return 'word'
            elif 'excel' in mime_type or 'spreadsheet' in mime_type:
                return 'excel'
            elif 'presentation' in mime_type:
                return 'powerpoint'
        
        return 'unknown'
    
    def is_supported(self, file_path: Union[str, Path]) -> bool:
        """
        Check if the file type is supported for text extraction.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if file type is supported
        """
        return self.get_file_type(file_path) != 'unknown'
    
    def get_file_type(self, file_path: Union[str, Path]) -> str:
        """Return the lowercase file extension without the dot."""
        return Path(file_path).suffix.lower().lstrip(".")

    def extract_text(self, file_path: Union[str, Path]) -> str:
        """Extract text from supported file types. Currently supports PDF."""
        file_type = self.get_file_type(file_path)

        if file_type == "pdf":
            return self._extract_pdf_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_pdf_text(self, file_path: Union[str, Path]) -> str:
        """Extract text from a PDF file."""
        text_content = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text_content.append(page.extract_text() or "")
        return "\n".join(text_content)

        
    
    def save_file(self, file_data: bytes, filename: str) -> Path:
        """
        Save file data to the /data directory.
        
        Args:
            file_data: Binary file data
            filename: Name for the file
            
        Returns:
            Path: Path to the saved file
        """
        file_path = self.download_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_data)
        return file_path
    
    def process_gmail_attachment(self, attachment_data: Dict, attachment_id: str, 
                               filename: Optional[str] = None, msg_metadata: Optional[Dict] = None) -> Dict:
        """
        Process a Gmail attachment: save to /data and extract text.
        
        Args:
            attachment_data: Attachment data from Gmail API
            attachment_id: ID of the attachment
            filename: Optional filename
            msg_metadata: Optional email metadata (sender, subject, date, etc.)
            
        Returns:
            Dict: Processed attachment information
        """
        try:
            # Decode file data
            file_data = base64.urlsafe_b64decode(attachment_data["data"])
            
            # Determine filename
            if not filename:
                filename = f"attachment_{attachment_id}"
            
            # Save file to /data directory
            # here we would need to call the OCR to scan the documents
            saved_file_path = self.save_file(file_data, filename)
            
            # Extract text content from saved file
            file_type = self.get_file_type(saved_file_path)
            text_content = ""
            
            if self.is_supported(saved_file_path):
                text_content = self.extract_text(saved_file_path)
            
            # Prepare response
            result = {
                'attachment_id': attachment_id,
                'filename': filename,
                'file_path': str(saved_file_path),
                'file_type': "pdf",
                'mime_type': "pdf",
                'text_content': text_content,
                'file_size': 0,
                'is_supported': "true",
                'processed_at': datetime.datetime.now().isoformat(),
                'success': True
            }
            
            # Add email metadata if provided
            if msg_metadata:
                result.update({
                    'email_subject': msg_metadata.get('subject', '')[:1000],  # Limit length
                    'email_sender': msg_metadata.get('sender', ''),
                    'email_date': msg_metadata.get('date', ''),
                    'message_id': msg_metadata.get('message_id', '')
                })
            
            self.logger.info(f"Successfully processed attachment: {filename}")
            return result
            
        except Exception as e:
            error_msg = f"Error processing attachment {attachment_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'attachment_id': attachment_id,
                'filename': filename or f"attachment_{attachment_id}",
                'success': False,
                'error': error_msg,
                'processed_at': datetime.datetime.now().isoformat()
            }


