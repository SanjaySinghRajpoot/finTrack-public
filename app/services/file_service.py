import base64
import datetime
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
    
    def extract_text(self, file_path: Union[str, Path]) -> str:
        """
        Extract text content from a file based on its type.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Extracted text content or empty string if extraction fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_type = self.get_file_type(file_path)
        
        try:
            if file_type == 'text':
                return self._extract_text_file(file_path)
            elif file_type == 'csv':
                return self._extract_csv_content(file_path)
            elif file_type == 'pdf':
                return self._extract_pdf_content(file_path)
            elif file_type == 'word':
                return self._extract_docx_content(file_path)
            elif file_type == 'excel':
                return self._extract_excel_content(file_path)
            elif file_type == 'powerpoint':
                return self._extract_pptx_content(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
                
        except Exception as e:
            print(f"Error extracting text from {file_path}: {str(e)}")
            return ""
    
    def _extract_text_file(self, file_path: Path) -> str:
        """Extract content from plain text files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
    
    def _extract_csv_content(self, file_path: Path) -> str:
        """Extract content from CSV files."""
        content = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                for row in csv_reader:
                    content.append(', '.join(str(cell) for cell in row))
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                csv_reader = csv.reader(f)
                for row in csv_reader:
                    content.append(', '.join(str(cell) for cell in row))
        
        return '\n'.join(content)
    
    def _extract_pdf_content(self, file_path: Path) -> str:
        """Extract text from PDF files."""
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")
        
        text = ""
        with open(file_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    
    def _extract_docx_content(self, file_path: Path) -> str:
        """Extract text from Word documents."""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not installed. Install with: pip install python-docx")
        
        doc = Document(file_path)
        text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text.append(paragraph.text)
        return '\n'.join(text)
    
    def _extract_excel_content(self, file_path: Path) -> str:
        """Extract content from Excel files."""
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.xlsx':
            if not XLSX_AVAILABLE:
                raise ImportError("openpyxl not installed. Install with: pip install openpyxl")
            
            workbook = load_workbook(file_path, data_only=True)
            content = []
            
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                content.append(f"Sheet: {sheet_name}")
                content.append("=" * (len(sheet_name) + 7))
                
                for row in sheet.iter_rows(values_only=True):
                    row_data = [str(cell) if cell is not None else "" for cell in row]
                    if any(cell.strip() for cell in row_data if cell):  # Skip empty rows
                        content.append(', '.join(row_data))
                content.append("")  # Add blank line between sheets
            
            return '\n'.join(content)
        
        elif file_extension == '.xls':
            if not XLS_AVAILABLE:
                raise ImportError("xlrd not installed. Install with: pip install xlrd")
            
            workbook = xlrd.open_workbook(file_path)
            content = []
            
            for sheet in workbook.sheets():
                content.append(f"Sheet: {sheet.name}")
                content.append("=" * (len(sheet.name) + 7))
                
                for row_idx in range(sheet.nrows):
                    row_data = []
                    for col_idx in range(sheet.ncols):
                        cell = sheet.cell(row_idx, col_idx)
                        row_data.append(str(cell.value))
                    if any(cell.strip() for cell in row_data if cell):
                        content.append(', '.join(row_data))
                content.append("")  # Add blank line between sheets
            
            return '\n'.join(content)
    
    def _extract_pptx_content(self, file_path: Path) -> str:
        """Extract text from PowerPoint files."""
        if not PPTX_AVAILABLE:
            raise ImportError("python-pptx not installed. Install with: pip install python-pptx")
        
        prs = Presentation(file_path)
        text = []
        
        for i, slide in enumerate(prs.slides, 1):
            slide_text = [f"Slide {i}:", "=" * 10]
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())
            
            if len(slide_text) > 2:  # More than just header
                text.append('\n'.join(slide_text))
        
        return '\n\n'.join(text)
    
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
                'file_type': file_type(),
                'mime_type': self.get_file_type(saved_file_path),
                'text_content': text_content,
                'file_size': len(file_data),
                'is_supported': self.is_supported(saved_file_path),
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
    
    def process_multiple_files(self, file_paths: List[Union[str, Path]]) -> List[Dict]:
        """
        Process multiple files and extract their text content.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            List[Dict]: List of processed file information
        """
        results = []
        
        for file_path in file_paths:
            file_path = Path(file_path)
            
            if not file_path.exists():
                results.append({
                    'file_path': str(file_path),
                    'filename': file_path.name,
                    'error': 'File not found',
                    'text_content': '',
                    'file_type': 'unknown'
                })
                continue
            
            try:
                file_type = self.get_file_type(file_path)
                text_content = self.extract_text(file_path) if self.is_supported(file_path) else ""
                
                results.append({
                    'file_path': str(file_path),
                    'filename': file_path.name,
                    'file_type': file_type,
                    'text_content': text_content,
                    'file_size': file_path.stat().st_size,
                    'is_supported': self.is_supported(file_path)
                })
                
            except Exception as e:
                results.append({
                    'file_path': str(file_path),
                    'filename': file_path.name,
                    'error': str(e),
                    'text_content': '',
                    'file_type': 'unknown'
                })
        
        return results


