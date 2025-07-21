"""
Vector Store Module for HVLC_DB

This module provides functionality for creating and searching vector embeddings
for documents processed by the document processor.
"""

import os
import json
import numpy as np
import pickle
from typing import Dict, List, Optional, Union, Any
import logging
from pathlib import Path
import requests
from datetime import datetime

from utils.config import get_config
from utils.logger import get_logger
from utils.document_processor import DocumentProcessor, get_document_processor

logger = get_logger()
config = get_config()

class VectorStore:
    """Manages vector embeddings for document chunks"""
    
    def __init__(self, 
                embeddings_dir: str = None,
                model_name: str = None):
        """Initialize vector store
        
        Args:
            embeddings_dir: Directory to store embeddings
            model_name: Name of the embedding model to use
        """
        self.embeddings_dir = embeddings_dir or config.get("paths.processed_docs_dir", "docs/processed")
        self.model_name = model_name or config.get("ollama.laptop_model", "llama3.1:8b")
        
        # Ensure embeddings directory exists
        os.makedirs(self.embeddings_dir, exist_ok=True)
        
        # Load index if it exists
        self.index = {}
        self._load_index()
        
        # Initialize document processor
        self.doc_processor = get_document_processor()
    
    def _load_index(self):
        """Load vector index from disk"""
        index_path = os.path.join(self.embeddings_dir, "vector_index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    self.index = json.load(f)
                logger.info(f"Loaded vector index with {len(self.index)} entries")
            except Exception as e:
                logger.error(f"Error loading vector index: {e}")
                self.index = {}
    
    def _save_index(self):
        """Save vector index to disk"""
        index_path = os.path.join(self.embeddings_dir, "vector_index.json")
        try:
            with open(index_path, 'w') as f:
                json.dump(self.index, f, indent=2)
            logger.info(f"Saved vector index with {len(self.index)} entries")
        except Exception as e:
            logger.error(f"Error saving vector index: {e}")
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using Ollama API
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        # Use the first available Ollama endpoint
        ollama_url = config.get("ollama.homelab_url", "http://localhost:11434")
        fallback_url = config.get("ollama.laptop_url", "http://localhost:11434")
        
        urls = [ollama_url, fallback_url]
        
        for url in urls:
            try:
                api_url = f"{url}/api/embeddings"
                response = requests.post(
                    api_url,
                    json={
                        "model": self.model_name,
                        "prompt": text
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("embedding", [])
                    
            except Exception as e:
                logger.warning(f"Error getting embedding from {url}: {e}")
                continue
        
        logger.error("Failed to get embedding from any Ollama endpoint")
        return None
    
    def process_document(self, file_path: str, force_reprocess: bool = False) -> bool:
        """Process document and create embeddings for its chunks
        
        Args:
            file_path: Path to document file
            force_reprocess: If True, reprocess even if already processed
            
        Returns:
            True if processing succeeded, False otherwise
        """
        # Check if already processed
        if not force_reprocess and self._is_document_processed(file_path):
            logger.info(f"Document already processed: {file_path}")
            return True
        
        # Extract chunks from document
        chunks = self.doc_processor.extract_chunks(file_path)
        if not chunks:
            logger.warning(f"No chunks extracted from document: {file_path}")
            return False
        
        # Create embeddings for chunks
        logger.info(f"Creating embeddings for {len(chunks)} chunks from {file_path}")
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_path}_{i}"
            
            # Check if we already have an embedding for this chunk
            if not force_reprocess and chunk_id in self.index:
                continue
                
            # Get embedding for chunk text
            embedding = self.get_embedding(chunk["text"])
            if not embedding:
                logger.warning(f"Failed to get embedding for chunk {i} of {file_path}")
                continue
                
            # Save embedding to disk
            embedding_path = os.path.join(self.embeddings_dir, f"{chunk_id}.pkl")
            try:
                with open(embedding_path, 'wb') as f:
                    pickle.dump(embedding, f)
                
                # Add to index
                self.index[chunk_id] = {
                    "file_path": file_path,
                    "chunk_index": i,
                    "metadata": chunk["metadata"],
                    "embedding_path": embedding_path,
                    "text_length": len(chunk["text"]),
                    "processed_time": datetime.now().timestamp()
                }
                
            except Exception as e:
                logger.error(f"Error saving embedding for chunk {i} of {file_path}: {e}")
        
        # Save updated index
        self._save_index()
        return True
    
    def _is_document_processed(self, file_path: str) -> bool:
        """Check if document has embeddings in the index"""
        for chunk_id, chunk_info in self.index.items():
            if chunk_info["file_path"] == file_path:
                return True
        return False
    
    def process_all_documents(self, force_reprocess: bool = False) -> int:
        """Process all documents in the docs directory
        
        Args:
            force_reprocess: If True, reprocess all documents
            
        Returns:
            Number of documents successfully processed
        """
        # Get all processed documents
        processed_docs = self.doc_processor.process_all_documents(force_reprocess)
        
        # Create embeddings for each document
        processed_count = 0
        for doc in processed_docs:
            if "error" in doc:
                continue
                
            file_path = doc["file_path"]
            success = self.process_document(file_path, force_reprocess)
            if success:
                processed_count += 1
        
        return processed_count
    
    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (0-1)
        """
        # Convert to numpy arrays
        a = np.array(vec1)
        b = np.array(vec2)
        
        # Calculate cosine similarity
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for documents similar to query
        
        Args:
            query: Query string
            top_k: Number of results to return
            
        Returns:
            List of document chunks with similarity scores
        """
        # Get embedding for query
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            logger.error("Failed to get embedding for query")
            return []
        
        # Calculate similarity with all document chunks
        results = []
        
        for chunk_id, chunk_info in self.index.items():
            # Load embedding
            embedding_path = chunk_info["embedding_path"]
            if not os.path.exists(embedding_path):
                continue
                
            try:
                with open(embedding_path, 'rb') as f:
                    chunk_embedding = pickle.load(f)
                
                # Calculate similarity
                sim_score = self.similarity(query_embedding, chunk_embedding)
                
                # Add to results
                results.append({
                    "chunk_id": chunk_id,
                    "file_path": chunk_info["file_path"],
                    "metadata": chunk_info["metadata"],
                    "similarity": sim_score
                })
                
            except Exception as e:
                logger.error(f"Error loading embedding {embedding_path}: {e}")
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Return top k results
        return results[:top_k]
    
    def get_chunks_text(self, search_results: List[Dict]) -> List[Dict]:
        """Get text for chunks from search results
        
        Args:
            search_results: List of search results from search()
            
        Returns:
            List of search results with added text field
        """
        results_with_text = []
        
        for result in search_results:
            chunk_id = result["chunk_id"]
            file_path = result["file_path"]
            chunk_index = int(chunk_id.split("_")[-1])
            
            # Get document content
            doc_content = self.doc_processor.get_document_content(file_path)
            if not doc_content:
                continue
            
            # Get chunks
            chunks = self.doc_processor.extract_chunks(file_path)
            if not chunks or chunk_index >= len(chunks):
                continue
            
            # Get text for this chunk
            chunk_text = chunks[chunk_index]["text"]
            
            # Add to results
            result_with_text = result.copy()
            result_with_text["text"] = chunk_text
            results_with_text.append(result_with_text)
        
        return results_with_text

def get_vector_store() -> VectorStore:
    """Get vector store instance with default configuration"""
    embeddings_dir = config.get("paths.processed_docs_dir", "docs/processed")
    
    return VectorStore(embeddings_dir=embeddings_dir)

# For command-line usage
if __name__ == "__main__":
    import sys
    
    # Process all documents
    vector_store = get_vector_store()
    
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        # Search for documents
        if len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            print(f"Searching for: {query}")
            
            results = vector_store.search(query)
            results_with_text = vector_store.get_chunks_text(results)
            
            print(f"Found {len(results_with_text)} results:")
            for i, result in enumerate(results_with_text):
                print(f"Result {i+1} (Similarity: {result['similarity']:.4f}):")
                print(f"File: {result['file_path']}")
                print(f"Title: {result['metadata'].get('title', 'Unknown')}")
                print(f"Text: {result['text'][:200]}...")
                print()
    else:
        # Process all documents
        count = vector_store.process_all_documents()
        print(f"Processed {count} documents")