"""
Input validation utility for HVLC_DB.

This module provides robust input validation functions for command-line input,
API parameters, and file operations.
"""

import os
import re
import json
import logging
import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from pathlib import Path

from utils.logger import get_logger

logger = get_logger()


class ValidationError(Exception):
    """Exception raised for input validation errors"""
    pass


def validate_path(path: str, must_exist: bool = True, 
                 must_be_file: bool = False, must_be_dir: bool = False,
                 file_extensions: List[str] = None) -> str:
    """Validate a file or directory path
    
    Args:
        path: Path to validate
        must_exist: Whether the path must exist
        must_be_file: Whether the path must be a file
        must_be_dir: Whether the path must be a directory
        file_extensions: List of allowed file extensions
        
    Returns:
        Validated path (normalized)
        
    Raises:
        ValidationError: If validation fails
    """
    if not path:
        raise ValidationError("Path cannot be empty")
    
    # Normalize path
    try:
        normalized_path = os.path.normpath(os.path.expanduser(path))
    except Exception as e:
        raise ValidationError(f"Invalid path format: {e}")
    
    # Check if path exists
    if must_exist and not os.path.exists(normalized_path):
        raise ValidationError(f"Path does not exist: {normalized_path}")
    
    # Check if path is a file
    if must_be_file and not os.path.isfile(normalized_path):
        raise ValidationError(f"Path is not a file: {normalized_path}")
    
    # Check if path is a directory
    if must_be_dir and not os.path.isdir(normalized_path):
        raise ValidationError(f"Path is not a directory: {normalized_path}")
    
    # Check file extension
    if file_extensions and must_be_file:
        _, ext = os.path.splitext(normalized_path)
        if ext.lower() not in file_extensions:
            raise ValidationError(f"File must have one of these extensions: {', '.join(file_extensions)}")
    
    return normalized_path


def validate_csv_path(path: str, must_exist: bool = True) -> str:
    """Validate a CSV file path
    
    Args:
        path: Path to validate
        must_exist: Whether the file must exist
        
    Returns:
        Validated path
        
    Raises:
        ValidationError: If validation fails
    """
    return validate_path(
        path, 
        must_exist=must_exist, 
        must_be_file=True, 
        file_extensions=['.csv']
    )


def validate_date(date_str: str, 
                 format_str: str = "%Y-%m-%d", 
                 min_date: str = None, 
                 max_date: str = None) -> str:
    """Validate a date string
    
    Args:
        date_str: Date string to validate
        format_str: Expected date format
        min_date: Minimum allowed date (same format as format_str)
        max_date: Maximum allowed date (same format as format_str)
        
    Returns:
        Validated date string
        
    Raises:
        ValidationError: If validation fails
    """
    if not date_str:
        raise ValidationError("Date cannot be empty")
    
    try:
        date = datetime.datetime.strptime(date_str, format_str)
    except ValueError as e:
        raise ValidationError(f"Invalid date format. Expected format: {format_str}")
    
    if min_date:
        min_date_obj = datetime.datetime.strptime(min_date, format_str)
        if date < min_date_obj:
            raise ValidationError(f"Date must be after {min_date}")
    
    if max_date:
        max_date_obj = datetime.datetime.strptime(max_date, format_str)
        if date > max_date_obj:
            raise ValidationError(f"Date must be before {max_date}")
    
    return date_str


def validate_choice(choice: str, options: List[str], 
                   case_sensitive: bool = False) -> str:
    """Validate a choice from a list of options
    
    Args:
        choice: Choice to validate
        options: List of valid options
        case_sensitive: Whether comparison is case-sensitive
        
    Returns:
        Validated choice
        
    Raises:
        ValidationError: If validation fails
    """
    if not choice:
        raise ValidationError("Choice cannot be empty")
    
    compare_choice = choice if case_sensitive else choice.lower()
    compare_options = options if case_sensitive else [opt.lower() for opt in options]
    
    if compare_choice not in compare_options:
        raise ValidationError(f"Invalid choice. Must be one of: {', '.join(options)}")
    
    # Return the original-cased version from options
    if not case_sensitive:
        for option in options:
            if option.lower() == compare_choice:
                return option
    
    return choice


def validate_int(value: str, min_value: int = None, 
                max_value: int = None) -> int:
    """Validate an integer
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Validated integer
        
    Raises:
        ValidationError: If validation fails
    """
    if not value and value != 0:
        raise ValidationError("Value cannot be empty")
    
    try:
        int_value = int(value)
    except ValueError:
        raise ValidationError(f"Value must be an integer: {value}")
    
    if min_value is not None and int_value < min_value:
        raise ValidationError(f"Value must be at least {min_value}")
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(f"Value must not exceed {max_value}")
    
    return int_value


def validate_float(value: str, min_value: float = None, 
                  max_value: float = None) -> float:
    """Validate a float
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Validated float
        
    Raises:
        ValidationError: If validation fails
    """
    if not value and value != 0:
        raise ValidationError("Value cannot be empty")
    
    try:
        float_value = float(value)
    except ValueError:
        raise ValidationError(f"Value must be a number: {value}")
    
    if min_value is not None and float_value < min_value:
        raise ValidationError(f"Value must be at least {min_value}")
    
    if max_value is not None and float_value > max_value:
        raise ValidationError(f"Value must not exceed {max_value}")
    
    return float_value


