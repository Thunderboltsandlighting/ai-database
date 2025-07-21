"""
SQLAlchemy ORM models for HVLC_DB.

This module defines the database models using SQLAlchemy's ORM system,
which enables database-agnostic operations across SQLite and PostgreSQL.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Text, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

Base = declarative_base()


class Provider(Base):
    """Provider model"""
    __tablename__ = 'providers'
    
    provider_id = Column(Integer, primary_key=True)
    provider_name = Column(String(100), nullable=False, unique=True)
    specialty = Column(String(100))
    npi_number = Column(String(10))
    active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.now)
    
    # Relationships
    transactions = relationship("PaymentTransaction", back_populates="provider")
    monthly_summaries = relationship("MonthlyProviderSummary", back_populates="provider")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "specialty": self.specialty,
            "npi_number": self.npi_number,
            "active": self.active,
            "created_date": self.created_date.isoformat() if self.created_date else None
        }


class PaymentTransaction(Base):
    """Payment transaction model"""
    __tablename__ = 'payment_transactions'
    
    transaction_id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey('providers.provider_id'))
    transaction_date = Column(Date)
    patient_id = Column(String(50))
    service_date = Column(Date)
    cash_applied = Column(Float)
    insurance_payment = Column(Float)
    patient_payment = Column(Float)
    adjustment_amount = Column(Float)
    cpt_code = Column(String(5))
    diagnosis_code = Column(String(10))
    payer_name = Column(String(100))
    claim_number = Column(String(50))
    upload_batch = Column(String(50))
    notes = Column(Text)
    created_date = Column(DateTime, default=datetime.now)
    
    # Relationships
    provider = relationship("Provider", back_populates="transactions")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "transaction_id": self.transaction_id,
            "provider_id": self.provider_id,
            "provider_name": self.provider.provider_name if self.provider else None,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "patient_id": self.patient_id,
            "service_date": self.service_date.isoformat() if self.service_date else None,
            "cash_applied": self.cash_applied,
            "insurance_payment": self.insurance_payment,
            "patient_payment": self.patient_payment,
            "adjustment_amount": self.adjustment_amount,
            "cpt_code": self.cpt_code,
            "diagnosis_code": self.diagnosis_code,
            "payer_name": self.payer_name,
            "claim_number": self.claim_number,
            "upload_batch": self.upload_batch,
            "notes": self.notes,
            "created_date": self.created_date.isoformat() if self.created_date else None
        }


class MonthlyProviderSummary(Base):
    """Monthly provider summary model"""
    __tablename__ = 'monthly_provider_summary'
    
    summary_id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey('providers.provider_id'))
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    total_cash_applied = Column(Float)
    total_transactions = Column(Integer)
    total_patients = Column(Integer)
    avg_payment_per_transaction = Column(Float)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    provider = relationship("Provider", back_populates="monthly_summaries")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "summary_id": self.summary_id,
            "provider_id": self.provider_id,
            "provider_name": self.provider.provider_name if self.provider else None,
            "year": self.year,
            "month": self.month,
            "total_cash_applied": self.total_cash_applied,
            "total_transactions": self.total_transactions,
            "total_patients": self.total_patients,
            "avg_payment_per_transaction": self.avg_payment_per_transaction,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


class BillingTerminology(Base):
    """Billing terminology model"""
    __tablename__ = 'billing_terminology'
    
    term_id = Column(Integer, primary_key=True)
    term = Column(String(100), nullable=False, unique=True)
    definition = Column(Text, nullable=False)
    category = Column(String(50))
    synonyms = Column(Text)  # JSON array of alternative terms
    examples = Column(Text)
    created_date = Column(DateTime, default=datetime.now)
    
    def get_synonyms(self) -> List[str]:
        """Get synonyms as list
        
        Returns:
            List of synonyms
        """
        if not self.synonyms:
            return []
        
        try:
            return json.loads(self.synonyms)
        except json.JSONDecodeError:
            return []
    
    def set_synonyms(self, synonyms: List[str]) -> None:
        """Set synonyms from list
        
        Args:
            synonyms: List of synonyms
        """
        self.synonyms = json.dumps(synonyms)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "term_id": self.term_id,
            "term": self.term,
            "definition": self.definition,
            "category": self.category,
            "synonyms": self.get_synonyms(),
            "examples": self.examples,
            "created_date": self.created_date.isoformat() if self.created_date else None
        }


class DenialCode(Base):
    """Denial code model"""
    __tablename__ = 'denial_codes'
    
    denial_code = Column(String(10), primary_key=True)
    description = Column(Text, nullable=False)
    category = Column(String(50))
    resolution_steps = Column(Text)
    common_causes = Column(Text)
    prevention_tips = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "denial_code": self.denial_code,
            "description": self.description,
            "category": self.category,
            "resolution_steps": self.resolution_steps,
            "common_causes": self.common_causes,
            "prevention_tips": self.prevention_tips
        }


class PayerRule(Base):
    """Payer rule model"""
    __tablename__ = 'payer_rules'
    
    rule_id = Column(Integer, primary_key=True)
    payer_name = Column(String(100), nullable=False)
    rule_type = Column(String(50))
    rule_description = Column(Text)
    effective_date = Column(Date)
    end_date = Column(Date)
    compliance_notes = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "rule_id": self.rule_id,
            "payer_name": self.payer_name,
            "rule_type": self.rule_type,
            "rule_description": self.rule_description,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "compliance_notes": self.compliance_notes
        }


class DataUpload(Base):
    """Data upload model"""
    __tablename__ = 'data_uploads'
    
    upload_id = Column(Integer, primary_key=True)
    filename = Column(String(200))
    upload_date = Column(DateTime, default=datetime.now)
    records_processed = Column(Integer)
    records_successful = Column(Integer)
    records_failed = Column(Integer)
    file_hash = Column(String(64))
    status = Column(String(20), default='processing')
    
    # Relationships
    quality_issues = relationship("DataQualityIssue", back_populates="upload")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "upload_id": self.upload_id,
            "filename": self.filename,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "records_processed": self.records_processed,
            "records_successful": self.records_successful,
            "records_failed": self.records_failed,
            "file_hash": self.file_hash,
            "status": self.status
        }


class DataQualityIssue(Base):
    """Data quality issue model"""
    __tablename__ = 'data_quality_issues'
    
    issue_id = Column(Integer, primary_key=True)
    upload_id = Column(Integer, ForeignKey('data_uploads.upload_id'))
    table_name = Column(String(50))
    record_id = Column(Integer)
    issue_type = Column(String(50))
    issue_description = Column(Text)
    severity = Column(String(10))
    resolved = Column(Boolean, default=False)
    detected_date = Column(DateTime, default=datetime.now)
    resolution_date = Column(DateTime)
    resolution_notes = Column(Text)
    
    # Relationships
    upload = relationship("DataUpload", back_populates="quality_issues")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "issue_id": self.issue_id,
            "upload_id": self.upload_id,
            "table_name": self.table_name,
            "record_id": self.record_id,
            "issue_type": self.issue_type,
            "issue_description": self.issue_description,
            "severity": self.severity,
            "resolved": self.resolved,
            "detected_date": self.detected_date.isoformat() if self.detected_date else None,
            "resolution_date": self.resolution_date.isoformat() if self.resolution_date else None,
            "resolution_notes": self.resolution_notes
        }


class Document(Base):
    """Document model for storing document metadata"""
    __tablename__ = 'documents'
    
    document_id = Column(Integer, primary_key=True)
    title = Column(String(200))
    filename = Column(String(200))
    document_type = Column(String(50))  # PDF, TXT, MD, etc.
    content_hash = Column(String(64))
    upload_date = Column(DateTime, default=datetime.now)
    processed = Column(Boolean, default=False)
    processing_error = Column(Text)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "document_id": self.document_id,
            "title": self.title,
            "filename": self.filename,
            "document_type": self.document_type,
            "content_hash": self.content_hash,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "processed": self.processed,
            "processing_error": self.processing_error,
            "chunks_count": len(self.chunks) if self.chunks else 0
        }


class DocumentChunk(Base):
    """Document chunk model for storing document chunks for vector search"""
    __tablename__ = 'document_chunks'
    
    chunk_id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.document_id'))
    chunk_index = Column(Integer)
    content = Column(Text)
    embedding = Column(Text)  # JSON array of embedding values
    chunk_metadata = Column(Text)  # JSON object with additional metadata
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    def get_embedding(self) -> List[float]:
        """Get embedding as list
        
        Returns:
            List of embedding values
        """
        if not self.embedding:
            return []
        
        try:
            return json.loads(self.embedding)
        except json.JSONDecodeError:
            return []
    
    def set_embedding(self, embedding: List[float]) -> None:
        """Set embedding from list
        
        Args:
            embedding: List of embedding values
        """
        self.embedding = json.dumps(embedding)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary
        
        Returns:
            Dictionary of metadata
        """
        if not self.chunk_metadata:
            return {}
        
        try:
            return json.loads(self.chunk_metadata)
        except json.JSONDecodeError:
            return {}
    
    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set metadata from dictionary
        
        Args:
            metadata: Dictionary of metadata
        """
        self.chunk_metadata = json.dumps(metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_title": self.document.title if self.document else None,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "metadata": self.get_metadata()
        }


class DataQualityCheck(Base):
    """Data quality check model for storing check results"""
    __tablename__ = 'data_quality_checks'
    
    check_id = Column(Integer, primary_key=True)
    table_name = Column(String(50), nullable=False)
    check_date = Column(DateTime, default=datetime.now)
    total_rules = Column(Integer)
    violated_rules = Column(Integer)
    check_summary = Column(Text)  # JSON object with summary data
    
    # Relationships
    rule_results = relationship("DataQualityRuleResult", back_populates="check")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary as dictionary
        
        Returns:
            Dictionary of summary data
        """
        if not self.check_summary:
            return {}
        
        try:
            return json.loads(self.check_summary)
        except json.JSONDecodeError:
            return {}
    
    def set_summary(self, summary: Dict[str, Any]) -> None:
        """Set summary from dictionary
        
        Args:
            summary: Dictionary of summary data
        """
        self.check_summary = json.dumps(summary)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "check_id": self.check_id,
            "table_name": self.table_name,
            "check_date": self.check_date.isoformat() if self.check_date else None,
            "total_rules": self.total_rules,
            "violated_rules": self.violated_rules,
            "summary": self.get_summary(),
            "rule_results": [r.to_dict() for r in self.rule_results] if self.rule_results else []
        }


