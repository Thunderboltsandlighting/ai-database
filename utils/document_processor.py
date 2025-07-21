"""
Document Processing Module for HVLC_DB

This module provides functions for processing various document types (PDF, docx, etc.)
and extracting their content for inclusion in the vector database for RAG capabilities.
"""

import os
import re
import json
import fitz  # PyMuPDF
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
from PIL import Image
import io

from utils.config import get_config
from utils.logger import get_logger

logger = get_logger()
config = get_config()

class DocumentProcessor:
    """Processes various document types and extracts content for RAG"""
    
    def __init__(self, 
                 docs_dir: str = None,
                 output_dir: str = None,
                 supported_extensions: List[str] = None):
        """Initialize document processor
        
        Args:
            docs_dir: Directory to scan for documents
            output_dir: Directory to save processed documents
            supported_extensions: List of supported file extensions (e.g., ['.pdf', '.docx'])
        """
        self.docs_dir = docs_dir or config.get("paths.docs_dir", "docs")
        self.output_dir = output_dir or config.get("paths.processed_docs_dir", "docs/processed")
        self.supported_extensions = supported_extensions or ['.pdf', '.txt', '.md']
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize document tracking
        self.processed_docs = []
        self._load_processed_docs()
    
    def _load_processed_docs(self):
        """Load list of already processed documents"""
        tracking_file = os.path.join(self.output_dir, "processed_docs.json")
        if os.path.exists(tracking_file):
            try:
                with open(tracking_file, 'r') as f:
                    self.processed_docs = json.load(f)
                logger.info(f"Loaded {len(self.processed_docs)} processed document records")
            except Exception as e:
                logger.error(f"Error loading processed documents: {e}")
                self.processed_docs = []
    
    def _save_processed_docs(self):
        """Save list of processed documents"""
        tracking_file = os.path.join(self.output_dir, "processed_docs.json")
        try:
            with open(tracking_file, 'w') as f:
                json.dump(self.processed_docs, f, indent=2)
            logger.info(f"Saved {len(self.processed_docs)} processed document records")
        except Exception as e:
            logger.error(f"Error saving processed documents: {e}")
    
    def process_all_documents(self, force_reprocess: bool = False) -> List[Dict]:
        """Process all documents in the docs directory
        
        Args:
            force_reprocess: If True, reprocess documents even if already processed
            
        Returns:
            List of document metadata dictionaries
        """
        logger.info(f"Processing documents in {self.docs_dir}")
        
        processed_docs = []
        for root, _, files in os.walk(self.docs_dir):
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                
                if ext.lower() not in self.supported_extensions:
                    continue
                
                # Check if already processed and not forcing reprocess
                if not force_reprocess and self._is_processed(file_path):
                    logger.info(f"Skipping already processed document: {file_path}")
                    # Get the existing metadata
                    for doc in self.processed_docs:
                        if doc["file_path"] == file_path:
                            processed_docs.append(doc)
                            break
                    continue
                
                try:
                    logger.info(f"Processing document: {file_path}")
                    doc_metadata = self.process_document(file_path)
                    if doc_metadata:
                        processed_docs.append(doc_metadata)
                except Exception as e:
                    logger.error(f"Error processing document {file_path}: {e}")
        
        return processed_docs
    
    def _is_processed(self, file_path: str) -> bool:
        """Check if document has already been processed"""
        for doc in self.processed_docs:
            if doc["file_path"] == file_path:
                # Check if the file has been modified since processing
                last_modified = os.path.getmtime(file_path)
                processed_time = doc.get("processed_time", 0)
                if last_modified > processed_time:
                    return False  # File has been modified, reprocess
                return True
        return False
    
    def process_document(self, file_path: str) -> Optional[Dict]:
        """Process a single document and extract content
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with document metadata and extracted content
        """
        if not os.path.exists(file_path):
            logger.error(f"Document not found: {file_path}")
            return None
            
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.pdf':
            doc_metadata = self._process_pdf(file_path)
        elif ext == '.txt':
            doc_metadata = self._process_text(file_path)
        elif ext == '.md':
            doc_metadata = self._process_markdown(file_path)
        else:
            logger.warning(f"Unsupported document type: {ext}")
            return None
            
        # Add to processed documents list
        if doc_metadata:
            # Check if already in processed_docs
            for i, doc in enumerate(self.processed_docs):
                if doc["file_path"] == file_path:
                    self.processed_docs[i] = doc_metadata
                    break
            else:
                self.processed_docs.append(doc_metadata)
            
            self._save_processed_docs()
            
        return doc_metadata
    
    def _process_pdf(self, file_path: str) -> Dict:
        """Process a PDF document
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with document metadata and extracted content
        """
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(file_path)
            
            # Extract text from all pages
            full_text = ""
            page_texts = []
            images = []
            
            for i, page in enumerate(doc):
                # Extract text
                page_text = page.get_text()
                page_texts.append(page_text)
                full_text += page_text + "\n\n"
                
                # Extract images
                image_list = page.get_images(full=True)
                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Save image to memory and get dimensions
                    try:
                        image = Image.open(io.BytesIO(image_bytes))
                        width, height = image.size
                        image_format = image.format.lower() if image.format else "unknown"
                        
                        # Save image metadata
                        image_meta = {
                            "page": i,
                            "index": img_index,
                            "width": width,
                            "height": height,
                            "format": image_format
                        }
                        images.append(image_meta)
                    except Exception as e:
                        logger.warning(f"Error processing image in PDF: {e}")
            
            # Extract document metadata
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
                "page_count": len(doc),
                "image_count": len(images)
            }
            
            # Create document metadata
            result = {
                "file_path": file_path,
                "file_type": "pdf",
                "filename": os.path.basename(file_path),
                "processed_time": datetime.now().timestamp(),
                "metadata": metadata,
                "full_text": full_text,
                "page_count": len(doc),
                "images": images,
                "pages": [{"page_num": i, "text": text} for i, text in enumerate(page_texts)]
            }
            
            # Save processed text to output directory
            base_name = os.path.basename(file_path).replace('.pdf', '')
            output_path = os.path.join(self.output_dir, f"{base_name}.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Processed PDF: {file_path} ({len(doc)} pages, {len(images)} images)")
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            return {
                "file_path": file_path,
                "file_type": "pdf",
                "filename": os.path.basename(file_path),
                "processed_time": datetime.now().timestamp(),
                "error": str(e)
            }
    
    def _process_text(self, file_path: str) -> Dict:
        """Process a plain text document
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Dictionary with document metadata and extracted content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into lines for easier processing
            lines = content.split('\n')
            
            # Try to extract title from first line
            title = lines[0].strip() if lines else ""
            
            # Create document metadata
            result = {
                "file_path": file_path,
                "file_type": "text",
                "filename": os.path.basename(file_path),
                "processed_time": datetime.now().timestamp(),
                "metadata": {
                    "title": title,
                    "line_count": len(lines)
                },
                "full_text": content
            }
            
            # Save processed text to output directory
            base_name = os.path.basename(file_path).replace('.txt', '')
            output_path = os.path.join(self.output_dir, f"{base_name}.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Processed text file: {file_path} ({len(lines)} lines)")
            return result
            
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            return {
                "file_path": file_path,
                "file_type": "text",
                "filename": os.path.basename(file_path),
                "processed_time": datetime.now().timestamp(),
                "error": str(e)
            }
    
    def _process_markdown(self, file_path: str) -> Dict:
        """Process a markdown document
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Dictionary with document metadata and extracted content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract headers
            headers = []
            for line in content.split('\n'):
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    text = line.lstrip('#').strip()
                    headers.append({"level": level, "text": text})
            
            # Try to extract title from first header
            title = headers[0]["text"] if headers else os.path.basename(file_path)
            
            # Create document metadata
            result = {
                "file_path": file_path,
                "file_type": "markdown",
                "filename": os.path.basename(file_path),
                "processed_time": datetime.now().timestamp(),
                "metadata": {
                    "title": title,
                    "headers": headers
                },
                "full_text": content
            }
            
            # Save processed markdown to output directory
            base_name = os.path.basename(file_path).replace('.md', '')
            output_path = os.path.join(self.output_dir, f"{base_name}.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Processed markdown file: {file_path} ({len(headers)} headers)")
            return result
            
        except Exception as e:
            logger.error(f"Error processing markdown file {file_path}: {e}")
            return {
                "file_path": file_path,
                "file_type": "markdown",
                "filename": os.path.basename(file_path),
                "processed_time": datetime.now().timestamp(),
                "error": str(e)
            }
    
    def get_document_content(self, file_path: str) -> Optional[Dict]:
        """Get processed content for a document
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with document metadata and content, or None if not processed
        """
        # Check if document has been processed
        for doc in self.processed_docs:
            if doc["file_path"] == file_path:
                # If document has an error, return None
                if "error" in doc:
                    return None
                    
                # If document is in processed_docs but JSON file doesn't exist, reprocess
                base_name = os.path.basename(file_path)
                base_name = os.path.splitext(base_name)[0]
                output_path = os.path.join(self.output_dir, f"{base_name}.json")
                
                if not os.path.exists(output_path):
                    return self.process_document(file_path)
                
                # Load from JSON file
                try:
                    with open(output_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error loading processed document {file_path}: {e}")
                    return None
        
        # Document not processed yet, process it now
        return self.process_document(file_path)
    
    def search_documents(self, query: str, limit: int = 5) -> List[Dict]:
        """Simple text-based search across processed documents
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching document metadata
        """
        query = query.lower()
        results = []
        
        for doc_meta in self.processed_docs:
            if "error" in doc_meta:
                continue
                
            # Get full document content
            doc_content = self.get_document_content(doc_meta["file_path"])
            if not doc_content:
                continue
            
            # Simple text matching
            full_text = doc_content.get("full_text", "").lower()
            if query in full_text:
                # Calculate rough relevance score based on frequency
                relevance = full_text.count(query) / len(full_text) * 1000
                
                # Boost score if query appears in title
                title = doc_content.get("metadata", {}).get("title", "").lower()
                if query in title:
                    relevance *= 2
                
                results.append({
                    "file_path": doc_meta["file_path"],
                    "file_type": doc_meta["file_type"],
                    "filename": doc_meta["filename"],
                    "title": doc_content.get("metadata", {}).get("title", ""),
                    "relevance": relevance
                })
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    def extract_chunks(self, file_path: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
        """Extract text chunks from a document for vector embedding
        
        Args:
            file_path: Path to the document file
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        doc_content = self.get_document_content(file_path)
        if not doc_content:
            return []
            
        full_text = doc_content.get("full_text", "")
        if not full_text:
            return []
            
        # For PDFs, split by pages first
        if doc_content.get("file_type") == "pdf":
            chunks = []
            for page in doc_content.get("pages", []):
                page_num = page.get("page_num", 0)
                page_text = page.get("text", "")
                
                # Skip empty pages
                if not page_text.strip():
                    continue
                    
                # Split page into chunks
                page_chunks = self._split_text(page_text, chunk_size, overlap)
                
                # Add page metadata to each chunk
                for i, chunk_text in enumerate(page_chunks):
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "file_path": file_path,
                            "file_type": doc_content.get("file_type"),
                            "title": doc_content.get("metadata", {}).get("title", ""),
                            "page": page_num,
                            "chunk": i
                        }
                    })
            
            return chunks
            
        # For other document types, split the full text
        text_chunks = self._split_text(full_text, chunk_size, overlap)
        
        # Create chunk dictionaries
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "file_path": file_path,
                    "file_type": doc_content.get("file_type"),
                    "title": doc_content.get("metadata", {}).get("title", ""),
                    "chunk": i
                }
            })
        
        return chunks
    
    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into chunks with overlap
        
        Args:
            text: Text to split
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        # If text is smaller than chunk size, return as is
        if len(text) <= chunk_size:
            return [text]
            
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk with potential overlap into next chunk
            end = start + chunk_size
            
            # If we're at the end of the text, just use the rest
            if end >= len(text):
                chunks.append(text[start:])
                break
                
            # Try to find a good splitting point (end of sentence, paragraph, etc.)
            split_point = self._find_split_point(text, end)
            
            chunks.append(text[start:split_point])
            
            # Start next chunk with overlap
            start = split_point - overlap
            if start < 0:
                start = 0
        
        return chunks
    
    def _find_split_point(self, text: str, position: int) -> int:
        """Find a good point to split text (end of sentence, paragraph)
        
        Args:
            text: Text to split
            position: Target position to split near
            
        Returns:
            Position to split at
        """
        # Search window
        window_size = 100  # characters to look forward
        end = min(position + window_size, len(text))
        search_text = text[position:end]
        
        # Look for paragraph break
        match = re.search(r'\n\s*\n', search_text)
        if match:
            return position + match.start() + 1
            
        # Look for end of sentence
        match = re.search(r'[.!?]\s+', search_text)
        if match:
            return position + match.end()
            
        # Look for end of line
        match = re.search(r'\n', search_text)
        if match:
            return position + match.end()
            
        # If no good split found, split at target position
        return position

def get_document_processor() -> DocumentProcessor:
    """Get document processor instance with default configuration"""
    docs_dir = config.get("paths.docs_dir", "docs")
    output_dir = config.get("paths.processed_docs_dir", "docs/processed")
    
    return DocumentProcessor(docs_dir=docs_dir, output_dir=output_dir)

# For command-line usage
if __name__ == "__main__":
    import sys
    
    # Process all documents
    processor = get_document_processor()
    
    if len(sys.argv) > 1:
        # Process specific file
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            doc_meta = processor.process_document(file_path)
            if doc_meta:
                print(f"Successfully processed: {file_path}")
                print(f"Title: {doc_meta.get('metadata', {}).get('title', 'Unknown')}")
                if doc_meta.get("file_type") == "pdf":
                    print(f"Pages: {doc_meta.get('page_count', 0)}")
                    print(f"Images: {doc_meta.get('metadata', {}).get('image_count', 0)}")
            else:
                print(f"Failed to process: {file_path}")
    else:
        # Process all documents
        docs = processor.process_all_documents()
        print(f"Processed {len(docs)} documents")
        
        # Show summary
        pdf_count = sum(1 for doc in docs if doc.get("file_type") == "pdf")
        text_count = sum(1 for doc in docs if doc.get("file_type") == "text")
        md_count = sum(1 for doc in docs if doc.get("file_type") == "markdown")
        
        print(f"PDF documents: {pdf_count}")
        print(f"Text documents: {text_count}")
        print(f"Markdown documents: {md_count}")