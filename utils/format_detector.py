"""
Report Format Detection System for HVLC_DB

This module provides tools for automatically detecting and classifying
different CSV report formats commonly used in medical billing.
"""

import os
import re
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Set, Any
from collections import defaultdict, Counter
import csv
import difflib
from pathlib import Path
import logging

from utils.config import get_config
from utils.logger import get_logger

# Configure logging
logger = get_logger()
config = get_config()


class FormatProfile:
    """Represents a known report format profile"""
    
    def __init__(self, 
                 name: str, 
                 description: str = None, 
                 header_patterns: Dict[str, List[str]] = None,
                 column_mappings: Dict[str, str] = None,
                 sample_values: Dict[str, List[Any]] = None,
                 data_types: Dict[str, str] = None,
                 metadata: Dict[str, Any] = None):
        """Initialize a format profile
        
        Args:
            name: Unique identifier for this format
            description: Human-readable description
            header_patterns: Mapping of standard columns to pattern lists that match them
            column_mappings: Direct mapping of format-specific column names to standard names
            sample_values: Sample values for each column (used for pattern matching)
            data_types: Expected data types for each column
            metadata: Additional metadata about this format
        """
        self.name = name
        self.description = description or f"Format profile for {name}"
        self.header_patterns = header_patterns or {}
        self.column_mappings = column_mappings or {}
        self.sample_values = sample_values or {}
        self.data_types = data_types or {}
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict:
        """Convert profile to dictionary for serialization
        
        Returns:
            Dictionary representation of profile
        """
        return {
            "name": self.name,
            "description": self.description,
            "header_patterns": self.header_patterns,
            "column_mappings": self.column_mappings,
            "sample_values": {k: [str(v) for v in vals] 
                              for k, vals in self.sample_values.items()},
            "data_types": self.data_types,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'FormatProfile':
        """Create profile from dictionary
        
        Args:
            data: Dictionary representation of profile
            
        Returns:
            FormatProfile instance
        """
        return cls(
            name=data["name"],
            description=data.get("description"),
            header_patterns=data.get("header_patterns"),
            column_mappings=data.get("column_mappings"),
            sample_values=data.get("sample_values"),
            data_types=data.get("data_types"),
            metadata=data.get("metadata")
        )
        
    def match_column(self, column_name: str) -> Tuple[str, float]:
        """Match a column name to a standard column
        
        Args:
            column_name: Column name to match
            
        Returns:
            Tuple of (standard_column, confidence_score)
        """
        # Direct mapping
        if column_name in self.column_mappings:
            return self.column_mappings[column_name], 1.0
            
        # Pattern matching
        best_match = None
        best_score = 0.0
        
        for std_column, patterns in self.header_patterns.items():
            for pattern in patterns:
                if re.search(pattern, column_name, re.IGNORECASE):
                    return std_column, 0.9  # Pattern match is high confidence
                    
            # String similarity as fallback
            similarity = difflib.SequenceMatcher(None, column_name.lower(), 
                                                std_column.lower()).ratio()
            if similarity > best_score:
                best_score = similarity
                best_match = std_column
                
        # Return best match if above threshold
        if best_score > 0.7:
            return best_match, best_score
            
        return None, 0.0


class FormatRegistry:
    """Registry for format profiles"""
    
    def __init__(self, registry_path: str = None):
        """Initialize format registry
        
        Args:
            registry_path: Path to registry file
        """
        self.registry_path = registry_path or config.get("paths.format_registry", 
                                               "utils/format_registry.json")
        self.profiles = {}
        self.load_registry()
        
    def load_registry(self):
        """Load registry from file"""
        if not os.path.exists(self.registry_path):
            logger.info(f"Format registry not found at {self.registry_path}, creating new registry")
            self._initialize_default_profiles()
            self.save_registry()
            return
            
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                
            for profile_data in data.get("profiles", []):
                profile = FormatProfile.from_dict(profile_data)
                self.profiles[profile.name] = profile
                
            logger.info(f"Loaded {len(self.profiles)} format profiles from registry")
            
        except Exception as e:
            logger.error(f"Error loading format registry: {e}")
            self._initialize_default_profiles()
            
    def _initialize_default_profiles(self):
        """Initialize default profiles for common formats"""
        # Credit Card Payment Format
        cc_profile = FormatProfile(
            name="credit_card_payment",
            description="Credit card payment transaction format",
            header_patterns={
                "transaction_id": [r"trans.?\s*#", r"transaction\s*id", r"id"],
                "transaction_date": [r"trans.?\s*date", r"date"],
                "amount": [r"gross\s*amt", r"amount", r"payment"],
                "payment_type": [r"acct\s*type", r"card\s*type", r"type"],
                "patient_name": [r"client\s*name", r"patient", r"name"],
                "provider_name": [r"provider"]
            },
            column_mappings={
                "Trans. #": "transaction_id",
                "Trans. Date": "transaction_date",
                "Gross Amt": "amount",
                "Acct Type": "payment_type",
                "Client Name": "patient_name",
                "Provider": "provider_name"
            }
        )
        
        # Insurance Claims Format
        insurance_profile = FormatProfile(
            name="insurance_claims",
            description="Insurance claims payment format",
            header_patterns={
                "transaction_id": [r"row\s*id", r"claim\s*id", r"id"],
                "transaction_date": [r"check\s*date", r"date"],
                "amount": [r"check\s*amount", r"amount", r"payment"],
                "cash_applied": [r"cash\s*applied", r"applied\s*amount"],
                "payer_name": [r"payment\s*from", r"payer", r"insurance"],
                "provider_name": [r"provider"]
            },
            column_mappings={
                "RowId": "transaction_id",
                "Check Date": "transaction_date",
                "Check Amount": "amount",
                "Cash Applied": "cash_applied",
                "Payment From": "payer_name",
                "Provider": "provider_name"
            }
        )
        
        self.profiles = {
            "credit_card_payment": cc_profile,
            "insurance_claims": insurance_profile
        }
            
    def save_registry(self):
        """Save registry to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            
            data = {
                "profiles": [profile.to_dict() for profile in self.profiles.values()]
            }
            
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved {len(self.profiles)} format profiles to registry")
            
        except Exception as e:
            logger.error(f"Error saving format registry: {e}")
            
    def add_profile(self, profile: FormatProfile):
        """Add a profile to the registry
        
        Args:
            profile: FormatProfile to add
        """
        self.profiles[profile.name] = profile
        self.save_registry()
        
    def get_profile(self, name: str) -> Optional[FormatProfile]:
        """Get a profile by name
        
        Args:
            name: Profile name
            
        Returns:
            FormatProfile if found, None otherwise
        """
        return self.profiles.get(name)
        
    def list_profiles(self) -> List[str]:
        """List all profile names
        
        Returns:
            List of profile names
        """
        return list(self.profiles.keys())


class FormatDetectionResult:
    """Result of format detection"""
    
    def __init__(self, 
                 format_name: str = None, 
                 confidence: float = 0.0,
                 column_map: Dict[str, str] = None,
                 confidence_scores: Dict[str, float] = None,
                 metadata: Dict[str, Any] = None):
        """Initialize format detection result
        
        Args:
            format_name: Detected format name
            confidence: Overall confidence score (0-1)
            column_map: Mapping of source columns to standard columns
            confidence_scores: Confidence scores for each mapped column
            metadata: Additional metadata about detection
        """
        self.format_name = format_name
        self.confidence = confidence
        self.column_map = column_map or {}
        self.confidence_scores = confidence_scores or {}
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict:
        """Convert result to dictionary
        
        Returns:
            Dictionary representation of result
        """
        return {
            "format_name": self.format_name,
            "confidence": self.confidence,
            "column_map": self.column_map,
            "confidence_scores": self.confidence_scores,
            "metadata": self.metadata
        }
        
    def get_summary(self) -> str:
        """Get human-readable summary
        
        Returns:
            Summary string
        """
        if not self.format_name:
            return "No format detected"
            
        summary = f"Detected format: {self.format_name} (confidence: {self.confidence:.2f})\n"
        summary += "Column mapping:\n"
        
        for src_col, std_col in self.column_map.items():
            conf = self.confidence_scores.get(src_col, 0.0)
            summary += f"  {src_col} -> {std_col} (confidence: {conf:.2f})\n"
            
        return summary


class ReportFormatDetector:
    """Detects and classifies CSV report formats"""
    
    def __init__(self, registry_path: str = None):
        """Initialize format detector
        
        Args:
            registry_path: Path to format registry file
        """
        self.registry = FormatRegistry(registry_path)
        
    def detect_format(self, file_path: str, sample_rows: int = 10) -> FormatDetectionResult:
        """Detect format of a CSV file
        
        Args:
            file_path: Path to CSV file
            sample_rows: Number of rows to sample for detection
            
        Returns:
            FormatDetectionResult with detection details
        """
        logger.info(f"Detecting format for {file_path}")
        
        try:
            # Sniff dialect
            with open(file_path, 'r', newline='') as f:
                sample = f.read(4096)
                dialect = csv.Sniffer().sniff(sample)
                has_header = csv.Sniffer().has_header(sample)
                
            # Read header and sample rows
            df = pd.read_csv(file_path, nrows=sample_rows, dialect=dialect)
            
            if not has_header:
                logger.warning(f"File {file_path} does not appear to have a header row")
                return FormatDetectionResult(
                    format_name=None,
                    confidence=0.0,
                    metadata={"error": "No header detected"}
                )
                
            headers = df.columns.tolist()
            
            # Match against known profiles
            results = []
            for profile_name, profile in self.registry.profiles.items():
                result = self._match_profile(headers, df, profile)
                results.append((profile_name, result))
                
            # Find best match
            results.sort(key=lambda x: x[1]["confidence"], reverse=True)
            best_match = results[0]
            
            if best_match[1]["confidence"] < 0.5:
                logger.warning(f"Low confidence format detection for {file_path}")
                return FormatDetectionResult(
                    format_name=None,
                    confidence=best_match[1]["confidence"],
                    metadata={"candidates": [r[0] for r in results[:3]]}
                )
                
            # Create result
            return FormatDetectionResult(
                format_name=best_match[0],
                confidence=best_match[1]["confidence"],
                column_map=best_match[1]["column_map"],
                confidence_scores=best_match[1]["confidence_scores"],
                metadata={"full_results": {r[0]: r[1] for r in results[:3]}}
            )
            
        except Exception as e:
            logger.error(f"Error detecting format for {file_path}: {e}")
            return FormatDetectionResult(
                format_name=None,
                confidence=0.0,
                metadata={"error": str(e)}
            )
            
    def _match_profile(self, headers: List[str], df: pd.DataFrame, 
                      profile: FormatProfile) -> Dict[str, Any]:
        """Match headers against a profile
        
        Args:
            headers: List of header names
            df: DataFrame with sample data
            profile: FormatProfile to match against
            
        Returns:
            Dictionary with match results
        """
        column_map = {}
        confidence_scores = {}
        matched_columns = 0
        
        # Try to match each header
        for header in headers:
            standard_col, confidence = profile.match_column(header)
            
            if standard_col and confidence > 0.5:
                column_map[header] = standard_col
                confidence_scores[header] = confidence
                matched_columns += 1
                
        # Calculate overall confidence
        required_columns = ["transaction_date", "amount", "provider_name"]
        required_matches = sum(1 for col in required_columns 
                              if col in column_map.values())
        
        if required_matches < len(required_columns):
            # Missing required columns
            confidence = 0.2
        else:
            # Calculate based on number of matches and their confidence
            match_ratio = matched_columns / len(headers)
            avg_confidence = (sum(confidence_scores.values()) / 
                             len(confidence_scores)) if confidence_scores else 0
            
            confidence = match_ratio * 0.5 + avg_confidence * 0.5
            
        return {
            "confidence": confidence,
            "column_map": column_map,
            "confidence_scores": confidence_scores,
            "matched_columns": matched_columns,
            "total_columns": len(headers)
        }
        
    def learn_from_sample(self, file_path: str, format_name: str, 
                         description: str = None) -> FormatProfile:
        """Learn a new format from a sample file
        
        Args:
            file_path: Path to sample CSV file
            format_name: Name for the new format
            description: Optional description
            
        Returns:
            Newly created FormatProfile
        """
        logger.info(f"Learning format {format_name} from {file_path}")
        
        try:
            # Read sample file
            df = pd.read_csv(file_path)
            headers = df.columns.tolist()
            
            # Create column mappings through interactive process
            column_mappings = {}
            
            # For now, create empty profile (would be interactive in a real app)
            profile = FormatProfile(
                name=format_name,
                description=description or f"Format profile for {format_name}",
                column_mappings=column_mappings
            )
            
            # Add to registry
            self.registry.add_profile(profile)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error learning format from {file_path}: {e}")
            raise
            
    def update_mapping(self, format_name: str, column_mappings: Dict[str, str]):
        """Update column mappings for a format
        
        Args:
            format_name: Format name
            column_mappings: New column mappings
        """
        profile = self.registry.get_profile(format_name)
        
        if not profile:
            logger.error(f"Format {format_name} not found")
            return
            
        profile.column_mappings.update(column_mappings)
        self.registry.save_registry()
        
    def get_column_mapping(self, file_path: str) -> Dict[str, str]:
        """Get column mapping for a file
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Dictionary mapping source columns to standard columns
        """
        result = self.detect_format(file_path)
        return result.column_map if result else {}


def detect_file_format(file_path: str) -> Dict[str, Any]:
    """Utility function to detect format of a file
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Dictionary with detection results
    """
    detector = ReportFormatDetector()
    result = detector.detect_format(file_path)
    return result.to_dict()


def main():
    """Command-line interface for format detection"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Detect CSV report formats")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect format of a file")
    detect_parser.add_argument("file_path", help="Path to CSV file")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List known formats")
    
    # Learn command
    learn_parser = subparsers.add_parser("learn", help="Learn format from sample")
    learn_parser.add_argument("file_path", help="Path to sample CSV file")
    learn_parser.add_argument("format_name", help="Name for the new format")
    learn_parser.add_argument("-d", "--description", help="Format description")
    
    args = parser.parse_args()
    
    detector = ReportFormatDetector()
    
    if args.command == "detect":
        result = detector.detect_format(args.file_path)
        print(result.get_summary())
        
    elif args.command == "list":
        profiles = detector.registry.list_profiles()
        print(f"Known formats ({len(profiles)}):")
        for profile in profiles:
            print(f"- {profile}")
            
    elif args.command == "learn":
        profile = detector.learn_from_sample(args.file_path, args.format_name, args.description)
        print(f"Learned new format: {profile.name}")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()