class DataQualityRuleResult(Base):
    """Data quality rule result model for storing rule check results"""
    __tablename__ = 'data_quality_rule_results'
    
    result_id = Column(Integer, primary_key=True)
    check_id = Column(Integer, ForeignKey('data_quality_checks.check_id'))
    rule_name = Column(String(100), nullable=False)
    rule_description = Column(Text)
    rule_type = Column(String(50))
    column_name = Column(String(50))
    violated = Column(Boolean, default=False)
    violation_count = Column(Integer)
    details = Column(Text)  # JSON object with violation details
    severity = Column(String(10))
    remediation = Column(Text)
    
    # Relationships
    check = relationship("DataQualityCheck", back_populates="rule_results")
    
    def get_details(self) -> Dict[str, Any]:
        """Get details as dictionary
        
        Returns:
            Dictionary of violation details
        """
        if not self.details:
            return {}
        
        try:
            return json.loads(self.details)
        except json.JSONDecodeError:
            return {}
    
    def set_details(self, details: Dict[str, Any]) -> None:
        """Set details from dictionary
        
        Args:
            details: Dictionary of violation details
        """
        self.details = json.dumps(details)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "result_id": self.result_id,
            "check_id": self.check_id,
            "rule_name": self.rule_name,
            "rule_description": self.rule_description,
            "rule_type": self.rule_type,
            "column_name": self.column_name,
            "violated": self.violated,
            "violation_count": self.violation_count,
            "details": self.get_details(),
            "severity": self.severity,
            "remediation": self.remediation
        }


