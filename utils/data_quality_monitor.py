"""
Data Quality Monitoring System for HVLC_DB

This module provides tools for monitoring and analyzing data quality,
detecting issues, and generating alerts with remediation steps.
"""

import os
import sys
import json
import time
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Set
import logging
from pathlib import Path
import re
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

from utils.config import get_config
from utils.logger import get_logger, log_data_quality_issue

# Configure logging
logger = get_logger()
config = get_config()

# Quality thresholds for metrics (configurable)
DEFAULT_THRESHOLDS = {
    "missing_values": 0.05,     # Max 5% missing values
    "negative_values": 0.01,    # Max 1% negative values
    "zero_values": 0.30,        # Max 30% zero values
    "outliers": 0.05,           # Max 5% outliers
    "duplicates": 0.01,         # Max 1% duplicates
    "statistical_change": 0.20  # Max 20% change in statistical measures
}

class DataQualityRule:
    """Base class for data quality rules"""
    
    def __init__(self, name: str, description: str, severity: str = "medium"):
        """Initialize data quality rule
        
        Args:
            name: Rule name
            description: Rule description
            severity: Rule severity (low, medium, high)
        """
        self.name = name
        self.description = description
        self.severity = severity
        self.violated = False
        self.details = {}
        
    def check(self, data: pd.DataFrame) -> bool:
        """Check if rule is violated
        
        Args:
            data: DataFrame to check
            
        Returns:
            True if rule is violated
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def get_remediation(self) -> str:
        """Get remediation steps
        
        Returns:
            Remediation steps as string
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def to_dict(self) -> Dict:
        """Convert rule to dictionary
        
        Returns:
            Dictionary representation of rule
        """
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "violated": self.violated,
            "details": self.details,
            "remediation": self.get_remediation() if self.violated else None
        }

class MissingValuesRule(DataQualityRule):
    """Rule for detecting missing values"""
    
    def __init__(self, column: str, threshold: float = None, severity: str = "medium"):
        """Initialize missing values rule
        
        Args:
            column: Column to check
            threshold: Maximum allowed percentage of missing values
            severity: Rule severity
        """
        super().__init__(
            name=f"missing_values_{column}",
            description=f"Check for missing values in {column}",
            severity=severity
        )
        self.column = column
        self.threshold = threshold or DEFAULT_THRESHOLDS["missing_values"]
        
    def check(self, data: pd.DataFrame) -> bool:
        """Check if rule is violated
        
        Args:
            data: DataFrame to check
            
        Returns:
            True if rule is violated
        """
        if self.column not in data.columns:
            self.violated = True
            self.details = {
                "error": f"Column {self.column} not found in data"
            }
            return True
            
        missing_count = data[self.column].isna().sum()
        total_count = len(data)
        missing_pct = missing_count / total_count if total_count > 0 else 0
        
        self.details = {
            "missing_count": int(missing_count),
            "total_count": int(total_count),
            "missing_percentage": float(missing_pct),
            "threshold": float(self.threshold)
        }
        
        self.violated = missing_pct > self.threshold
        return self.violated
        
    def get_remediation(self) -> str:
        """Get remediation steps
        
        Returns:
            Remediation steps as string
        """
        if not self.violated:
            return ""
            
        if "error" in self.details:
            return f"Add column {self.column} to the dataset or update the quality rule configuration"
            
        missing_pct = self.details.get("missing_percentage", 0) * 100
        threshold_pct = self.details.get("threshold", 0) * 100
        
        return (
            f"Column {self.column} has {missing_pct:.1f}% missing values (threshold: {threshold_pct:.1f}%).\n"
            f"Remediation steps:\n"
            f"1. Identify the source of missing data\n"
            f"2. Update data collection process to ensure completeness\n"
            f"3. Consider implementing data validation at entry points\n"
            f"4. For existing data, evaluate imputation strategies if appropriate"
        )

class NegativeValuesRule(DataQualityRule):
    """Rule for detecting negative values in numeric columns"""
    
    def __init__(self, column: str, threshold: float = None, severity: str = "high"):
        """Initialize negative values rule
        
        Args:
            column: Column to check
            threshold: Maximum allowed percentage of negative values
            severity: Rule severity
        """
        super().__init__(
            name=f"negative_values_{column}",
            description=f"Check for negative values in {column}",
            severity=severity
        )
        self.column = column
        self.threshold = threshold or DEFAULT_THRESHOLDS["negative_values"]
        
    def check(self, data: pd.DataFrame) -> bool:
        """Check if rule is violated
        
        Args:
            data: DataFrame to check
            
        Returns:
            True if rule is violated
        """
        if self.column not in data.columns:
            self.violated = True
            self.details = {
                "error": f"Column {self.column} not found in data"
            }
            return True
            
        # Skip non-numeric columns
        if not pd.api.types.is_numeric_dtype(data[self.column]):
            self.violated = False
            self.details = {
                "error": f"Column {self.column} is not numeric"
            }
            return False
            
        # Count negative values (excluding missing values)
        valid_data = data[self.column].dropna()
        negative_count = (valid_data < 0).sum()
        total_count = len(valid_data)
        negative_pct = negative_count / total_count if total_count > 0 else 0
        
        self.details = {
            "negative_count": int(negative_count),
            "total_count": int(total_count),
            "negative_percentage": float(negative_pct),
            "threshold": float(self.threshold),
            "example_negative_values": list(valid_data[valid_data < 0].head(5).values)
        }
        
        self.violated = negative_pct > self.threshold
        return self.violated
        
    def get_remediation(self) -> str:
        """Get remediation steps
        
        Returns:
            Remediation steps as string
        """
        if not self.violated:
            return ""
            
        if "error" in self.details and "not found" in self.details["error"]:
            return f"Add column {self.column} to the dataset or update the quality rule configuration"
            
        if "error" in self.details and "not numeric" in self.details["error"]:
            return f"Rule only applies to numeric columns. Update rule configuration."
            
        negative_pct = self.details.get("negative_percentage", 0) * 100
        threshold_pct = self.details.get("threshold", 0) * 100
        examples = self.details.get("example_negative_values", [])
        examples_str = ", ".join([str(x) for x in examples[:3]])
        
        return (
            f"Column {self.column} has {negative_pct:.1f}% negative values (threshold: {threshold_pct:.1f}%).\n"
            f"Examples: {examples_str}\n"
            f"Remediation steps:\n"
            f"1. Verify if negative values are valid for this column\n"
            f"2. If invalid, identify the source of negative values\n"
            f"3. Implement data validation to prevent negative values\n"
            f"4. Consider data correction for existing records"
        )

