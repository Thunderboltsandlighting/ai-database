"""
Test suite for report format detection system.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np
import tempfile
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.format_detector import (
    ReportFormatDetector, FormatProfile, FormatRegistry, FormatDetectionResult
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
def unknown_format_csv():
    """Fixture for unknown format CSV"""
    content = """Column1,Column2,Column3,Column4
1,2,3,4
5,6,7,8
9,10,11,12"""
    return create_test_csv(content, "unknown_format_test.csv")


@pytest.fixture
def registry_path():
    """Fixture for temporary registry path"""
    return os.path.join(tempfile.gettempdir(), "test_format_registry.json")


@pytest.fixture
def format_detector(registry_path):
    """Fixture for format detector"""
    detector = ReportFormatDetector(registry_path)
    yield detector
    
    # Cleanup
    if os.path.exists(registry_path):
        os.remove(registry_path)


class TestFormatProfile:
    """Tests for FormatProfile class"""
    
    def test_init(self):
        """Test initialization"""
        profile = FormatProfile("test_format", "Test format")
        assert profile.name == "test_format"
        assert profile.description == "Test format"
        assert profile.header_patterns == {}
        assert profile.column_mappings == {}
        
    def test_to_dict(self):
        """Test conversion to dictionary"""
        profile = FormatProfile(
            "test_format", 
            "Test format",
            header_patterns={"col1": ["pattern1", "pattern2"]},
            column_mappings={"Original": "Mapped"}
        )
        
        data = profile.to_dict()
        assert data["name"] == "test_format"
        assert data["description"] == "Test format"
        assert data["header_patterns"] == {"col1": ["pattern1", "pattern2"]}
        assert data["column_mappings"] == {"Original": "Mapped"}
        
    def test_from_dict(self):
        """Test creation from dictionary"""
        data = {
            "name": "test_format",
            "description": "Test format",
            "header_patterns": {"col1": ["pattern1", "pattern2"]},
            "column_mappings": {"Original": "Mapped"}
        }
        
        profile = FormatProfile.from_dict(data)
        assert profile.name == "test_format"
        assert profile.description == "Test format"
        assert profile.header_patterns == {"col1": ["pattern1", "pattern2"]}
        assert profile.column_mappings == {"Original": "Mapped"}
        
    def test_match_column_direct(self):
        """Test direct column matching"""
        profile = FormatProfile(
            "test_format",
            column_mappings={"Original": "Mapped"}
        )
        
        col, score = profile.match_column("Original")
        assert col == "Mapped"
        assert score == 1.0
        
    def test_match_column_pattern(self):
        """Test pattern-based column matching"""
        profile = FormatProfile(
            "test_format",
            header_patterns={"mapped_col": [r"orig.*", r"test"]}
        )
        
        col, score = profile.match_column("original")
        assert col == "mapped_col"
        assert score == 0.9
        
    def test_match_column_similarity(self):
        """Test similarity-based column matching"""
        profile = FormatProfile(
            "test_format",
            header_patterns={"transaction_date": ["date"]}
        )
        
        col, score = profile.match_column("trans_date")
        assert col == "transaction_date"
        assert score > 0.7


class TestFormatRegistry:
    """Tests for FormatRegistry class"""
    
    def test_init(self, registry_path):
        """Test initialization"""
        registry = FormatRegistry(registry_path)
        assert len(registry.profiles) > 0
        assert "credit_card_payment" in registry.profiles
        assert "insurance_claims" in registry.profiles
        
    def test_add_profile(self, registry_path):
        """Test adding a profile"""
        registry = FormatRegistry(registry_path)
        
        # Add a new profile
        profile = FormatProfile("test_format", "Test format")
        registry.add_profile(profile)
        
        assert "test_format" in registry.profiles
        
        # Reload to verify persistence
        registry2 = FormatRegistry(registry_path)
        assert "test_format" in registry2.profiles
        
    def test_get_profile(self, registry_path):
        """Test getting a profile"""
        registry = FormatRegistry(registry_path)
        
        profile = registry.get_profile("credit_card_payment")
        assert profile is not None
        assert profile.name == "credit_card_payment"
        
        profile = registry.get_profile("nonexistent")
        assert profile is None
        
    def test_list_profiles(self, registry_path):
        """Test listing profiles"""
        registry = FormatRegistry(registry_path)
        
        profiles = registry.list_profiles()
        assert "credit_card_payment" in profiles
        assert "insurance_claims" in profiles


class TestReportFormatDetector:
    """Tests for ReportFormatDetector class"""
    
    def test_detect_cc_payment_format(self, format_detector, cc_payment_csv):
        """Test detecting credit card payment format"""
        result = format_detector.detect_format(cc_payment_csv)
        
        assert result.format_name == "credit_card_payment"
        assert result.confidence > 0.7
        assert "Trans. #" in result.column_map
        assert result.column_map["Trans. #"] == "transaction_id"
        assert result.column_map["Client Name"] == "patient_name"
        
    def test_detect_insurance_claims_format(self, format_detector, insurance_claims_csv):
        """Test detecting insurance claims format"""
        result = format_detector.detect_format(insurance_claims_csv)
        
        assert result.format_name == "insurance_claims"
        assert result.confidence > 0.7
        assert "RowId" in result.column_map
        assert result.column_map["RowId"] == "transaction_id"
        assert result.column_map["Payment From"] == "payer_name"
        
    def test_detect_unknown_format(self, format_detector, unknown_format_csv):
        """Test detecting unknown format"""
        result = format_detector.detect_format(unknown_format_csv)
        
        assert result.format_name is None
        assert result.confidence < 0.5
        
    def test_get_column_mapping(self, format_detector, cc_payment_csv):
        """Test getting column mapping"""
        mapping = format_detector.get_column_mapping(cc_payment_csv)
        
        assert mapping["Trans. #"] == "transaction_id"
        assert mapping["Trans. Date"] == "transaction_date"
        assert mapping["Gross Amt"] == "amount"
        assert mapping["Client Name"] == "patient_name"


def test_format_detection_result():
    """Test FormatDetectionResult class"""
    result = FormatDetectionResult(
        format_name="test_format",
        confidence=0.85,
        column_map={"Original": "Mapped"},
        confidence_scores={"Original": 0.9}
    )
    
    assert result.format_name == "test_format"
    assert result.confidence == 0.85
    assert result.column_map == {"Original": "Mapped"}
    assert result.confidence_scores == {"Original": 0.9}
    
    # Test to_dict
    data = result.to_dict()
    assert data["format_name"] == "test_format"
    assert data["confidence"] == 0.85
    assert data["column_map"] == {"Original": "Mapped"}
    
    # Test get_summary
    summary = result.get_summary()
    assert "test_format" in summary
    assert "0.85" in summary
    assert "Original -> Mapped" in summary