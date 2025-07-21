"""
Files API Routes.

This module provides API endpoints for file operations.
"""

import os
import time
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.exceptions import BadRequest, NotFound
from werkzeug.utils import secure_filename

from api.utils.db import get_db_connection

# Try to import format detection modules
try:
    from utils.format_detector import ReportFormatDetector
    from utils.report_transformer import ReportTransformer
    from utils.import_helper import ImportHelper
    FORMAT_DETECTION_AVAILABLE = True
except ImportError:
    FORMAT_DETECTION_AVAILABLE = False

# Create Blueprint
files_bp = Blueprint('files', __name__)

def allowed_file(filename):
    """Check if a file has an allowed extension.
    
    Args:
        filename: Name of the file to check.
        
    Returns:
        True if file extension is allowed, False otherwise.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@files_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload a file.
    
    Returns:
        JSON response with uploaded file information.
    """
    # Check if the post request has the file part
    if 'file' not in request.files:
        raise BadRequest('No file part')
    
    file = request.files['file']
    
    # If user does not select file, browser also submits an empty part without filename
    if file.filename == '':
        raise BadRequest('No selected file')
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Get file metadata
        file_info = {
            'filename': filename,
            'original_filename': file.filename,
            'path': file_path,
            'size': os.path.getsize(file_path),
            'mime_type': file.content_type,
            'upload_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # For CSV files, try to detect format if available
        if filename.lower().endswith('.csv') and FORMAT_DETECTION_AVAILABLE:
            try:
                detector = ReportFormatDetector()
                format_info = detector.detect_format(file_path)
                file_info['format_detection'] = format_info
            except Exception as e:
                current_app.logger.error(f"Error detecting format: {e}")
                file_info['format_detection_error'] = str(e)
        
        return jsonify({
            'success': True,
            'file': file_info
        })
    
    raise BadRequest('File type not allowed')


@files_bp.route('/detect-format', methods=['POST'])
def detect_format():
    """Detect format of a CSV file.
    
    Returns:
        JSON response with format detection results.
    """
    if not FORMAT_DETECTION_AVAILABLE:
        raise BadRequest('Format detection not available')
    
    # Check if the post request has the file part
    if 'file' not in request.files:
        raise BadRequest('No file part')
    
    file = request.files['file']
    
    # If user does not select file, browser also submits an empty part without filename
    if file.filename == '':
        raise BadRequest('No selected file')
    
    if file and file.filename.lower().endswith('.csv'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            detector = ReportFormatDetector()
            format_info = detector.detect_format(file_path)
            return jsonify(format_info)
        except Exception as e:
            current_app.logger.error(f"Error detecting format: {e}")
            raise BadRequest(f"Error detecting format: {str(e)}")
    
    raise BadRequest('File must be a CSV')


@files_bp.route('/import', methods=['POST'])
def import_file():
    """Import a CSV file into the database.
    
    Request JSON:
        {
            "file_path": "/path/to/file.csv",
            "format_name": "Blue Cross" (optional)
        }
        
    Returns:
        JSON response with import results.
    """
    data = request.get_json()
    
    if not data or 'file_path' not in data:
        raise BadRequest("Missing 'file_path' parameter")
    
    file_path = data['file_path']
    format_name = data.get('format_name')
    
    if not os.path.exists(file_path):
        raise NotFound(f"File not found: {file_path}")
    
    if not file_path.lower().endswith('.csv'):
        raise BadRequest('File must be a CSV')
    
    try:
        # Use format detection if available
        if FORMAT_DETECTION_AVAILABLE:
            import_helper = ImportHelper(db_path=current_app.config['DATABASE_PATH'])
            result = import_helper.import_file(file_path, format_name)
            return jsonify({
                'success': True,
                'result': result
            })
        else:
            # Fall back to basic import
            from medical_billing_db import MedicalBillingDB
            db = MedicalBillingDB(db_path=current_app.config['DATABASE_PATH'])
            result = db.upload_csv_file(file_path)
            return jsonify({
                'success': True,
                'result': result
            })
    except Exception as e:
        current_app.logger.error(f"Error importing file: {e}")
        raise BadRequest(f"Error importing file: {str(e)}")


@files_bp.route('/transform', methods=['POST'])
def transform_file():
    """Transform a CSV file to canonical format.
    
    Request JSON:
        {
            "file_path": "/path/to/file.csv",
            "format_name": "Blue Cross" (optional)
        }
        
    Returns:
        JSON response with transformation results.
    """
    if not FORMAT_DETECTION_AVAILABLE:
        raise BadRequest('Format transformation not available')
    
    data = request.get_json()
    
    if not data or 'file_path' not in data:
        raise BadRequest("Missing 'file_path' parameter")
    
    file_path = data['file_path']
    format_name = data.get('format_name')
    
    if not os.path.exists(file_path):
        raise NotFound(f"File not found: {file_path}")
    
    if not file_path.lower().endswith('.csv'):
        raise BadRequest('File must be a CSV')
    
    try:
        transformer = ReportTransformer()
        result_df, metadata = transformer.transform(file_path, format_name)
        
        # Save transformed file
        base_name = os.path.basename(file_path)
        name_parts = os.path.splitext(base_name)
        transformed_filename = f"{name_parts[0]}_transformed{name_parts[1]}"
        transformed_path = os.path.join(current_app.config['UPLOAD_FOLDER'], transformed_filename)
        
        result_df.to_csv(transformed_path, index=False)
        
        return jsonify({
            'success': True,
            'metadata': metadata,
            'transformed_file': transformed_path,
            'columns': list(result_df.columns),
            'row_count': len(result_df)
        })
    except Exception as e:
        current_app.logger.error(f"Error transforming file: {e}")
        raise BadRequest(f"Error transforming file: {str(e)}")


@files_bp.route('/list', methods=['GET'])
def list_files():
    """List uploaded files.
    
    Returns:
        JSON response with list of uploaded files.
    """
    folder = current_app.config['UPLOAD_FOLDER']
    
    if not os.path.exists(folder):
        return jsonify({'files': []})
    
    files = []
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            files.append({
                'filename': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'modified': time.ctime(os.path.getmtime(file_path))
            })
    
    return jsonify({'files': files})


@files_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download a file.
    
    Args:
        filename: Name of the file to download.
        
    Returns:
        File for download.
    """
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=True
    )