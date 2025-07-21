"""
Test suite for database migration utilities.
"""

import os
import sys
import pytest
import tempfile
import sqlite3
import pandas as pd
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_migration import DatabaseMigrator, get_migrator_from_config
from utils.db_models import Base, Provider, PaymentTransaction, create_all_tables


@pytest.fixture
def source_db_path():
    """Fixture for source SQLite database path"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Initialize engine and create tables
    engine = create_engine(f"sqlite:///{path}")
    create_all_tables(engine)
    
    # Add some test data
    with engine.connect() as conn:
        # Add providers
        conn.execute(text("""
            INSERT INTO providers (provider_name, specialty, npi_number, active)
            VALUES 
                ('Provider 1', 'Specialty 1', '1234567890', 1),
                ('Provider 2', 'Specialty 2', '0987654321', 1)
        """))
        
        # Add transactions
        conn.execute(text("""
            INSERT INTO payment_transactions 
                (provider_id, transaction_date, patient_id, cash_applied)
            VALUES 
                (1, '2025-07-15', 'P12345', 100.50),
                (1, '2025-07-16', 'P12346', 200.75),
                (2, '2025-07-15', 'P12347', 150.25)
        """))
        
        conn.commit()
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def target_db_path():
    """Fixture for target SQLite database path"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def migrator(source_db_path, target_db_path):
    """Fixture for DatabaseMigrator"""
    migrator = DatabaseMigrator(
        f"sqlite:///{source_db_path}",
        f"sqlite:///{target_db_path}"
    )
    
    yield migrator


class TestDatabaseMigrator:
    """Tests for DatabaseMigrator"""
    
    def test_init(self, source_db_path, target_db_path):
        """Test initialization"""
        migrator = DatabaseMigrator(
            f"sqlite:///{source_db_path}",
            f"sqlite:///{target_db_path}"
        )
        
        assert migrator.source_url == f"sqlite:///{source_db_path}"
        assert migrator.target_url == f"sqlite:///{target_db_path}"
        assert migrator.source_engine is not None
        assert migrator.target_engine is not None
        
    def test_check_compatibility(self, migrator):
        """Test compatibility check"""
        compatible, issues = migrator.check_compatibility()
        
        assert compatible == True
        assert len(issues) == 0
        
    def test_create_target_schema(self, migrator):
        """Test creating target schema"""
        success = migrator.create_target_schema()
        
        assert success == True
        
        # Check that tables were created
        inspector = migrator.target_engine.dialect.inspector.from_engine(migrator.target_engine)
        tables = inspector.get_table_names()
        
        assert "providers" in tables
        assert "payment_transactions" in tables
        
    def test_get_table_rowcount(self, migrator):
        """Test getting row count"""
        count = migrator.get_table_rowcount(migrator.source_engine, "providers")
        
        assert count == 2
        
        count = migrator.get_table_rowcount(migrator.source_engine, "payment_transactions")
        
        assert count == 3
        
    def test_migrate_table(self, migrator):
        """Test migrating a table"""
        # Create schema first
        migrator.create_target_schema()
        
        # Migrate providers table
        result = migrator.migrate_table("providers")
        
        assert result["success"] == True
        assert result["rows_migrated"] == 2
        assert result["rows_in_target"] == 2
        
        # Check target database
        with migrator.target_engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM providers"))
            rows = result.fetchall()
            
            assert len(rows) == 2
            assert rows[0][1] == "Provider 1"  # provider_name
            assert rows[1][1] == "Provider 2"  # provider_name
        
    def test_migrate_all(self, migrator):
        """Test migrating all tables"""
        result = migrator.migrate_all(["providers", "payment_transactions"])
        
        assert result["success"] == True
        assert result["tables_total"] == 2
        assert result["tables_migrated"] == 2
        
        # Check target database for providers
        with migrator.target_engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM providers"))
            rows = result.fetchall()
            
            assert len(rows) == 2
            
            # Check payment_transactions
            result = conn.execute(text("SELECT * FROM payment_transactions"))
            rows = result.fetchall()
            
            assert len(rows) == 3
            
    def test_migrate_nonexistent_table(self, migrator):
        """Test migrating a nonexistent table"""
        # Create schema first
        migrator.create_target_schema()
        
        # Try to migrate nonexistent table
        result = migrator.migrate_table("nonexistent_table")
        
        assert result["success"] == False
        assert "error" in result
        assert result["rows_migrated"] == 0


def test_get_migrator_from_config():
    """Test creating migrator from configuration"""
    with patch('utils.db_migration.get_config') as mock_get_config:
        # Mock configuration
        mock_config = MagicMock()
        mock_config.get_db_url.return_value = "sqlite:///:memory:"
        mock_get_config.return_value = mock_config
        
        # Get migrator
        migrator = get_migrator_from_config()
        
        assert migrator.source_url == "sqlite:///:memory:"
        assert migrator.target_url == "sqlite:///:memory:"