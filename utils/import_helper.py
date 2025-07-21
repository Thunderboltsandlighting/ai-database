"""
CSV Import Helper for HVLC_DB

This module integrates the format detection and transformation systems
with the database import functionality, allowing automatic processing
of various CSV formats.
"""

import os
import sys
import json
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import time
from datetime import datetime
from pathlib import Path

from utils.config import get_config
from utils.logger import get_logger
from utils.format_detector import ReportFormatDetector, FormatDetectionResult
from utils.report_transformer import ReportTransformer
from medical_billing_db import MedicalBillingDB

# Configure logging
logger = get_logger()
config = get_config()


class ImportHelper:
    """Helper for importing CSV files into the database"""
    
    def __init__(self, db_path: str = None):
        """Initialize import helper
        
        Args:
            db_path: Path to database file
        """
        self.detector = ReportFormatDetector()
        self.transformer = ReportTransformer(self.detector)
        self.db = MedicalBillingDB(db_path)
        
    def import_file(self, file_path: str, format_name: str = None, 
                   chunk_size: int = None) -> Dict:
        """Import a CSV file into the database
        
        Args:
            file_path: Path to CSV file
            format_name: Optional format name (detected if not provided)
            chunk_size: Number of rows to process in each chunk
            
        Returns:
            Dictionary with import results
        """
        logger.info(f"Importing file {file_path}")
        
        start_time = time.time()
        
        # Detect format if not provided
        if not format_name:
            detection_result = self.detector.detect_format(file_path)
            format_name = detection_result.format_name
            
            if not format_name:
                error_msg = f"Could not detect format for {file_path}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "file_path": file_path,
                    "elapsed_time": time.time() - start_time
                }
                
            logger.info(f"Detected format: {format_name} (confidence: {detection_result.confidence:.2f})")
            
        # Transform the file
        df, transform_metadata = self.transformer.transform(file_path, format_name)
        
        if df.empty:
            error_msg = f"Transformation failed: {transform_metadata.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "file_path": file_path,
                "format": format_name,
                "transformation": transform_metadata,
                "elapsed_time": time.time() - start_time
            }
            
        # Validate transformation
        if transform_metadata.get("validation_errors"):
            logger.warning(f"Transformation had {len(transform_metadata['validation_errors'])} validation errors")
            for error in transform_metadata["validation_errors"]:
                logger.warning(f"  {error['message']}")
                
        # Import into database
        try:
            import_result = self.db.upload_csv_data(df, os.path.basename(file_path))
            
            # Add metadata
            import_result["file_path"] = file_path
            import_result["format"] = format_name
            import_result["transformation"] = transform_metadata
            import_result["elapsed_time"] = time.time() - start_time
            
            return import_result
            
        except Exception as e:
            logger.error(f"Error importing file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "format": format_name,
                "transformation": transform_metadata,
                "elapsed_time": time.time() - start_time
            }
            
    def import_directory(self, directory_path: str, 
                        recursive: bool = False,
                        extensions: List[str] = None) -> Dict:
        """Import all CSV files in a directory
        
        Args:
            directory_path: Path to directory
            recursive: Whether to search subdirectories
            extensions: List of file extensions to import (default: ['.csv'])
            
        Returns:
            Dictionary with import results
        """
        logger.info(f"Importing files from directory {directory_path} (recursive: {recursive})")
        
        extensions = extensions or ['.csv']
        start_time = time.time()
        
        # Find all files
        files = []
        if recursive:
            for root, _, filenames in os.walk(directory_path):
                for filename in filenames:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in extensions:
                        files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(directory_path):
                ext = os.path.splitext(filename)[1].lower()
                if ext in extensions:
                    files.append(os.path.join(directory_path, filename))
                    
        if not files:
            logger.warning(f"No matching files found in {directory_path}")
            return {
                "success": True,
                "files_found": 0,
                "files_imported": 0,
                "elapsed_time": time.time() - start_time
            }
            
        logger.info(f"Found {len(files)} files to import")
        
        # Import each file
        results = []
        successful = 0
        
        for file_path in files:
            result = self.import_file(file_path)
            results.append(result)
            
            if result.get("success", False):
                successful += 1
                
        # Compile summary
        summary = {
            "success": True,
            "files_found": len(files),
            "files_imported": successful,
            "failed_imports": len(files) - successful,
            "results": results,
            "elapsed_time": time.time() - start_time
        }
        
        logger.info(f"Import complete: {successful}/{len(files)} files successfully imported")
        
        return summary
        
    def close(self):
        """Close database connection"""
        self.db.close()


def import_file(file_path: str, format_name: str = None) -> Dict:
    """Utility function to import a file
    
    Args:
        file_path: Path to CSV file
        format_name: Optional format name
        
    Returns:
        Import results dictionary
    """
    helper = ImportHelper()
    try:
        return helper.import_file(file_path, format_name)
    finally:
        helper.close()


def import_directory(directory_path: str, recursive: bool = False) -> Dict:
    """Utility function to import a directory
    
    Args:
        directory_path: Path to directory
        recursive: Whether to search subdirectories
        
    Returns:
        Import results dictionary
    """
    helper = ImportHelper()
    try:
        return helper.import_directory(directory_path, recursive)
    finally:
        helper.close()


def main():
    """Command-line interface for CSV import"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import CSV files into the database")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Import file command
    file_parser = subparsers.add_parser("file", help="Import a single file")
    file_parser.add_argument("file_path", help="Path to CSV file")
    file_parser.add_argument("-f", "--format", help="Format name (detected if not provided)")
    
    # Import directory command
    dir_parser = subparsers.add_parser("directory", help="Import all CSV files in a directory")
    dir_parser.add_argument("directory_path", help="Path to directory")
    dir_parser.add_argument("-r", "--recursive", action="store_true", help="Search subdirectories")
    
    args = parser.parse_args()
    
    if args.command == "file":
        result = import_file(args.file_path, args.format)
        
        if result.get("success", False):
            print(f"Successfully imported {args.file_path}")
            print(f"Format: {result.get('format', 'Unknown')}")
            print(f"Records: {result.get('total_records', 0)} total, {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
            
            if result.get("issues"):
                print(f"Issues found: {len(result['issues'])}")
                for issue in result["issues"][:5]:  # Show first 5 issues
                    print(f"  {issue.get('type')}: {issue.get('description')}")
                if len(result["issues"]) > 5:
                    print(f"  ... and {len(result['issues']) - 5} more issues")
        else:
            print(f"Failed to import {args.file_path}")
            print(f"Error: {result.get('error', 'Unknown error')}")
            
    elif args.command == "directory":
        result = import_directory(args.directory_path, args.recursive)
        
        if result.get("success", False):
            print(f"Import summary for {args.directory_path}:")
            print(f"Files found: {result.get('files_found', 0)}")
            print(f"Files imported: {result.get('files_imported', 0)}")
            print(f"Failed imports: {result.get('failed_imports', 0)}")
            print(f"Elapsed time: {result.get('elapsed_time', 0):.2f} seconds")
            
            if result.get("failed_imports", 0) > 0:
                print("\nFailed imports:")
                for file_result in result.get("results", []):
                    if not file_result.get("success", False):
                        print(f"  {file_result.get('file_path')}: {file_result.get('error', 'Unknown error')}")
        else:
            print(f"Import failed")
            print(f"Error: {result.get('error', 'Unknown error')}")
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()