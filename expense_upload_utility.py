#!/usr/bin/env python3
"""
Expense Upload Utility

Upload and process month-to-month expense data for profitability analysis.
Handles variable and fixed costs with budget variance tracking.
"""

import pandas as pd
import sqlite3
import argparse
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from utils.logger import get_logger
from utils.config import get_config
from utils.expense_analyzer import ExpenseAnalyzer

logger = get_logger()
config = get_config()

class ExpenseUploader:
    """Handles uploading and processing expense data"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.get_db_path()
        self.analyzer = ExpenseAnalyzer(self.db_path)
    
    def validate_csv_format(self, df: pd.DataFrame) -> List[str]:
        """Validate CSV format and return list of issues"""
        issues = []
        
        required_columns = ['expense_date', 'category', 'subcategory', 'amount']
        missing_columns = set(required_columns) - set(df.columns)
        
        if missing_columns:
            issues.append(f"Missing required columns: {missing_columns}")
        
        # Check date format
        if 'expense_date' in df.columns:
            try:
                pd.to_datetime(df['expense_date'])
            except:
                issues.append("Invalid date format in expense_date column")
        
        # Check amount is numeric
        if 'amount' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['amount']):
                try:
                    pd.to_numeric(df['amount'])
                except:
                    issues.append("Non-numeric values in amount column")
        
        # Check for empty required fields
        for col in required_columns:
            if col in df.columns and df[col].isnull().any():
                issues.append(f"Empty values found in required column: {col}")
        
        return issues
    
    def clean_and_prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare expense data for upload"""
        df = df.copy()
        
        # Convert date column
        df['expense_date'] = pd.to_datetime(df['expense_date']).dt.date
        
        # Convert amount to float
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # Fill optional columns with defaults
        optional_defaults = {
            'budgeted_amount': df['amount'],  # Use actual amount if no budget
            'is_variable': 0,
            'usage_count': None,
            'rate_per_unit': None,
            'due_date': None,
            'frequency': 'monthly',
            'status': 'active',
            'notes': ''
        }
        
        for col, default_value in optional_defaults.items():
            if col not in df.columns:
                df[col] = default_value
        
        # Calculate variance
        df['variance'] = df['amount'] - df['budgeted_amount']
        
        # Add upload metadata
        df['upload_batch'] = f"expense_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return df
    
    def upload_expenses(self, csv_path: str, preview_only: bool = False) -> Dict:
        """Upload expense data from CSV file"""
        try:
            # Read CSV
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} expense records from {csv_path}")
            
            # Validate format
            issues = self.validate_csv_format(df)
            if issues:
                return {
                    'success': False,
                    'error': f"CSV validation failed: {'; '.join(issues)}",
                    'records_processed': 0
                }
            
            # Clean and prepare data
            df_clean = self.clean_and_prepare_data(df)
            
            if preview_only:
                return {
                    'success': True,
                    'preview': df_clean.head(10).to_dict('records'),
                    'total_records': len(df_clean),
                    'summary': self.get_upload_summary(df_clean)
                }
            
            # Upload to database
            conn = sqlite3.connect(self.db_path)
            try:
                # Insert expense transactions
                df_clean.to_sql('expense_transactions', conn, if_exists='append', index=False)
                
                # Update monthly summaries
                self.analyzer.update_monthly_summaries()
                
                conn.commit()
                
                return {
                    'success': True,
                    'records_processed': len(df_clean),
                    'summary': self.get_upload_summary(df_clean),
                    'upload_batch': df_clean['upload_batch'].iloc[0]
                }
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error uploading expenses: {e}")
            return {
                'success': False,
                'error': str(e),
                'records_processed': 0
            }
    
    def get_upload_summary(self, df: pd.DataFrame) -> Dict:
        """Generate summary of uploaded expense data"""
        summary = {
            'total_records': len(df),
            'date_range': {
                'start': df['expense_date'].min().strftime('%Y-%m-%d'),
                'end': df['expense_date'].max().strftime('%Y-%m-%d')
            },
            'categories': df['category'].value_counts().to_dict(),
            'total_amount': float(df['amount'].sum()),
            'variable_vs_fixed': {
                'variable_expenses': float(df[df['is_variable'] == 1]['amount'].sum()),
                'fixed_expenses': float(df[df['is_variable'] == 0]['amount'].sum())
            },
            'monthly_totals': df.groupby(df['expense_date'].astype(str).str[:7])['amount'].sum().to_dict()
        }
        
        return summary
    
    def analyze_uploaded_data(self, upload_batch: str) -> Dict:
        """Analyze recently uploaded expense data"""
        conn = sqlite3.connect(self.db_path)
        try:
            query = """
                SELECT 
                    strftime('%Y-%m', expense_date) as month,
                    category,
                    SUM(amount) as total_amount,
                    SUM(budgeted_amount) as total_budgeted,
                    SUM(variance) as total_variance,
                    AVG(CASE WHEN budgeted_amount > 0 THEN variance/budgeted_amount*100 ELSE 0 END) as avg_variance_pct
                FROM expense_transactions
                WHERE upload_batch = ?
                GROUP BY month, category
                ORDER BY month, total_variance DESC
            """
            
            df = pd.read_sql_query(query, conn, params=[upload_batch])
            
            return {
                'variance_analysis': df.to_dict('records'),
                'total_variance': float(df['total_variance'].sum()),
                'categories_over_budget': len(df[df['total_variance'] > 0]),
                'categories_under_budget': len(df[df['total_variance'] < 0])
            }
            
        finally:
            conn.close()

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Upload expense data for profitability analysis')
    parser.add_argument('csv_file', help='Path to expense CSV file')
    parser.add_argument('--preview', action='store_true', help='Preview data without uploading')
    parser.add_argument('--analyze', action='store_true', help='Analyze data after upload')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"❌ File not found: {args.csv_file}")
        sys.exit(1)
    
    uploader = ExpenseUploader()
    
    print("💰 HVLC_DB Expense Upload Utility")
    print("=" * 50)
    print(f"📁 File: {args.csv_file}")
    
    if args.preview:
        print("\n👀 Preview Mode - No data will be uploaded")
    
    # Upload expenses
    result = uploader.upload_expenses(args.csv_file, preview_only=args.preview)
    
    if not result['success']:
        print(f"❌ Upload failed: {result['error']}")
        sys.exit(1)
    
    if args.preview:
        print(f"\n✅ Preview successful - {result['total_records']} records ready for upload")
        print("\n📊 Summary:")
        summary = result['summary']
        print(f"  • Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
        print(f"  • Total amount: ${summary['total_amount']:,.2f}")
        print(f"  • Fixed expenses: ${summary['variable_vs_fixed']['fixed_expenses']:,.2f}")
        print(f"  • Variable expenses: ${summary['variable_vs_fixed']['variable_expenses']:,.2f}")
        print("\n📋 Categories:")
        for category, count in summary['categories'].items():
            print(f"  • {category}: {count} records")
        
        print(f"\n💡 To upload this data, run without --preview flag")
        
    else:
        print(f"✅ Upload successful - {result['records_processed']} records processed")
        
        summary = result['summary']
        print("\n📊 Upload Summary:")
        print(f"  • Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
        print(f"  • Total amount: ${summary['total_amount']:,.2f}")
        print(f"  • Fixed expenses: ${summary['variable_vs_fixed']['fixed_expenses']:,.2f}")
        print(f"  • Variable expenses: ${summary['variable_vs_fixed']['variable_expenses']:,.2f}")
        
        if args.analyze:
            print("\n📈 Variance Analysis:")
            analysis = uploader.analyze_uploaded_data(result['upload_batch'])
            print(f"  • Total variance: ${analysis['total_variance']:,.2f}")
            print(f"  • Categories over budget: {analysis['categories_over_budget']}")
            print(f"  • Categories under budget: {analysis['categories_under_budget']}")
        
        print(f"\n🎯 Next steps:")
        print("1. Use the business reasoning system to analyze profitability")
        print("2. Ask questions like 'What's our monthly break-even point?'")
        print("3. Upload revenue data to calculate net profit margins")

if __name__ == "__main__":
    main() 