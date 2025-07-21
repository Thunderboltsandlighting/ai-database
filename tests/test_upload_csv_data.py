import pandas as pd
import os
import pytest
import sqlite3
import tempfile
from pathlib import Path
from medical_billing_db import MedicalBillingDB

test_db_path = 'test_medical_billing.db'

def setup_module(module):
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

def teardown_module(module):
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

@pytest.fixture
def db():
    """Fixture to provide a fresh database instance for each test"""
    # Create a new database for testing
    db_instance = MedicalBillingDB(db_path=test_db_path)
    yield db_instance
    db_instance.close()

def test_upload_normal(db):
    """Test uploading a normal, valid CSV record"""
    df = pd.DataFrame([
        {'Cash Applied': 100.0, 'Provider': 'Dr. Smith', 'Date': '2024-01-01', 
         'Patient ID': 'P1', 'Service Date': '2024-01-01', 'Insurance Payment': 80.0, 
         'Patient Payment': 20.0, 'Adjustment Amount': 0.0, 'CPT Code': '99213', 
         'Diagnosis Code': 'A10', 'Payer': 'Aetna', 'Claim Number': 'C123', 'Notes': 'None'},
    ])
    result = db.upload_csv_data(df, 'test.csv')
    assert result['success']
    assert result['successful'] == 1
    assert result['failed'] == 0
    assert not result['issues']
    
    # Verify data was inserted correctly
    cursor = db.conn.execute(
        """SELECT pt.cash_applied, p.provider_name, pt.transaction_date, pt.patient_id 
           FROM payment_transactions pt
           JOIN providers p ON pt.provider_id = p.provider_id"""
    )
    row = cursor.fetchone()
    assert row[0] == 100.0
    assert row[1] == 'Dr. Smith'
    assert row[2] == '2024-01-01'
    assert row[3] == 'P1'
    
    # Verify provider was inserted
    cursor = db.conn.execute("SELECT provider_name FROM providers")
    provider = cursor.fetchone()
    assert provider[0] == 'Dr. Smith'
    
    # Check upload record
    cursor = db.conn.execute("SELECT filename, records_processed, records_successful FROM data_uploads")
    upload = cursor.fetchone()
    assert upload[0] == 'test.csv'
    assert upload[1] == 1
    assert upload[2] == 1

def test_upload_missing_and_negative_values(db):
    """Test handling of missing and negative values"""
    df = pd.DataFrame([
        {'Cash Applied': '', 'Provider': 'Dr. Smith', 'Date': '2024-01-01', 
         'Patient ID': 'P2', 'Service Date': '2024-01-01', 'Insurance Payment': 80.0, 
         'Patient Payment': 20.0, 'Adjustment Amount': 0.0, 'CPT Code': '99213', 
         'Diagnosis Code': 'A10', 'Payer': 'Aetna', 'Claim Number': 'C124', 'Notes': 'None'},
        {'Cash Applied': -50.0, 'Provider': 'Dr. Smith', 'Date': '2024-01-02', 
         'Patient ID': 'P3', 'Service Date': '2024-01-02', 'Insurance Payment': 40.0, 
         'Patient Payment': 10.0, 'Adjustment Amount': 0.0, 'CPT Code': '99214', 
         'Diagnosis Code': 'B20', 'Payer': 'Cigna', 'Claim Number': 'C125', 'Notes': 'Negative payment'},
    ])
    result = db.upload_csv_data(df, 'test2.csv')
    assert result['success']
    assert result['successful'] == 2  # Both rows processed, but with issues
    assert result['failed'] == 0
    
    # Check data quality issues
    issue_types = [issue['type'] for issue in result['issues']]
    assert 'missing_value' in issue_types
    assert 'negative_payment' in issue_types
    
    # Verify issues were recorded in the database
    cursor = db.conn.execute("SELECT issue_type, issue_description FROM data_quality_issues")
    issues = cursor.fetchall()
    assert len(issues) >= 2
    issue_types_db = [issue[0] for issue in issues]
    assert 'missing_value' in issue_types_db
    assert 'negative_payment' in issue_types_db
    
    # Verify the data was still inserted despite issues
    cursor = db.conn.execute("""
        SELECT COUNT(*) FROM payment_transactions pt
        JOIN providers p ON pt.provider_id = p.provider_id
        WHERE p.provider_name = 'Dr. Smith' AND
              (pt.patient_id = 'P2' OR pt.patient_id = 'P3')
    """)
    count = cursor.fetchone()[0]
    assert count == 2
    
    # Check that missing value is NULL in database
    cursor = db.conn.execute(
        "SELECT cash_applied FROM payment_transactions WHERE patient_id = 'P2'"
    )
    row = cursor.fetchone()
    assert row[0] is None

