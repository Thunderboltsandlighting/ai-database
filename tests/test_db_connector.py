"""
Test suite for database connector module.
"""

import os
import sys
import pytest
import tempfile
import pandas as pd
import sqlite3
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_connector import DBConnector
from utils.config import Config


@pytest.fixture
def sqlite_db_path():
    """Fixture for temporary SQLite database path"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Initialize schema
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value REAL
        );
        
        INSERT INTO test_table (name, value) VALUES
            ('item1', 10.5),
            ('item2', 20.75),
            ('item3', 30.25);
    """)
    conn.commit()
    conn.close()
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def mock_config():
    """Fixture for mocked configuration"""
    with patch('utils.db_connector.get_config') as mock_get_config:
        config = Config()
        
        # Set up SQLite configuration
        config.set("database.type", "sqlite")
        config.set("database.db_path", ":memory:")
        
        mock_get_config.return_value = config
        yield config


@pytest.fixture
def db_connector(sqlite_db_path):
    """Fixture for DBConnector with SQLite database"""
    connector = DBConnector(f"sqlite:///{sqlite_db_path}")
    yield connector
    connector.close()


class TestDBConnector:
    """Tests for DBConnector class"""
    
    def test_init_with_url(self):
        """Test initialization with URL"""
        connector = DBConnector("sqlite:///:memory:")
        assert connector.db_url == "sqlite:///:memory:"
        assert connector.engine is not None
        assert connector.Session is not None
        
    def test_init_with_config(self, mock_config):
        """Test initialization with configuration"""
        connector = DBConnector()
        assert connector.db_url == "sqlite:///:memory:"
        assert connector.engine is not None
        assert connector.Session is not None
        
    def test_execute_query(self, db_connector):
        """Test executing query"""
        result = db_connector.execute_query("SELECT * FROM test_table")
        
        assert result["success"] == True
        assert result["row_count"] == 3
        assert len(result["rows"]) == 3
        assert "id" in result["columns"]
        assert "name" in result["columns"]
        assert "value" in result["columns"]
        
    def test_execute_query_with_params(self, db_connector):
        """Test executing query with parameters"""
        result = db_connector.execute_query(
            "SELECT * FROM test_table WHERE value > :min_value",
            {"min_value": 15.0}
        )
        
        assert result["success"] == True
        assert result["row_count"] == 2
        assert len(result["rows"]) == 2
        assert result["rows"][0]["name"] == "item2"
        assert result["rows"][1]["name"] == "item3"
        
    def test_execute_query_error(self, db_connector):
        """Test executing query with error"""
        result = db_connector.execute_query("SELECT * FROM nonexistent_table")
        
        assert result["success"] == False
        assert "error" in result
        
    def test_execute_query_df(self, db_connector):
        """Test executing query to DataFrame"""
        df = db_connector.execute_query_df("SELECT * FROM test_table")
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "id" in df.columns
        assert "name" in df.columns
        assert "value" in df.columns
        
    def test_execute_query_df_with_params(self, db_connector):
        """Test executing query to DataFrame with parameters"""
        df = db_connector.execute_query_df(
            "SELECT * FROM test_table WHERE value > :min_value",
            {"min_value": 15.0}
        )
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert df.iloc[0]["name"] == "item2"
        assert df.iloc[1]["name"] == "item3"
        
    def test_execute_query_df_error(self, db_connector):
        """Test executing query to DataFrame with error"""
        df = db_connector.execute_query_df("SELECT * FROM nonexistent_table")
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        
    def test_get_session(self, db_connector):
        """Test getting session"""
        session = db_connector.get_session()
        
        assert session is not None
        
        # Clean up
        session.close()
        
    def test_get_table_schema_sqlite(self, db_connector):
        """Test getting table schema for SQLite"""
        schema = db_connector.get_table_schema("test_table")
        
        assert len(schema) == 3
        assert schema[0][0] == "id"
        assert schema[1][0] == "name"
        assert schema[2][0] == "value"
        
    def test_list_tables_sqlite(self, db_connector):
        """Test listing tables for SQLite"""
        tables = db_connector.list_tables()
        
        assert "test_table" in tables


@pytest.mark.parametrize("db_type,expected_url", [
    ("sqlite", "sqlite:///medical_billing.db"),
    ("postgresql", "postgresql://postgres:@localhost:5432/medical_billing?sslmode=prefer")
])
def test_config_get_db_url(db_type, expected_url):
    """Test getting database URL from configuration"""
    config = Config()
    config.set("database.type", db_type)
    
    if db_type == "sqlite":
        config.set("database.db_path", "medical_billing.db")
    else:
        config.set("database.postgresql.host", "localhost")
        config.set("database.postgresql.port", 5432)
        config.set("database.postgresql.database", "medical_billing")
        config.set("database.postgresql.user", "postgres")
        config.set("database.postgresql.password", "")
    
    url = config.get_db_url()
    assert url == expected_url


def test_config_get_db_url_unsupported():
    """Test getting database URL for unsupported type"""
    config = Config()
    config.set("database.type", "unsupported")
    
    with pytest.raises(ValueError):
        config.get_db_url()