"""
Database Utility Functions.

This module provides database utility functions for the API.
"""

import os
import sqlite3
import pandas as pd
from flask import current_app

def get_db_connection():
    """Get a database connection.
    
    Returns:
        sqlite3.Connection: Database connection.
    """
    db_path = current_app.config.get('DATABASE_PATH', 'medical_billing.db')
    
    # Make sure the database file exists
    if not os.path.exists(db_path) and db_path != ':memory:':
        raise FileNotFoundError(f"Database file not found: {db_path}")
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_table_list():
    """Get list of tables in the database.
    
    Returns:
        List of table names.
    """
    conn = get_db_connection()
    try:
        # Query for table names
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        current_app.logger.error(f"Error getting table list: {e}")
        conn.close()
        raise

def execute_query(query, params=None):
    """Execute a SQL query.
    
    Args:
        query: SQL query to execute.
        params: Query parameters.
        
    Returns:
        DataFrame with query results.
    """
    try:
        conn = get_db_connection()
        result = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return result
    except Exception as e:
        current_app.logger.error(f"Error executing query: {e}")
        conn.close()
        raise

def execute_write_query(query, params=None):
    """Execute a SQL query that modifies the database.
    
    Args:
        query: SQL query string.
        params: Query parameters.
        
    Returns:
        Number of rows affected.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        return rows_affected
    except Exception as e:
        current_app.logger.error(f"Error executing write query: {e}")
        raise