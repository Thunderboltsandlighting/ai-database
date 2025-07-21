"""
Files Bridge API Routes.

This module provides API endpoints to access and import files from the csv_folder directory.
"""

import os
import time
import json
import csv
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.exceptions import BadRequest, NotFound

# Import the database module
from medical_billing_db import MedicalBillingDB

# Create Blueprint
files_bridge_bp = Blueprint('files_bridge', __name__)

@files_bridge_bp.route('/csv-folder', methods=['GET'])
def list_csv_folder():
    """List files in the csv_folder directory structure.
    
    Returns:
        JSON response with list of CSV files.
    """
    csv_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'csv_folder')
    
    if not os.path.exists(csv_folder):
        return jsonify({'folders': [], 'files': []})
    
    folders = []
    all_files = []
    
    # Walk through directory structure
    for dirpath, dirnames, filenames in os.walk(csv_folder):
        # Get relative path from csv_folder
        rel_path = os.path.relpath(dirpath, csv_folder)
        if rel_path != '.':  # Skip root folder
            folders.append({
                'name': os.path.basename(dirpath),
                'path': rel_path,
                'full_path': dirpath
            })
        
        # List CSV files in this directory
        csv_files = [f for f in filenames if f.lower().endswith('.csv')]
        for filename in csv_files:
            file_path = os.path.join(dirpath, filename)
            all_files.append({
                'name': filename,
                'folder': rel_path if rel_path != '.' else '',
                'path': os.path.join(rel_path, filename) if rel_path != '.' else filename,
                'full_path': file_path,
                'size': os.path.getsize(file_path),
                'modified': time.ctime(os.path.getmtime(file_path))
            })
    
    return jsonify({
        'folders': folders,
        'files': all_files
    })

@files_bridge_bp.route('/import-csv-file', methods=['POST'])
def import_csv_file():
    """Import a CSV file from the csv_folder directory.
    
    Request JSON:
        {
            "file_path": "/path/to/file.csv"
        }
        
    Returns:
        JSON response with import results.
    """
    data = request.get_json()
    
    if not data or 'file_path' not in data:
        raise BadRequest("Missing 'file_path' parameter")
    
    file_path = data['file_path']
    
    if not os.path.exists(file_path):
        raise NotFound(f"File not found: {file_path}")
    
    if not file_path.lower().endswith('.csv'):
        raise BadRequest('File must be a CSV')
    
    try:
        # Use the MedicalBillingDB to import the file
        db = MedicalBillingDB(db_path=current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
        result = db.upload_csv_file(file_path)
        
        # Clean up result for JSON serialization
        serializable_result = {
            'success': True,
            'filename': os.path.basename(file_path),
            'records_processed': result.get('total_records', 0),
            'records_successful': result.get('successful', 0),
            'records_failed': result.get('failed', 0),
            'issues_count': len(result.get('issues', []))
        }
        
        return jsonify(serializable_result)
        
    except Exception as e:
        current_app.logger.error(f"Error importing file: {e}")
        raise BadRequest(f"Error importing file: {str(e)}")

@files_bridge_bp.route('/preview-csv-file', methods=['POST'])
def preview_csv_file():
    """Preview contents of a CSV file from the csv_folder.
    
    Request JSON:
        {
            "file_path": "/path/to/file.csv",
            "max_rows": 10
        }
        
    Returns:
        JSON with CSV preview data.
    """
    data = request.get_json()
    
    if not data or 'file_path' not in data:
        raise BadRequest("Missing 'file_path' parameter")
    
    file_path = data['file_path']
    max_rows = int(data.get('max_rows', 10))
    
    if not os.path.exists(file_path):
        raise NotFound(f"File not found: {file_path}")
    
    if not file_path.lower().endswith('.csv'):
        raise BadRequest('File must be a CSV')
    
    try:
        import pandas as pd
        
        # Read the first few rows of the CSV file
        df = pd.read_csv(file_path, nrows=max_rows)
        
        # Convert to JSON-serializable format
        headers = df.columns.tolist()
        rows = df.values.tolist()
        
        # Detect format
        format_detection = detect_csv_format(df, file_path)
        
        return jsonify({
            'headers': headers,
            'rows': rows,
            'total_rows': len(pd.read_csv(file_path, nrows=0)),
            'filename': os.path.basename(file_path),
            'format_detection': format_detection
        })
        
    except Exception as e:
        current_app.logger.error(f"Error previewing file: {e}")
        raise BadRequest(f"Error previewing file: {str(e)}")


def detect_csv_format(df, file_path):
    """Detect the format of a CSV file.
    
    Args:
        df: Pandas DataFrame with CSV data
        file_path: Path to CSV file
        
    Returns:
        dict: Format detection results
    """
    try:
        headers = df.columns.tolist()
        headers_lower = [h.lower() for h in headers]
        file_name = os.path.basename(file_path).lower()
        
        # Detect format based on headers and filename
        if any(term in file_name for term in ['provider', 'doctor', 'physician']):
            format_score = 30
        else:
            format_score = 0
            
        if any(h in headers_lower for h in ['provider', 'provider_name', 'doctor', 'physician']):
            format_type = 'Provider Information'
            format_score += 60
        elif any(h in headers_lower for h in ['payment', 'transaction', 'claim', 'amount', 'cash', 'payer']):
            format_type = 'Payment Transaction'
            format_score += 60
        elif any(h in headers_lower for h in ['monthly', 'summary', 'period', 'month']):
            format_type = 'Monthly Summary'
            format_score += 60
        else:
            # Try deeper analysis of column contents
            if 'provider' in headers_lower and 'name' in headers_lower:
                format_type = 'Provider Information'
                format_score += 40
            elif 'amount' in headers_lower or 'payment' in headers_lower:
                format_type = 'Payment Transaction'
                format_score += 40
            elif 'month' in headers_lower or 'date' in headers_lower:
                format_type = 'Monthly Summary'
                format_score += 40
            else:
                format_type = 'Unknown'
                format_score = 20
        
        # Cap confidence at 95%
        confidence = min(format_score, 95)
        
        return {
            'format': format_type,
            'confidence': confidence,
            'delimiter': ',',
            'hasHeader': True,
            'recommended_table': format_type.lower().replace(' ', '_')
        }
    except Exception as e:
        current_app.logger.error(f"Error detecting CSV format: {e}")
        return {
            'format': 'Unknown',
            'confidence': 0,
            'error': str(e)
        }