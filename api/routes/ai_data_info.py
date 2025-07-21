"""
AI Data Information Helpers.

This module provides functions for the AI assistant to gather information about
available data files and database content.
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
from flask import current_app

def get_available_data_files():
    """Get information about available data files in the system.
    
    Returns:
        str: Formatted information about available CSV files
    """
    # Get csv_folder path
    csv_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'csv_folder')
    uploads_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
    
    # Track statistics
    total_files = 0
    files_by_category = {}
    recent_files = []
    
    # Check csv_folder
    if os.path.exists(csv_folder):
        for dirpath, _, filenames in os.walk(csv_folder):
            category = os.path.basename(dirpath)
            if category not in files_by_category:
                files_by_category[category] = []
                
            # Include both .csv and Excel files that might have .csv extension
            potential_data_files = [f for f in filenames if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
            for filename in potential_data_files:
                total_files += 1
                file_path = os.path.join(dirpath, filename)
                file_size = os.path.getsize(file_path)
                mod_time = os.path.getmtime(file_path)
                
                files_by_category[category].append({
                    'name': filename,
                    'path': file_path,
                    'size': file_size,
                    'modified': datetime.fromtimestamp(mod_time)
                })
                
                # Track recent files
                recent_files.append({
                    'name': filename,
                    'path': file_path,
                    'category': category,
                    'size': file_size,
                    'modified': datetime.fromtimestamp(mod_time)
                })
    
    # Check uploads folder
    if os.path.exists(uploads_folder):
        category = "uploads"
        if category not in files_by_category:
            files_by_category[category] = []
            
        for filename in os.listdir(uploads_folder):
            if filename.lower().endswith('.csv'):
                total_files += 1
                file_path = os.path.join(uploads_folder, filename)
                file_size = os.path.getsize(file_path)
                mod_time = os.path.getmtime(file_path)
                
                files_by_category[category].append({
                    'name': filename,
                    'path': file_path,
                    'size': file_size,
                    'modified': datetime.fromtimestamp(mod_time)
                })
                
                # Track recent files
                recent_files.append({
                    'name': filename,
                    'path': file_path,
                    'category': category,
                    'size': file_size,
                    'modified': datetime.fromtimestamp(mod_time)
                })
    
    # Sort recent files by modification time (newest first)
    recent_files.sort(key=lambda x: x['modified'], reverse=True)
    recent_files = recent_files[:5]  # Only show 5 most recent
    
    # Create formatted response
    response = f"I can work with {total_files} data files in the system. "
    
    if total_files == 0:
        response += "No data files have been uploaded yet. You can upload CSV or Excel files through the Upload page."
        return response
    
    # Add category breakdown
    response += "These files are organized into the following categories:\n\n"
    for category, files in files_by_category.items():
        if files:
            response += f"- {category}: {len(files)} files\n"
    
    # Add recent files
    if recent_files:
        response += "\nThe most recently modified files are:\n"
        for i, file in enumerate(recent_files, 1):
            size_kb = file['size'] / 1024
            response += f"{i}. {file['name']} ({file['category']}, {size_kb:.1f} KB, modified {file['modified'].strftime('%Y-%m-%d')})\n"
    
    # Add usage hint
    response += "\nYou can view, preview, and import these files through the Upload page, in the 'Browse CSV Folder' tab."
    response += "\nNote: Some files with .csv extension are actually Excel files and need to be converted to true CSV format before importing."
    response += "\nFor analysis, you can ask questions about providers, revenue, payer comparisons, and data quality based on the imported data."
    
    # Add specific information about billing data if it exists
    if 'billing' in files_by_category and files_by_category['billing']:
        billing_count = len(files_by_category['billing'])
        response += f"\n\nI noticed you have {billing_count} billing files in the billing folder. These files contain payment transaction data, including credit card co-pays and insurance claims."
    
    return response

def get_database_summary():
    """Get a summary of the database content.
    
    Returns:
        str: Formatted information about database tables and record counts
    """
    try:
        # Connect to database
        db_path = current_app.config.get('DATABASE_PATH', 'medical_billing.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get record counts for each table
        table_counts = {}
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count
            except:
                table_counts[table] = "Error counting"
        
        # Close connection
        conn.close()
        
        # Create formatted response
        response = "The database contains the following tables:\n\n"
        for table, count in table_counts.items():
            response += f"- {table}: {count} records\n"
        
        # Add more details for key tables
        if 'providers' in table_counts and table_counts['providers'] > 0:
            conn = sqlite3.connect(db_path)
            providers_df = pd.read_sql_query("SELECT * FROM providers LIMIT 5", conn)
            conn.close()
            
            provider_names = providers_df['provider_name'].tolist()
            provider_sample = ", ".join(provider_names)
            
            response += f"\nProviders include: {provider_sample}, and others."
        
        if 'payment_transactions' in table_counts and table_counts['payment_transactions'] > 0:
            conn = sqlite3.connect(db_path)
            try:
                # Get date range
                date_query = "SELECT MIN(transaction_date), MAX(transaction_date) FROM payment_transactions"
                cursor = conn.cursor()
                cursor.execute(date_query)
                min_date, max_date = cursor.fetchone()
                
                # Get payer summary
                payer_query = "SELECT payer_name, COUNT(*) FROM payment_transactions GROUP BY payer_name ORDER BY COUNT(*) DESC LIMIT 3"
                payers_df = pd.read_sql_query(payer_query, conn)
                payer_summary = ", ".join([f"{row['payer_name']} ({row[1]} transactions)" for _, row in payers_df.iterrows()])
                
                response += f"\nTransaction data spans from {min_date} to {max_date}."
                response += f"\nTop payers include: {payer_summary}"
            except:
                pass
            finally:
                conn.close()
        
        return response
    
    except Exception as e:
        return f"Unable to retrieve database summary: {str(e)}"