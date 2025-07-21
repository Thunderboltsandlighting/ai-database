"""
Validation Utility Functions.

This module provides validation functions for the API.
"""

import re
from werkzeug.exceptions import BadRequest

def validate_query(query):
    """Validate a SQL query to prevent SQL injection.
    
    Args:
        query: SQL query to validate.
        
    Raises:
        BadRequest: If query contains disallowed SQL commands.
    """
    # Lowercase query for easier matching
    query_lower = query.lower()
    
    # Check for dangerous SQL commands
    dangerous_commands = [
        r'\bdrop\s+table\b',
        r'\btruncate\s+table\b',
        r'\bdelete\s+from\b\s+without\s+where',
        r'\balter\s+table\b',
        r'\bcreate\s+trigger\b',
        r'\bexec\b',
        r'\bexecute\b',
        r'\bxp_cmdshell\b',
        r'\bsysadmin\b',
        r'\bsystem\b',
        r'\bmaster\b\.\bdbo\b',
    ]
    
    for pattern in dangerous_commands:
        if re.search(pattern, query_lower):
            raise BadRequest(f"Query contains disallowed SQL command: {pattern}")
    
    # Check for multiple statements (potential injection)
    if ';' in query_lower and not query_lower.endswith(';'):
        if not query_lower.endswith(' ;') and 'insert into' not in query_lower:
            raise BadRequest("Multiple SQL statements not allowed")
    
    return True

def validate_table_name(table_name):
    """Validate a table name.
    
    Args:
        table_name: Table name to validate.
        
    Returns:
        True if table name is valid.
        
    Raises:
        BadRequest: If table name is invalid.
    """
    if not table_name:
        raise BadRequest("Table name cannot be empty")
    
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        raise BadRequest("Table name can only contain letters, numbers, and underscores")
    
    return True

def validate_column_name(column_name):
    """Validate a column name.
    
    Args:
        column_name: Column name to validate.
        
    Returns:
        True if column name is valid.
        
    Raises:
        BadRequest: If column name is invalid.
    """
    if not column_name:
        raise BadRequest("Column name cannot be empty")
    
    if not re.match(r'^[a-zA-Z0-9_]+$', column_name):
        raise BadRequest("Column name can only contain letters, numbers, and underscores")
    
    return True