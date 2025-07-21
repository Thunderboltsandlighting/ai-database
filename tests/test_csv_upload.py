#!/usr/bin/env python
import os
import pandas as pd
import tempfile
from medical_billing_db import MedicalBillingDB

def test_csv_upload():
    """Test CSV upload functionality"""
    print("Creating test CSV file...")
    
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        temp_path = temp_file.name
        # Write CSV data
        temp_file.write(b"Provider,Date,Patient ID,Cash Applied,Insurance Payment,Patient Payment\n")
        temp_file.write(b"Test Provider,2024-07-01,P123,100.50,80.00,20.50\n")
        temp_file.write(b"Test Provider,2024-07-02,P124,200.75,150.75,50.00\n")
        temp_file.write(b"Another Provider,2024-07-01,P125,150.25,120.25,30.00\n")
    
    print(f"Test CSV created at: {temp_path}")
    
    try:
        # Initialize database
        print("Initializing database connection...")
        db = MedicalBillingDB()
        
        # Test chunked CSV upload
        print("Testing chunked CSV upload...")
        result = db.upload_csv_file(temp_path)
        
        print("\nUpload result:")
        print(f"Success: {result.get('success', False)}")
        print(f"Total rows processed: {result.get('total_rows_processed', 0)}")
        print(f"Successful rows: {result.get('successful_rows', 0)}")
        print(f"Failed rows: {result.get('failed_rows', 0)}")
        print(f"Chunks processed: {result.get('chunks_processed', 0)}")
        
        if 'issues' in result and result['issues']:
            print(f"\nIssues ({len(result['issues'])}):")
            for issue in result['issues'][:3]:
                print(f"- {issue.get('type')}: {issue.get('description')}")
            if len(result['issues']) > 3:
                print(f"  ... and {len(result['issues']) - 3} more issues")
        
        # Verify data was inserted
        print("\nVerifying data insertion...")
        query = """
            SELECT p.provider_name, pt.transaction_date, pt.cash_applied
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
            WHERE p.provider_name LIKE 'Test%'
            ORDER BY pt.transaction_date
        """
        cursor = db.conn.execute(query)
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} matching rows:")
        for row in rows:
            print(f"- {row[0]}, {row[1]}, ${row[2]}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        # Clean up
        print("\nCleaning up...")
        if 'db' in locals():
            db.close()
        os.unlink(temp_path)
        print("Test CSV deleted")

if __name__ == "__main__":
    print("Testing CSV upload functionality...")
    success = test_csv_upload()
    print(f"\nTest {'successful' if success else 'failed'}")