"""
Quality check script for HVLC_DB

This script provides a command-line interface for running quality checks,
generating reports, and viewing trends.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
import sqlite3
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_quality_monitor import (
    DataQualityMonitor, MissingValuesRule, NegativeValuesRule, 
    OutlierRule, PatternMatchRule, CompletenessRule, ForeignKeyRule
)
from utils.config import get_config
from utils.logger import get_logger

# Configure logging
logger = get_logger()
config = get_config()

def list_tables(monitor: DataQualityMonitor) -> None:
    """List all tables in the database
    
    Args:
        monitor: DataQualityMonitor instance
    """
    if monitor.conn is None:
        print("Error: No database connection")
        return
        
    try:
        cursor = monitor.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("No tables found in the database")
            return
            
        print(f"Found {len(tables)} tables:")
        for table in tables:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            
            print(f"- {table} ({row_count} rows)")
            
    except Exception as e:
        print(f"Error listing tables: {e}")

def check_table(monitor: DataQualityMonitor, table: str, verbose: bool = False) -> None:
    """Check data quality for a table
    
    Args:
        monitor: DataQualityMonitor instance
        table: Table name
        verbose: Whether to print verbose output
    """
    if monitor.conn is None:
        print("Error: No database connection")
        return
        
    print(f"Checking table: {table}")
    
    # Create standard rules
    rules = monitor.create_standard_rules(table)
    
    if not rules:
        print(f"No rules created for table {table}")
        return
        
    print(f"Created {len(rules)} rules")
    
    if verbose:
        for rule in rules:
            print(f"- {rule.name}: {rule.description}")
            
    # Run quality check
    check = monitor.check_table(table, rules)
    
    if not check.violations:
        print(f"No data quality issues found in {table}")
        return
        
    # Print violations
    print(f"Found {len(check.violations)} data quality issues:")
    
    for rule in check.violations:
        print(f"\n{'-' * 80}")
        print(f"Rule: {rule.name}")
        print(f"Description: {rule.description}")
        print(f"Severity: {rule.severity}")
        print(f"Details: {json.dumps(rule.details, indent=2)}")
        print(f"Remediation: {rule.get_remediation()}")

def generate_report(monitor: DataQualityMonitor, days: int = 7, output: str = None) -> None:
    """Generate quality report
    
    Args:
        monitor: DataQualityMonitor instance
        days: Number of days to include
        output: Output file path
    """
    print(f"Generating quality report for the last {days} days...")
    
    report_path = monitor.generate_quality_report(days=days, report_path=output)
    
    if report_path:
        print(f"Report generated: {report_path}")
    else:
        print("Failed to generate report")

def show_trend(monitor: DataQualityMonitor, table: str, column: str, statistic: str = "count", 
              days: int = 30, output: str = None) -> None:
    """Show trend for a statistic
    
    Args:
        monitor: DataQualityMonitor instance
        table: Table name
        column: Column name
        statistic: Statistic to show
        days: Number of days to include
        output: Output file path
    """
    print(f"Generating trend chart for {table}.{column}.{statistic} for the last {days} days...")
    
    chart_path = monitor.generate_trend_chart(table, column, statistic, days, output)
    
    if chart_path:
        print(f"Chart generated: {chart_path}")
    else:
        print("Failed to generate chart")

def check_all_tables(monitor: DataQualityMonitor, verbose: bool = False) -> None:
    """Check all tables
    
    Args:
        monitor: DataQualityMonitor instance
        verbose: Whether to print verbose output
    """
    print("Checking all tables...")
    
    results = monitor.check_all_tables()
    
    if not results:
        print("No tables checked")
        return
        
    # Count violations
    total_tables = len(results)
    tables_with_violations = sum(1 for check in results.values() if check.violations)
    total_violations = sum(len(check.violations) for check in results.values())
    
    print(f"Checked {total_tables} tables, found {total_violations} violations in {tables_with_violations} tables")
    
    if verbose:
        for table, check in results.items():
            if check.violations:
                print(f"\n{'-' * 80}")
                print(check.get_summary())

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Data Quality Check Tool")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List tables
    list_parser = subparsers.add_parser("list", help="List all tables")
    
    # Check table
    check_parser = subparsers.add_parser("check", help="Check data quality for a table")
    check_parser.add_argument("table", help="Table name")
    check_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    # Check all tables
    check_all_parser = subparsers.add_parser("check-all", help="Check all tables")
    check_all_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    # Generate report
    report_parser = subparsers.add_parser("report", help="Generate quality report")
    report_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days to include")
    report_parser.add_argument("-o", "--output", help="Output file path")
    
    # Show trend
    trend_parser = subparsers.add_parser("trend", help="Show trend for a statistic")
    trend_parser.add_argument("table", help="Table name")
    trend_parser.add_argument("column", help="Column name")
    trend_parser.add_argument("-s", "--statistic", default="count", help="Statistic to show")
    trend_parser.add_argument("-d", "--days", type=int, default=30, help="Number of days to include")
    trend_parser.add_argument("-o", "--output", help="Output file path")
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = DataQualityMonitor()
    
    if args.command == "list":
        list_tables(monitor)
    elif args.command == "check":
        check_table(monitor, args.table, args.verbose)
    elif args.command == "check-all":
        check_all_tables(monitor, args.verbose)
    elif args.command == "report":
        generate_report(monitor, args.days, args.output)
    elif args.command == "trend":
        show_trend(monitor, args.table, args.column, args.statistic, args.days, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()