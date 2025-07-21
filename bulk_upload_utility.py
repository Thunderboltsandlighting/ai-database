#!/usr/bin/env python3
"""
Bulk Upload Utility for Historical Medical Billing Data

This script provides tools for systematically uploading large volumes of historical
CSV data while maintaining data quality and performance monitoring.
"""

import os
import time
import json
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse

# Import project modules
from medical_billing_db import MedicalBillingDB
from utils.logger import get_logger
from utils.config import get_config

# Configure logging
logger = get_logger()
config = get_config()

class BulkUploadManager:
    """Manages bulk upload operations with progress tracking and quality monitoring"""
    
    def __init__(self, db_path: str = None):
        """Initialize the bulk upload manager"""
        self.db_path = db_path or config.get("database.db_path", "medical_billing.db")
        self.db = MedicalBillingDB(self.db_path)
        self.upload_log = []
        self.total_stats = {
            'files_processed': 0,
            'total_rows': 0,
            'successful_rows': 0,
            'failed_rows': 0,
            'total_time': 0,
            'issues': []
        }
        
    def create_backup(self, backup_name: str = None) -> str:
        """Create a backup of the current database"""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"database_backup_{timestamp}.db"
            
        backup_path = f"backups/{backup_name}"
        os.makedirs("backups", exist_ok=True)
        
        # Copy database file
        import shutil
        shutil.copy2(self.db_path, backup_path)
        
        logger.info(f"Database backup created: {backup_path}")
        print(f"✅ Database backup created: {backup_path}")
        return backup_path
    
    def upload_folder(self, folder_path: str, file_pattern: str = "*.csv") -> Dict:
        """Upload all CSV files in a folder"""
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            logger.error(f"Folder not found: {folder_path}")
            return {'success': False, 'error': f'Folder not found: {folder_path}'}
        
        # Find all CSV files matching pattern
        csv_files = list(folder_path.glob(file_pattern))
        
        if not csv_files:
            logger.warning(f"No CSV files found in {folder_path}")
            return {'success': True, 'files_processed': 0, 'message': 'No CSV files found'}
        
        folder_stats = {
            'folder': str(folder_path),
            'files_found': len(csv_files),
            'files_processed': 0,
            'total_rows': 0,
            'successful_rows': 0,
            'failed_rows': 0,
            'start_time': time.time(),
            'file_results': []
        }
        
        print(f"\n📁 Processing folder: {folder_path}")
        print(f"   Found {len(csv_files)} CSV files")
        
        # Process each file
        for csv_file in sorted(csv_files):
            print(f"\n📄 Processing: {csv_file.name}")
            
            file_start = time.time()
            result = self.db.upload_csv_file(str(csv_file))
            file_time = time.time() - file_start
            
            # Update folder stats
            folder_stats['files_processed'] += 1
            if result.get('success', False):
                folder_stats['total_rows'] += result.get('total_rows_processed', 0)
                folder_stats['successful_rows'] += result.get('successful_rows', 0)
                folder_stats['failed_rows'] += result.get('failed_rows', 0)
                
                print(f"   ✅ Success: {result['successful_rows']:,} rows in {file_time:.1f}s")
                if result.get('issues'):
                    print(f"   ⚠️  Issues: {len(result['issues'])} data quality issues found")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            
            # Store file result
            folder_stats['file_results'].append({
                'filename': csv_file.name,
                'success': result.get('success', False),
                'rows_processed': result.get('total_rows_processed', 0),
                'processing_time': file_time,
                'issues_count': len(result.get('issues', [])),
                'error': result.get('error')
            })
        
        folder_stats['total_time'] = time.time() - folder_stats['start_time']
        
        # Update overall stats
        self.total_stats['files_processed'] += folder_stats['files_processed']
        self.total_stats['total_rows'] += folder_stats['total_rows']
        self.total_stats['successful_rows'] += folder_stats['successful_rows']
        self.total_stats['failed_rows'] += folder_stats['failed_rows']
        self.total_stats['total_time'] += folder_stats['total_time']
        
        self.upload_log.append(folder_stats)
        
        # Print folder summary
        print(f"\n📊 Folder Summary:")
        print(f"   Files: {folder_stats['files_processed']}/{folder_stats['files_found']}")
        print(f"   Rows: {folder_stats['successful_rows']:,} successful, {folder_stats['failed_rows']:,} failed")
        print(f"   Time: {folder_stats['total_time']:.1f} seconds")
        print(f"   Speed: {folder_stats['total_rows'] / folder_stats['total_time']:.0f} rows/second")
        
        return folder_stats
    
    def upload_historical_data(self, base_path: str = "csv_folder/historical") -> Dict:
        """Upload historical data following the recommended structure"""
        base_path = Path(base_path)
        
        if not base_path.exists():
            logger.error(f"Historical data path not found: {base_path}")
            return {'success': False, 'error': f'Path not found: {base_path}'}
        
        print(f"🚀 Starting Historical Data Upload")
        print(f"   Base path: {base_path}")
        
        # Create initial backup
        backup_path = self.create_backup("pre_historical_upload")
        
        overall_start = time.time()
        
        # Find all year directories
        year_dirs = [d for d in base_path.iterdir() if d.is_dir() and d.name.isdigit()]
        year_dirs.sort()
        
        if not year_dirs:
            logger.warning(f"No year directories found in {base_path}")
            return {'success': True, 'message': 'No year directories found'}
        
        print(f"   Found years: {[d.name for d in year_dirs]}")
        
        # Process each year
        for year_dir in year_dirs:
            print(f"\n🗓️  Processing Year: {year_dir.name}")
            
            # Create year backup
            year_backup = self.create_backup(f"year_{year_dir.name}_backup")
            
            # Find category directories
            category_dirs = [d for d in year_dir.iterdir() if d.is_dir()]
            category_dirs.sort()
            
            for category_dir in category_dirs:
                print(f"\n📂 Processing Category: {category_dir.name}")
                
                # Upload folder contents
                folder_result = self.upload_folder(category_dir)
                
                # Verify data after each category
                self.verify_upload_quality(year_dir.name, category_dir.name)
        
        # Final summary
        total_time = time.time() - overall_start
        self.total_stats['total_time'] = total_time
        
        self.print_final_summary()
        self.save_upload_report()
        
        return {
            'success': True,
            'stats': self.total_stats,
            'backup_path': backup_path
        }
    
    def verify_upload_quality(self, year: str, category: str) -> Dict:
        """Verify data quality after upload"""
        print(f"🔍 Verifying data quality for {year}/{category}...")
        
        # Basic integrity checks
        checks = {
            'provider_consistency': self.check_provider_consistency(),
            'date_ranges': self.check_date_ranges(year),
            'revenue_totals': self.check_revenue_totals(),
            'duplicate_detection': self.check_duplicates()
        }
        
        issues = [check for check, result in checks.items() if not result['success']]
        
        if issues:
            print(f"   ⚠️  Issues found: {', '.join(issues)}")
        else:
            print(f"   ✅ Quality checks passed")
        
        return checks
    
    def check_provider_consistency(self) -> Dict:
        """Check for provider name consistency"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Look for potential duplicate providers
            cursor.execute("""
                SELECT provider_name, COUNT(*) as count
                FROM providers
                GROUP BY LOWER(provider_name)
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            conn.close()
            
            return {
                'success': len(duplicates) == 0,
                'duplicates_found': len(duplicates),
                'duplicate_names': [name for name, count in duplicates]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_date_ranges(self, year: str) -> Dict:
        """Check for reasonable date ranges"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for dates outside expected year
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM payment_transactions
                WHERE strftime('%Y', transaction_date) != ?
                AND strftime('%Y', transaction_date) IS NOT NULL
            """, (year,))
            
            unexpected_dates = cursor.fetchone()[0]
            conn.close()
            
            return {
                'success': unexpected_dates == 0,
                'unexpected_date_count': unexpected_dates
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_revenue_totals(self) -> Dict:
        """Basic revenue sanity checks"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for negative revenues
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM payment_transactions
                WHERE cash_applied < 0
            """)
            
            negative_revenues = cursor.fetchone()[0]
            
            # Check for extremely large amounts (potential data errors)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM payment_transactions
                WHERE cash_applied > 50000
            """)
            
            large_amounts = cursor.fetchone()[0]
            conn.close()
            
            return {
                'success': negative_revenues == 0 and large_amounts < 5,
                'negative_revenues': negative_revenues,
                'large_amounts': large_amounts
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_duplicates(self) -> Dict:
        """Check for potential duplicate transactions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Look for transactions with same provider, date, and amount
            cursor.execute("""
                SELECT COUNT(*) as duplicate_groups
                FROM (
                    SELECT provider_id, transaction_date, cash_applied, COUNT(*) as cnt
                    FROM payment_transactions
                    GROUP BY provider_id, transaction_date, cash_applied
                    HAVING COUNT(*) > 1
                )
            """)
            
            duplicate_groups = cursor.fetchone()[0]
            conn.close()
            
            return {
                'success': duplicate_groups < 10,  # Allow some duplicates as they might be legitimate
                'duplicate_groups': duplicate_groups
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def print_final_summary(self):
        """Print comprehensive upload summary"""
        stats = self.total_stats
        
        print(f"\n🎉 Historical Data Upload Complete!")
        print(f"=" * 50)
        print(f"📊 Overall Statistics:")
        print(f"   Files Processed: {stats['files_processed']:,}")
        print(f"   Total Rows: {stats['total_rows']:,}")
        print(f"   Successful: {stats['successful_rows']:,} ({stats['successful_rows']/stats['total_rows']*100:.1f}%)")
        print(f"   Failed: {stats['failed_rows']:,} ({stats['failed_rows']/stats['total_rows']*100:.1f}%)")
        print(f"   Total Time: {stats['total_time']:.1f} seconds ({stats['total_time']/60:.1f} minutes)")
        print(f"   Processing Speed: {stats['total_rows']/stats['total_time']:.0f} rows/second")
        
        # Database size
        db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
        print(f"   Database Size: {db_size:.1f} MB")
        
    def save_upload_report(self):
        """Save detailed upload report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"upload_reports/historical_upload_{timestamp}.json"
        
        os.makedirs("upload_reports", exist_ok=True)
        
        report = {
            'timestamp': timestamp,
            'total_stats': self.total_stats,
            'folder_details': self.upload_log,
            'database_path': self.db_path,
            'database_size_mb': os.path.getsize(self.db_path) / (1024 * 1024)
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📋 Detailed report saved: {report_file}")
        
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'db'):
            self.db.close()

def main():
    """Command line interface for bulk upload utility"""
    parser = argparse.ArgumentParser(description='Bulk upload historical medical billing data')
    parser.add_argument('--path', default='csv_folder/historical', 
                       help='Path to historical data folder')
    parser.add_argument('--backup', action='store_true', 
                       help='Create backup before upload')
    parser.add_argument('--single-folder', 
                       help='Upload single folder instead of full historical structure')
    
    args = parser.parse_args()
    
    # Initialize upload manager
    manager = BulkUploadManager()
    
    try:
        if args.single_folder:
            # Upload single folder
            print(f"📁 Uploading single folder: {args.single_folder}")
            result = manager.upload_folder(args.single_folder)
        else:
            # Upload full historical structure
            print(f"🚀 Starting historical data upload from: {args.path}")
            result = manager.upload_historical_data(args.path)
        
        if result['success']:
            print("\n✅ Upload completed successfully!")
        else:
            print(f"\n❌ Upload failed: {result.get('error', 'Unknown error')}")
            
    except KeyboardInterrupt:
        print("\n⏹️  Upload interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        logger.error(f"Bulk upload error: {e}")
    finally:
        manager.close()

if __name__ == "__main__":
    main() 