class OutlierRule(DataQualityRule):
    """Rule for detecting outliers in numeric columns"""
    
    def __init__(self, column: str, threshold: float = None, outlier_method: str = "iqr", 
                 outlier_threshold: float = 1.5, severity: str = "medium"):
        """Initialize outlier rule
        
        Args:
            column: Column to check
            threshold: Maximum allowed percentage of outliers
            outlier_method: Method for outlier detection ('iqr' or 'std')
            outlier_threshold: Threshold for outlier detection (1.5 for IQR, 3 for std)
            severity: Rule severity
        """
        super().__init__(
            name=f"outliers_{column}",
            description=f"Check for outliers in {column}",
            severity=severity
        )
        self.column = column
        self.threshold = threshold or DEFAULT_THRESHOLDS["outliers"]
        self.outlier_method = outlier_method
        self.outlier_threshold = outlier_threshold
        
    def check(self, data: pd.DataFrame) -> bool:
        """Check if rule is violated
        
        Args:
            data: DataFrame to check
            
        Returns:
            True if rule is violated
        """
        if self.column not in data.columns:
            self.violated = True
            self.details = {
                "error": f"Column {self.column} not found in data"
            }
            return True
            
        # Skip non-numeric columns
        if not pd.api.types.is_numeric_dtype(data[self.column]):
            self.violated = False
            self.details = {
                "error": f"Column {self.column} is not numeric"
            }
            return False
            
        # Get valid data (non-missing values)
        valid_data = data[self.column].dropna()
        
        # Detect outliers
        outliers = None
        if self.outlier_method == "iqr":
            q1 = valid_data.quantile(0.25)
            q3 = valid_data.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - self.outlier_threshold * iqr
            upper_bound = q3 + self.outlier_threshold * iqr
            outliers = (valid_data < lower_bound) | (valid_data > upper_bound)
            
            self.details["lower_bound"] = float(lower_bound)
            self.details["upper_bound"] = float(upper_bound)
            
        elif self.outlier_method == "std":
            mean = valid_data.mean()
            std = valid_data.std()
            lower_bound = mean - self.outlier_threshold * std
            upper_bound = mean + self.outlier_threshold * std
            outliers = (valid_data < lower_bound) | (valid_data > upper_bound)
            
            self.details["lower_bound"] = float(lower_bound)
            self.details["upper_bound"] = float(upper_bound)
            
        else:
            self.violated = True
            self.details = {
                "error": f"Invalid outlier method: {self.outlier_method}"
            }
            return True
            
        # Calculate outlier percentage
        outlier_count = outliers.sum()
        total_count = len(valid_data)
        outlier_pct = outlier_count / total_count if total_count > 0 else 0
        
        self.details.update({
            "outlier_count": int(outlier_count),
            "total_count": int(total_count),
            "outlier_percentage": float(outlier_pct),
            "threshold": float(self.threshold),
            "outlier_method": self.outlier_method,
            "example_outliers": list(valid_data[outliers].head(5).values)
        })
        
        self.violated = outlier_pct > self.threshold
        return self.violated
        
    def get_remediation(self) -> str:
        """Get remediation steps
        
        Returns:
            Remediation steps as string
        """
        if not self.violated:
            return ""
            
        if "error" in self.details and "not found" in self.details["error"]:
            return f"Add column {self.column} to the dataset or update the quality rule configuration"
            
        if "error" in self.details and "not numeric" in self.details["error"]:
            return f"Rule only applies to numeric columns. Update rule configuration."
            
        if "error" in self.details and "Invalid outlier method" in self.details["error"]:
            return f"Use a valid outlier method: 'iqr' or 'std'"
            
        outlier_pct = self.details.get("outlier_percentage", 0) * 100
        threshold_pct = self.details.get("threshold", 0) * 100
        examples = self.details.get("example_outliers", [])
        examples_str = ", ".join([str(x) for x in examples[:3]])
        
        lower_bound = self.details.get("lower_bound")
        upper_bound = self.details.get("upper_bound")
        
        return (
            f"Column {self.column} has {outlier_pct:.1f}% outliers (threshold: {threshold_pct:.1f}%).\n"
            f"Outlier definition: values outside [{lower_bound:.2f}, {upper_bound:.2f}]\n"
            f"Examples: {examples_str}\n"
            f"Remediation steps:\n"
            f"1. Verify if these values are valid or errors\n"
            f"2. Implement data validation to flag potential outliers\n"
            f"3. Investigate business processes that might be causing extreme values\n"
            f"4. Consider data transformation or normalization techniques"
        )

