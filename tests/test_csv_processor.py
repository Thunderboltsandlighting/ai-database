import pandas as pd
import pytest
import tempfile
import os
from pathlib import Path
from utils.csv_processor import (
    count_csv_rows,
    estimate_memory_usage,
    get_optimal_chunksize,
    process_csv_in_chunks,
    read_csv_sample,
    detect_csv_dialect
)

@pytest.fixture
def sample_csv_file():
    """Create a temporary CSV file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        temp_path = temp_file.name
        # Write CSV data
        temp_file.write(b"Name,Age,City,Salary\n")
        for i in range(1000):
            temp_file.write(f"Person{i},30,New York,{50000 + i}\n".encode())
    
    yield temp_path
    
    # Clean up temp file
    if os.path.exists(temp_path):
        os.unlink(temp_path)

def test_count_csv_rows(sample_csv_file):
    """Test counting CSV rows"""
    # Should be 1001 rows (1000 data rows + header)
    assert count_csv_rows(sample_csv_file) == 1001

def test_estimate_memory_usage(sample_csv_file):
    """Test memory usage estimation"""
    estimate = estimate_memory_usage(sample_csv_file, sample_rows=100)
    
    # Check structure
    assert 'sample_rows' in estimate
    assert 'total_rows' in estimate
    assert 'estimated_total_memory_bytes' in estimate
    
    # Check values
    assert estimate['total_rows'] == 1000
    assert estimate['sample_rows'] == 100
    assert estimate['estimated_total_memory_bytes'] > 0

def test_get_optimal_chunksize(sample_csv_file):
    """Test chunk size calculation"""
    chunk_size = get_optimal_chunksize(sample_csv_file)
    
    # Chunk size should be a reasonable number
    assert chunk_size >= 1000
    assert chunk_size <= 100000

def test_process_csv_in_chunks(sample_csv_file):
    """Test processing CSV in chunks"""
    # Define a simple processing function
    def process_chunk(chunk, chunk_index):
        return {
            "successful": len(chunk),
            "failed": 0,
            "sum": chunk['Salary'].sum(),
            "issues": []
        }
    
    # Process the CSV
    result = process_csv_in_chunks(
        sample_csv_file,
        process_chunk,
        chunk_size=200
    )
    
    # Check results
    assert result['success'] is True
    assert result['total_rows_processed'] == 1000
    assert result['successful_rows'] == 1000
    assert result['failed_rows'] == 0
    assert 'total_time_seconds' in result
    
    # Should have 5 chunks (1000 rows / 200 rows per chunk)
    assert result['chunks_processed'] == 5
    assert len(result['chunk_results']) == 5

def test_read_csv_sample(sample_csv_file):
    """Test reading a sample from a CSV"""
    sample_df = read_csv_sample(sample_csv_file, sample_rows=50)
    
    # Check the sample
    assert not sample_df.empty
    assert len(sample_df) <= 50
    assert all(col in sample_df.columns for col in ['Name', 'Age', 'City', 'Salary'])

def test_detect_csv_dialect(sample_csv_file):
    """Test CSV dialect detection"""
    dialect = detect_csv_dialect(sample_csv_file)
    
    # Check the detected dialect
    assert dialect['delimiter'] == ','
    assert dialect['has_header'] is True