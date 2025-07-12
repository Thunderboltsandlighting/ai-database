import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalBillingDB:
    def __init__(self, db_path="medical_billing.db"):
        """Initialize the medical billing database"""
        self.db_path = db_path
        self.connection = None
        self.connect()
        self.create_tables()
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            if not self.connection:
                raise Exception("Database connection not established")
                
            cursor = self.connection.cursor()
            
            # Create billing_data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS billing_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT,
                    provider_name TEXT,
                    date_of_service DATE,
                    amount REAL,
                    payment_method TEXT,
                    insurance_company TEXT,
                    claim_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create providers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS providers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_name TEXT UNIQUE,
                    specialty TEXT,
                    hire_date DATE,
                    pay_rate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_provider_name ON billing_data(provider_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_date_of_service ON billing_data(date_of_service)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_name ON billing_data(patient_name)')
            
            self.connection.commit()
            logger.info("Database tables created/verified successfully")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def execute_query(self, query, params=None):
        """Execute a SQL query and return results"""
        try:
            if not self.connection:
                raise Exception("Database connection not established")
                
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            return []
    
    def get_provider_stats(self, provider_name=None, start_date=None, end_date=None):
        """Get provider statistics"""
        try:
            query = """
                SELECT 
                    provider_name,
                    COUNT(DISTINCT patient_name) as client_count,
                    COUNT(*) as total_sessions,
                    SUM(amount) as total_revenue,
                    AVG(amount) as avg_session_amount
                FROM billing_data
                WHERE 1=1
            """
            params = []
            
            if provider_name:
                query += " AND LOWER(provider_name) LIKE ?"
                params.append(f"%{provider_name.lower()}%")
            
            if start_date:
                query += " AND date_of_service >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND date_of_service <= ?"
                params.append(end_date)
            
            query += " GROUP BY provider_name"
            
            results = self.execute_query(query, params if params else None)
            return results
            
        except Exception as e:
            logger.error(f"Error getting provider stats: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")