def test_upload_duplicate_providers(db):
    """Test handling of duplicate providers"""
    # First, add a provider
    provider_id = db.insert_provider("Dr. Smith")
    
    # Now upload data with the same provider
    df = pd.DataFrame([
        {'Cash Applied': 120.0, 'Provider': 'Dr. Smith', 'Date': '2024-01-03', 
         'Patient ID': 'P4', 'Service Date': '2024-01-03', 'Insurance Payment': 100.0, 
         'Patient Payment': 20.0, 'Adjustment Amount': 0.0, 'CPT Code': '99215', 
         'Diagnosis Code': 'C30', 'Payer': 'Aetna', 'Claim Number': 'C126', 'Notes': 'None'},
        {'Cash Applied': 130.0, 'Provider': 'Dr. Smith', 'Date': '2024-01-04', 
         'Patient ID': 'P5', 'Service Date': '2024-01-04', 'Insurance Payment': 110.0, 
         'Patient Payment': 20.0, 'Adjustment Amount': 0.0, 'CPT Code': '99215', 
         'Diagnosis Code': 'C31', 'Payer': 'Aetna', 'Claim Number': 'C127', 'Notes': 'None'},
    ])
    result = db.upload_csv_data(df, 'test3.csv')
    assert result['success']
    assert result['successful'] == 2
    assert result['failed'] == 0
    
    # Verify only one provider record exists
    cursor = db.conn.execute("SELECT COUNT(*) FROM providers WHERE provider_name = 'Dr. Smith'")
    count = cursor.fetchone()[0]
    assert count == 1
    
    # Verify that both transactions use the same provider_id
    cursor = db.conn.execute(
        """SELECT DISTINCT pt.provider_id 
           FROM payment_transactions pt
           JOIN providers p ON pt.provider_id = p.provider_id
           WHERE p.provider_name = 'Dr. Smith'"""
    )
    distinct_ids = cursor.fetchall()
    assert len(distinct_ids) == 1
    assert distinct_ids[0][0] == provider_id

def test_upload_invalid_data_types(db):
    """Test handling of invalid data types"""
    df = pd.DataFrame([
        {'Cash Applied': 'not_a_number', 'Provider': 'Dr. Lee', 'Date': '2024-01-05', 
         'Patient ID': 'P6', 'Service Date': '2024-01-05', 'Insurance Payment': 'oops', 
         'Patient Payment': 10.0, 'Adjustment Amount': 0.0, 'CPT Code': '99212', 
         'Diagnosis Code': 'D40', 'Payer': 'BlueCross', 'Claim Number': 'C128', 'Notes': 'Invalid data'},
    ])
    result = db.upload_csv_data(df, 'test4.csv')
    assert result['success']
    assert result['successful'] == 1  # Row processed, but with issues
    assert result['failed'] == 0
    
    # Check issues were recorded
    issue_types = [issue['type'] for issue in result['issues']]
    assert 'missing_value' in issue_types or 'processing_error' in issue_types
    
    # Verify the provider was still added
    cursor = db.conn.execute("SELECT COUNT(*) FROM providers WHERE provider_name = 'Dr. Lee'")
    count = cursor.fetchone()[0]
    assert count == 1
    
    # Verify numeric fields were converted to NULL
    cursor = db.conn.execute(
        "SELECT cash_applied, insurance_payment FROM payment_transactions WHERE patient_id = 'P6'"
    )
    row = cursor.fetchone()
    assert row[0] is None  # 'not_a_number' should be NULL
    assert row[1] is None  # 'oops' should be NULL

def test_upload_empty_dataframe(db):
    """Test handling of empty dataframe"""
    df = pd.DataFrame([])
    result = db.upload_csv_data(df, 'empty.csv')
    assert result['success']
    assert result['successful'] == 0
    assert result['failed'] == 0
    
    # Verify upload was recorded
    cursor = db.conn.execute("SELECT filename, records_processed FROM data_uploads WHERE filename = 'empty.csv'")
    upload = cursor.fetchone()
    assert upload is not None
    assert upload[0] == 'empty.csv'
    assert upload[1] == 0

def test_monthly_summary_updates(db):
    """Test that monthly summaries are updated after CSV uploads"""
    # Add test data
    provider_id = db.insert_provider("Dr. Monthly")
    
    # Insert transactions in different months
    db.conn.executemany(
        "INSERT INTO payment_transactions (provider_id, transaction_date, cash_applied, patient_id) VALUES (?, ?, ?, ?)",
        [
            (provider_id, "2024-01-15", 100.0, "P1"),
            (provider_id, "2024-01-20", 150.0, "P2"),
            (provider_id, "2024-02-10", 200.0, "P3"),
            (provider_id, "2024-02-15", 250.0, "P1"),
        ]
    )
    
    # Update monthly summaries
    db.update_monthly_summaries()
    
    # Check January summary
    cursor = db.conn.execute(
        "SELECT total_cash_applied, total_transactions, total_patients FROM monthly_provider_summary WHERE provider_id = ? AND month = '01' AND year = '2024'",
        (provider_id,)
    )
    jan_summary = cursor.fetchone()
    assert jan_summary is not None
    assert jan_summary[0] == 250.0  # January total
    assert jan_summary[1] == 2      # 2 transactions
    assert jan_summary[2] == 2      # 2 patients
    
    # Check February summary
    cursor = db.conn.execute(
        "SELECT total_cash_applied, total_transactions, total_patients FROM monthly_provider_summary WHERE provider_id = ? AND month = '02' AND year = '2024'",
        (provider_id,)
    )
    feb_summary = cursor.fetchone()
    assert feb_summary is not None
    assert feb_summary[0] == 450.0  # February total
    assert feb_summary[1] == 2      # 2 transactions
    assert feb_summary[2] == 2      # 2 patients (P1 and P3)