class StatisticalChangeRule(DataQualityRule):
    """Rule for detecting significant changes in statistical measures"""
    
    def __init__(self, column: str, statistic: str = "mean", threshold: float = None, 
                 baseline: Dict = None, severity: str = "medium"):
        """Initialize statistical change rule
        
        Args:
            column: Column to check
            statistic: Statistic to check ('mean', 'median', 'std', etc.)
            threshold: Maximum allowed percentage change
            baseline: Baseline statistics
            severity: Rule severity
        """
        super().__init__(
            name=f"statistical_change_{statistic}_{column}",
            description=f"Check for significant changes in {statistic} of {column}",
            severity=severity
        )
        self.column = column
        self.statistic = statistic
        self.threshold = threshold or DEFAULT_THRESHOLDS["statistical_change"]
        self.baseline = baseline or {}
        
    def check(self, data: pd.DataFrame) -> bool:
        """Check if rule is violated
        
        Args:
            data: DataFrame to check
            
        Returns:
            True if rule is violated
        """
        if self.column not in data.columns:
            self.violated = True
            self.details = {
                "error": f"Column {self.column} not found in data"
            }
            return True
            
        # Skip non-numeric columns
        if not pd.api.types.is_numeric_dtype(data[self.column]):
            self.violated = False
            self.details = {
                "error": f"Column {self.column} is not numeric"
            }
            return False
            
        # Get valid data (non-missing values)
        valid_data = data[self.column].dropna()
        
        # Calculate current statistic
        current_value = None
        if self.statistic == "mean":
            current_value = valid_data.mean()
        elif self.statistic == "median":
            current_value = valid_data.median()
        elif self.statistic == "std":
            current_value = valid_data.std()
        elif self.statistic == "min":
            current_value = valid_data.min()
        elif self.statistic == "max":
            current_value = valid_data.max()
        elif self.statistic == "count":
            current_value = len(valid_data)
        elif self.statistic == "sum":
            current_value = valid_data.sum()
        else:
            self.violated = True
            self.details = {
                "error": f"Invalid statistic: {self.statistic}"
            }
            return True
            
        # Get baseline value (if available)
        baseline_value = self.baseline.get(self.column, {}).get(self.statistic)
        
        # If no baseline, set current as baseline and don't violate
        if baseline_value is None:
            self.violated = False
            self.details = {
                "current_value": float(current_value),
                "baseline_value": None,
                "change_percentage": 0,
                "threshold": float(self.threshold)
            }
            return False
            
        # Calculate change percentage
        if baseline_value == 0:
            # Avoid division by zero
            change_pct = 1.0 if current_value != 0 else 0.0
        else:
            change_pct = abs(current_value - baseline_value) / abs(baseline_value)
        
        self.details = {
            "current_value": float(current_value),
            "baseline_value": float(baseline_value),
            "change_percentage": float(change_pct),
            "threshold": float(self.threshold)
        }
        
        self.violated = change_pct > self.threshold
        return self.violated
        
    def get_remediation(self) -> str:
        """Get remediation steps
        
        Returns:
            Remediation steps as string
        """
        if not self.violated:
            return ""
            
        if "error" in self.details and "not found" in self.details["error"]:
            return f"Add column {self.column} to the dataset or update the quality rule configuration"
            
        if "error" in self.details and "not numeric" in self.details["error"]:
            return f"Rule only applies to numeric columns. Update rule configuration."
            
        if "error" in self.details and "Invalid statistic" in self.details["error"]:
            return f"Use a valid statistic: 'mean', 'median', 'std', 'min', 'max', 'count', 'sum'"
            
        current_value = self.details.get("current_value")
        baseline_value = self.details.get("baseline_value")
        change_pct = self.details.get("change_percentage", 0) * 100
        threshold_pct = self.details.get("threshold", 0) * 100
        
        direction = "increased" if current_value > baseline_value else "decreased"
        
        return (
            f"Column {self.column} {self.statistic} has {direction} by {change_pct:.1f}% "
            f"(threshold: {threshold_pct:.1f}%).\n"
            f"Previous value: {baseline_value:.2f}, Current value: {current_value:.2f}\n"
            f"Remediation steps:\n"
            f"1. Verify if this change is expected due to business conditions\n"
            f"2. Check for any process changes that might affect this metric\n"
            f"3. Investigate data collection or processing changes\n"
            f"4. Consider adjusting thresholds if this change is the new normal"
        )

class PatternMatchRule(DataQualityRule):
    """Rule for checking if values match a specific pattern"""
    
    def __init__(self, column: str, pattern: str, name: str = None, 
                 threshold: float = 0.05, severity: str = "medium"):
        """Initialize pattern match rule
        
        Args:
            column: Column to check
            pattern: Regex pattern
            name: Rule name (defaults to pattern_column)
            threshold: Maximum allowed percentage of non-matching values
            severity: Rule severity
        """
        rule_name = name or f"pattern_{column}"
        super().__init__(
            name=rule_name,
            description=f"Check if values in {column} match pattern {pattern}",
            severity=severity
        )
        self.column = column
        self.pattern = pattern
        self.threshold = threshold
        
    def check(self, data: pd.DataFrame) -> bool:
        """Check if rule is violated
        
        Args:
            data: DataFrame to check
            
        Returns:
            True if rule is violated
        """
        if self.column not in data.columns:
            self.violated = True
            self.details = {
                "error": f"Column {self.column} not found in data"
            }
            return True
            
        # Skip check if column is not string
        if not pd.api.types.is_string_dtype(data[self.column]) and not pd.api.types.is_object_dtype(data[self.column]):
            self.violated = False
            self.details = {
                "error": f"Column {self.column} is not string type"
            }
            return False
            
        # Get valid data (non-missing values)
        valid_data = data[self.column].dropna()
        
        # Convert all values to strings
        valid_data = valid_data.astype(str)
        
        # Check pattern match
        pattern_regex = re.compile(self.pattern)
        matches = valid_data.apply(lambda x: bool(pattern_regex.match(x)))
        
        # Calculate match percentage
        match_count = matches.sum()
        total_count = len(valid_data)
        match_pct = match_count / total_count if total_count > 0 else 1.0
        non_match_pct = 1.0 - match_pct
        
        # Get examples of non-matching values
        non_matching_values = valid_data[~matches].head(5).tolist()
        
        self.details = {
            "match_count": int(match_count),
            "total_count": int(total_count),
            "match_percentage": float(match_pct),
            "non_match_percentage": float(non_match_pct),
            "threshold": float(self.threshold),
            "example_non_matching": non_matching_values
        }
        
        self.violated = non_match_pct > self.threshold
        return self.violated
        
    def get_remediation(self) -> str:
        """Get remediation steps
        
        Returns:
            Remediation steps as string
        """
        if not self.violated:
            return ""
            
        if "error" in self.details and "not found" in self.details["error"]:
            return f"Add column {self.column} to the dataset or update the quality rule configuration"
            
        if "error" in self.details and "not string type" in self.details["error"]:
            return f"Rule only applies to string columns. Update rule configuration."
            
        non_match_pct = self.details.get("non_match_percentage", 0) * 100
        threshold_pct = self.details.get("threshold", 0) * 100
        examples = self.details.get("example_non_matching", [])
        examples_str = ", ".join([f"'{x}'" for x in examples[:3]])
        
        return (
            f"Column {self.column} has {non_match_pct:.1f}% values not matching pattern '{self.pattern}' "
            f"(threshold: {threshold_pct:.1f}%).\n"
            f"Examples of non-matching values: {examples_str}\n"
            f"Remediation steps:\n"
            f"1. Verify if the pattern is correct for this column\n"
            f"2. Implement data validation to ensure pattern compliance\n"
            f"3. Standardize data entry processes\n"
            f"4. Consider data cleansing for existing records"
        )