class FormatProfile(Base):
    """Format profile model for storing CSV format profiles"""
    __tablename__ = 'format_profiles'
    
    profile_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    header_patterns = Column(Text)  # JSON object with header patterns
    column_mappings = Column(Text)  # JSON object with column mappings
    sample_values = Column(Text)  # JSON object with sample values
    data_types = Column(Text)  # JSON object with data types
    profile_metadata = Column(Text)  # JSON object with additional metadata
    created_date = Column(DateTime, default=datetime.now)
    
    def get_header_patterns(self) -> Dict[str, List[str]]:
        """Get header patterns as dictionary
        
        Returns:
            Dictionary of header patterns
        """
        if not self.header_patterns:
            return {}
        
        try:
            return json.loads(self.header_patterns)
        except json.JSONDecodeError:
            return {}
    
    def set_header_patterns(self, patterns: Dict[str, List[str]]) -> None:
        """Set header patterns from dictionary
        
        Args:
            patterns: Dictionary of header patterns
        """
        self.header_patterns = json.dumps(patterns)
    
    def get_column_mappings(self) -> Dict[str, str]:
        """Get column mappings as dictionary
        
        Returns:
            Dictionary of column mappings
        """
        if not self.column_mappings:
            return {}
        
        try:
            return json.loads(self.column_mappings)
        except json.JSONDecodeError:
            return {}
    
    def set_column_mappings(self, mappings: Dict[str, str]) -> None:
        """Set column mappings from dictionary
        
        Args:
            mappings: Dictionary of column mappings
        """
        self.column_mappings = json.dumps(mappings)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary
        
        Returns:
            Dictionary representation of model
        """
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "header_patterns": self.get_header_patterns(),
            "column_mappings": self.get_column_mappings(),
            "created_date": self.created_date.isoformat() if self.created_date else None
        }


# Schema creation function
def create_all_tables(engine):
    """Create all tables in the database
    
    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.create_all(engine)