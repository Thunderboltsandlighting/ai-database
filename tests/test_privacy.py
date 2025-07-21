import pandas as pd
import pytest
from utils.privacy import (
    mask_patient_id,
    anonymize_dataframe,
    is_sensitive_data,
    generate_privacy_report
)

def test_mask_patient_id():
    """Test that patient IDs are properly masked"""
    # Test normal patient ID
    assert mask_patient_id("P12345") == "P***5"
    
    # Test short patient ID
    assert mask_patient_id("P1") == "P1"
    
    # Test empty string
    assert mask_patient_id("") == ""
    
    # Test None
    assert mask_patient_id(None) == None

def test_anonymize_dataframe():
    """Test dataframe anonymization"""
    # Create test dataframe with sensitive data
    df = pd.DataFrame({
        'patient_id': ['P12345', 'P67890', 'P24680'],
        'provider_name': ['Dr. Smith', 'Dr. Jones', 'Dr. Smith'],
        'cash_applied': [100.0, 200.0, 150.0],
        'diagnosis_code': ['A123', 'B456', 'C789'],
        'email': ['patient1@example.com', 'patient2@example.com', 'patient3@example.com']
    })
    
    # Anonymize the dataframe
    anon_df = anonymize_dataframe(df)
    
    # Check that sensitive columns were anonymized
    assert anon_df['patient_id'][0] != 'P12345'
    assert anon_df['provider_name'][0] != 'Dr. Smith'
    assert anon_df['email'][0] != 'patient1@example.com'
    
    # Check that non-sensitive columns were not changed
    assert anon_df['cash_applied'].equals(df['cash_applied'])
    
    # Check that the original dataframe was not modified
    assert df['patient_id'][0] == 'P12345'

def test_is_sensitive_data():
    """Test sensitive data detection"""
    # Test patient IDs
    assert is_sensitive_data("P12345") == True
    
    # Test diagnosis codes
    assert is_sensitive_data("A123") == True
    
    # Test non-sensitive data
    assert is_sensitive_data("hello world") == False
    assert is_sensitive_data(123) == False
    
    # Test None
    assert is_sensitive_data(None) == False
    
    # Test data with sensitive keywords
    assert is_sensitive_data("SSN: 123-45-6789") == True

def test_generate_privacy_report():
    """Test privacy report generation"""
    # Create test dataframe with sensitive data
    df = pd.DataFrame({
        'patient_id': ['P12345', 'P67890', 'P24680'],
        'provider_name': ['Dr. Smith', 'Dr. Jones', 'Dr. Smith'],
        'cash_applied': [100.0, 200.0, 150.0],
        'diagnosis_code': ['A123', 'B456', 'C789'],
        'email': ['patient1@example.com', 'patient2@example.com', 'patient3@example.com']
    })
    
    # Generate privacy report
    report = generate_privacy_report(df)
    
    # Check report structure
    assert 'potential_pii_columns' in report
    assert 'recommendations' in report
    assert 'unique_values_count' in report
    
    # Check that sensitive columns were identified
    assert 'patient_id' in report['potential_pii_columns']
    assert 'email' in report['potential_pii_columns']
    
    # Check that recommendations were generated
    assert len(report['recommendations']) > 0