class CompletenessRule(DataQualityRule):
    """Rule for checking if all required columns are present"""
    
    def __init__(self, required_columns: List[str], severity: str = "high"):
        """Initialize completeness rule
        
        Args:
            required_columns: List of required columns
            severity: Rule severity
        """
        super().__init__(
            name="completeness",
            description=f"Check if all required columns are present",
            severity=severity
        )
        self.required_columns = required_columns
        
    def check(self, data: pd.DataFrame) -> bool:
        """Check if rule is violated
        
        Args:
            data: DataFrame to check
            
        Returns:
            True if rule is violated
        """
        # Check if all required columns are present
        missing_columns = [col for col in self.required_columns if col not in data.columns]
        
        self.details = {
            "required_columns": self.required_columns,
            "missing_columns": missing_columns,
            "missing_count": len(missing_columns),
            "total_required": len(self.required_columns)
        }
        
        self.violated = len(missing_columns) > 0
        return self.violated
        
    def get_remediation(self) -> str:
        """Get remediation steps
        
        Returns:
            Remediation steps as string
        """
        if not self.violated:
            return ""
            
        missing_columns = self.details.get("missing_columns", [])
        missing_columns_str = ", ".join(missing_columns)
        
        return (
            f"Missing required columns: {missing_columns_str}\n"
            f"Remediation steps:\n"
            f"1. Add missing columns to the dataset\n"
            f"2. Verify data collection process includes all required fields\n"
            f"3. Check if column names have changed or are inconsistent\n"
            f"4. Update data import/export processes to include all required columns"
        )

class ForeignKeyRule(DataQualityRule):
    """Rule for checking foreign key integrity"""
    
    def __init__(self, column: str, reference_table: str, reference_column: str, 
                 threshold: float = 0.01, severity: str = "high"):
        """Initialize foreign key rule
        
        Args:
            column: Column to check
            reference_table: Referenced table
            reference_column: Referenced column
            threshold: Maximum allowed percentage of violations
            severity: Rule severity
        """
        super().__init__(
            name=f"foreign_key_{column}",
            description=f"Check foreign key integrity for {column} referencing {reference_table}.{reference_column}",
            severity=severity
        )
        self.column = column
        self.reference_table = reference_table
        self.reference_column = reference_column
        self.threshold = threshold
        self.conn = None
        
    def check(self, data: pd.DataFrame) -> bool:
        """Check if rule is violated
        
        Args:
            data: DataFrame to check
            
        Returns:
            True if rule is violated
        """
        if self.column not in data.columns:
            self.violated = True
            self.details = {
                "error": f"Column {self.column} not found in data"
            }
            return True
            
        # Skip check if no database connection
        if self.conn is None:
            self.violated = False
            self.details = {
                "error": "No database connection provided"
            }
            return False
            
        try:
            # Get reference values
            query = f"SELECT DISTINCT {self.reference_column} FROM {self.reference_table}"
            reference_df = pd.read_sql(query, self.conn)
            reference_values = set(reference_df[self.reference_column].dropna().astype(str))
            
            # Get valid data (non-missing values)
            valid_data = data[self.column].dropna()
            
            # Check if values exist in reference
            values = set(valid_data.astype(str))
            violations = values - reference_values
            
            # Get violation rows
            violation_mask = data[self.column].astype(str).isin(violations)
            violation_count = violation_mask.sum()
            total_count = len(valid_data)
            violation_pct = violation_count / total_count if total_count > 0 else 0
            
            # Get examples of violations
            violation_examples = data.loc[violation_mask, self.column].head(5).tolist()
            
            self.details = {
                "violation_count": int(violation_count),
                "total_count": int(total_count),
                "violation_percentage": float(violation_pct),
                "threshold": float(self.threshold),
                "example_violations": violation_examples
            }
            
            self.violated = violation_pct > self.threshold
            return self.violated
            
        except Exception as e:
            self.violated = True
            self.details = {
                "error": f"Error checking foreign key: {str(e)}"
            }
            return True
        
    def get_remediation(self) -> str:
        """Get remediation steps
        
        Returns:
            Remediation steps as string
        """
        if not self.violated:
            return ""
            
        if "error" in self.details and "not found" in self.details["error"]:
            return f"Add column {self.column} to the dataset or update the quality rule configuration"
            
        if "error" in self.details and "No database connection" in self.details["error"]:
            return f"Provide a database connection to check foreign key integrity"
            
        if "error" in self.details and "Error checking foreign key" in self.details["error"]:
            return f"Fix database error: {self.details['error']}"
            
        violation_pct = self.details.get("violation_percentage", 0) * 100
        threshold_pct = self.details.get("threshold", 0) * 100
        examples = self.details.get("example_violations", [])
        examples_str = ", ".join([str(x) for x in examples[:3]])
        
        return (
            f"Column {self.column} has {violation_pct:.1f}% values not found in {self.reference_table}.{self.reference_column} "
            f"(threshold: {threshold_pct:.1f}%).\n"
            f"Examples of violations: {examples_str}\n"
            f"Remediation steps:\n"
            f"1. Add missing values to the reference table\n"
            f"2. Fix incorrect values in this column\n"
            f"3. Implement referential integrity constraints\n"
            f"4. Improve data entry validation to ensure valid references"
        )