def test_transaction_integrity(db):
    """Test data integrity between transactions and their references"""
    # Create test CSV with columns in different order and some missing
    df = pd.DataFrame([
        {'Provider': 'Dr. Integrity', 'Payer': 'Integrity Insurance', 
         'Patient ID': 'P100', 'Cash Applied': 500.0, 'Date': '2024-03-01',
         'CPT Code': '99213'},
    ])
    
    result = db.upload_csv_data(df, 'integrity_test.csv')
    assert result['success']
    
    # Verify transaction was inserted
    cursor = db.conn.execute(
        "SELECT pt.provider_id, pt.transaction_date, pt.cash_applied, pt.patient_id, pt.payer_name, p.provider_name " 
        "FROM payment_transactions pt " 
        "JOIN providers p ON pt.provider_id = p.provider_id " 
        "WHERE p.provider_name = 'Dr. Integrity'"
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[2] == 500.0  # cash_applied
    assert row[3] == 'P100'  # patient_id
    assert row[4] == 'Integrity Insurance'  # payer_name
    assert row[5] == 'Dr. Integrity'  # provider_name through join
    
    # Verify foreign key constraint integrity
    provider_id = row[0]
    cursor = db.conn.execute("SELECT provider_id FROM providers WHERE provider_id = ?", (provider_id,))
    assert cursor.fetchone() is not None

def test_csv_from_file(db):
    """Test loading a real CSV file from disk"""
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        temp_path = temp_file.name
        # Write CSV data
        temp_file.write(b"Cash Applied,Provider,Date,Patient ID,Service Date,Insurance Payment,Patient Payment\n")
        temp_file.write(b"200.0,Dr. CSV,2024-04-01,P200,2024-03-31,180.0,20.0\n")
        temp_file.write(b"300.0,Dr. CSV,2024-04-02,P201,2024-04-01,250.0,50.0\n")
    
    try:
        # Load the CSV file
        df = pd.read_csv(temp_path)
        result = db.upload_csv_data(df, Path(temp_path).name)
        
        assert result['success']
        assert result['successful'] == 2
        assert result['failed'] == 0
        
        # Verify data was inserted
        cursor = db.conn.execute(
            """SELECT COUNT(*) FROM payment_transactions pt
               JOIN providers p ON pt.provider_id = p.provider_id
               WHERE p.provider_name = 'Dr. CSV'"""
        )
        count = cursor.fetchone()[0]
        assert count == 2
    finally:
        # Clean up temporary file
        os.unlink(temp_path)
        
        
def test_chunked_csv_upload(db):
    """Test uploading a CSV file with chunked processing"""
    # Create a larger temporary CSV file
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        temp_path = temp_file.name
        # Write CSV header
        temp_file.write(b"Cash Applied,Provider,Date,Patient ID,Service Date,Insurance Payment,Patient Payment\n")
        
        # Write 200 rows of data
        for i in range(200):
            row = f"{100.0 + i},Dr. Chunked,2024-05-{(i % 30) + 1:02d},P{300 + i},2024-05-{(i % 30) + 1:02d},{80.0 + i},{20.0}\n"
            temp_file.write(row.encode())
    
    try:
        # Use the new chunked upload method with a small chunk size
        result = db.upload_csv_file(temp_path, chunk_size=50)
        
        assert result['success']
        assert result['total_rows_processed'] == 200
        assert result['successful_rows'] == 200
        assert result['failed_rows'] == 0
        assert result['chunks_processed'] == 4  # 200 rows / 50 rows per chunk = 4 chunks
        
        # Verify all data was inserted
        cursor = db.conn.execute(
            """SELECT COUNT(*) FROM payment_transactions pt
               JOIN providers p ON pt.provider_id = p.provider_id
               WHERE p.provider_name = 'Dr. Chunked'"""
        )
        count = cursor.fetchone()[0]
        assert count == 200
        
        # Verify monthly summaries were updated
        cursor = db.conn.execute(
            """SELECT COUNT(*) FROM monthly_provider_summary mps
               JOIN providers p ON mps.provider_id = p.provider_id
               WHERE p.provider_name = 'Dr. Chunked' AND mps.year = '2024' AND mps.month = '05'"""
        )
        count = cursor.fetchone()[0]
        assert count == 1
        
        # Verify data upload record was created
        cursor = db.conn.execute(
            "SELECT records_processed, records_successful, status FROM data_uploads WHERE filename = ?",
            (os.path.basename(temp_path),)
        )
        upload = cursor.fetchone()
        assert upload is not None
        assert upload[0] == 200  # records_processed
        assert upload[1] == 200  # records_successful
        assert upload[2] == 'completed'  # status
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)