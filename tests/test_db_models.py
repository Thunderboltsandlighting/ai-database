"""
Test suite for SQLAlchemy ORM models.
"""

import os
import sys
import pytest
import tempfile
from datetime import datetime, date
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_models import (
    Base, Provider, PaymentTransaction, MonthlyProviderSummary,
    BillingTerminology, DenialCode, PayerRule, DataUpload,
    DataQualityIssue, Document, DocumentChunk, DataQualityCheck,
    DataQualityRuleResult, FormatProfile, create_all_tables
)


@pytest.fixture
def db_engine():
    """Fixture for SQLAlchemy engine with in-memory SQLite database"""
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables
    create_all_tables(engine)
    
    yield engine
    
    # Dispose of engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Fixture for SQLAlchemy session"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    
    yield session
    
    # Close session
    session.close()


class TestProvider:
    """Tests for Provider model"""
    
    def test_create_provider(self, db_session):
        """Test creating provider"""
        provider = Provider(
            provider_name="Test Provider",
            specialty="Test Specialty",
            npi_number="1234567890",
            active=True
        )
        
        db_session.add(provider)
        db_session.commit()
        
        # Query back
        provider = db_session.query(Provider).first()
        
        assert provider.provider_name == "Test Provider"
        assert provider.specialty == "Test Specialty"
        assert provider.npi_number == "1234567890"
        assert provider.active == True
        assert provider.created_date is not None
        
    def test_to_dict(self, db_session):
        """Test conversion to dictionary"""
        provider = Provider(
            provider_name="Test Provider",
            specialty="Test Specialty",
            npi_number="1234567890",
            active=True
        )
        
        db_session.add(provider)
        db_session.commit()
        
        data = provider.to_dict()
        
        assert data["provider_name"] == "Test Provider"
        assert data["specialty"] == "Test Specialty"
        assert data["npi_number"] == "1234567890"
        assert data["active"] == True
        assert data["created_date"] is not None


class TestPaymentTransaction:
    """Tests for PaymentTransaction model"""
    
    def test_create_transaction(self, db_session):
        """Test creating transaction"""
        # Create provider first
        provider = Provider(provider_name="Test Provider")
        db_session.add(provider)
        db_session.flush()
        
        # Create transaction
        transaction = PaymentTransaction(
            provider_id=provider.provider_id,
            transaction_date=date(2025, 7, 15),
            patient_id="P12345",
            cash_applied=100.50,
            insurance_payment=75.25,
            patient_payment=25.25,
            payer_name="Test Insurance"
        )
        
        db_session.add(transaction)
        db_session.commit()
        
        # Query back
        transaction = db_session.query(PaymentTransaction).first()
        
        assert transaction.provider_id == provider.provider_id
        assert transaction.transaction_date == date(2025, 7, 15)
        assert transaction.patient_id == "P12345"
        assert transaction.cash_applied == 100.50
        assert transaction.insurance_payment == 75.25
        assert transaction.patient_payment == 25.25
        assert transaction.payer_name == "Test Insurance"
        assert transaction.created_date is not None
        
    def test_to_dict(self, db_session):
        """Test conversion to dictionary"""
        # Create provider first
        provider = Provider(provider_name="Test Provider")
        db_session.add(provider)
        db_session.flush()
        
        # Create transaction
        transaction = PaymentTransaction(
            provider_id=provider.provider_id,
            transaction_date=date(2025, 7, 15),
            patient_id="P12345",
            cash_applied=100.50
        )
        
        db_session.add(transaction)
        db_session.commit()
        
        data = transaction.to_dict()
        
        assert data["provider_id"] == provider.provider_id
        assert data["provider_name"] == "Test Provider"
        assert data["transaction_date"] == "2025-07-15"
        assert data["patient_id"] == "P12345"
        assert data["cash_applied"] == 100.50


class TestBillingTerminology:
    """Tests for BillingTerminology model"""
    
    def test_create_term(self, db_session):
        """Test creating terminology entry"""
        term = BillingTerminology(
            term="CPT",
            definition="Current Procedural Terminology",
            category="Coding",
            synonyms=json.dumps(["Procedure Code", "Service Code"]),
            examples="99213, 90791"
        )
        
        db_session.add(term)
        db_session.commit()
        
        # Query back
        term = db_session.query(BillingTerminology).first()
        
        assert term.term == "CPT"
        assert term.definition == "Current Procedural Terminology"
        assert term.category == "Coding"
        assert term.get_synonyms() == ["Procedure Code", "Service Code"]
        assert term.examples == "99213, 90791"
        
    def test_get_set_synonyms(self, db_session):
        """Test getting and setting synonyms"""
        term = BillingTerminology(
            term="CPT",
            definition="Current Procedural Terminology"
        )
        
        # Set synonyms
        term.set_synonyms(["Procedure Code", "Service Code"])
        
        db_session.add(term)
        db_session.commit()
        
        # Query back and get synonyms
        term = db_session.query(BillingTerminology).first()
        synonyms = term.get_synonyms()
        
        assert synonyms == ["Procedure Code", "Service Code"]


