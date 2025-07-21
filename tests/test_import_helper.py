"""
Test suite for CSV import helper.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.import_helper import ImportHelper, import_file, import_directory
from utils.format_detector import ReportFormatDetector
from utils.report_transformer import ReportTransformer
from medical_billing_db import MedicalBillingDB


def create_test_csv(content, filename=None):
    """Create a test CSV file
    
    Args:
        content: CSV content as string
        filename: Optional filename, if None a temporary file is created
        
    Returns:
        Path to created file
    """
    if filename:
        filepath = os.path.join(tempfile.gettempdir(), filename)
    else:
        fd, filepath = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        
    with open(filepath, "w") as f:
        f.write(content)
        
    return filepath


@pytest.fixture
def cc_payment_csv():
    """Fixture for credit card payment CSV"""
    content = """Trans. #,Trans. Date,Settle Date,Gross Amt,Disc. Fee,Per Trans. Fee,Net Amt,Acct Type,Acct Details,Trans. Type,Payer Name,Client Name,Provider
9690,01-04-2025,01-04-2025,55,-1.64,-0.3,53.06,Visa,3563,CC,None None,Kate Martin,Tammy Maxey
9691,01-04-2025,01-04-2025,50,-1.5,-0.3,48.2,Visa,9416,CC,None None,Isabel Rehak,Tammy Maxey
9692,01-04-2025,01-04-2025,10,-0.3,-0.3,9.4,Visa,6292,CC,None None,Jill Tulloch,Tammy Maxey"""
    return create_test_csv(content, "cc_payment_test.csv")


@pytest.fixture
def insurance_claims_csv():
    """Fixture for insurance claims CSV"""
    content = """RowId,Check Date,Date Posted,Check Number,Payment From,Reference,Check Amount,Cash Applied,Provider
4393,6/10/25,6/10/25,825156000193521,Aetna,ERAM_AVAILITY_825156000193521_060525_1026.MCP.xml,138.61,,Sidney Snipes
4394,,,,Aetna,Sess:05-22-2025(Michael Dages),,138.61,Sidney Snipes
4371,5/14/25,6/5/25,,Ashley Shumaker,Paid at session,20,,Sidney Snipes"""
    return create_test_csv(content, "insurance_claims_test.csv")


@pytest.fixture
def csv_directory():
    """Fixture for directory with CSVs"""
    directory = tempfile.mkdtemp()
    
    # Create CC payment CSV
    cc_content = """Trans. #,Trans. Date,Settle Date,Gross Amt,Disc. Fee,Per Trans. Fee,Net Amt,Acct Type,Acct Details,Trans. Type,Payer Name,Client Name,Provider
9690,01-04-2025,01-04-2025,55,-1.64,-0.3,53.06,Visa,3563,CC,None None,Kate Martin,Tammy Maxey"""
    
    with open(os.path.join(directory, "cc_payment.csv"), "w") as f:
        f.write(cc_content)
    
    # Create insurance claims CSV
    insurance_content = """RowId,Check Date,Date Posted,Check Number,Payment From,Reference,Check Amount,Cash Applied,Provider
