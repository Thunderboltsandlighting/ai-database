"""
Tests for the SQL Agent functionality.

These tests verify that the SQL agent correctly translates natural language
queries into SQL and returns appropriate results.
"""

import os
import pytest
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock
import sys
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the SQL agent
try:
    from agents.sql_agent import MedicalBillingSQLAgent
    SQL_AGENT_AVAILABLE = True
except ImportError:
    SQL_AGENT_AVAILABLE = False

# Import the database
from medical_billing_db import MedicalBillingDB, Transaction, Provider

# Skip all tests if SQL agent is not available
pytestmark = pytest.mark.skipif(not SQL_AGENT_AVAILABLE, reason="SQL Agent not available")

# Create a temporary test database
@pytest.fixture
def test_db_path():
    """Create a temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def db(test_db_path):
    """Set up a test database with sample data."""
    # Create a database with SQLAlchemy
    db = MedicalBillingDB(db_path=test_db_path, use_sqlalchemy=True)
    
    # Create tables
    Transaction.metadata.create_all(db.engine)
    Provider.metadata.create_all(db.engine)
    
    # Add test data
    session = db.get_session()
    
    # Add providers
    providers = [
        Provider(provider_name="Dr. Smith", specialty="Cardiology", npi_number="1234567890"),
        Provider(provider_name="Dr. Jones", specialty="Neurology", npi_number="0987654321"),
        Provider(provider_name="Dr. Brown", specialty="Orthopedics", npi_number="1122334455")
    ]
    session.add_all(providers)
    session.commit()
    
    # Get provider IDs
    smith_id = session.query(Provider).filter_by(provider_name="Dr. Smith").first().provider_id
    jones_id = session.query(Provider).filter_by(provider_name="Dr. Jones").first().provider_id
    brown_id = session.query(Provider).filter_by(provider_name="Dr. Brown").first().provider_id
    
    # Add transactions
    transactions = [
        # Dr. Smith transactions
        Transaction(provider_id=smith_id, transaction_date="2024-01-15", patient_id="PAT001", cash_applied=100.0),
        Transaction(provider_id=smith_id, transaction_date="2024-02-20", patient_id="PAT002", cash_applied=150.0),
        Transaction(provider_id=smith_id, transaction_date="2024-03-10", patient_id="PAT003", cash_applied=200.0),
        
        # Dr. Jones transactions
        Transaction(provider_id=jones_id, transaction_date="2024-01-05", patient_id="PAT004", cash_applied=120.0),
        Transaction(provider_id=jones_id, transaction_date="2024-02-15", patient_id="PAT005", cash_applied=180.0),
        
        # Dr. Brown transactions
        Transaction(provider_id=brown_id, transaction_date="2024-01-25", patient_id="PAT006", cash_applied=90.0),
        Transaction(provider_id=brown_id, transaction_date="2024-02-10", patient_id="PAT007", cash_applied=110.0),
        Transaction(provider_id=brown_id, transaction_date="2024-03-20", patient_id="PAT008", cash_applied=130.0)
    ]
    session.add_all(transactions)
    session.commit()
    session.close()
    
    yield db
    db.close()

@pytest.fixture
def mock_ollama():
    """Mock the Ollama LLM for testing."""
    with patch("langchain.llms.ollama.Ollama") as mock:
        # Set up the mock to return a simple SQL query
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def sql_agent(test_db_path, mock_ollama):
    """Create a SQL agent with a mocked LLM."""
    # Connect the SQL agent to the test database
    db_url = f"sqlite:///{test_db_path}"
    agent = MedicalBillingSQLAgent(db_url=db_url, ollama_url="mock://localhost:11434", model="mock-model")
    agent.llm = mock_ollama
    return agent

def test_sql_agent_initialization(sql_agent):
    """Test that the SQL agent initializes correctly."""
    assert sql_agent is not None
    assert sql_agent.db is not None
    assert sql_agent.llm is not None
    assert sql_agent.agent is not None

def test_get_schema_str(sql_agent):
    """Test that the SQL agent can retrieve the database schema."""
    schema = sql_agent.get_schema_str()
    assert "providers" in schema
    assert "payment_transactions" in schema

def test_get_tables(sql_agent):
    """Test that the SQL agent can list tables."""
    tables = sql_agent.get_tables()
    assert "providers" in tables
    assert "payment_transactions" in tables

def test_get_table_info(sql_agent):
    """Test that the SQL agent can get information about a specific table."""
    info = sql_agent.get_table_info("providers")
    assert "provider_name" in info
    assert "specialty" in info
    assert "npi_number" in info

def test_execute_direct_sql(sql_agent):
    """Test that the SQL agent can execute SQL directly."""
    result = sql_agent.execute_direct_sql("SELECT provider_name FROM providers")
    assert result["success"] is True
    assert len(result["rows"]) == 3
    assert "Dr. Smith" in [row["provider_name"] for row in result["rows"]]
    assert "Dr. Jones" in [row["provider_name"] for row in result["rows"]]
    assert "Dr. Brown" in [row["provider_name"] for row in result["rows"]]

def test_process_query_with_mock(sql_agent, mock_ollama):
    """Test that the SQL agent processes queries correctly with a mocked LLM."""
    # Set up the mock to return a response
    mock_ollama.run.return_value = "Dr. Smith has the highest revenue with $450.00."
    
    # Process a query
    result = sql_agent.process_query("Who has the highest revenue?")
    
    # Check that the mock was called
    mock_ollama.run.assert_called_once()
    
    # Check the result
    assert "Dr. Smith" in result
    assert "$450.00" in result

def test_integration_with_db(db, sql_agent, mock_ollama):
    """Test the integration between the SQL agent and the database."""
    # Set up the mock to return a specific SQL query result
    mock_ollama.run.return_value = "The total revenue is $1080.00."
    
    # Process a query
    result = sql_agent.process_query("What is the total revenue?")
    
    # Check that the mock was called with a query about the database
    mock_ollama.run.assert_called_once()
    
    # Check the result
    assert "total revenue" in result.lower()
    assert "$1080.00" in result

def test_error_handling(sql_agent, mock_ollama):
    """Test that the SQL agent handles errors gracefully."""
    # Set up the mock to raise an exception
    mock_ollama.run.side_effect = Exception("Test error")
    
    # Process a query
    result = sql_agent.process_query("What is the total revenue?")
    
    # Check that the error was handled
    assert "error" in result.lower()
    assert "Test error" in result