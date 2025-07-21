#!/usr/bin/env python3
"""
Debug CSV Processor for Medical Billing Data

This script debugs CSV files with continuation rows by combining them
before inserting into the database.
"""

import os
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import re

from medical_billing_db import MedicalBillingDB
from utils.logger import get_logger
from utils.config import get_config

# Configure logging
logger = get_logger()
config = get_config()

class DebugCSVProcessor:
    """Processes CSV files with continuation rows by combining them properly"""
    
    def __init__(self, db_path: str = None):
        """Initialize the processor"""
        self.db_path = db_path or config.get("database.db_path", "medical_billing.db")
        self.db = MedicalBillingDB(self.db_path)
        
    def process_csv_file(self, file_path: str) -> Dict:
        """Process a single CSV file, handling continuation rows"""
        print(f"📄 Processing: {Path(file_path).name}")
        
        try:
            # Read the CSV file with more flexible parsing
            df = pd.read_csv(file_path, dtype=str)
            
            print(f"   📊 Raw CSV shape: {df.shape}")
            print(f"   📋 Columns: {list(df.columns)}")
            
            # Clean up column names
            df.columns = df.columns.str.strip()
            
            # Remove empty rows
            df = df.dropna(how='all')
            
            print(f"   📊 After removing empty rows: {df.shape}")
            
            # Show first few rows for debugging
            print(f"   🔍 First 4 rows:")
            for i in range(min(4, len(df))):
                row = df.iloc[i]
                print(f"      Row {i}: Check Date='{row.get('Check Date', '')}', Cash Applied='{row.get('Cash Applied', '')}', Provider='{row.get('Provider', '')}'")
            
            # Process the data to combine continuation rows
            processed_data = self._combine_continuation_rows(df)
            
            print(f"   🔄 Processed {len(processed_data)} transactions")
            
            # Show first few processed transactions
            for i, transaction in enumerate(processed_data[:3]):
                print(f"      Transaction {i}: {transaction['provider_name']} - {transaction['check_date']} - ${transaction['cash_applied']}")
            
            # Insert into database
            result = self._insert_processed_data(processed_data, file_path)
            
            print(f"   ✅ Success: {result['successful_rows']} rows in {result['processing_time']:.1f}s")
            if result.get('issues'):
                print(f"   ⚠️  Issues: {len(result['issues'])} data quality issues found")
                for issue in result['issues'][:3]:  # Show first 3 issues
                    print(f"      - {issue}")
                
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            logger.error(error_msg)
            print(f"   ❌ Failed: {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _combine_continuation_rows(self, df: pd.DataFrame) -> List[Dict]:
        """Combine continuation rows with their parent rows"""
        processed_rows = []
        current_transaction = None
        
        for index, row in df.iterrows():
            # Get the key fields
            check_date = str(row.get('Check Date', '')).strip()
            cash_applied = str(row.get('Cash Applied', '')).strip()
            provider = str(row.get('Provider', '')).strip()
            
            # Check if this is a continuation row (empty Check Date but has Cash Applied)
            is_continuation = (
                check_date == '' or 
                check_date == 'nan' or
                pd.isna(row.get('Check Date', ''))
            ) and (
                cash_applied != '' and 
                cash_applied != 'nan' and
                not pd.isna(row.get('Cash Applied', ''))
            )
            
            if is_continuation:
                # This is a continuation row - combine with current transaction
                if current_transaction:
                    # Add the cash applied amount to the current transaction
                    cash_applied_amount = self._parse_amount(cash_applied)
                    if cash_applied_amount != 0:
                        current_transaction['cash_applied'] = cash_applied_amount
                        
                    # Add any additional session information
                    reference = str(row.get('Reference', '')).strip()
                    if reference and 'Sess:' in reference:
                        current_transaction['session_info'] = reference
                        
            else:
                # This is a new transaction row
                # Save the previous transaction if it exists
                if current_transaction:
                    processed_rows.append(current_transaction)
                
                # Start a new transaction
                current_transaction = self._create_transaction_from_row(row)
        
        # Don't forget the last transaction
        if current_transaction:
            processed_rows.append(current_transaction)
        
        return processed_rows
    
    def _create_transaction_from_row(self, row: pd.Series) -> Dict:
        """Create a transaction dictionary from a CSV row"""
        # Parse dates
        check_date = self._parse_date(str(row.get('Check Date', '')).strip())
        date_posted = self._parse_date(str(row.get('Date Posted', '')).strip())
        
        # Parse amounts
        check_amount = self._parse_amount(str(row.get('Check Amount', '')).strip())
        cash_applied = self._parse_amount(str(row.get('Cash Applied', '')).strip())
        
        # Get provider name
        provider_name = str(row.get('Provider', '')).strip()
        if provider_name == 'nan':
            provider_name = ''
        
        # Create transaction
        transaction = {
            'check_date': check_date,
            'date_posted': date_posted,
            'check_number': str(row.get('Check Number', '')).strip(),
            'payment_from': str(row.get('Payment From', '')).strip(),
            'reference': str(row.get('Reference', '')).strip(),
            'check_amount': check_amount,
            'cash_applied': cash_applied,
            'provider_name': provider_name,
            'session_info': ''
        }
        
        return transaction
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to YYYY-MM-DD format"""
        if not date_str or date_str == '' or date_str == 'nan':
            return None
            
        try:
            # Handle MM/DD/YYYY format
            if '/' in date_str and len(date_str.split('/')[2]) == 4:
                date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                return date_obj.strftime('%Y-%m-%d')
            
            # Handle MM/DD/YY format (2-digit year)
            elif '/' in date_str and len(date_str.split('/')[2]) == 2:
                date_obj = datetime.strptime(date_str, '%m/%d/%y')
                return date_obj.strftime('%Y-%m-%d')
            
            # Handle YYYY-MM-DD format
            elif '-' in date_str and len(date_str.split('-')[0]) == 4:
                return date_str
            
            # Handle other formats
            else:
                # Try to parse with pandas
                parsed_date = pd.to_datetime(date_str, errors='coerce')
                if pd.notna(parsed_date):
                    return parsed_date.strftime('%Y-%m-%d')
                    
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
            
        return None
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount to float"""
        if not amount_str or amount_str == '' or amount_str == 'nan':
            return 0.0
            
        try:
            # Remove currency symbols and commas
            amount_str = str(amount_str).strip()
            amount_str = re.sub(r'[^\d.-]', '', amount_str)
            
            if amount_str == '' or amount_str == '-':
                return 0.0
                
            return float(amount_str)
            
        except Exception as e:
            logger.warning(f"Could not parse amount '{amount_str}': {e}")
            return 0.0
    
    def _insert_processed_data(self, processed_data: List[Dict], file_path: str) -> Dict:
        """Insert processed data into the database"""
        start_time = datetime.now()
        successful_rows = 0
        failed_rows = 0
        issues = []
        
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for transaction in processed_data:
                try:
                    # Skip if no provider name
                    if not transaction['provider_name']:
                        issues.append(f"Missing provider name in transaction")
                        failed_rows += 1
                        continue
                    
                    # Skip if no check date
                    if not transaction['check_date']:
                        issues.append(f"Missing check date for {transaction['provider_name']}")
                        failed_rows += 1
                        continue
                    
                    # Insert provider if not exists and get provider_id
                    cursor.execute("""
                        INSERT OR IGNORE INTO providers (provider_name, contract_type, base_percentage)
                        VALUES (?, ?, ?)
                    """, (transaction['provider_name'], 'Independent Contractor', 0.0))
                    
                    # Get provider_id
                    cursor.execute("SELECT provider_id FROM providers WHERE provider_name = ?", 
                                 (transaction['provider_name'],))
                    provider_result = cursor.fetchone()
                    if not provider_result:
                        issues.append(f"Could not find provider_id for {transaction['provider_name']}")
                        failed_rows += 1
                        continue
                    
                    provider_id = provider_result[0]
                    
                    # Insert transaction
                    cursor.execute("""
                        INSERT INTO payment_transactions 
                        (provider_id, transaction_date, service_date, cash_applied, 
                         patient_payment, payer_name, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        provider_id,
                        transaction['check_date'],
                        transaction['check_date'],  # Use check_date as service_date
                        transaction['cash_applied'],
                        transaction['check_amount'],  # Use check_amount as patient_payment
                        transaction['payment_from'],  # Use payment_from as payer_name
                        f"Reference: {transaction['reference']}; Session: {transaction['session_info']}"
                    ))
                    
                    successful_rows += 1
                    
                except Exception as e:
                    issues.append(f"Error inserting transaction: {str(e)}")
                    failed_rows += 1
            
            # Commit changes
            conn.commit()
            conn.close()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'successful_rows': successful_rows,
                'failed_rows': failed_rows,
                'total_rows_processed': len(processed_data),
                'processing_time': processing_time,
                'issues': issues
            }
            
        except Exception as e:
            if 'conn' in locals():
                conn.close()
            return {
                'success': False,
                'error': str(e),
                'successful_rows': successful_rows,
                'failed_rows': failed_rows,
                'total_rows_processed': len(processed_data),
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'issues': issues
            }
    
    def process_single_file(self, file_path: str) -> Dict:
        """Process a single file for debugging"""
        return self.process_csv_file(file_path)

def main():
    """Main function to debug a single CSV file"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug CSV Processor for Medical Billing Data')
    parser.add_argument('--file', default='csv_folder/billing/3-31-23 Payments-Hendersonville - Dustin Nisley.csv', 
                       help='Path to CSV file to debug')
    
    args = parser.parse_args()
    
    # Process the single file
    processor = DebugCSVProcessor()
    result = processor.process_single_file(args.file)
    
    if result.get('success', False):
        print(f"\n✅ Processing completed successfully!")
    else:
        print(f"\n❌ Processing failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main() 