class TestDocument:
    """Tests for Document model"""
    
    def test_create_document(self, db_session):
        """Test creating document"""
        document = Document(
            title="Test Document",
            filename="test.pdf",
            document_type="PDF",
            content_hash="abc123",
            processed=True
        )
        
        db_session.add(document)
        db_session.commit()
        
        # Query back
        document = db_session.query(Document).first()
        
        assert document.title == "Test Document"
        assert document.filename == "test.pdf"
        assert document.document_type == "PDF"
        assert document.content_hash == "abc123"
        assert document.processed == True
        
    def test_create_document_with_chunks(self, db_session):
        """Test creating document with chunks"""
        document = Document(
            title="Test Document",
            filename="test.pdf",
            document_type="PDF"
        )
        
        # Add chunks
        chunk1 = DocumentChunk(
            chunk_index=0,
            content="This is chunk 1",
            metadata=json.dumps({"page": 1})
        )
        
        chunk2 = DocumentChunk(
            chunk_index=1,
            content="This is chunk 2",
            metadata=json.dumps({"page": 1})
        )
        
        document.chunks = [chunk1, chunk2]
        
        db_session.add(document)
        db_session.commit()
        
        # Query back
        document = db_session.query(Document).first()
        
        assert document.title == "Test Document"
        assert len(document.chunks) == 2
        assert document.chunks[0].content == "This is chunk 1"
        assert document.chunks[1].content == "This is chunk 2"
        
    def test_document_to_dict(self, db_session):
        """Test document to_dict method"""
        document = Document(
            title="Test Document",
            filename="test.pdf",
            document_type="PDF"
        )
        
        # Add chunks
        chunk1 = DocumentChunk(
            chunk_index=0,
            content="This is chunk 1"
        )
        
        chunk2 = DocumentChunk(
            chunk_index=1,
            content="This is chunk 2"
        )
        
        document.chunks = [chunk1, chunk2]
        
        db_session.add(document)
        db_session.commit()
        
        data = document.to_dict()
        
        assert data["title"] == "Test Document"
        assert data["filename"] == "test.pdf"
        assert data["document_type"] == "PDF"
        assert data["chunks_count"] == 2


class TestDataQualityCheck:
    """Tests for DataQualityCheck model"""
    
    def test_create_check(self, db_session):
        """Test creating data quality check"""
        check = DataQualityCheck(
            table_name="test_table",
            total_rules=5,
            violated_rules=2,
            check_summary=json.dumps({
                "quality_score": 0.6,
                "severity_counts": {"high": 1, "medium": 1, "low": 0}
            })
        )
        
        # Add rule results
        rule1 = DataQualityRuleResult(
            rule_name="Missing Values",
            rule_description="Check for missing values",
            rule_type="completeness",
            column_name="test_column",
            violated=True,
            violation_count=10,
            details=json.dumps({"rows": [1, 2, 3]}),
            severity="high",
            remediation="Fix missing values"
        )
        
        rule2 = DataQualityRuleResult(
            rule_name="Negative Values",
            rule_description="Check for negative values",
            rule_type="range",
            column_name="test_column",
            violated=True,
            violation_count=5,
            details=json.dumps({"rows": [4, 5]}),
            severity="medium",
            remediation="Fix negative values"
        )
        
        check.rule_results = [rule1, rule2]
        
        db_session.add(check)
        db_session.commit()
        
        # Query back
        check = db_session.query(DataQualityCheck).first()
        
        assert check.table_name == "test_table"
        assert check.total_rules == 5
        assert check.violated_rules == 2
        assert check.get_summary()["quality_score"] == 0.6
        assert len(check.rule_results) == 2
        assert check.rule_results[0].rule_name == "Missing Values"
        assert check.rule_results[1].rule_name == "Negative Values"
        
    def test_get_set_summary(self, db_session):
        """Test getting and setting summary"""
        check = DataQualityCheck(
            table_name="test_table",
            total_rules=5,
            violated_rules=2
        )
        
        # Set summary
        check.set_summary({
            "quality_score": 0.6,
            "severity_counts": {"high": 1, "medium": 1, "low": 0}
        })
        
        db_session.add(check)
        db_session.commit()
        
        # Query back and get summary
        check = db_session.query(DataQualityCheck).first()
        summary = check.get_summary()
        
        assert summary["quality_score"] == 0.6
        assert summary["severity_counts"]["high"] == 1


def test_create_all_tables(db_engine):
    """Test creating all tables"""
    # Check that tables were created
    inspector = db_engine.dialect.inspector.from_engine(db_engine)
    tables = inspector.get_table_names()
    
    expected_tables = [
        "providers",
        "payment_transactions",
        "monthly_provider_summary",
        "billing_terminology",
        "denial_codes",
        "payer_rules",
        "data_uploads",
        "data_quality_issues",
        "documents",
        "document_chunks",
        "data_quality_checks",
        "data_quality_rule_results",
        "format_profiles"
    ]
    
    for table in expected_tables:
        assert table in tables