def validate_db_connection_string(conn_string: str) -> str:
    """Validate a database connection string
    
    Args:
        conn_string: Connection string to validate
        
    Returns:
        Validated connection string
        
    Raises:
        ValidationError: If validation fails
    """
    if not conn_string:
        raise ValidationError("Connection string cannot be empty")
    
    # SQLite connection string
    if conn_string.startswith("sqlite:///"):
        path = conn_string[10:]
        try:
            validate_path(path, must_exist=False)
        except ValidationError as e:
            raise ValidationError(f"Invalid SQLite connection string: {e}")
    
    # PostgreSQL connection string
    elif conn_string.startswith("postgresql://"):
        # Check basic structure
        if not re.match(r'postgresql://[^:]+:[^@]*@[^:]+:\d+/[^?]*', conn_string):
            raise ValidationError("Invalid PostgreSQL connection string format. Expected: postgresql://user:password@host:port/database")
    
    # Other connection strings
    else:
        raise ValidationError("Unsupported database type. Only SQLite and PostgreSQL are supported.")
    
    return conn_string


def validate_email(email: str) -> str:
    """Validate an email address
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email address
        
    Raises:
        ValidationError: If validation fails
    """
    if not email:
        raise ValidationError("Email cannot be empty")
    
    # Simple regex for basic email validation
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
        raise ValidationError("Invalid email format")
    
    return email


def validate_regex(value: str, pattern: str, error_message: str = None) -> str:
    """Validate a string against a regular expression
    
    Args:
        value: Value to validate
        pattern: Regex pattern to match
        error_message: Custom error message
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If validation fails
    """
    if not value:
        raise ValidationError("Value cannot be empty")
    
    if not re.match(pattern, value):
        message = error_message or f"Value does not match pattern: {pattern}"
        raise ValidationError(message)
    
    return value


def validate_table_name(table_name: str) -> str:
    """Validate a database table name
    
    Args:
        table_name: Table name to validate
        
    Returns:
        Validated table name
        
    Raises:
        ValidationError: If validation fails
    """
    if not table_name:
        raise ValidationError("Table name cannot be empty")
    
    # Only allow alphanumeric characters, underscores, and no spaces
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        raise ValidationError("Table name can only contain letters, numbers, and underscores")
    
    # Table name should not start with a number
    if re.match(r'^[0-9]', table_name):
        raise ValidationError("Table name cannot start with a number")
    
    return table_name


def validate_column_name(column_name: str) -> str:
    """Validate a database column name
    
    Args:
        column_name: Column name to validate
        
    Returns:
        Validated column name
        
    Raises:
        ValidationError: If validation fails
    """
    if not column_name:
        raise ValidationError("Column name cannot be empty")
    
    # Only allow alphanumeric characters, underscores, and no spaces
    if not re.match(r'^[a-zA-Z0-9_]+$', column_name):
        raise ValidationError("Column name can only contain letters, numbers, and underscores")
    
    # Column name should not start with a number
    if re.match(r'^[0-9]', column_name):
        raise ValidationError("Column name cannot start with a number")
    
    return column_name


def validate_json_string(json_str: str) -> Dict:
    """Validate a JSON string
    
    Args:
        json_str: JSON string to validate
        
    Returns:
        Parsed JSON object
        
    Raises:
        ValidationError: If validation fails
    """
    if not json_str:
        raise ValidationError("JSON string cannot be empty")
    
    try:
        json_obj = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")
    
    return json_obj


def validate_input(prompt: str, validator: Callable[[str], Any], 
                  error_message: str = None, 
                  default: str = None,
                  max_attempts: int = 3) -> Any:
    """Validate user input with a custom validator function
    
    Args:
        prompt: Prompt to display to user
        validator: Function that validates input and returns processed value
        error_message: Custom error message
        default: Default value if user enters empty string
        max_attempts: Maximum number of validation attempts
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If validation fails after max_attempts
    """
    attempts = 0
    
    while attempts < max_attempts:
        if default:
            value = input(f"{prompt} [{default}]: ").strip()
            if not value:
                value = default
        else:
            value = input(f"{prompt}: ").strip()
        
        if value.lower() in ('exit', 'quit', 'cancel'):
            raise ValidationError("Operation cancelled by user")
        
        try:
            return validator(value)
        except ValidationError as e:
            attempts += 1
            message = error_message or str(e)
            remaining = max_attempts - attempts
            
            if remaining > 0:
                print(f"❌ {message}. {remaining} attempts remaining.")
            else:
                print(f"❌ {message}. No attempts remaining.")
                raise ValidationError(f"Validation failed after {max_attempts} attempts")


# Example usage functions

def get_csv_path() -> str:
    """Prompt user for a CSV file path and validate it
    
    Returns:
        Validated CSV file path
    """
    return validate_input(
        "Enter CSV file path",
        lambda path: validate_csv_path(path),
        "Invalid CSV file path"
    )


def get_database_choice() -> str:
    """Prompt user for database type and validate it
    
    Returns:
        Validated database type
    """
    return validate_input(
        "Select database type (sqlite or postgresql)",
        lambda choice: validate_choice(choice, ["sqlite", "postgresql"]),
        "Invalid database type"
    )


def get_date_range() -> Tuple[str, str]:
    """Prompt user for a date range and validate it
    
    Returns:
        Tuple of (start_date, end_date)
    """
    start_date = validate_input(
        "Enter start date (YYYY-MM-DD)",
        lambda date: validate_date(date),
        "Invalid start date"
    )
    
    end_date = validate_input(
        "Enter end date (YYYY-MM-DD)",
        lambda date: validate_date(date, min_date=start_date),
        "Invalid end date (must be after start date)"
    )
    
    return start_date, end_date