"""
Test suite for report transformation system.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np
import tempfile
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.format_detector import ReportFormatDetector
from utils.report_transformer import (
    ReportTransformer, TransformationRule, RenameColumnsRule, 
    DateFormatRule, NumberFormatRule, MergeColumnsRule
)


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
def transformer():
    """Fixture for ReportTransformer"""
    detector = ReportFormatDetector()
    return ReportTransformer(detector)


class TestTransformationRules:
    """Tests for transformation rules"""
    
    def test_rename_columns_rule(self):
        """Test RenameColumnsRule"""
        df = pd.DataFrame({
            "Old1": [1, 2, 3],
            "Old2": [4, 5, 6],
            "Keep": [7, 8, 9]
        })
        
        rule = RenameColumnsRule({"Old1": "New1", "Old2": "New2", "Missing": "NewMissing"})
        result = rule.apply(df)
        
        assert "New1" in result.columns
        assert "New2" in result.columns
        assert "Keep" in result.columns
        assert "Old1" not in result.columns
        assert "Old2" not in result.columns
        assert "NewMissing" not in result.columns
        
    def test_date_format_rule(self):
        """Test DateFormatRule"""
        df = pd.DataFrame({
            "Date1": ["01/04/2025", "02/05/2025", "03/06/2025"],
            "Date2": ["2025-01-04", "2025-02-05", "2025-03-06"],
            "NonDate": ["A", "B", "C"]
        })
        
        rule = DateFormatRule(["Date1", "Date2", "Missing"], output_format="%Y-%m-%d")
        result = rule.apply(df)
        
        assert result["Date1"].iloc[0] == "2025-01-04"
        assert result["Date2"].iloc[0] == "2025-01-04"
        assert result["NonDate"].iloc[0] == "A"
        
    def test_number_format_rule(self):
        """Test NumberFormatRule"""
        df = pd.DataFrame({
            "Num1": ["$123.45", "$678.90", "$234.56"],
            "Num2": ["123", "678", "234"],
            "NonNum": ["A", "B", "C"]
        })
        
        rule = NumberFormatRule(["Num1", "Num2", "Missing"])
        result = rule.apply(df)
        
        assert result["Num1"].dtype == np.float64
        assert result["Num1"].iloc[0] == 123.45
        assert result["Num2"].dtype == np.int64 or result["Num2"].dtype == np.float64
        assert result["Num2"].iloc[0] == 123
        assert result["NonNum"].iloc[0] == "A"
        
    def test_merge_columns_rule(self):
        """Test MergeColumnsRule"""
        df = pd.DataFrame({
            "Col1": [1, np.nan, 3],
            "Col2": [np.nan, 2, 4],
            "Other": ["A", "B", "C"]
        })
        
        rule = MergeColumnsRule(["Col1", "Col2"], "Merged")
        result = rule.apply(df)
        
        assert "Merged" in result.columns
        assert result["Merged"].iloc[0] == 1
        assert result["Merged"].iloc[1] == 2
        assert result["Merged"].iloc[2] == 3  # Uses first non-null value


class TestReportTransformer:
    """Tests for ReportTransformer"""
    
    def test_transform_cc_payment(self, transformer, cc_payment_csv):
        """Test transforming credit card payment format"""
        df, metadata = transformer.transform(cc_payment_csv, "credit_card_payment")
        
        assert not df.empty
        assert metadata["format"] == "credit_card_payment"
        assert metadata["success"] == True
        
        # Check transformed columns
        assert "transaction_id" in df.columns
        assert "transaction_date" in df.columns
        assert "cash_applied" in df.columns
        assert "provider_name" in df.columns
        
        # Check values
        assert df["transaction_id"].iloc[0] == "9690"
        assert df["transaction_date"].iloc[0] == "2025-01-04"
        assert df["cash_applied"].iloc[0] == 55.0
        assert df["provider_name"].iloc[0] == "Tammy Maxey"
        
    def test_transform_insurance_claims(self, transformer, insurance_claims_csv):
        """Test transforming insurance claims format"""
        df, metadata = transformer.transform(insurance_claims_csv, "insurance_claims")
        
        assert not df.empty
        assert metadata["format"] == "insurance_claims"
        assert metadata["success"] == True
        
        # Check transformed columns
        assert "transaction_id" in df.columns
        assert "transaction_date" in df.columns
        assert "cash_applied" in df.columns
        assert "provider_name" in df.columns
        
        # Check values
        assert df["transaction_id"].iloc[0] == "4393"
        assert df["transaction_date"].iloc[0] == "2025-06-10"
        assert df["cash_applied"].iloc[0] == 138.61
        assert df["provider_name"].iloc[0] == "Sidney Snipes"
        
    def test_transform_unknown_format(self, transformer):
        """Test transforming unknown format"""
        unknown_csv = create_test_csv(
            "Col1,Col2,Col3\n1,2,3\n4,5,6",
            "unknown.csv"
        )
        
        df, metadata = transformer.transform(unknown_csv, "nonexistent_format")
        
        assert df.empty
        assert "error" in metadata
        assert metadata["success"] if "success" in metadata else False == False
        
    def test_validate_transformation(self, transformer, cc_payment_csv):
        """Test validation of transformed data"""
        # Create a transformation with missing required values
        df = pd.DataFrame({
            "transaction_id": [1, 2, 3],
            "transaction_date": ["2025-01-01", np.nan, "2025-01-03"],
            "cash_applied": [100, 200, -50],  # Negative value
            "provider_name": ["Provider", "Provider", np.nan]  # Missing value
        })
        
        errors = transformer._validate_transformation(df, "test_format")
        
        assert len(errors) == 3  # Missing date, missing provider, negative cash
        
        # Check error types
        error_types = [error["type"] for error in errors]
        assert "missing_required" in error_types
        assert "negative_values" in error_types


def test_transform_file_utility(cc_payment_csv):
    """Test transform_file utility function"""
    from utils.report_transformer import transform_file
    
    result = transform_file(cc_payment_csv)
    
    assert result["format"] == "credit_card_payment"
    assert result["row_count"] > 0
    assert result["column_count"] > 0
    assert result["success"] == True