class DataQualityCheck:
    """Data quality check result"""
    
    def __init__(self, table: str, rules: List[DataQualityRule], 
                 timestamp: datetime = None, check_id: str = None):
        """Initialize data quality check
        
        Args:
            table: Table name
            rules: List of rules
            timestamp: Check timestamp
            check_id: Check ID
        """
        self.table = table
        self.rules = rules
        self.timestamp = timestamp or datetime.now()
        self.check_id = check_id or f"{table}_{self.timestamp.strftime('%Y%m%d%H%M%S')}"
        self.violations = []
        
    def to_dict(self) -> Dict:
        """Convert check to dictionary
        
        Returns:
            Dictionary representation of check
        """
        return {
            "check_id": self.check_id,
            "table": self.table,
            "timestamp": self.timestamp.isoformat(),
            "rules": [rule.to_dict() for rule in self.rules],
            "violations": [rule.to_dict() for rule in self.violations],
            "violation_count": len(self.violations),
            "total_rules": len(self.rules)
        }
        
    def to_json(self) -> str:
        """Convert check to JSON
        
        Returns:
            JSON representation of check
        """
        return json.dumps(self.to_dict(), indent=2)
        
    def get_summary(self) -> str:
        """Get summary of check
        
        Returns:
            Summary as string
        """
        if len(self.violations) == 0:
            return f"No data quality issues found in {self.table}"
            
        summary = f"Found {len(self.violations)} data quality issues in {self.table}:\n"
        
        for rule in self.violations:
            summary += f"- {rule.name}: {rule.description}\n"
            if hasattr(rule, 'column'):
                summary += f"  Column: {rule.column}\n"
            summary += f"  Severity: {rule.severity}\n"
            summary += f"  Details: {rule.details}\n"
            summary += f"  Remediation: {rule.get_remediation()}\n\n"
            
        return summary
        
    def log_violations(self):
        """Log violations to data quality log"""
        for rule in self.violations:
            if hasattr(rule, 'column'):
                log_data_quality_issue(
                    table=self.table,
                    column=rule.column,
                    issue=f"{rule.name}: {rule.description}",
                    count=rule.details.get('total_count', None)
                )
            else:
                log_data_quality_issue(
                    table=self.table,
                    column="",
                    issue=f"{rule.name}: {rule.description}"
                )

