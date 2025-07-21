#!/usr/bin/env python3
"""
Weekly Upload Workflow for Medical Billing Data

This script provides a streamlined workflow for uploading new weekly/monthly
medical billing reports while maintaining data quality and providing insights.
"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import argparse

from bulk_upload_utility import BulkUploadManager
from advanced_analytics_queries import AdvancedAnalytics
from medical_billing_db import MedicalBillingDB
from utils.logger import get_logger
from utils.config import get_config

logger = get_logger()
config = get_config()

class WeeklyWorkflow:
    """Manages weekly data upload and analysis workflow"""
    
    def __init__(self):
        """Initialize the weekly workflow manager"""
        self.upload_manager = BulkUploadManager()
        self.analytics = AdvancedAnalytics()
        self.db = MedicalBillingDB()
        
    def upload_new_reports(self, reports_folder: str, backup: bool = True) -> Dict:
        """Upload new weekly/monthly reports"""
        
        print(f"🗓️  Weekly Upload Workflow Starting")
        print(f"   Reports folder: {reports_folder}")
        print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Create backup if requested
        if backup:
            backup_path = self.upload_manager.create_backup(
                f"weekly_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            print(f"   Backup created: {backup_path}")
        
        # Upload the reports
        result = self.upload_manager.upload_folder(reports_folder)
        
        if result['success']:
            print(f"\n✅ Upload completed successfully!")
            print(f"   Files processed: {result['files_processed']}")
            print(f"   Rows uploaded: {result['successful_rows']:,}")
            print(f"   Processing time: {result['total_time']:.1f} seconds")
            
            if result['failed_rows'] > 0:
                print(f"   ⚠️  Failed rows: {result['failed_rows']}")
        else:
            print(f"\n❌ Upload failed: {result.get('error', 'Unknown error')}")
            
        return result
    
    def generate_weekly_insights(self) -> Dict:
        """Generate insights for the weekly report"""
        
        print(f"\n📊 Generating Weekly Insights...")
        
        # Get recent activity (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Recent revenue summary
        recent_summary_query = f"""
        SELECT 
            COUNT(*) as recent_transactions,
            SUM(cash_applied) as recent_revenue,
            AVG(cash_applied) as recent_avg_transaction,
            COUNT(DISTINCT provider_id) as recent_active_providers,
            COUNT(DISTINCT payer_name) as recent_payers
        FROM payment_transactions 
        WHERE transaction_date >= '{thirty_days_ago}'
        """
        
        # Provider activity in last 30 days
        provider_activity_query = f"""
        SELECT 
            p.provider_name,
            COUNT(*) as recent_transactions,
            SUM(pt.cash_applied) as recent_revenue,
            MAX(pt.transaction_date) as last_transaction_date
        FROM providers p
        JOIN payment_transactions pt ON p.provider_id = pt.provider_id
        WHERE pt.transaction_date >= '{thirty_days_ago}'
        GROUP BY p.provider_name
        ORDER BY recent_revenue DESC
        """
        
        # Execute queries
        import sqlite3
        import pandas as pd
        
        conn = sqlite3.connect(self.analytics.db_path)
        
        recent_summary = pd.read_sql_query(recent_summary_query, conn)
        provider_activity = pd.read_sql_query(provider_activity_query, conn)
        
        conn.close()
        
        # Format insights
        insights = {
            'period': f"Last 30 days (since {thirty_days_ago})",
            'summary': recent_summary.iloc[0].to_dict() if not recent_summary.empty else {},
            'top_providers': provider_activity.head(5).to_dict('records') if not provider_activity.empty else [],
            'generated_at': datetime.now().isoformat()
        }
        
        # Print key insights
        if not recent_summary.empty:
            summary = recent_summary.iloc[0]
            print(f"   Recent Activity (30 days):")
            print(f"   - Transactions: {summary['recent_transactions']:,}")
            print(f"   - Revenue: ${summary['recent_revenue']:,.2f}")
            print(f"   - Avg Transaction: ${summary['recent_avg_transaction']:.2f}")
            print(f"   - Active Providers: {summary['recent_active_providers']}")
        
        if not provider_activity.empty:
            print(f"\n   Top Performing Providers (30 days):")
            for i, provider in enumerate(provider_activity.head(3).itertuples(), 1):
                print(f"   {i}. {provider.provider_name}: ${provider.recent_revenue:,.2f}")
        
        return insights
    
    def check_data_quality(self) -> Dict:
        """Run data quality checks after upload"""
        
        print(f"\n🔍 Running Data Quality Checks...")
        
        quality_checks = {
            'missing_providers': self._check_missing_providers(),
            'date_anomalies': self._check_date_anomalies(),
            'revenue_anomalies': self._check_revenue_anomalies(),
            'recent_uploads': self._check_recent_uploads()
        }
        
        # Print quality summary
        issues_found = sum(1 for check in quality_checks.values() if not check.get('passed', True))
        
        if issues_found == 0:
            print(f"   ✅ All quality checks passed")
        else:
            print(f"   ⚠️  {issues_found} potential issues found")
            for check_name, check_result in quality_checks.items():
                if not check_result.get('passed', True):
                    print(f"     - {check_name}: {check_result.get('message', 'Issue detected')}")
        
        return quality_checks
    
    def _check_missing_providers(self) -> Dict:
        """Check for transactions with missing provider information"""
        import sqlite3
        
        conn = sqlite3.connect(self.analytics.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as missing_count
            FROM payment_transactions 
            WHERE provider_id IS NULL 
               OR provider_id NOT IN (SELECT provider_id FROM providers)
        """)
        
        missing_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            'passed': missing_count == 0,
            'missing_count': missing_count,
            'message': f"{missing_count} transactions with missing provider info" if missing_count > 0 else "All transactions have valid providers"
        }
    
    def _check_date_anomalies(self) -> Dict:
        """Check for unusual date patterns"""
        import sqlite3
        
        conn = sqlite3.connect(self.analytics.db_path)
        cursor = conn.cursor()
        
        # Check for future dates
        cursor.execute("""
            SELECT COUNT(*) as future_count
            FROM payment_transactions 
            WHERE transaction_date > date('now')
        """)
        
        future_count = cursor.fetchone()[0]
        
        # Check for very old dates (more than 10 years ago)
        cursor.execute("""
            SELECT COUNT(*) as old_count
            FROM payment_transactions 
            WHERE transaction_date < date('now', '-10 years')
        """)
        
        old_count = cursor.fetchone()[0]
        conn.close()
        
        anomalies = future_count + old_count
        
        return {
            'passed': anomalies == 0,
            'future_dates': future_count,
            'old_dates': old_count,
            'message': f"{anomalies} transactions with unusual dates" if anomalies > 0 else "All dates look reasonable"
        }
    
    def _check_revenue_anomalies(self) -> Dict:
        """Check for unusual revenue patterns"""
        import sqlite3
        import pandas as pd
        
        conn = sqlite3.connect(self.analytics.db_path)
        
        # Get revenue statistics
        df = pd.read_sql_query("""
            SELECT cash_applied 
            FROM payment_transactions 
            WHERE cash_applied IS NOT NULL
        """, conn)
        
        conn.close()
        
        if df.empty:
            return {'passed': True, 'message': 'No revenue data to check'}
        
        # Calculate statistics
        mean_revenue = df['cash_applied'].mean()
        std_revenue = df['cash_applied'].std()
        
        # Count outliers (more than 3 standard deviations from mean)
        outliers = df[abs(df['cash_applied'] - mean_revenue) > 3 * std_revenue]
        outlier_count = len(outliers)
        
        # Count negative revenues
        negative_count = len(df[df['cash_applied'] < 0])
        
        total_issues = outlier_count + negative_count
        
        return {
            'passed': total_issues < 10,  # Allow some outliers as they might be legitimate
            'outlier_count': outlier_count,
            'negative_count': negative_count,
            'mean_revenue': mean_revenue,
            'message': f"{total_issues} revenue anomalies detected" if total_issues >= 10 else "Revenue patterns look normal"
        }
    
    def _check_recent_uploads(self) -> Dict:
        """Check recent upload history"""
        import sqlite3
        
        conn = sqlite3.connect(self.analytics.db_path)
        cursor = conn.cursor()
        
        # Check for recent successful uploads
        cursor.execute("""
            SELECT COUNT(*) as recent_uploads
            FROM data_uploads 
            WHERE created_date >= date('now', '-7 days')
              AND status = 'completed'
        """)
        
        recent_uploads = cursor.fetchone()[0]
        conn.close()
        
        return {
            'passed': True,  # This is just informational
            'recent_uploads': recent_uploads,
            'message': f"{recent_uploads} successful uploads in the last 7 days"
        }
    
    def save_weekly_report(self, upload_result: Dict, insights: Dict, quality_checks: Dict) -> str:
        """Save a comprehensive weekly report"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"weekly_reports/weekly_report_{timestamp}.json"
        
        report = {
            'report_date': datetime.now().isoformat(),
            'report_type': 'weekly_upload',
            'upload_results': upload_result,
            'insights': insights,
            'quality_checks': quality_checks,
            'database_stats': {
                'total_transactions': self._get_total_transactions(),
                'total_providers': self._get_total_providers(),
                'database_size_mb': os.path.getsize(self.analytics.db_path) / (1024 * 1024)
            }
        }
        
        # Save report
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📋 Weekly report saved: {report_file}")
        return report_file
    
    def _get_total_transactions(self) -> int:
        """Get total transaction count"""
        import sqlite3
        
        conn = sqlite3.connect(self.analytics.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM payment_transactions")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def _get_total_providers(self) -> int:
        """Get total provider count"""
        import sqlite3
        
        conn = sqlite3.connect(self.analytics.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM providers WHERE active = 1")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def run_complete_workflow(self, reports_folder: str, backup: bool = True) -> Dict:
        """Run the complete weekly workflow"""
        
        workflow_start = time.time()
        
        # Step 1: Upload new reports
        upload_result = self.upload_new_reports(reports_folder, backup)
        
        # Step 2: Generate insights (only if upload was successful)
        if upload_result.get('success', False):
            insights = self.generate_weekly_insights()
            quality_checks = self.check_data_quality()
        else:
            insights = {'error': 'Upload failed, skipping insights'}
            quality_checks = {'error': 'Upload failed, skipping quality checks'}
        
        # Step 3: Save weekly report
        report_file = self.save_weekly_report(upload_result, insights, quality_checks)
        
        # Final summary
        total_time = time.time() - workflow_start
        
        print(f"\n🎉 Weekly Workflow Complete!")
        print(f"   Total time: {total_time:.1f} seconds")
        print(f"   Report saved: {report_file}")
        
        return {
            'success': upload_result.get('success', False),
            'upload_result': upload_result,
            'insights': insights,
            'quality_checks': quality_checks,
            'report_file': report_file,
            'total_time': total_time
        }
    
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'upload_manager'):
            self.upload_manager.close()
        if hasattr(self, 'analytics'):
            self.analytics.close()
        if hasattr(self, 'db'):
            self.db.close()

def main():
    """Command line interface for weekly workflow"""
    parser = argparse.ArgumentParser(description='Weekly medical billing data upload workflow')
    parser.add_argument('reports_folder', help='Path to folder containing new reports')
    parser.add_argument('--no-backup', action='store_true', help='Skip database backup')
    parser.add_argument('--insights-only', action='store_true', help='Generate insights without uploading')
    
    args = parser.parse_args()
    
    workflow = WeeklyWorkflow()
    
    try:
        if args.insights_only:
            # Just generate insights and quality checks
            insights = workflow.generate_weekly_insights()
            quality_checks = workflow.check_data_quality()
            print("\n✅ Insights and quality checks completed")
        else:
            # Run complete workflow
            result = workflow.run_complete_workflow(
                args.reports_folder, 
                backup=not args.no_backup
            )
            
            if result['success']:
                print("\n✅ Weekly workflow completed successfully!")
            else:
                print(f"\n❌ Weekly workflow failed: {result.get('error', 'Unknown error')}")
                
    except KeyboardInterrupt:
        print("\n⏹️  Workflow interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        logger.error(f"Weekly workflow error: {e}")
    finally:
        workflow.close()

if __name__ == "__main__":
    main() 