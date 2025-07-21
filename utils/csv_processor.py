"""
Utility functions for efficient CSV processing in the Medical Billing system.
This module provides tools for handling large CSV files with memory efficiency.
"""

import os
import pandas as pd
import numpy as np
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable, Iterator, Tuple
import logging

from utils.logger import get_logger
from utils.config import get_config

# Get configuration and logger
logger = get_logger()
config = get_config()

def count_csv_rows(file_path: Union[str, Path]) -> int:
    """
    Count the number of rows in a CSV file without loading it into memory.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        The number of rows in the file (including header)
    """
    try:
        with open(file_path, 'r') as f:
            row_count = sum(1 for _ in f)
        logger.debug(f"Counted {row_count} rows in {file_path}")
        return row_count
    except Exception as e:
        logger.error(f"Error counting rows in {file_path}: {e}")
        return 0

def estimate_memory_usage(file_path: Union[str, Path], sample_rows: int = 1000) -> Dict[str, Any]:
    """
    Estimate memory usage for a CSV file based on a sample.
    
    Args:
        file_path: Path to the CSV file
        sample_rows: Number of rows to sample
        
    Returns:
        Dictionary with memory usage information
    """
    try:
        # Count total rows
        total_rows = count_csv_rows(file_path) - 1  # Subtract header
        
        # Read a sample
        sample_df = pd.read_csv(file_path, nrows=min(sample_rows, total_rows))
        
        # Calculate memory usage
        memory_usage = sample_df.memory_usage(deep=True).sum()
        estimated_total = (memory_usage / len(sample_df)) * total_rows
        
        result = {
            "sample_rows": len(sample_df),
            "total_rows": total_rows,
            "columns": len(sample_df.columns),
            "sample_memory_bytes": memory_usage,
            "estimated_total_memory_bytes": estimated_total,
            "estimated_total_memory_mb": estimated_total / (1024 * 1024),
            "column_memory": {col: sample_df[col].memory_usage(deep=True) / len(sample_df) for col in sample_df.columns}
        }
        
        logger.debug(f"Estimated memory for {file_path}: {result['estimated_total_memory_mb']:.2f} MB")
        return result
        
    except Exception as e:
        logger.error(f"Error estimating memory usage for {file_path}: {e}")
        return {
            "error": str(e),
            "total_rows": count_csv_rows(file_path) - 1  # Subtract header
        }

def get_optimal_chunksize(file_path: Union[str, Path], target_chunk_mb: float = 100) -> int:
    """
    Calculate optimal chunk size for processing a CSV file.
    
    Args:
        file_path: Path to the CSV file
        target_chunk_mb: Target chunk size in MB
        
    Returns:
        Number of rows per chunk
    """
    try:
        # Get memory estimate
        mem_estimate = estimate_memory_usage(file_path)
        
        if "error" in mem_estimate:
            # Default to 10,000 rows if estimation fails
            logger.warning(f"Using default chunk size of 10,000 rows for {file_path}")
            return 10000
            
        # Calculate rows per MB
        rows_per_mb = mem_estimate["sample_rows"] / (mem_estimate["sample_memory_bytes"] / (1024 * 1024))
        
        # Calculate chunk size
        chunk_size = int(rows_per_mb * target_chunk_mb)
        
        # Ensure chunk size is reasonable
        chunk_size = max(1000, min(chunk_size, 100000))
        
        logger.debug(f"Calculated optimal chunk size for {file_path}: {chunk_size} rows")
        return chunk_size
        
    except Exception as e:
        logger.error(f"Error calculating chunk size for {file_path}: {e}")
        return 10000  # Default

