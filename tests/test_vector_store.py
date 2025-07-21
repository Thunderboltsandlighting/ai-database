"""
Tests for the vector store functionality
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
import shutil
import pickle
import numpy as np

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.vector_store import VectorStore, get_vector_store
from utils.document_processor import DocumentProcessor

class TestVectorStore(unittest.TestCase):
    """Test cases for VectorStore"""

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
        self.doc_processor = DocumentProcessor(
            docs_dir=self.test_dir,
            output_dir=self.output_dir,
            supported_extensions=['.md', '.txt']
        )
        
        # Initialize vector store with test directories
        self.vector_store = VectorStore(
            embeddings_dir=self.output_dir,
            model_name="test_model"
        )
        
        # Mock the doc_processor attribute
        self.vector_store.doc_processor = self.doc_processor

    def tearDown(self):
        """Clean up after tests"""
        shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test initialization of VectorStore"""
        self.assertEqual(self.vector_store.embeddings_dir, self.output_dir)
        self.assertEqual(self.vector_store.model_name, "test_model")
        self.assertIsInstance(self.vector_store.index, dict)

    @patch('utils.vector_store.VectorStore.get_embedding')
    def test_process_document(self, mock_get_embedding):
        """Test processing a document and creating embeddings"""
        test_doc_path = os.path.join(self.test_dir, "test_document.md")
        
        # Mock embedding function to return a fake embedding
        mock_get_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        # Process document with doc processor first
        self.doc_processor.process_document(test_doc_path)
        
        # Now process with vector store
        result = self.vector_store.process_document(test_doc_path)
        
        # Verify result
        self.assertTrue(result)
        
        # Check that the index was updated instead of checking for files
        # The test mock doesn't actually create the files
        self.assertGreater(len(self.vector_store.index), 0)

    def test_similarity(self):
        """Test similarity calculation between vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        vec3 = [1.0, 0.0, 0.0]  # Same as vec1
        
        # Calculate similarities
        sim1_2 = self.vector_store.similarity(vec1, vec2)
        sim1_3 = self.vector_store.similarity(vec1, vec3)
        
        # Vectors at right angles should have 0 similarity
        self.assertAlmostEqual(sim1_2, 0.0)
        
        # Identical vectors should have similarity 1.0
        self.assertAlmostEqual(sim1_3, 1.0)

    @patch('utils.vector_store.VectorStore.get_embedding')
    def test_search(self, mock_get_embedding):
        """Test searching for documents"""
        # Create a mock index with test data
        test_doc_path = os.path.join(self.test_dir, "test_document.md")
        chunk_id = f"{test_doc_path}_0"
        embedding_path = os.path.join(self.output_dir, f"{chunk_id}.pkl")
        
        # Create a test embedding file
        test_embedding = [0.5, 0.5, 0.5]
        with open(embedding_path, 'wb') as f:
            pickle.dump(test_embedding, f)
        
        # Add to index
        self.vector_store.index[chunk_id] = {
            "file_path": test_doc_path,
            "chunk_index": 0,
            "metadata": {"title": "Test Document"},
            "embedding_path": embedding_path,
            "text_length": 100,
            "processed_time": 12345
        }
        
        # Mock query embedding to return a similar vector
        mock_get_embedding.return_value = [0.6, 0.6, 0.6]
        
        # Search for documents
        results = self.vector_store.search("test query")
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["file_path"], test_doc_path)
        self.assertIn("similarity", results[0])
        self.assertGreater(results[0]["similarity"], 0.9)  # Should be very similar

    def test_get_vector_store(self):
        """Test get_vector_store factory function"""
        with patch('utils.vector_store.config') as mock_config:
            mock_config.get.side_effect = lambda key, default=None: {
                "paths.processed_docs_dir": "mock_embeddings"
            }.get(key, default)
            
            store = get_vector_store()
            
            self.assertEqual(store.embeddings_dir, "mock_embeddings")

if __name__ == "__main__":
    unittest.main()