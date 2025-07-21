import os
import sqlite3
import pytest
import pandas as pd
import json
from medical_billing_db import MedicalBillingDB, Transaction, Provider

# Use a temporary database for testing to avoid affecting production data
import os
import tempfile

test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db')

def setup_module(module):
    # Remove test DB if it exists from previous runs
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

def teardown_module(module):
    # Clean up test DB after tests
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

@pytest.fixture
def db():
    """
    Fixture to provide a fresh in-memory database instance for each test.
    Uses SQLAlchemy ORM to add test data (providers, transactions) for consistency and best practice.
    """
    # Use an in-memory SQLite database for testing
    db = MedicalBillingDB(db_url="sqlite:///:memory:", use_sqlalchemy=True)
    # Create tables
    Transaction.metadata.create_all(db.engine)
    Provider.metadata.create_all(db.engine)
    # Add test data using ORM
    session = db.get_session()
    # Add a provider using ORM
    provider = Provider(provider_name="Dr. Smith")
    session.add(provider)
    session.commit()
    provider_id = provider.provider_id
    # Add a transaction for Dr. Smith (optional, for tests that need it)
    from datetime import date
    transaction = Transaction(provider_id=provider_id, patient_id="PAT001", cash_applied=150.0, transaction_date=date(2024, 1, 1))
    session.add(transaction)
    session.commit()
    session.close()
    yield db
    db.close()

def test_tables_created(db):
    """
    Test that all required tables are created when initializing MedicalBillingDB.
    This ensures the database schema is set up correctly.
    """
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    # List of expected tables
    expected_tables = [
        'providers',
        'payment_transactions',
        'monthly_provider_summary',
        'billing_terminology',
        'denial_codes',
        'payer_rules',
        'data_uploads',
        'data_quality_issues',
    ]
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = set(row[0] for row in cursor.fetchall())
    for table in expected_tables:
        assert table in tables, f"Table '{table}' should exist in the database."
    conn.close()

def test_insert_provider(db):
    """Test provider insertion functionality"""
    # Test inserting a new provider
    provider_id = db.insert_provider("Dr. Test", "Cardiology", "1234567890")
    assert provider_id > 0, "Provider ID should be a positive integer"
    
    # Test retrieving the provider
    cursor = db.conn.execute("SELECT provider_name, specialty, npi_number FROM providers WHERE provider_id = ?", (provider_id,))
    provider = cursor.fetchone()
    assert provider is not None, "Provider should exist in database"
    assert provider[0] == "Dr. Test", "Provider name should match"
    assert provider[1] == "Cardiology", "Provider specialty should match"
    assert provider[2] == "1234567890", "Provider NPI should match"
    
    # Test duplicate insertion returns same ID
    duplicate_id = db.insert_provider("Dr. Test", "Cardiology", "1234567890")
    assert duplicate_id == provider_id, "Duplicate provider should return same ID"
    
    # Test inserting with just name
    simple_id = db.insert_provider("Dr. Simple")
    assert simple_id > 0, "Provider ID should be a positive integer"
    cursor = db.conn.execute("SELECT specialty, npi_number FROM providers WHERE provider_id = ?", (simple_id,))
    simple_provider = cursor.fetchone()
    assert simple_provider[0] is None, "Specialty should be NULL"
    assert simple_provider[1] is None, "NPI should be NULL"

