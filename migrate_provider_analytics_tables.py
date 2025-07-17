#!/usr/bin/env python3
"""
Provider Analytics Database Migration
Creates tables for tracking provider monthly/annual performance with session date vs payment date mapping
"""

import sqlite3
import os
from datetime import datetime

def create_provider_analytics_tables():
    """Create provider analytics tracking tables"""
    
    # Connect to database
    db_path = 'medical_billing.db'
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    # Create backup
    backup_path = f"medical_billing_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    os.system(f"cp {db_path} {backup_path}")
    print(f"✅ Database backed up to: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🏗️ Creating provider analytics tables...")
        
        # 1. Payment to Session Mapping Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_session_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_date DATE NOT NULL,
                session_date DATE NOT NULL,
                provider_name TEXT NOT NULL,
                cash_applied DECIMAL(10,2) NOT NULL,
                payment_source TEXT,
                session_reference TEXT,
                check_number TEXT,
                payment_from TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_reference, payment_date, cash_applied)
            )
        ''')
        
        # 2. Provider Monthly Summary Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS provider_monthly_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                year_month TEXT NOT NULL,
                total_cash_applied DECIMAL(10,2) DEFAULT 0,
                credit_card_transactions DECIMAL(10,2) DEFAULT 0,
                insurance_payments DECIMAL(10,2) DEFAULT 0,
                cash_payments DECIMAL(10,2) DEFAULT 0,
                provider_cut_percentage DECIMAL(5,2) NOT NULL,
                provider_income DECIMAL(10,2) GENERATED ALWAYS AS (total_cash_applied * provider_cut_percentage / 100) STORED,
                company_income DECIMAL(10,2) GENERATED ALWAYS AS (total_cash_applied * (100 - provider_cut_percentage) / 100) STORED,
                session_count INTEGER DEFAULT 0,
                avg_payment_per_session DECIMAL(10,2) GENERATED ALWAYS AS (
                    CASE WHEN session_count > 0 THEN total_cash_applied / session_count ELSE 0 END
                ) STORED,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider_name, year_month)
            )
        ''')
        
        # 3. Provider Annual Summary Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS provider_annual_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                total_revenue DECIMAL(10,2) DEFAULT 0,
                total_provider_income DECIMAL(10,2) DEFAULT 0,
                total_company_income DECIMAL(10,2) DEFAULT 0,
                months_active INTEGER DEFAULT 0,
                avg_monthly_revenue DECIMAL(10,2) GENERATED ALWAYS AS (
                    CASE WHEN months_active > 0 THEN total_revenue / months_active ELSE 0 END
                ) STORED,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider_name, year)
            )
        ''')
        
        # 4. Provider Split Contracts Table (for historical tracking)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS provider_contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                effective_date DATE NOT NULL,
                end_date DATE,
                split_percentage DECIMAL(5,2) NOT NULL,
                contract_type TEXT DEFAULT 'percentage_split',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_payment_session_provider_date ON payment_session_mapping(provider_name, session_date)",
            "CREATE INDEX IF NOT EXISTS idx_payment_session_payment_date ON payment_session_mapping(payment_date)",
            "CREATE INDEX IF NOT EXISTS idx_monthly_summary_provider_month ON provider_monthly_summary(provider_name, year_month)",
            "CREATE INDEX IF NOT EXISTS idx_annual_summary_provider_year ON provider_annual_summary(provider_name, year)",
            "CREATE INDEX IF NOT EXISTS idx_contracts_provider_dates ON provider_contracts(provider_name, effective_date, end_date)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # Insert initial provider contracts from the TSV data
        print("📋 Inserting provider contract data...")
        
        provider_contracts = [
            ("Dustin Nisley", "2023-01-01", None, 65.0, "percentage_split", "65% split"),
            ("Tammy Maxey", "2023-01-01", None, 100.0, "percentage_split", "100% minus credit card fees"),
            ("Sidney Snipes", "2023-01-01", None, 60.0, "percentage_split", "60% split"),
            ("Isabel Rehak", "2023-01-01", None, 100.0, "percentage_split", "100% owner minus fees"),
            ("Ardelle Bland", "2024-01-01", None, 60.0, "percentage_split", "60% split"),
            ("Alisha Clark", "2024-01-01", None, 60.0, "percentage_split", "60% split")
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO provider_contracts 
            (provider_name, effective_date, end_date, split_percentage, contract_type, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', provider_contracts)
        
        conn.commit()
        print("✅ Provider analytics tables created successfully!")
        
        # Show table structures
        tables = ['payment_session_mapping', 'provider_monthly_summary', 'provider_annual_summary', 'provider_contracts']
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            print(f"\n📋 {table} columns:")
            for col in columns:
                print(f"   {col[1]} ({col[2]})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Provider Analytics Database Migration")
    print("=" * 50)
    success = create_provider_analytics_tables()
    if success:
        print("\n✅ Migration completed successfully!")
        print("Next steps:")
        print("1. Run the CSV processor to populate the tables")
        print("2. Generate monthly summaries")
        print("3. Calculate annual totals")
    else:
        print("\n❌ Migration failed!") 