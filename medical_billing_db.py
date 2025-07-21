import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
import json
import os
import traceback
from typing import Optional
from utils.logger import get_logger, get_quality_logger
from utils.config import get_config
from utils.privacy import anonymize_dataframe, mask_patient_id, generate_privacy_report
from utils.csv_processor import process_csv_in_chunks, count_csv_rows, get_optimal_chunksize
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, Date

# Get the loggers and configuration
logger = get_logger()
quality_logger = get_quality_logger()
config = get_config()

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "payment_transactions"
    transaction_id = Column(Integer, primary_key=True)
    provider_id = Column(Integer)
    transaction_date = Column(Date)
    patient_id = Column(String)
    cash_applied = Column(Float)
    insurance_payment = Column(Float)
    patient_payment = Column(Float)
    adjustment_amount = Column(Float)
    cpt_code = Column(String)
    diagnosis_code = Column(String)
    payer_name = Column(String)
    claim_number = Column(String)
    upload_batch = Column(String)
    notes = Column(String)
    created_date = Column(Date)

class Provider(Base):
    __tablename__ = "providers"
    provider_id = Column(Integer, primary_key=True)
    provider_name = Column(String)
    specialty = Column(String)
    npi_number = Column(String)
    active = Column(Integer)
    created_date = Column(Date)

