"""
Logger configuration for HVLC_DB.

Provides a unified logging setup for the entire application.
"""

import os
import logging
import sys
from pathlib import Path
from datetime import datetime
from utils.config import get_config

# Global logger instance
_logger = None

def get_logger(name=None):
    """Get configured logger instance
    
    Args:
        name: Logger name (default: __name__)
        
    Returns:
        Configured logger instance
    """
    global _logger
    
    # Return existing logger if already configured
    if _logger is not None:
        return _logger
    
    # Get configuration
    config = get_config()
    log_level_str = config.get("logging.level", "INFO")
    log_dir = config.get("paths.log_dir", "logs")
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Map string log level to constant
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"hvlc_db_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create and configure logger
    logger_name = name or 'hvlc_db'
    _logger = logging.getLogger(logger_name)
    _logger.setLevel(log_level)
    
    # Set lower level for third-party loggers
    for logger_name in ['httpx', 'urllib3', 'sqlalchemy']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    _logger.info(f"Logger initialized with level {log_level_str}")
    
    return _logger


def log_query(query, result=None, error=None):
    """Log a query to the query log file
    
    Args:
        query: The query string
        result: Optional result data
        error: Optional error message
    """
    logger = get_logger()
    config = get_config()
    query_log_path = config.get("logging.query_log")
    
    if not query_log_path:
        logger.warning("Query log path not configured")
        return
    
    try:
        # Create log entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] QUERY: {query}\n"
        
        if error:
            log_entry += f"ERROR: {error}\n"
        elif result:
            # Truncate result if too long
            result_str = str(result)
            if len(result_str) > 500:
                result_str = result_str[:500] + "... [truncated]"
            log_entry += f"RESULT: {result_str}\n"
        
        log_entry += "-" * 80 + "\n"
        
        # Append to log file
        with open(query_log_path, 'a') as f:
            f.write(log_entry)
            
    except Exception as e:
        logger.error(f"Failed to log query: {e}")


def log_clarification(term, column):
    """Log a term clarification to the clarification log file
    
    Args:
        term: The ambiguous term
        column: The mapped database column
    """
    logger = get_logger()
    config = get_config()
    clarification_log_path = config.get("logging.clarification_log")
    
    if not clarification_log_path:
        logger.warning("Clarification log path not configured")
        return
    
    try:
        # Create log entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] CLARIFICATION: '{term}' → '{column}'\n"
        
        # Append to log file
        with open(clarification_log_path, 'a') as f:
            f.write(log_entry)
            
    except Exception as e:
        logger.error(f"Failed to log clarification: {e}")


def log_data_quality_issue(table, column, issue, count=None):
    """Log a data quality issue
    
    Args:
        table: The table name
        column: The column name
        issue: Description of the issue
        count: Optional count of affected rows
    """
    logger = get_logger()
    config = get_config()
    data_quality_log_path = config.get("logging.data_quality_log")
    
    if not data_quality_log_path:
        logger.warning("Data quality log path not configured")
        return
    
    try:
        # Create log entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {table}.{column}: {issue}"
        
        if count is not None:
            log_entry += f" ({count} rows affected)"
        
        log_entry += "\n"
        
        # Append to log file
        with open(data_quality_log_path, 'a') as f:
            f.write(log_entry)
            
    except Exception as e:
        logger.error(f"Failed to log data quality issue: {e}")


def get_quality_logger():
    """Compatibility function for medical_billing_ai.py
    
    Returns:
        Standard logger with the same interface
    """
    return get_logger()