def test_get_provider_revenue(db):
    """Test provider revenue retrieval functionality"""
    # Insert test provider
    provider_id = db.insert_provider("Dr. Revenue")
    
    # Insert test transactions for this provider
    current_year = 2024
    db.conn.executemany(
        "INSERT INTO payment_transactions (provider_id, transaction_date, cash_applied) VALUES (?, ?, ?)",
        [
            (provider_id, f"{current_year}-01-15", 100.0),
            (provider_id, f"{current_year}-01-20", 150.0),
            (provider_id, f"{current_year}-02-10", 200.0),
            (provider_id, f"{current_year-1}-12-10", 300.0),  # Previous year
        ]
    )
    
    # Update monthly summaries
    db.update_monthly_summaries()
    
    # Test getting revenue for current year
    revenue_df = db.get_provider_revenue(year=current_year)
    assert not revenue_df.empty, "Revenue DataFrame should not be empty"
    assert len(revenue_df) > 0, "Should have at least one row"
    
    # Filter for our test provider
    provider_revenue = revenue_df[revenue_df['provider_name'] == 'Dr. Revenue']
    assert not provider_revenue.empty, "Test provider should have revenue data"
    
    # Sum the monthly values to verify total
    total_revenue = provider_revenue['total_cash_applied'].sum()
    assert total_revenue == 450.0, "Total revenue should match sum of transactions"
    
    # Test filtering by provider name
    provider_only_df = db.get_provider_revenue(provider_name="Dr. Revenue")
    assert not provider_only_df.empty, "Provider-filtered DataFrame should not be empty"
    assert len(provider_only_df) > 0, "Should have at least one row"
    assert all(provider_only_df['provider_name'] == "Dr. Revenue"), "All rows should be for Dr. Revenue"

def test_knowledge_base_functions(db):
    """Test adding and retrieving knowledge base entries"""
    # Test adding knowledge
    term = "CPT Code"
    definition = "Current Procedural Terminology code used for medical billing"
    category = "Billing"
    synonyms = ["Procedure Code", "Service Code"]
    
    db.add_knowledge(term, definition, category, synonyms)
    
    # Test exact term search
    results = db.search_knowledge("CPT Code")
    assert len(results) == 1, "Should find exactly one result for exact term"
    assert results[0]['term'] == term, "Term should match"
    assert results[0]['definition'] == definition, "Definition should match"
    assert results[0]['category'] == category, "Category should match"
    assert results[0]['synonyms'] == synonyms, "Synonyms should match"
    
    # Test partial term search
    partial_results = db.search_knowledge("CPT")
    assert len(partial_results) > 0, "Should find results for partial term"
    
    # Test definition search
    definition_results = db.search_knowledge("procedural")
    assert len(definition_results) > 0, "Should find results from definition text"
    
    # Add another term
    db.add_knowledge("ICD-10", "International Classification of Diseases codes", "Diagnosis", ["Diagnosis Code"])
    
    # Test multiple results
    multiple_results = db.search_knowledge("code")
    assert len(multiple_results) > 1, "Should find multiple results with common term"

def test_data_quality_functions(db):
    """Test data quality-related functions"""
    # Insert test transactions with missing cash_applied
    provider_id = db.insert_provider("Dr. Quality")
    db.conn.executemany(
        "INSERT INTO payment_transactions (provider_id, transaction_date, patient_id, cash_applied) VALUES (?, ?, ?, ?)",
        [
            (provider_id, "2024-03-15", "P1", 100.0),  # Normal transaction
            (provider_id, "2024-03-16", "P2", None),   # Missing cash_applied
            (provider_id, "2024-03-17", "P3", None),   # Missing cash_applied
        ]
    )
    
    # Test finding rows with missing cash_applied
    missing_df = db.get_rows_with_missing_cash_applied()
    assert len(missing_df) == 2, "Should find exactly 2 rows with missing cash_applied"
    assert all(pd.isna(missing_df['cash_applied'])), "All rows should have NULL cash_applied"
    
    # Test data quality issues recording
    db.conn.execute(
        "INSERT INTO data_quality_issues (table_name, issue_type, issue_description, severity, record_id) VALUES (?, ?, ?, ?, ?)",
        ("payment_transactions", "missing_value", "Missing cash_applied value", "medium", 1)
    )
    
    cursor = db.conn.execute("SELECT COUNT(*) FROM data_quality_issues WHERE issue_type = 'missing_value'")
    count = cursor.fetchone()[0]
    assert count > 0, "Should have recorded data quality issues"

