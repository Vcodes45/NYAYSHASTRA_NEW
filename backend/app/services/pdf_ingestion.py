"""
NyayGuru AI Pro - PDF Ingestion Service
Ingests PDF documents from legal_data/ subfolders with domain metadata tagging.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

logger = logging.getLogger(__name__)

# Domain mapping from folder names to domain values
FOLDER_TO_DOMAIN = {
    "Criminal": "criminal",
    "Corporate": "corporate",
    "Civil": "civil",
    "Environment": "environmental",
    "IT_Act": "it_cyber",
    "Labour": "labour",
    "Family": "family",
    "Property": "property",
    "Constitutional": "constitutional",
    "Financial": "financial",
}


class PDFIngestionService:
    """Service for ingesting PDFs from legal_data folder with domain metadata."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the service.
        
        Args:
            data_dir: Path to the legal_data directory. Defaults to app/data copy.
        """
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # Default to 'legal_data' folder relative to app
            self.data_dir = Path(__file__).parent.parent / "legal_data"
            
        # Create directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.chunk_size = 1000  # characters per chunk
        self.chunk_overlap = 200  # overlap between chunks
        
        logger.info(f"PDF Ingestion Service initialized with data_dir: {self.data_dir}")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        text = ""
        
        try:
            if PDFPLUMBER_AVAILABLE:
                # Use pdfplumber (better for complex layouts)
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
                logger.debug(f"Extracted {len(text)} chars from {pdf_path.name} using pdfplumber")
                
            elif PYPDF2_AVAILABLE:
                # Fallback to PyPDF2
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                logger.debug(f"Extracted {len(text)} chars from {pdf_path.name} using PyPDF2")
                
            else:
                logger.error("No PDF library available. Install pdfplumber or PyPDF2.")
                
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
        
        return text.strip()
    
    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata.
        
        Args:
            text: Full text to chunk
            metadata: Base metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or len(text) < self.chunk_size:
            return [{
                "text": text,
                "chunk_index": 0,
                "total_chunks": 1,
                **metadata
            }]
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to end at sentence boundary
            if end < len(text):
                # Look for sentence end markers
                for marker in ['. ', '.\n', '? ', '?\n', '! ', '!\n']:
                    last_marker = text.rfind(marker, start + self.chunk_size // 2, end)
                    if last_marker > start:
                        end = last_marker + 1
                        break
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    **metadata
                })
                chunk_index += 1
            
            start = end - self.chunk_overlap
        
        # Add total_chunks to all
        for chunk in chunks:
            chunk["total_chunks"] = len(chunks)
        
        return chunks
    
    def scan_folder(self, folder_path: Path) -> List[Path]:
        """Scan a folder for PDF files.
        
        Args:
            folder_path: Path to scan
            
        Returns:
            List of PDF file paths
        """
        pdf_files = []
        
        if folder_path.exists() and folder_path.is_dir():
            for file_path in folder_path.glob("**/*.pdf"):
                pdf_files.append(file_path)
        
        return pdf_files
    
    def get_domain_from_folder(self, folder_name: str) -> str:
        """Map folder name to domain value.
        
        Args:
            folder_name: Name of the folder (e.g., "Criminal")
            
        Returns:
            Domain value (e.g., "criminal")
        """
        return FOLDER_TO_DOMAIN.get(folder_name, folder_name.lower())
    
    def ingest_all_documents(self) -> List[Dict[str, Any]]:
        """Ingest all PDFs from legal_data subfolders.
        
        Returns:
            List of all document chunks with metadata
        """
        all_chunks = []
        
        if not self.data_dir.exists():
            logger.error(f"Data directory does not exist: {self.data_dir}")
            return all_chunks
        
        # Scan each subdirectory
        for subfolder in self.data_dir.iterdir():
            if subfolder.is_dir() and not subfolder.name.startswith("__"):
                domain = self.get_domain_from_folder(subfolder.name)
                pdf_files = self.scan_folder(subfolder)
                
                logger.info(f"Processing folder '{subfolder.name}' (domain: {domain}) - {len(pdf_files)} PDFs")
                
                for pdf_path in pdf_files:
                    # Extract text
                    text = self.extract_text_from_pdf(pdf_path)
                    
                    if not text:
                        logger.warning(f"No text extracted from {pdf_path.name}")
                        continue
                    
                    # Create metadata
                    metadata = {
                        "source": "pdf",
                        "filename": pdf_path.name,
                        "filepath": str(pdf_path),
                        "category": domain,  # Folder-based category
                        "domain": domain,    # Also as domain for consistency
                        "folder": subfolder.name,
                    }
                    
                    # Chunk the text
                    chunks = self.chunk_text(text, metadata)
                    all_chunks.extend(chunks)
                    
                    logger.info(f"Ingested {pdf_path.name}: {len(chunks)} chunks (domain: {domain})")
        
        logger.info(f"Total documents ingested: {len(all_chunks)} chunks")
        return all_chunks
    
    def ingest_folder(self, folder_name: str) -> List[Dict[str, Any]]:
        """Ingest PDFs from a specific subfolder.
        
        Args:
            folder_name: Name of the subfolder (e.g., "Criminal")
            
        Returns:
            List of document chunks with metadata
        """
        folder_path = self.data_dir / folder_name
        
        if not folder_path.exists():
            logger.error(f"Folder does not exist: {folder_path}")
            return []
        
        domain = self.get_domain_from_folder(folder_name)
        pdf_files = self.scan_folder(folder_path)
        all_chunks = []
        
        for pdf_path in pdf_files:
            text = self.extract_text_from_pdf(pdf_path)
            
            if not text:
                continue
            
            metadata = {
                "source": "pdf",
                "filename": pdf_path.name,
                "filepath": str(pdf_path),
                "category": domain,
                "domain": domain,
                "folder": folder_name,
            }
            
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
        
        logger.info(f"Ingested {len(all_chunks)} chunks from folder '{folder_name}'")
        return all_chunks


# Singleton instance
_pdf_ingestion_service: Optional[PDFIngestionService] = None


def get_pdf_ingestion_service() -> PDFIngestionService:
    """Get or create PDF ingestion service singleton."""
    global _pdf_ingestion_service
    if _pdf_ingestion_service is None:
        _pdf_ingestion_service = PDFIngestionService()
    return _pdf_ingestion_service