class DataQualityMonitor:
    """Data quality monitoring system"""
    
    def __init__(self, db_path: str = None, log_dir: str = None, 
                 history_dir: str = None, thresholds: Dict = None):
        """Initialize data quality monitor
        
        Args:
            db_path: Database path
            log_dir: Log directory
            history_dir: History directory
            thresholds: Quality thresholds
        """
        # Get configuration
        config_obj = get_config()
        self.db_path = db_path or config_obj.get("database.db_path", "medical_billing.db")
        self.log_dir = log_dir or config_obj.get("paths.log_dir", "logs")
        self.history_dir = history_dir or os.path.join(self.log_dir, "data_quality")
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        
        # Create directories
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)
        
        # Initialize database connection
        self.conn = None
        self.connect_db()
        
        # Initialize baseline statistics
        self.baseline_stats = {}
        self.load_baseline()
        
    def connect_db(self):
        """Connect to database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            self.conn = None
            
    def load_baseline(self):
        """Load baseline statistics"""
        baseline_path = os.path.join(self.history_dir, "baseline_stats.json")
        
        if os.path.exists(baseline_path):
            try:
                with open(baseline_path, 'r') as f:
                    self.baseline_stats = json.load(f)
                logger.info(f"Loaded baseline statistics from {baseline_path}")
            except Exception as e:
                logger.error(f"Error loading baseline statistics: {e}")
                self.baseline_stats = {}
                
    def save_baseline(self):
        """Save baseline statistics"""
        baseline_path = os.path.join(self.history_dir, "baseline_stats.json")
        
        try:
            with open(baseline_path, 'w') as f:
                json.dump(self.baseline_stats, f, indent=2)
            logger.info(f"Saved baseline statistics to {baseline_path}")
        except Exception as e:
            logger.error(f"Error saving baseline statistics: {e}")
            
    def update_baseline(self, table: str, column: str, stats: Dict):
        """Update baseline statistics
        
        Args:
            table: Table name
            column: Column name
            stats: Statistics dictionary
        """
        if table not in self.baseline_stats:
            self.baseline_stats[table] = {}
            
        if column not in self.baseline_stats[table]:
            self.baseline_stats[table][column] = {}
            
        self.baseline_stats[table][column].update(stats)
        self.save_baseline()
        
    def calculate_statistics(self, table: str) -> Dict:
        """Calculate statistics for table
        
        Args:
            table: Table name
            
        Returns:
            Dictionary of statistics by column
        """
        if self.conn is None:
            logger.error(f"No database connection")
            return {}
            
        try:
            # Get table data
            query = f"SELECT * FROM {table}"
            df = pd.read_sql(query, self.conn)
            
            if len(df) == 0:
                logger.warning(f"No data in table {table}")
                return {}
                
            # Calculate statistics for each column
            stats = {}
            
            for column in df.columns:
                col_stats = {}
                
                # Skip non-numeric columns for numerical statistics
                if pd.api.types.is_numeric_dtype(df[column]):
                    col_stats["count"] = int(df[column].count())
                    col_stats["missing"] = int(df[column].isna().sum())
                    col_stats["mean"] = float(df[column].mean())
                    col_stats["median"] = float(df[column].median())
                    col_stats["std"] = float(df[column].std())
                    col_stats["min"] = float(df[column].min())
                    col_stats["max"] = float(df[column].max())
                    col_stats["negative_count"] = int((df[column] < 0).sum())
                    col_stats["zero_count"] = int((df[column] == 0).sum())
                    
                    # Calculate percentiles
                    percentiles = df[column].quantile([0.01, 0.05, 0.25, 0.75, 0.95, 0.99])
                    col_stats["p01"] = float(percentiles[0.01])
                    col_stats["p05"] = float(percentiles[0.05])
                    col_stats["p25"] = float(percentiles[0.25])
                    col_stats["p75"] = float(percentiles[0.75])
                    col_stats["p95"] = float(percentiles[0.95])
                    col_stats["p99"] = float(percentiles[0.99])
                    
                    # Calculate IQR
                    col_stats["iqr"] = float(col_stats["p75"] - col_stats["p25"])
                    
                else:
                    # For non-numeric columns, calculate basic statistics
                    col_stats["count"] = int(df[column].count())
                    col_stats["missing"] = int(df[column].isna().sum())
                    col_stats["unique"] = int(df[column].nunique())
                    
                    # Calculate most common values
                    most_common = df[column].value_counts().head(5).to_dict()
                    col_stats["most_common"] = {str(k): int(v) for k, v in most_common.items()}
                    
                # Add to statistics
                stats[column] = col_stats
                
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating statistics for table {table}: {e}")
            return {}
            
    def create_standard_rules(self, table: str, columns: List[str] = None) -> List[DataQualityRule]:
        """Create standard rules for table
        
        Args:
            table: Table name
            columns: List of columns to check (if None, check all columns)
            
        Returns:
            List of data quality rules
        """
        if self.conn is None:
            logger.error(f"No database connection")
            return []
            
        try:
            # Get table data
            query = f"SELECT * FROM {table} LIMIT 1"
            df = pd.read_sql(query, self.conn)
            
            if len(df) == 0:
                logger.warning(f"No data in table {table}")
                return []
                
            # If columns not specified, use all columns
            if columns is None:
                columns = df.columns.tolist()
                
            # Create rules
            rules = []
            
            # Completeness rule
            rules.append(CompletenessRule(required_columns=columns, severity="high"))
            
            # Column-specific rules
            for column in columns:
                # Missing values rule
                rules.append(MissingValuesRule(column=column))
                
                # For numeric columns
                if column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
                    # Negative values rule for amounts
                    if any(word in column.lower() for word in ['amount', 'payment', 'cash', 'revenue', 'price']):
                        rules.append(NegativeValuesRule(column=column))
                    
                    # Outlier rule
                    rules.append(OutlierRule(column=column))
                    
                    # Statistical change rules
                    if table in self.baseline_stats and column in self.baseline_stats.get(table, {}):
                        for stat in ['mean', 'median', 'std']:
                            if stat in self.baseline_stats[table][column]:
                                rules.append(StatisticalChangeRule(
                                    column=column,
                                    statistic=stat,
                                    baseline=self.baseline_stats[table]
                                ))
                
                # For string/object columns
                elif column in df.columns and (pd.api.types.is_string_dtype(df[column]) or pd.api.types.is_object_dtype(df[column])):
                    # Pattern rules for specific columns
                    if column.lower() in ['email', 'email_address']:
                        rules.append(PatternMatchRule(
                            column=column,
                            pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                            name=f"email_pattern_{column}"
                        ))
                    elif column.lower() in ['phone', 'phone_number', 'telephone']:
                        rules.append(PatternMatchRule(
                            column=column,
                            pattern=r'^\+?[0-9\-\(\)\s]{10,15}$',
                            name=f"phone_pattern_{column}"
                        ))
                    elif column.lower() in ['zip', 'zipcode', 'postal_code']:
                        rules.append(PatternMatchRule(
                            column=column,
                            pattern=r'^\d{5}(-\d{4})?$',
                            name=f"zipcode_pattern_{column}"
                        ))
                    elif column.lower() in ['npi', 'npi_number']:
                        rules.append(PatternMatchRule(
                            column=column,
                            pattern=r'^\d{10}$',
                            name=f"npi_pattern_{column}"
                        ))
                        
            return rules
            
        except Exception as e:
            logger.error(f"Error creating rules for table {table}: {e}")
            return []
            
    def check_table(self, table: str, rules: List[DataQualityRule] = None, 
                    columns: List[str] = None) -> DataQualityCheck:
        """Check data quality for table
        
        Args:
            table: Table name
            rules: List of rules to check
            columns: List of columns to check
            
        Returns:
            DataQualityCheck result
        """
        if self.conn is None:
            logger.error(f"No database connection")
            return DataQualityCheck(table=table, rules=[])
            
        try:
            # Get table data
            query = f"SELECT * FROM {table}"
            df = pd.read_sql(query, self.conn)
            
            if len(df) == 0:
                logger.warning(f"No data in table {table}")
                return DataQualityCheck(table=table, rules=[])
                
            # If rules not specified, create standard rules
            if rules is None:
                rules = self.create_standard_rules(table, columns)
                
            # Create check
            check = DataQualityCheck(table=table, rules=rules)
            
            # Check each rule
            for rule in rules:
                # For foreign key rules, set connection
                if isinstance(rule, ForeignKeyRule):
                    rule.conn = self.conn
                    
                # Check rule
                violated = rule.check(df)
                
                if violated:
                    check.violations.append(rule)
                    
            # Log violations
            check.log_violations()
            
            # Save check result
            self._save_check_result(check)
            
            return check
            
        except Exception as e:
            logger.error(f"Error checking table {table}: {e}")
            return DataQualityCheck(table=table, rules=[])
            
    def _save_check_result(self, check: DataQualityCheck):
        """Save check result
        
        Args:
            check: DataQualityCheck result
        """
        try:
            # Create filename
            filename = f"{check.check_id}.json"
            filepath = os.path.join(self.history_dir, filename)
            
            # Save as JSON
            with open(filepath, 'w') as f:
                f.write(check.to_json())
                
            logger.info(f"Saved check result to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving check result: {e}")
            
    def generate_trend_chart(self, table: str, column: str, statistic: str = "count", 
                             days: int = 30, chart_path: str = None) -> str:
        """Generate trend chart for statistic
        
        Args:
            table: Table name
            column: Column name
            statistic: Statistic to chart
            days: Number of days to include
            chart_path: Path to save chart (if None, use default path)
            
        Returns:
            Path to saved chart
        """
        try:
            # Define time period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get statistics history
            stats_history = self._get_statistics_history(table, column, start_date, end_date)
            
            if not stats_history:
                logger.warning(f"No statistics history for {table}.{column}")
                return None
                
            # Extract dates and values
            dates = []
            values = []
            
            for item in stats_history:
                if statistic in item["stats"]:
                    dates.append(datetime.fromisoformat(item["timestamp"]))
                    values.append(item["stats"][statistic])
                    
            if not dates:
                logger.warning(f"No {statistic} data for {table}.{column}")
                return None
                
            # Create chart
            plt.figure(figsize=(10, 5))
            plt.plot(dates, values, marker='o')
            plt.title(f"{statistic.capitalize()} trend for {table}.{column}")
            plt.xlabel("Date")
            plt.ylabel(statistic.capitalize())
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save chart
            if chart_path is None:
                chart_filename = f"{table}_{column}_{statistic}_trend.png"
                chart_path = os.path.join(self.history_dir, chart_filename)
                
            plt.savefig(chart_path)
            plt.close()
            
            logger.info(f"Generated trend chart for {table}.{column}.{statistic} at {chart_path}")
            
            return chart_path
            
        except Exception as e:
            logger.error(f"Error generating trend chart: {e}")
            return None
            
    def _get_statistics_history(self, table: str, column: str, start_date: datetime, 
                                end_date: datetime) -> List[Dict]:
        """Get statistics history
        
        Args:
            table: Table name
            column: Column name
            start_date: Start date
            end_date: End date
            
        Returns:
            List of statistics entries
        """
        try:
            # Find all check files
            history = []
            
            for filename in os.listdir(self.history_dir):
                if filename.endswith('.json') and filename.startswith(table):
                    filepath = os.path.join(self.history_dir, filename)
                    
                    try:
                        with open(filepath, 'r') as f:
                            check_data = json.load(f)
                            
                        # Parse timestamp
                        timestamp = datetime.fromisoformat(check_data.get("timestamp", ""))
                        
                        # Check if within date range
                        if start_date <= timestamp <= end_date:
                            # Look for column statistics
                            stats = check_data.get("statistics", {}).get(column, {})
                            
                            if stats:
                                history.append({
                                    "timestamp": check_data["timestamp"],
                                    "stats": stats
                                })
                    except Exception as e:
                        logger.error(f"Error reading check file {filename}: {e}")
                        
            # Sort by timestamp
            history.sort(key=lambda x: x["timestamp"])
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting statistics history: {e}")
            return []
            
    def generate_quality_report(self, tables: List[str] = None, 
                               days: int = 7, report_path: str = None) -> str:
        """Generate quality report
        
        Args:
            tables: List of tables to include
            days: Number of days to include
            report_path: Path to save report (if None, use default path)
            
        Returns:
            Path to saved report
        """
        try:
            # Define time period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # If tables not specified, get all tables
            if tables is None and self.conn is not None:
                cursor = self.conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
            if not tables:
                logger.warning("No tables found for quality report")
                return None
                
            # Create report
            report = [
                f"# Data Quality Report",
                f"",
                f"**Generated:** {end_date.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({days} days)",
                f"",
                f"## Summary",
                f"",
            ]
            
            # Get all check files in the period
            check_files = []
            
            for filename in os.listdir(self.history_dir):
                if not filename.endswith('.json') or filename == "baseline_stats.json":
                    continue
                    
                filepath = os.path.join(self.history_dir, filename)
                
                try:
                    with open(filepath, 'r') as f:
                        check_data = json.load(f)
                        
                    # Parse timestamp
                    timestamp = datetime.fromisoformat(check_data.get("timestamp", ""))
                    
                    # Check if within date range
                    if start_date <= timestamp <= end_date:
                        check_files.append((filepath, check_data))
                except Exception as e:
                    logger.error(f"Error reading check file {filename}: {e}")
                    
            # Aggregate violations by table
            violations_by_table = {}
            
            for _, check_data in check_files:
                table = check_data.get("table", "unknown")
                
                if table not in violations_by_table:
                    violations_by_table[table] = {
                        "total_checks": 0,
                        "total_violations": 0,
                        "violations_by_rule": {}
                    }
                    
                violations_by_table[table]["total_checks"] += 1
                violations_by_table[table]["total_violations"] += check_data.get("violation_count", 0)
                
                # Aggregate by rule
                for violation in check_data.get("violations", []):
                    rule_name = violation.get("name", "unknown")
                    
                    if rule_name not in violations_by_table[table]["violations_by_rule"]:
                        violations_by_table[table]["violations_by_rule"][rule_name] = {
                            "count": 0,
                            "severity": violation.get("severity", "medium"),
                            "description": violation.get("description", "")
                        }
                        
                    violations_by_table[table]["violations_by_rule"][rule_name]["count"] += 1
                    
            # Filter to requested tables
            violations_by_table = {table: data for table, data in violations_by_table.items() if table in tables}
            
            # Add summary
            total_checks = sum(data["total_checks"] for data in violations_by_table.values())
            total_violations = sum(data["total_violations"] for data in violations_by_table.values())
            
            if total_checks > 0:
                report.append(f"- **Total Checks:** {total_checks}")
                report.append(f"- **Total Violations:** {total_violations}")
                report.append(f"- **Violation Rate:** {total_violations / total_checks:.2%}")
                report.append(f"")
                
                # Add table summaries
                report.append(f"### Violations by Table")
                report.append(f"")
                report.append(f"| Table | Checks | Violations | Rate |")
                report.append(f"|-------|--------|------------|------|")
                
                for table, data in violations_by_table.items():
                    checks = data["total_checks"]
                    violations = data["total_violations"]
                    rate = violations / checks if checks > 0 else 0
                    
                    report.append(f"| {table} | {checks} | {violations} | {rate:.2%} |")
                    
                # Add detailed section for each table
                report.append(f"")
                report.append(f"## Detailed Findings")
                report.append(f"")
                
                for table, data in violations_by_table.items():
                    if data["total_violations"] == 0:
                        continue
                        
                    report.append(f"### {table}")
                    report.append(f"")
                    report.append(f"| Rule | Severity | Count | Description |")
                    report.append(f"|------|----------|-------|-------------|")
                    
                    # Sort by severity and count
                    severity_order = {"high": 0, "medium": 1, "low": 2}
                    
                    sorted_rules = sorted(
                        data["violations_by_rule"].items(),
                        key=lambda x: (severity_order.get(x[1]["severity"], 3), -x[1]["count"])
                    )
                    
                    for rule_name, rule_data in sorted_rules:
                        report.append(
                            f"| {rule_name} | {rule_data['severity']} | {rule_data['count']} | {rule_data['description']} |"
                        )
                        
                    report.append(f"")
                    
                # Add trend charts
                report.append(f"## Trends")
                report.append(f"")
                
                # Generate trend charts for key metrics
                for table in tables:
                    if table not in violations_by_table:
                        continue
                        
                    # Get columns for this table
                    if self.conn is not None:
                        cursor = self.conn.cursor()
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [row[1] for row in cursor.fetchall()]
                        
                        # Generate charts for numeric columns
                        for column in columns:
                            # Try to determine if column is numeric
                            try:
                                cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
                                value = cursor.fetchone()[0]
                                
                                if isinstance(value, (int, float)):
                                    # Generate chart
                                    chart_filename = f"{table}_{column}_count_trend.png"
                                    chart_path = os.path.join(self.history_dir, chart_filename)
                                    
                                    if self.generate_trend_chart(table, column, "count", days, chart_path):
                                        report.append(f"### {table}.{column} Count Trend")
                                        report.append(f"")
                                        report.append(f"![{table}.{column} Count Trend]({chart_path})")
                                        report.append(f"")
                            except Exception:
                                # Skip if error
                                continue
            else:
                report.append(f"No data quality checks found in the specified period.")
                
            # Save report
            if report_path is None:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                report_path = os.path.join(self.history_dir, f"quality_report_{timestamp}.md")
                
            with open(report_path, 'w') as f:
                f.write("\n".join(report))
                
            logger.info(f"Generated quality report at {report_path}")
            
            return report_path
            
        except Exception as e:
            logger.error(f"Error generating quality report: {e}")
            return None
            
    def check_all_tables(self, tables: List[str] = None) -> Dict[str, DataQualityCheck]:
        """Check all tables
        
        Args:
            tables: List of tables to check (if None, check all tables)
            
        Returns:
            Dictionary of DataQualityCheck results by table
        """
        if self.conn is None:
            logger.error(f"No database connection")
            return {}
            
        try:
            # If tables not specified, get all tables
            if tables is None:
                cursor = self.conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
            if not tables:
                logger.warning("No tables found")
                return {}
                
            # Check each table
            results = {}
            
            for table in tables:
                logger.info(f"Checking table {table}")
                check = self.check_table(table)
                results[table] = check
                
                # Calculate and update statistics
                stats = self.calculate_statistics(table)
                
                for column, col_stats in stats.items():
                    self.update_baseline(table, column, col_stats)
                    
            return results
            
        except Exception as e:
            logger.error(f"Error checking all tables: {e}")
            return {}
            
    def setup_monitoring_schedule(self, frequency_hours: int = 24):
        """Set up monitoring schedule
        
        Args:
            frequency_hours: Frequency in hours
        """
        # This is just a placeholder for a real scheduling mechanism
        # In a real application, you would use a scheduler like APScheduler or Celery
        logger.info(f"Setting up monitoring schedule: every {frequency_hours} hours")
        logger.info(f"Note: This is a placeholder. You need to implement actual scheduling.")
        
        # Example scheduling code:
        # from apscheduler.schedulers.background import BackgroundScheduler
        # scheduler = BackgroundScheduler()
        # scheduler.add_job(self.check_all_tables, 'interval', hours=frequency_hours)
        # scheduler.start()

# Convenience function to get monitor
def get_data_quality_monitor() -> DataQualityMonitor:
    """Get data quality monitor instance
    
    Returns:
        DataQualityMonitor instance
    """
    return DataQualityMonitor()

# Command line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Quality Monitoring System")
    parser.add_argument("--check", action="store_true", help="Check all tables")
    parser.add_argument("--report", action="store_true", help="Generate quality report")
    parser.add_argument("--days", type=int, default=7, help="Days to include in report")
    parser.add_argument("--table", type=str, help="Specific table to check")
    args = parser.parse_args()
    
    monitor = get_data_quality_monitor()
    
    if args.check:
        if args.table:
            check = monitor.check_table(args.table)
            print(check.get_summary())
        else:
            results = monitor.check_all_tables()
            for table, check in results.items():
                if check.violations:
                    print(f"\n{'-' * 80}\n")
                    print(check.get_summary())
    
    if args.report:
        tables = [args.table] if args.table else None
        report_path = monitor.generate_quality_report(tables=tables, days=args.days)
        
        if report_path:
            print(f"Report generated: {report_path}")
        else:
            print("Failed to generate report")