def process_csv_in_chunks(
    file_path: Union[str, Path], 
    process_chunk: Callable[[pd.DataFrame, int], Dict],
    chunk_size: Optional[int] = None,
    max_chunks: Optional[int] = None
) -> Dict:
    """
    Process a large CSV file in chunks to minimize memory usage.
    
    Args:
        file_path: Path to the CSV file
        process_chunk: Function that processes each chunk and returns a dictionary of results
        chunk_size: Number of rows in each chunk (calculated automatically if not provided)
        max_chunks: Maximum number of chunks to process (None for all)
        
    Returns:
        Dictionary with processing results
    """
    start_time = time.time()
    file_path = Path(file_path)
    
    try:
        # Determine chunk size if not provided
        if chunk_size is None:
            chunk_size = get_optimal_chunksize(file_path)
        
        # Check if file exists
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        # Initialize results
        results = {
            "success": True,
            "file_path": str(file_path),
            "total_rows_processed": 0,
            "chunks_processed": 0,
            "successful_rows": 0,
            "failed_rows": 0,
            "issues": [],
            "chunk_results": []
        }
        
        # Process in chunks
        logger.info(f"Processing {file_path} in chunks of {chunk_size} rows")
        
        # Create a chunked reader
        reader = pd.read_csv(file_path, chunksize=chunk_size)
        
        # Process each chunk
        for i, chunk in enumerate(reader):
            if max_chunks and i >= max_chunks:
                logger.info(f"Reached maximum chunk limit ({max_chunks}), stopping")
                break
                
            chunk_start = time.time()
            logger.debug(f"Processing chunk {i+1} with {len(chunk)} rows")
            
            # Process the chunk
            chunk_result = process_chunk(chunk, i)
            
            # Update overall results
            results["total_rows_processed"] += len(chunk)
            results["chunks_processed"] += 1
            results["successful_rows"] += chunk_result.get("successful", 0)
            results["failed_rows"] += chunk_result.get("failed", 0)
            
            # Add any issues
            if "issues" in chunk_result:
                results["issues"].extend(chunk_result["issues"])
            
            # Add chunk result
            results["chunk_results"].append({
                "chunk": i+1,
                "rows": len(chunk),
                "time_seconds": time.time() - chunk_start,
                **{k: v for k, v in chunk_result.items() if k not in ["issues"]}
            })
            
            # Log progress
            logger.debug(f"Completed chunk {i+1} in {time.time() - chunk_start:.2f} seconds")
        
        # Calculate overall metrics
        results["total_time_seconds"] = time.time() - start_time
        results["rows_per_second"] = results["total_rows_processed"] / results["total_time_seconds"] if results["total_time_seconds"] > 0 else 0
        
        logger.info(f"Completed processing {results['total_rows_processed']} rows in {results['total_time_seconds']:.2f} seconds")
        
        return results
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error processing CSV in chunks: {e}")
        return {
            "success": False,
            "file_path": str(file_path),
            "error": str(e),
            "total_time_seconds": elapsed
        }

def read_csv_sample(file_path: Union[str, Path], sample_rows: int = 100) -> pd.DataFrame:
    """
    Read a sample of rows from a CSV file.
    
    Args:
        file_path: Path to the CSV file
        sample_rows: Number of rows to sample
        
    Returns:
        DataFrame with sampled rows
    """
    try:
        # Count total rows
        total_rows = count_csv_rows(file_path) - 1  # Subtract header
        
        if total_rows <= sample_rows:
            # Just read the whole file if it's small
            logger.debug(f"Reading entire file {file_path} ({total_rows} rows)")
            return pd.read_csv(file_path)
        
        # Generate random row indices
        row_indices = sorted(np.random.choice(range(1, total_rows+1), 
                                     size=min(sample_rows - 10, total_rows - 10), 
                                     replace=False))
        
        # Always include the first 10 rows for context
        top_rows = list(range(1, min(11, total_rows+1)))
        combined_indices = sorted(list(set(top_rows + row_indices)))
        
        # Ensure we don't exceed the requested sample size
        if len(combined_indices) > sample_rows:
            combined_indices = combined_indices[:sample_rows]
        
        # Read specific rows
        df_chunks = []
        current_pos = 0
        
        with open(file_path, 'r') as f:
            # Always read header
            header = f.readline().strip()
            
            for row_num, line in enumerate(f, start=1):
                if row_num in combined_indices:
                    df_chunks.append(pd.DataFrame([line.strip().split(',')]))
        
        if df_chunks:
            # Combine chunks and set column names
            df = pd.concat(df_chunks, ignore_index=True)
            df.columns = header.split(',')
            
            logger.debug(f"Read {len(df)} sample rows from {file_path}")
            return df
        else:
            # Fallback to simple sampling
            logger.debug(f"Using simpler sampling method for {file_path}")
            return pd.read_csv(file_path, nrows=sample_rows)
            
    except Exception as e:
        logger.error(f"Error reading CSV sample from {file_path}: {e}")
        # Fallback to simple approach
        try:
            return pd.read_csv(file_path, nrows=sample_rows)
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")
            return pd.DataFrame()

def detect_csv_dialect(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Detect the dialect of a CSV file (delimiter, quote character, etc.).
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Dictionary with dialect information
    """
    import csv
    
    try:
        with open(file_path, 'r', newline='') as f:
            sample = f.read(4096)
            
        dialect = csv.Sniffer().sniff(sample)
        
        result = {
            "delimiter": dialect.delimiter,
            "quotechar": dialect.quotechar,
            "escapechar": dialect.escapechar,
            "doublequote": dialect.doublequote,
            "has_header": csv.Sniffer().has_header(sample)
        }
        
        logger.debug(f"Detected CSV dialect for {file_path}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error detecting CSV dialect for {file_path}: {e}")
        return {
            "delimiter": ",",
            "quotechar": '"',
            "doublequote": True,
            "has_header": True
        }