4393,6/10/25,6/10/25,825156000193521,Aetna,ERAM_AVAILITY_825156000193521_060525_1026.MCP.xml,138.61,,Sidney Snipes"""
    
    with open(os.path.join(directory, "insurance_claims.csv"), "w") as f:
        f.write(insurance_content)
    
    # Create a non-CSV file
    with open(os.path.join(directory, "not_a_csv.txt"), "w") as f:
        f.write("This is not a CSV file")
    
    # Create a subdirectory with a CSV
    subdirectory = os.path.join(directory, "subdir")
    os.makedirs(subdirectory)
    
    with open(os.path.join(subdirectory, "subdir_file.csv"), "w") as f:
        f.write(cc_content)
    
    return directory


@pytest.fixture
def db_path():
    """Fixture for temporary database path"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Initialize schema
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE providers (
            provider_id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_name VARCHAR(100) NOT NULL UNIQUE,
            specialty VARCHAR(100),
            npi_number VARCHAR(10),
            active BOOLEAN DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE payment_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER,
            transaction_date DATE,
            patient_id VARCHAR(50),
            service_date DATE,
            cash_applied DECIMAL(10,2),
            insurance_payment DECIMAL(10,2),
            patient_payment DECIMAL(10,2),
            adjustment_amount DECIMAL(10,2),
            cpt_code VARCHAR(5),
            diagnosis_code VARCHAR(10),
            payer_name VARCHAR(100),
            claim_number VARCHAR(50),
            upload_batch VARCHAR(50),
            notes TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (provider_id) REFERENCES providers(provider_id)
        );
        
        CREATE TABLE data_uploads (
            upload_id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename VARCHAR(200),
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            records_processed INTEGER,
            records_successful INTEGER,
            records_failed INTEGER,
            file_hash VARCHAR(64),
            status VARCHAR(20) DEFAULT 'processing'
        );
        
        CREATE TABLE data_quality_issues (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name VARCHAR(50),
            record_id INTEGER,
            issue_type VARCHAR(50),
            issue_description TEXT,
            severity VARCHAR(10),
            resolved BOOLEAN DEFAULT 0,
            detected_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def import_helper(db_path):
    """Fixture for ImportHelper"""
    helper = ImportHelper(db_path)
    yield helper
    helper.close()


class TestImportHelper:
    """Tests for ImportHelper"""
    
    def test_import_cc_payment_file(self, import_helper, cc_payment_csv):
        """Test importing credit card payment file"""
        result = import_helper.import_file(cc_payment_csv)
        
        assert result["success"] == True
        assert result["format"] == "credit_card_payment"
        assert result["total_records"] > 0
        assert result["successful"] > 0
        
        # Check metadata
        assert "transformation" in result
        assert result["transformation"]["format"] == "credit_card_payment"
        assert result["transformation"]["success"] == True
        
    def test_import_insurance_claims_file(self, import_helper, insurance_claims_csv):
        """Test importing insurance claims file"""
        result = import_helper.import_file(insurance_claims_csv)
        
        assert result["success"] == True
        assert result["format"] == "insurance_claims"
        assert result["total_records"] > 0
        assert result["successful"] > 0
        
    def test_import_unknown_format(self, import_helper):
        """Test importing unknown format"""
        unknown_csv = create_test_csv(
            "Col1,Col2,Col3\n1,2,3\n4,5,6",
            "unknown.csv"
        )
        
        result = import_helper.import_file(unknown_csv)
        
        assert result["success"] == False
        assert "error" in result
        assert "format" not in result
        
    def test_import_directory(self, import_helper, csv_directory):
        """Test importing directory"""
        result = import_helper.import_directory(csv_directory)
        
        assert result["success"] == True
        assert result["files_found"] == 2  # 2 CSV files in the main directory
        assert result["files_imported"] > 0
        
        # Check recursive import
        result = import_helper.import_directory(csv_directory, recursive=True)
        
        assert result["success"] == True
        assert result["files_found"] == 3  # 2 in main dir + 1 in subdir
        assert result["files_imported"] > 0


def test_import_file_utility(cc_payment_csv, db_path):
    """Test import_file utility function"""
    with patch('utils.import_helper.ImportHelper') as mock_helper_class:
        mock_helper = MagicMock()
        mock_helper_class.return_value = mock_helper
        mock_helper.import_file.return_value = {"success": True, "test": "result"}
        
        result = import_file(cc_payment_csv)
        
        mock_helper_class.assert_called_once()
        mock_helper.import_file.assert_called_once_with(cc_payment_csv, None)
        mock_helper.close.assert_called_once()
        assert result == {"success": True, "test": "result"}


def test_import_directory_utility(csv_directory, db_path):
    """Test import_directory utility function"""
    with patch('utils.import_helper.ImportHelper') as mock_helper_class:
        mock_helper = MagicMock()
        mock_helper_class.return_value = mock_helper
        mock_helper.import_directory.return_value = {"success": True, "test": "result"}
        
        result = import_directory(csv_directory, recursive=True)
        
        mock_helper_class.assert_called_once()
        mock_helper.import_directory.assert_called_once_with(csv_directory, True)
        mock_helper.close.assert_called_once()
        assert result == {"success": True, "test": "result"}