def test_total_revenue_2024(db):
    """Test the get_total_revenue_2024 function"""
    # Insert test providers
    provider1_id = db.insert_provider("Dr. Alpha")
    provider2_id = db.insert_provider("Dr. Beta")
    
    # Insert test transactions for 2024
    db.conn.executemany(
        "INSERT INTO payment_transactions (provider_id, transaction_date, cash_applied) VALUES (?, ?, ?)",
        [
            (provider1_id, "2024-01-15", 500.0),
            (provider1_id, "2024-02-20", 600.0),
            (provider2_id, "2024-01-10", 400.0),
            (provider2_id, "2024-02-15", 700.0),
            # Add a transaction for another year to ensure it's filtered out
            (provider1_id, "2023-12-10", 1000.0),
        ]
    )
    
    # Update monthly summaries
    db.update_monthly_summaries()
    
    # Test the function
    revenue_df = db.get_total_revenue_2024()
    
    # Filter to only include our test providers
    test_providers = ['Dr. Alpha', 'Dr. Beta']
    filtered_df = revenue_df[revenue_df['provider_name'].isin(test_providers)]
    assert len(filtered_df) == 2, "Should have rows for both test providers"
    
    # Check Dr. Alpha's revenue
    alpha_row = filtered_df[filtered_df['provider_name'] == 'Dr. Alpha']
    assert not alpha_row.empty, "Dr. Alpha should be in results"
    assert alpha_row.iloc[0]['total_2024_revenue'] == 1100.0, "Dr. Alpha's revenue should be 1100.0"
    
    # Check Dr. Beta's revenue
    beta_row = filtered_df[filtered_df['provider_name'] == 'Dr. Beta']
    assert not beta_row.empty, "Dr. Beta should be in results"
    assert beta_row.iloc[0]['total_2024_revenue'] == 1100.0, "Dr. Beta's revenue should be 1100.0"
    
    # Verify both providers are returned (order may vary by DB implementation)
    providers = set(filtered_df['provider_name'].tolist())
    assert providers == set(["Dr. Alpha", "Dr. Beta"]), "Results should include both providers"

def test_get_transactions_by_provider(db):
    results = db.get_transactions_by_provider("Dr. Smith")
    assert len(results) == 1
    assert results[0].cash_applied == 100.0

def test_get_provider_by_name(db):
    # Add a provider for testing
    session = db.get_session()
    provider = Provider(provider_name="Dr. Test", specialty="Cardiology", npi_number="1234567890", active=1)
    session.add(provider)
    session.commit()
    session.close()

    # Test the ORM method
    result = db.get_provider_by_name("Dr. Test")
    assert result is not None
    assert result.provider_name == "Dr. Test"
    assert result.specialty == "Cardiology"

def test_get_transactions_by_patient(db):
    """
    Test fetching all transactions for a given patient ID using the ORM method.
    This test:
    1. Adds a provider to the test database.
    2. Adds a transaction for a specific patient (patient_id="PAT123").
    3. Calls get_transactions_by_patient to fetch transactions for that patient.
    4. Asserts that the returned transaction matches the inserted data.
    """
    # Step 1: Add a provider for the transaction
    session = db.get_session()
    provider = Provider(provider_name="Dr. Patient", specialty="General", npi_number="9876543210", active=1)
    session.add(provider)
    session.commit()
    provider_id = provider.provider_id

    # Step 2: Add a transaction for patient_id="PAT123"
    transaction = Transaction(
        provider_id=provider_id,
        patient_id="PAT123",
        cash_applied=200.0,
        transaction_date=date(2024, 2, 1)
    )
    session.add(transaction)
    session.commit()
    session.close()

    # Step 3: Use the ORM method to fetch transactions for patient_id="PAT123"
    results = db.get_transactions_by_patient("PAT123")

    # Step 4: Assert that the returned transaction matches what we inserted
    assert len(results) == 1
    assert results[0].cash_applied == 200.0
    assert results[0].patient_id == "PAT123"