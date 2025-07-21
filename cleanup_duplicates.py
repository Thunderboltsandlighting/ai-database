#!/usr/bin/env python3
"""
Cleanup Duplicate Transactions

This script removes duplicate transactions from the database.
"""

import sqlite3
from datetime import datetime

def cleanup_duplicates(db_path: str = 'medical_billing.db'):
    """Remove duplicate transactions from the database."""
    print("🧹 Cleaning up duplicate transactions...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, let's see how many duplicates we have
    cursor.execute("""
        SELECT COUNT(*) as total_duplicates
        FROM (
            SELECT transaction_date, cash_applied, payer_name, claim_number, COUNT(*) as count
            FROM payment_transactions 
            GROUP BY transaction_date, cash_applied, payer_name, claim_number 
            HAVING COUNT(*) > 1
        )
    """)
    
    total_duplicates = cursor.fetchone()[0]
    print(f"   Found {total_duplicates} groups of duplicate transactions")
    
    if total_duplicates == 0:
        print("   ✅ No duplicates found!")
        conn.close()
        return
    
    # Create a temporary table with deduplicated data
    cursor.execute("""
        CREATE TEMPORARY TABLE deduplicated_transactions AS
        SELECT MIN(transaction_id) as transaction_id,
               provider_id,
               transaction_date,
               patient_id,
               service_date,
               cash_applied,
               insurance_payment,
               patient_payment,
               adjustment_amount,
               cpt_code,
               diagnosis_code,
               payer_name,
               claim_number,
               upload_batch,
               notes,
               created_date
        FROM payment_transactions
        GROUP BY transaction_date, cash_applied, payer_name, claim_number, provider_id
    """)
    
    # Count how many rows we'll keep
    cursor.execute("SELECT COUNT(*) FROM deduplicated_transactions")
    rows_to_keep = cursor.fetchone()[0]
    
    # Count total rows before cleanup
    cursor.execute("SELECT COUNT(*) FROM payment_transactions")
    total_before = cursor.fetchone()[0]
    
    print(f"   Will keep {rows_to_keep} transactions (removing {total_before - rows_to_keep} duplicates)")
    
    # Replace the original table with deduplicated data
    cursor.execute("DELETE FROM payment_transactions")
    cursor.execute("""
        INSERT INTO payment_transactions 
        SELECT * FROM deduplicated_transactions
    """)
    
    # Count total rows after cleanup
    cursor.execute("SELECT COUNT(*) FROM payment_transactions")
    total_after = cursor.fetchone()[0]
    
    # Drop temporary table
    cursor.execute("DROP TABLE deduplicated_transactions")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"   ✅ Cleanup complete! Removed {total_before - total_after} duplicate transactions")
    print(f"   📊 Before: {total_before} transactions, After: {total_after} transactions")

def main():
    """Main function"""
    cleanup_duplicates()

if __name__ == "__main__":
    main() 