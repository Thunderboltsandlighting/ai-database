"""
Utility functions for handling data privacy concerns in the Medical Billing system.
This module provides tools for masking, anonymizing, and handling sensitive data.
"""

import re
import pandas as pd
import hashlib
import random
from typing import Dict, List, Any, Optional, Union

from utils.logger import get_logger
from utils.config import get_config

# Get configuration and logger
logger = get_logger()
config = get_config()

# Define sensitive field patterns
PATIENT_ID_PATTERN = re.compile(r'^P\d+$')
DIAGNOSIS_CODE_PATTERN = re.compile(r'^[A-Z]\d+$')
NPI_PATTERN = re.compile(r'^\d{10}$')


def mask_patient_id(patient_id: str) -> str:
    """
    Mask a patient ID to show only the first and last characters.
    
    Args:
        patient_id: The patient ID to mask
        
    Returns:
        A masked version of the patient ID
    """
    if not patient_id or len(patient_id) < 4:
        return patient_id
        
    # Keep first character, mask the middle with exactly 3 asterisks, keep last character
    masked = patient_id[0] + '***' + patient_id[-1]
    return masked


def anonymize_dataframe(df: pd.DataFrame, sensitive_columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Create an anonymized copy of a dataframe by masking sensitive columns.
    
    Args:
        df: The dataframe to anonymize
        sensitive_columns: List of column names to anonymize. If None, auto-detect.
        
    Returns:
        An anonymized copy of the dataframe
    """
    if df.empty:
        return df.copy()
        
    # Create a copy to avoid modifying the original
    anonymized_df = df.copy()
    
    # Auto-detect sensitive columns if not provided
    if not sensitive_columns:
        sensitive_columns = []
        for col in df.columns:
            col_lower = col.lower()
            if any(term in col_lower for term in ['patient', 'person', 'name', 'ssn', 'address', 'phone', 'email']):
                sensitive_columns.append(col)
                
    # Apply anonymization to each sensitive column
    for col in sensitive_columns:
        if col not in df.columns:
            continue
            
        # Apply appropriate anonymization based on column type and name
        col_lower = col.lower()
        
        if 'patient' in col_lower and 'id' in col_lower:
            # Patient IDs: use consistent masking
            anonymized_df[col] = df[col].apply(lambda x: mask_patient_id(str(x)) if pd.notna(x) else x)
            
        elif any(term in col_lower for term in ['name', 'provider']):
            # Names: replace with "Person 1", "Provider 2", etc.
            unique_values = df[col].dropna().unique()
            replacement_map = {val: f"{col.title()} {i+1}" for i, val in enumerate(unique_values)}
            anonymized_df[col] = df[col].map(lambda x: replacement_map.get(x, x) if pd.notna(x) else x)
            
        elif any(term in col_lower for term in ['address', 'location', 'street']):
            # Addresses: replace with generic text
            anonymized_df[col] = anonymized_df[col].apply(lambda x: "Address Redacted" if pd.notna(x) else x)
            
        elif any(term in col_lower for term in ['ssn', 'social', 'security']):
            # SSNs: completely redact
            anonymized_df[col] = anonymized_df[col].apply(lambda _: "XXX-XX-XXXX" if pd.notna(_) else _)
            
        elif any(term in col_lower for term in ['email']):
            # Emails: replace with anonymized version
            anonymized_df[col] = anonymized_df[col].apply(
                lambda x: f"user{abs(hash(str(x)) % 10000):04d}@example.com" if pd.notna(x) else x
            )
            
        elif any(term in col_lower for term in ['phone', 'mobile', 'cell']):
            # Phone numbers: replace with fake number
            anonymized_df[col] = anonymized_df[col].apply(
                lambda _: "(555) 555-0000" if pd.notna(_) else _
            )
    
    logger.info(f"Anonymized {len(sensitive_columns)} columns in dataframe")
    return anonymized_df


def is_sensitive_data(data: Any) -> bool:
    """
    Check if a piece of data appears to be sensitive.
    
    Args:
        data: The data to check
        
    Returns:
        True if the data appears sensitive, False otherwise
    """
    if data is None:
        return False
        
    # Convert to string for pattern matching
    data_str = str(data)
    
    # Check against patterns
    if PATIENT_ID_PATTERN.match(data_str):
        return True
    if DIAGNOSIS_CODE_PATTERN.match(data_str):
        return True
    if NPI_PATTERN.match(data_str):
        return True
        
    # Check for common sensitive data patterns
    if any(pattern in data_str.lower() for pattern in ['ssn', 'social security', 'password', 'secret']):
        return True
        
    return False


def generate_privacy_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate a privacy report for a dataframe, identifying potential privacy concerns.
    
    Args:
        df: The dataframe to analyze
        
    Returns:
        A dictionary with the privacy report
    """
    report = {
        "potential_pii_columns": [],
        "unique_values_count": {},
        "sample_data": {},
        "recommendations": []
    }
    
    # Check each column for potential PII
    for col in df.columns:
        col_lower = col.lower()
        unique_count = df[col].nunique()
        sample = df[col].dropna().sample(min(3, len(df))).tolist() if not df.empty else []
        
        # Store basic info
        report["unique_values_count"][col] = unique_count
        report["sample_data"][col] = sample
        
        # Check for potentially sensitive columns
        if any(term in col_lower for term in ['patient', 'person', 'name', 'ssn', 'address', 'phone', 'email', 
                                              'birth', 'age', 'gender', 'race', 'diagnosis']):
            report["potential_pii_columns"].append(col)
            report["recommendations"].append(f"Consider anonymizing or masking the '{col}' column")
        
        # Check for high-cardinality columns that might be identifiers
        if unique_count > 0.8 * len(df) and unique_count > 10:
            if col not in report["potential_pii_columns"]:
                report["potential_pii_columns"].append(col)
                report["recommendations"].append(
                    f"Column '{col}' has high uniqueness ({unique_count} values) and may be an identifier"
                )
    
    # Add general recommendations
    if report["potential_pii_columns"]:
        report["recommendations"].append("Use the anonymize_dataframe() function before sharing or exporting data")
        
    return report