class MedicalBillingDB:
    def __init__(self, db_path: str = None, use_sqlalchemy: bool = False, db_url: str = None):
        # Use configured database path if not provided
        if db_path is None:
            db_path = config.get_db_path()
            
        self.db_path = db_path
        self.use_sqlalchemy = use_sqlalchemy
        self.engine = None
        if self.use_sqlalchemy:
            if db_url is None:
                db_url = f"sqlite:///{db_path or config.get_db_path()}"
            self.engine = create_engine(db_url)
            logger.info(f"SQLAlchemy engine created for {db_url}")
        else:
            try:
                logger.info(f"Connecting to database at {db_path}")
                self.conn = sqlite3.connect(db_path)
                
                # Enable foreign keys if configured
                if config.get("database.enable_foreign_keys", True):
                    self.conn.execute("PRAGMA foreign_keys = ON")
                    
                self.create_tables()
                logger.info("Database connection established and tables verified")
            except sqlite3.Error as e:
                logger.error(f"Database connection error: {e}")
                raise
    
    def create_tables(self):
        """Create all necessary tables for medical billing data"""
        try:
            logger.debug("Creating/verifying database tables")
            # Core operational tables
            self.conn.executescript("""
        -- Providers table
        CREATE TABLE IF NOT EXISTS providers (
            provider_id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_name VARCHAR(100) NOT NULL UNIQUE,
            specialty VARCHAR(100),
            npi_number VARCHAR(10),
            active BOOLEAN DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        -- Payment transactions (main CSV data)
        CREATE TABLE IF NOT EXISTS payment_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER,
            transaction_date DATE,
            patient_id VARCHAR(50),
            service_date DATE,
            cash_applied DECIMAL(10,2),  -- allow NULL
            insurance_payment DECIMAL(10,2),
            patient_payment DECIMAL(10,2),
            adjustment_amount DECIMAL(10,2),
            cpt_code VARCHAR(5),
            diagnosis_code VARCHAR(10),
            payer_name VARCHAR(100),
            claim_number VARCHAR(50),
            upload_batch VARCHAR(50),
            notes TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (provider_id) REFERENCES providers(provider_id)
        );
        -- Monthly aggregated data for faster reporting
        CREATE TABLE IF NOT EXISTS monthly_provider_summary (
            summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            total_cash_applied DECIMAL(12,2),
            total_transactions INTEGER,
            total_patients INTEGER,
            avg_payment_per_transaction DECIMAL(10,2),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (provider_id) REFERENCES providers(provider_id),
            UNIQUE(provider_id, year, month)
        );
        -- Knowledge base tables
        CREATE TABLE IF NOT EXISTS billing_terminology (
            term_id INTEGER PRIMARY KEY AUTOINCREMENT,
            term VARCHAR(100) NOT NULL UNIQUE,
            definition TEXT NOT NULL,
            category VARCHAR(50),
            synonyms TEXT, -- JSON array of alternative terms
            examples TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS denial_codes (
            denial_code VARCHAR(10) PRIMARY KEY,
            description TEXT NOT NULL,
            category VARCHAR(50),
            resolution_steps TEXT,
            common_causes TEXT,
            prevention_tips TEXT
        );
        CREATE TABLE IF NOT EXISTS payer_rules (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            payer_name VARCHAR(100) NOT NULL,
            rule_type VARCHAR(50),
            rule_description TEXT,
            effective_date DATE,
            end_date DATE,
            compliance_notes TEXT
        );
        -- Data quality and audit tables
        CREATE TABLE IF NOT EXISTS data_uploads (
            upload_id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename VARCHAR(200),
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            records_processed INTEGER,
            records_successful INTEGER,
            records_failed INTEGER,
            file_hash VARCHAR(64),
            status VARCHAR(20) DEFAULT 'processing'
        );
        CREATE TABLE IF NOT EXISTS data_quality_issues (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name VARCHAR(50),
            record_id INTEGER,
            issue_type VARCHAR(50),
            issue_description TEXT,
            severity VARCHAR(10),
            resolved BOOLEAN DEFAULT 0,
            detected_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
            # Create indexes for better performance
            self.conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_payment_provider_date ON payment_transactions(provider_id, transaction_date);
            CREATE INDEX IF NOT EXISTS idx_payment_date ON payment_transactions(transaction_date);
            CREATE INDEX IF NOT EXISTS idx_monthly_summary ON monthly_provider_summary(provider_id, year, month);
            CREATE INDEX IF NOT EXISTS idx_terminology_term ON billing_terminology(term);
            """)
            self.conn.commit()
            logger.debug("Database schema creation/verification completed successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def insert_provider(self, name: str, specialty: str = None, npi: str = None) -> int:
        """Insert a provider or return existing provider ID if already exists"""
        try:
            logger.debug(f"Inserting or retrieving provider: {name}")
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO providers (provider_name, specialty, npi_number) VALUES (?, ?, ?)",
                (name, specialty, npi)
            )
            self.conn.commit()
            cursor = self.conn.execute("SELECT provider_id FROM providers WHERE provider_name = ?", (name,))
            provider_id = cursor.fetchone()[0]
            logger.debug(f"Provider {name} has ID {provider_id}")
            return provider_id
        except sqlite3.Error as e:
            logger.error(f"Error inserting provider {name}: {e}")
            raise
    
    def upload_csv_file(self, file_path: str, chunk_size: Optional[int] = None) -> Dict:
        """Upload a CSV file using chunked processing for memory efficiency
        
        Args:
            file_path: Path to the CSV file
            chunk_size: Number of rows to process in each chunk (auto-calculated if None)
            
        Returns:
            Dictionary with upload results
        """
        logger.info(f"Starting chunked upload of CSV file: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # Count rows for progress tracking
        total_rows = count_csv_rows(file_path) - 1  # Subtract header
        
        # Create upload record
        try:
            upload_cursor = self.conn.execute(
                "INSERT INTO data_uploads (filename, records_processed) VALUES (?, ?)",
                (os.path.basename(file_path), total_rows)
            )
            upload_id = upload_cursor.lastrowid
            self.conn.commit()
            logger.debug(f"Created upload record with ID {upload_id}")
            
        except Exception as e:
            logger.error(f"Error creating upload record: {e}")
            return {'success': False, 'error': str(e)}
        
        # Calculate chunk size if not provided
        if chunk_size is None:
            chunk_size = get_optimal_chunksize(file_path)
            logger.debug(f"Using calculated chunk size: {chunk_size} rows")
        
        # Define chunk processor function
        def process_chunk(chunk_df, chunk_index):
            chunk_start = chunk_size * chunk_index
            logger.debug(f"Processing chunk {chunk_index+1} with {len(chunk_df)} rows (starting at row {chunk_start})")
            
            # Process the chunk
            try:
                # Add row offset to indices for proper error reporting
                chunk_df.index = range(chunk_start, chunk_start + len(chunk_df))
                
                # Process the dataframe chunk
                result = self._process_dataframe(chunk_df, os.path.basename(file_path), upload_id)
                
                return {
                    'successful': result['successful'],
                    'failed': result['failed'],
                    'issues': result['issues']
                }
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_index}: {e}")
                return {
                    'successful': 0,
                    'failed': len(chunk_df),
                    'issues': [{'type': 'chunk_error', 'description': str(e), 'chunk': chunk_index}]
                }
        
        # Process the CSV file in chunks
        result = process_csv_in_chunks(file_path, process_chunk, chunk_size=chunk_size)
        
        # Update upload status with final counts
        try:
            self.conn.execute(
                "UPDATE data_uploads SET records_successful = ?, records_failed = ?, status = ? WHERE upload_id = ?",
                (result['successful_rows'], result['failed_rows'], 
                 'completed' if result['success'] else 'failed', upload_id)
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating upload status: {e}")
        
        # Add upload ID to result
        result['upload_id'] = upload_id
        result['filename'] = os.path.basename(file_path)
        
        return result
        
    def upload_csv_data(self, df: pd.DataFrame, filename: str) -> Dict:
        """Upload CSV data to the database with validation and error handling"""
        logger.info(f"Starting upload of CSV data from {filename} with {len(df)} records")
        upload_cursor = None
        upload_id = None
        
        try:
            # Create upload record
            upload_cursor = self.conn.execute(
                "INSERT INTO data_uploads (filename, records_processed) VALUES (?, ?)",
                (filename, len(df))
            )
            upload_id = upload_cursor.lastrowid
            logger.debug(f"Created upload record with ID {upload_id}")
            
            # Process the dataframe
            return self._process_dataframe(df, filename, upload_id)
            
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Fatal error during CSV upload: {str(e)}\n{error_details}")
            self.conn.rollback()
            
            # Try to update upload status if we had created an upload record
            if upload_id:
                try:
                    self.conn.execute(
                        "UPDATE data_uploads SET status = 'failed', records_failed = ? WHERE upload_id = ?", 
                        (len(df), upload_id)
                    )
                    self.conn.commit()
                except Exception as update_error:
                    logger.error(f"Failed to update upload status: {update_error}")
            
            return {
                'success': False,
                'error': str(e),
                'details': error_details
            }
    
    def _process_dataframe(self, df: pd.DataFrame, filename: str, upload_id: int) -> Dict:
        """Process a dataframe and insert records into the database"""
        successful_records = 0
        failed_records = 0
        issues = []
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Smart cleaning: handle missing/blank values
                def get_val(key, default=None, numeric=False):
                    val = row.get(key, default)
                    if pd.isna(val) or val == '':
                        return None
                    if numeric:
                        try:
                            return float(val)
                        except Exception:
                            return None
                    return val
                
                # Extract and validate values - handle both original and transformed column names
                cash_applied = get_val('cash_applied', numeric=True) or get_val('Cash Applied', numeric=True)
                
                # Check for data quality issues
                if cash_applied is not None and cash_applied < 0:
                    issue = {'type': 'negative_payment', 'description': f'Negative cash applied: {cash_applied}', 'row': index}
                    issues.append(issue)
                    quality_logger.warning(f"Row {index}: Negative payment {cash_applied} in {filename}")
                
                if cash_applied is None:
                    issue = {'type': 'missing_value', 'description': 'Missing cash_applied', 'row': index}
                    issues.append(issue)
                    quality_logger.warning(f"Row {index}: Missing cash_applied value in {filename}")
                
                # Extract remaining fields - handle both original and transformed column names
                provider_name = get_val('provider_name') or get_val('Provider', default='Unknown')
                provider_id = self.insert_provider(provider_name)
                transaction_date = get_val('transaction_date') or get_val('Date')
                patient_id = get_val('patient_id') or get_val('Patient ID')
                service_date = get_val('service_date') or get_val('Service Date')
                insurance_payment = get_val('insurance_payment', numeric=True) or get_val('Insurance Payment', numeric=True)
                patient_payment = get_val('patient_payment', numeric=True) or get_val('Patient Payment', numeric=True)
                adjustment_amount = get_val('adjustment_amount', numeric=True) or get_val('Adjustment Amount', numeric=True)
                cpt_code = get_val('cpt_code') or get_val('CPT Code')
                diagnosis_code = get_val('diagnosis_code') or get_val('Diagnosis Code')
                payer_name = get_val('payer_name') or get_val('Payer')
                claim_number = get_val('claim_number') or get_val('Claim Number')
                notes = get_val('notes') or get_val('Notes')
                
                # Insert transaction record
                self.conn.execute("""
                    INSERT INTO payment_transactions 
                    (provider_id, transaction_date, cash_applied, patient_id, service_date, 
                     insurance_payment, patient_payment, adjustment_amount, cpt_code, 
                     diagnosis_code, payer_name, claim_number, upload_batch, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    provider_id, transaction_date, cash_applied, patient_id, service_date, 
                    insurance_payment, patient_payment, adjustment_amount, cpt_code, 
                    diagnosis_code, payer_name, claim_number, filename, notes
                ))
                
                successful_records += 1
                
            except Exception as e:
                failed_records += 1
                error_details = traceback.format_exc()
                issue = {'type': 'processing_error', 'description': str(e), 'row': index}
                issues.append(issue)
                quality_logger.error(f"Error processing row {index} in {filename}: {str(e)}\n{error_details}")
        
        # Update upload status
        self.conn.execute("""
            UPDATE data_uploads 
            SET records_successful = ?, records_failed = ?, status = 'completed'
            WHERE upload_id = ?
        """, (successful_records, failed_records, upload_id))
        
        # Record data quality issues
        for issue in issues:
            self.conn.execute("""
                INSERT INTO data_quality_issues 
                (table_name, issue_type, issue_description, severity, record_id)
                VALUES ('payment_transactions', ?, ?, 'medium', ?)
            """, (issue['type'], issue['description'], issue.get('row')))
        
        # Commit transaction and update monthly summaries
        self.conn.commit()
        self.update_monthly_summaries()
        
        logger.info(f"CSV upload completed: {successful_records} successful, {failed_records} failed, {len(issues)} issues")
        
        return {
            'success': True,
            'total_records': len(df),
            'successful': successful_records,
            'failed': failed_records,
            'issues': issues
        }
    def update_monthly_summaries(self):
        """Update the monthly summary tables for faster reporting"""
        try:
            logger.debug("Updating monthly provider summaries")
            self.conn.execute("""
                INSERT OR REPLACE INTO monthly_provider_summary 
                (provider_id, year, month, total_cash_applied, total_transactions, total_patients, avg_payment_per_transaction)
                SELECT 
                    provider_id,
                    strftime('%Y', transaction_date) as year,
                    strftime('%m', transaction_date) as month,
                    SUM(cash_applied) as total_cash_applied,
                    COUNT(*) as total_transactions,
                    COUNT(DISTINCT patient_id) as total_patients,
                    AVG(cash_applied) as avg_payment_per_transaction
                FROM payment_transactions
                WHERE cash_applied IS NOT NULL
                GROUP BY provider_id, strftime('%Y', transaction_date), strftime('%m', transaction_date)
            """)
            self.conn.commit()
            logger.debug("Monthly provider summaries updated successfully")
        except sqlite3.Error as e:
            logger.error(f"Error updating monthly summaries: {e}")
            self.conn.rollback()
            raise
    def get_provider_revenue(self, year: int = None, provider_name: str = None) -> pd.DataFrame:
        """Get provider revenue data, optionally filtered by year and/or provider name"""
        try:
            logger.debug(f"Getting provider revenue data: year={year}, provider={provider_name}")
            query = """
                SELECT 
                    p.provider_name,
                    mps.year,
                    mps.month,
                    mps.total_cash_applied,
                    mps.total_transactions,
                    mps.total_patients
                FROM monthly_provider_summary mps
                JOIN providers p ON mps.provider_id = p.provider_id
            """
            params = []
            conditions = []
            if year:
                conditions.append("mps.year = ?")
                params.append(year)
            if provider_name:
                conditions.append("p.provider_name = ?")
                params.append(provider_name)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY p.provider_name, mps.year, mps.month"
            
            result_df = pd.read_sql_query(query, self.conn, params=params)
            logger.debug(f"Retrieved {len(result_df)} revenue records")
            return result_df
        except Exception as e:
            logger.error(f"Error retrieving provider revenue data: {e}")
            # Return an empty DataFrame rather than crashing
            return pd.DataFrame(columns=['provider_name', 'year', 'month', 'total_cash_applied', 'total_transactions', 'total_patients'])
    def get_total_revenue_2024(self) -> pd.DataFrame:
        """Get total 2024 revenue by provider"""
        try:
            logger.debug("Retrieving total 2024 revenue by provider")
            if not self.use_sqlalchemy:
                # Old sqlite3 path
                query = "SELECT provider, SUM(cash_applied) as total FROM payment_transactions WHERE strftime('%Y', transaction_date) = '2024' GROUP BY provider"
                cursor = self.conn.cursor()
                cursor.execute(query)
                return pd.DataFrame(cursor.fetchall(), columns=["provider", "total"])
            else:
                # New SQLAlchemy path
                query = text("SELECT provider, SUM(cash_applied) as total FROM payment_transactions WHERE strftime('%Y', transaction_date) = '2024' GROUP BY provider")
                with self.engine.connect() as conn:
                    result = conn.execute(query)
                    return pd.DataFrame(result.fetchall(), columns=["provider", "total"])
        except Exception as e:
            logger.error(f"Error retrieving 2024 revenue data: {e}")
            # Return an empty DataFrame rather than crashing
            return pd.DataFrame(columns=['provider_name', 'total_2024_revenue', 'total_transactions', 'avg_payment'])
    def add_knowledge(self, term: str, definition: str, category: str = None, synonyms: List[str] = None):
        """Add or update a term in the knowledge base"""
        try:
            logger.debug(f"Adding knowledge term: {term}")
            synonyms_json = json.dumps(synonyms) if synonyms else None
            self.conn.execute("""
                INSERT OR REPLACE INTO billing_terminology 
                (term, definition, category, synonyms)
                VALUES (?, ?, ?, ?)
            """, (term, definition, category, synonyms_json))
            self.conn.commit()
            logger.debug(f"Knowledge term '{term}' added/updated successfully")
        except Exception as e:
            logger.error(f"Error adding knowledge term '{term}': {e}")
            self.conn.rollback()
            raise
    def search_knowledge(self, search_term: str) -> List[Dict]:
        """Search the knowledge base for terms or definitions"""
        try:
            logger.debug(f"Searching knowledge base for: '{search_term}'")
            cursor = self.conn.execute("""
                SELECT term, definition, category, synonyms
                FROM billing_terminology 
                WHERE term LIKE ? OR definition LIKE ?
                ORDER BY 
                    CASE 
                        WHEN term LIKE ? THEN 1
                        WHEN definition LIKE ? THEN 2
                        ELSE 3
                    END
            """, (f'%{search_term}%', f'%{search_term}%', f'{search_term}%', f'{search_term}%'))
            
            results = []
            for row in cursor.fetchall():
                try:
                    synonyms = json.loads(row[3]) if row[3] else []
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in synonyms for term '{row[0]}': {row[3]}")
                    synonyms = []
                    
                results.append({
                    'term': row[0],
                    'definition': row[1],
                    'category': row[2],
                    'synonyms': synonyms
                })
            
            logger.debug(f"Found {len(results)} knowledge base entries for '{search_term}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base for '{search_term}': {e}")
            return []
    def get_rows_with_missing_cash_applied(self, anonymize: bool = True) -> pd.DataFrame:
        """Get all transactions with missing cash_applied values
        
        Args:
            anonymize: Whether to anonymize sensitive data in the result
            
        Returns:
            DataFrame with transactions that have missing cash_applied values
        """
        try:
            logger.debug("Retrieving transactions with missing cash_applied values")
            query = "SELECT * FROM payment_transactions WHERE cash_applied IS NULL"
            result_df = pd.read_sql_query(query, self.conn)
            logger.debug(f"Found {len(result_df)} transactions with missing cash_applied values")
            
            # Anonymize sensitive data if requested
            if anonymize and not result_df.empty:
                logger.debug("Anonymizing sensitive data in results")
                result_df = anonymize_dataframe(result_df, 
                                               sensitive_columns=['patient_id', 'claim_number'])
            
            return result_df
        except Exception as e:
            logger.error(f"Error retrieving transactions with missing cash_applied: {e}")
            # Return an empty DataFrame rather than crashing
            return pd.DataFrame()
        
    def generate_privacy_audit(self) -> Dict:
        """Generate a privacy audit report for the database
        
        Returns:
            A dictionary with privacy audit information
        """
        try:
            logger.info("Generating privacy audit report")
            
            # Get sample data from key tables
            transactions_query = "SELECT * FROM payment_transactions LIMIT 100"
            providers_query = "SELECT * FROM providers LIMIT 100"
            
            transactions_df = pd.read_sql_query(transactions_query, self.conn)
            providers_df = pd.read_sql_query(providers_query, self.conn)
            
            # Generate privacy reports
            transactions_report = generate_privacy_report(transactions_df)
            providers_report = generate_privacy_report(providers_df)
            
            # Count records with sensitive data
            patient_count_query = "SELECT COUNT(DISTINCT patient_id) FROM payment_transactions"
            patient_count = self.conn.execute(patient_count_query).fetchone()[0]
            
            # Compile audit report
            audit_report = {
                "timestamp": datetime.now().isoformat(),
                "database_path": self.db_path,
                "tables_analyzed": [
                    "payment_transactions",
                    "providers"
                ],
                "sensitive_data_summary": {
                    "unique_patients": patient_count,
                    "potential_pii_columns": {
                        "payment_transactions": transactions_report["potential_pii_columns"],
                        "providers": providers_report["potential_pii_columns"]
                    }
                },
                "recommendations": transactions_report["recommendations"] + providers_report["recommendations"]
            }
            
            logger.info("Privacy audit report generated successfully")
            return audit_report
            
        except Exception as e:
            logger.error(f"Error generating privacy audit: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def close(self):
        """Close the database connection properly"""
        try:
            logger.debug("Closing database connection")
            if self.use_sqlalchemy:
                if self.engine:
                    self.engine.dispose()
                    logger.debug("SQLAlchemy engine disposed")
            else:
                self.conn.close()
                logger.debug("SQLite3 connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
            # Still want to continue even if there's an error

    def get_engine(self):
        """Return the SQLAlchemy engine if using SQLAlchemy, else None."""
        return self.engine

    def get_session(self):
        """Return a SQLAlchemy session if using SQLAlchemy."""
        if not self.use_sqlalchemy or self.engine is None:
            raise RuntimeError("SQLAlchemy engine not initialized")
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        return Session()

    def get_provider_by_name(self, provider_name):
        if not self.use_sqlalchemy:
            query = "SELECT * FROM providers WHERE provider_name = ?"
            return pd.read_sql_query(query, self.conn, params=(provider_name,))
        else:
            session = self.get_session()
            provider = session.query(Provider).filter(Provider.provider_name == provider_name).first()
            session.close()
            return provider

    def get_transactions_by_patient(self, patient_id):
        """
        Fetch all transactions for a given patient ID.
        If use_sqlalchemy is True, uses the ORM to query the Transaction table.
        Otherwise, uses the legacy sqlite3 connection and returns a DataFrame.
        Args:
            patient_id (str): The patient ID to search for.
        Returns:
            List[Transaction] if using ORM, or DataFrame if using sqlite3.
        """
        if not self.use_sqlalchemy:
            query = "SELECT * FROM payment_transactions WHERE patient_id = ?"
            return pd.read_sql_query(query, self.conn, params=(patient_id,))
        else:
            session = self.get_session()
            results = session.query(Transaction).filter(Transaction.patient_id == patient_id).all()
            session.close()
            return results

    def get_total_revenue_by_provider(self, provider_name: str = None, start_date: str = None, end_date: str = None):
        """
        Get total revenue by provider - DUAL BACKEND EXAMPLE
        
        This method demonstrates the migration pattern:
        - Supports both sqlite3 and SQLAlchemy backends
        - Gradual migration approach with feature flag
        """
        logger.debug(f"Getting total revenue by provider using SQLAlchemy: {self.use_sqlalchemy}")
        
        # Build dynamic WHERE conditions
        conditions = []
        params = []
        
        if provider_name:
            conditions.append("p.provider_name LIKE ?")
            params.append(f"%{provider_name}%")
            
        if start_date:
            conditions.append("pt.transaction_date >= ?")
            params.append(start_date)
            
        if end_date:
            conditions.append("pt.transaction_date <= ?")
            params.append(end_date)
        
        where_clause = " AND " + " AND ".join(conditions) if conditions else ""
        
        base_query = f"""
        SELECT 
            p.provider_name,
            p.specialty,
            COUNT(pt.transaction_id) as transaction_count,
            SUM(pt.cash_applied) as total_revenue,
            AVG(pt.cash_applied) as avg_payment,
            MIN(pt.transaction_date) as first_transaction,
            MAX(pt.transaction_date) as last_transaction
        FROM payment_transactions pt
        JOIN providers p ON pt.provider_id = p.provider_id
        WHERE pt.cash_applied IS NOT NULL{where_clause}
        GROUP BY p.provider_id, p.provider_name, p.specialty
        ORDER BY total_revenue DESC
        """
        
        if not self.use_sqlalchemy:
            # LEGACY PATH - sqlite3
            logger.debug("Using sqlite3 backend")
            try:
                cursor = self.conn.cursor()
                cursor.execute(base_query, params)
                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()
                
                if not results:
                    logger.info("No revenue data found")
                    return pd.DataFrame()
                    
                return pd.DataFrame(results, columns=columns)
                
            except sqlite3.Error as e:
                logger.error(f"SQLite error in get_total_revenue_by_provider: {e}")
                return pd.DataFrame()
        else:
            # NEW PATH - SQLAlchemy
            logger.debug("Using SQLAlchemy backend")
            try:
                with self.engine.connect() as conn:
                    # Convert ? placeholders to :param format for SQLAlchemy
                    sqlalchemy_query = base_query
                    sqlalchemy_params = {}
                    
                    # Convert positional params to named params
                    for i, param in enumerate(params):
                        param_name = f"param_{i}"
                        sqlalchemy_query = sqlalchemy_query.replace("?", f":{param_name}", 1)
                        sqlalchemy_params[param_name] = param
                    
                    result = conn.execute(text(sqlalchemy_query), sqlalchemy_params)
                    columns = list(result.keys())
                    rows = result.fetchall()
                    
                    if not rows:
                        logger.info("No revenue data found")
                        return pd.DataFrame()
                        
                    return pd.DataFrame(rows, columns=columns)
                    
            except Exception as e:
                logger.error(f"SQLAlchemy error in get_total_revenue_by_provider: {e}")
                return pd.DataFrame()

    def get_payment_type_analysis(self):
        """
        Analyze payments by type (insurance vs credit card vs other) - DUAL BACKEND EXAMPLE
        
        This shows how to handle different data types in unified analysis
        """
        logger.debug(f"Getting payment type analysis using SQLAlchemy: {self.use_sqlalchemy}")
        
        query = """
        SELECT 
            CASE 
                WHEN pt.payer_name LIKE '%insurance%' OR pt.payer_name LIKE '%aetna%' OR pt.payer_name LIKE '%cigna%' 
                     OR pt.payer_name LIKE '%medicare%' OR pt.payer_name LIKE '%medicaid%' THEN 'Insurance'
                WHEN pt.payer_name LIKE '%credit%' OR pt.payer_name LIKE '%card%' OR pt.payer_name LIKE '%visa%' 
                     OR pt.payer_name LIKE '%mastercard%' THEN 'Credit Card'
                ELSE 'Other'
            END as payment_category,
            COUNT(*) as transaction_count,
            SUM(pt.cash_applied) as total_amount,
            AVG(pt.cash_applied) as avg_amount,
            MIN(pt.cash_applied) as min_amount,
            MAX(pt.cash_applied) as max_amount
        FROM payment_transactions pt
        WHERE pt.cash_applied IS NOT NULL AND pt.cash_applied > 0
        GROUP BY payment_category
        ORDER BY total_amount DESC
        """
        
        if not self.use_sqlalchemy:
            # LEGACY PATH
            try:
                cursor = self.conn.cursor()
                cursor.execute(query)
                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()
                return pd.DataFrame(results, columns=columns)
            except sqlite3.Error as e:
                logger.error(f"SQLite error in get_payment_type_analysis: {e}")
                return pd.DataFrame()
        else:
            # NEW PATH
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(query))
                    columns = list(result.keys())
                    rows = result.fetchall()
                    return pd.DataFrame(rows, columns=columns)
            except Exception as e:
                logger.error(f"SQLAlchemy error in get_payment_type_analysis: {e}")
                return pd.DataFrame()