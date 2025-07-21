"""
Tests for the document processor functionality
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
import shutil

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.document_processor import DocumentProcessor, get_document_processor
from utils.config import get_config

class TestDocumentProcessor(unittest.TestCase):
    """Test cases for DocumentProcessor"""

    def setUp(self):
        """Set up test environment"""
        # Create temporary directories for test
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.test_dir, "processed")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Copy test document to test directory
        test_doc_path = os.path.join("tests", "test_data", "docs", "test_document.md")
        if os.path.exists(test_doc_path):
            shutil.copy(test_doc_path, self.test_dir)
        
        # Initialize document processor with test directories
        self.processor = DocumentProcessor(
            docs_dir=self.test_dir,
            output_dir=self.output_dir,
            supported_extensions=['.md', '.txt']
        )

    def tearDown(self):
        """Clean up after tests"""
        shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test initialization of DocumentProcessor"""
        self.assertEqual(self.processor.docs_dir, self.test_dir)
        self.assertEqual(self.processor.output_dir, self.output_dir)
        self.assertIn('.md', self.processor.supported_extensions)
        self.assertIn('.txt', self.processor.supported_extensions)

    def test_process_markdown(self):
        """Test processing a markdown document"""
        test_doc_path = os.path.join(self.test_dir, "test_document.md")
        
        # Ensure test document exists
        self.assertTrue(os.path.exists(test_doc_path), "Test document not found")
        
        # Process document
        result = self.processor.process_document(test_doc_path)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["file_type"], "markdown")
        self.assertEqual(result["filename"], "test_document.md")
        self.assertIn("full_text", result)
        self.assertIn("metadata", result)
        
        # Check that processed file was created
        output_path = os.path.join(self.output_dir, "test_document.json")
        self.assertTrue(os.path.exists(output_path))
        
        # Verify processed document content
        with open(output_path, 'r') as f:
            processed_data = json.load(f)
            self.assertEqual(processed_data["file_type"], "markdown")
            self.assertEqual(processed_data["filename"], "test_document.md")
            self.assertIn("Test Medical Billing Document", processed_data["full_text"])

    def test_extract_chunks(self):
        """Test extracting chunks from a document"""
        test_doc_path = os.path.join(self.test_dir, "test_document.md")
        
        # Process document first
        self.processor.process_document(test_doc_path)
        
        # Extract chunks
        chunks = self.processor.extract_chunks(test_doc_path, chunk_size=500, overlap=100)
        
        # Verify chunks
        self.assertGreater(len(chunks), 0)
        self.assertIn("text", chunks[0])
        self.assertIn("metadata", chunks[0])
        self.assertEqual(chunks[0]["metadata"]["file_type"], "markdown")

    def test_search_documents(self):
        """Test searching for documents"""
        test_doc_path = os.path.join(self.test_dir, "test_document.md")
        
        # Process document first
        self.processor.process_document(test_doc_path)
        
        # Search for documents
        results = self.processor.search_documents("medical billing")
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], "test_document.md")

    def test_get_document_processor(self):
        """Test get_document_processor factory function"""
        with patch('utils.document_processor.config') as mock_config:
            mock_config.get.side_effect = lambda key, default=None: {
                "paths.docs_dir": "mock_docs", 
                "paths.processed_docs_dir": "mock_processed"
            }.get(key, default)
            
            processor = get_document_processor()
            
            self.assertEqual(processor.docs_dir, "mock_docs")
            self.assertEqual(processor.output_dir, "mock_processed")

if __name__ == "__main__":
    unittest.main()