#!/usr/bin/env python3
"""
Database Migration: Add Expense Tracking Tables

This script adds month-to-month expense tracking capabilities to the existing
HVLC_DB medical billing database.
"""

import sqlite3
import os
import sys
from datetime import datetime
from utils.logger import get_logger
from utils.config import get_config
from utils.expense_analyzer import ExpenseAnalyzer

logger = get_logger()
config = get_config()

def backup_database(db_path: str) -> str:
    """Create a backup of the current database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        # Use SQLite backup API for safe backup
        source = sqlite3.connect(db_path)
        backup = sqlite3.connect(backup_path)
        source.backup(backup)
        source.close()
        backup.close()
        
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise

def verify_existing_tables(db_path: str) -> bool:
    """Verify that core tables exist before migration"""
    required_tables = ['providers', 'payment_transactions']
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        missing_tables = set(required_tables) - existing_tables
        if missing_tables:
            logger.error(f"Missing required tables: {missing_tables}")
            return False
        
        logger.info("All required tables found")
        return True
    finally:
        conn.close()

def add_expense_tables(db_path: str) -> bool:
    """Add expense tracking tables to the database"""
    try:
        analyzer = ExpenseAnalyzer(db_path)
        analyzer.create_expense_tables()
        
        # Add expense categories table (not created by analyzer)
        conn = sqlite3.connect(db_path)
        try:
            # Create expense categories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS expense_categories (
                    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name VARCHAR(50) NOT NULL UNIQUE,
                    category_type VARCHAR(30),
                    description TEXT,
                    default_frequency VARCHAR(20) DEFAULT 'monthly',
                    tax_deductible BOOLEAN DEFAULT 1,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add some sample expense categories
            sample_categories = [
                ('Utilities', 'fixed', 'Monthly utility bills'),
                ('Services', 'variable', 'Usage-based services like EMR'),
                ('Property', 'fixed', 'Property-related expenses'),
                ('Payroll', 'variable', 'Staff compensation'),
                ('Insurance', 'fixed', 'Insurance premiums'),
                ('Equipment', 'variable', 'Equipment and supplies'),
                ('Marketing', 'variable', 'Marketing and advertising'),
                ('Professional', 'fixed', 'Professional services'),
                ('Other', 'variable', 'Miscellaneous expenses')
            ]
            
            conn.executemany("""
                INSERT OR IGNORE INTO expense_categories 
                (category_name, category_type, description)
                VALUES (?, ?, ?)
            """, sample_categories)
            
            conn.commit()
            logger.info("Expense tables and sample categories added successfully")
            return True
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Failed to add expense tables: {e}")
        return False

def validate_migration(db_path: str) -> bool:
    """Validate that the migration was successful"""
    expected_tables = [
        'expense_transactions',
        'variable_expense_rates', 
        'monthly_expense_summary',
        'expense_categories'
    ]
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        missing_tables = set(expected_tables) - existing_tables
        if missing_tables:
            logger.error(f"Migration incomplete - missing tables: {missing_tables}")
            return False
        
        # Test inserting a sample expense record
        cursor.execute("""
            INSERT INTO expense_transactions 
            (category, subcategory, expense_date, amount, is_variable, notes)
            VALUES ('Test', 'Migration Test', '2024-01-01', 0.01, 0, 'Migration validation test')
        """)
        
        # Clean up test record
        cursor.execute("DELETE FROM expense_transactions WHERE notes = 'Migration validation test'")
        conn.commit()
        
        logger.info("Migration validation successful")
        return True
        
    except Exception as e:
        logger.error(f"Migration validation failed: {e}")
        return False
    finally:
        conn.close()

def main():
    """Main migration function"""
    print("🏥 HVLC_DB Expense Tracking Migration")
    print("=" * 50)
    
    db_path = config.get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    print(f"📁 Database: {db_path}")
    
    # Step 1: Verify existing database
    print("\n1️⃣ Verifying existing database structure...")
    if not verify_existing_tables(db_path):
        print("❌ Required tables missing. Please ensure your medical billing database is set up correctly.")
        sys.exit(1)
    print("✅ Existing database structure verified")
    
    # Step 2: Create backup
    print("\n2️⃣ Creating database backup...")
    backup_path = backup_database(db_path)
    print(f"✅ Backup created: {backup_path}")
    
    # Step 3: Add expense tables
    print("\n3️⃣ Adding expense tracking tables...")
    if not add_expense_tables(db_path):
        print("❌ Failed to add expense tables")
        sys.exit(1)
    print("✅ Expense tables added successfully")
    
    # Step 4: Validate migration
    print("\n4️⃣ Validating migration...")
    if not validate_migration(db_path):
        print("❌ Migration validation failed")
        print(f"💡 You can restore from backup: {backup_path}")
        sys.exit(1)
    print("✅ Migration validation successful")
    
    print("\n🎉 Migration completed successfully!")
    print("\nNext steps:")
    print("1. Create your expense CSV file using the recommended format")
    print("2. Upload expense data using the bulk upload utility")
    print("3. Start analyzing profitability with month-to-month tracking")
    print(f"\nBackup location: {backup_path}")

if __name__ == "__main__":
    main() 