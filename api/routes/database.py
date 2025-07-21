"""
Database API Routes.

This module provides API endpoints for database operations.
"""

import sqlite3
import pandas as pd
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest, NotFound

from api.utils.db import get_db_connection, execute_query
from api.utils.validators import validate_query

# Create Blueprint
database_bp = Blueprint('database', __name__)

@database_bp.route('/tables', methods=['GET'])
def get_tables():
    """Get all tables in the database.
    
    Returns:
        JSON response with list of tables and their row counts.
    """
    try:
        # Get tables
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        tables_result = execute_query(tables_query)
        
        if tables_result.empty:
            return jsonify({'tables': []})
        
        tables = tables_result['name'].tolist()
        counts = {}
        
        # Get row counts for each table
        for table in tables:
            count_query = f"SELECT COUNT(*) as count FROM {table}"
            count_result = execute_query(count_query)
            if not count_result.empty:
                counts[table] = int(count_result['count'].iloc[0])
        
        return jsonify({
            'tables': tables,
            'counts': counts
        })
    except Exception as e:
        current_app.logger.error(f"Error getting tables: {e}")
        raise BadRequest(f"Error getting tables: {str(e)}")


@database_bp.route('/tables/<table_name>', methods=['GET'])
def get_table_data(table_name):
    """Get data from a specific table.
    
    Args:
        table_name: Name of the table to get data from.
        
    Returns:
        JSON response with table data.
    """
    try:
        # Check if table exists
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        tables_result = execute_query(tables_query, params=(table_name,))
        
        if tables_result.empty:
            raise NotFound(f"Table '{table_name}' not found")
        
        # Get pagination parameters
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        # Get total row count
        count_query = f"SELECT COUNT(*) as count FROM {table_name}"
        count_result = execute_query(count_query)
        total_rows = int(count_result['count'].iloc[0]) if not count_result.empty else 0
        
        # Get table data
        query = f"SELECT * FROM {table_name} LIMIT ? OFFSET ?"
        result = execute_query(query, params=(limit, offset))
        
        # Convert to JSON
        return jsonify({
            'table': table_name,
            'data': result.to_dict(orient='records'),
            'columns': list(result.columns),
            'total_rows': total_rows,
            'limit': limit,
            'offset': offset
        })
    except NotFound:
        raise
    except Exception as e:
        current_app.logger.error(f"Error getting table data: {e}")
        raise BadRequest(f"Error getting table data: {str(e)}")


@database_bp.route('/query', methods=['POST'])
def execute_sql_query():
    """Execute a SQL query.
    
    Request JSON:
        {
            "query": "SELECT * FROM table_name",
            "params": [] (optional)
        }
        
    Returns:
        JSON response with query results.
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            raise BadRequest("Missing 'query' parameter")
        
        query = data['query']
        params = data.get('params', [])
        
        # Validate query to prevent SQL injection
        validate_query(query)
        
        # Execute query
        result = execute_query(query, params=params)
        
        # Check if result is a DataFrame
        if isinstance(result, pd.DataFrame):
            return jsonify({
                'success': True,
                'data': result.to_dict(orient='records'),
                'columns': list(result.columns),
                'row_count': len(result)
            })
        else:
            return jsonify({
                'success': True,
                'message': str(result)
            })
    except Exception as e:
        current_app.logger.error(f"Error executing query: {e}")
        raise BadRequest(f"Error executing query: {str(e)}")


@database_bp.route('/schema/<table_name>', methods=['GET'])
def get_table_schema(table_name):
    """Get schema information for a specific table.
    
    Args:
        table_name: Name of the table to get schema for.
        
    Returns:
        JSON response with table schema.
    """
    try:
        # Check if table exists
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        tables_result = execute_query(tables_query, params=(table_name,))
        
        if tables_result.empty:
            raise NotFound(f"Table '{table_name}' not found")
        
        # Get table schema
        schema_query = f"PRAGMA table_info({table_name})"
        schema_result = execute_query(schema_query)
        
        if schema_result.empty:
            return jsonify({'columns': []})
        
        # Format schema information
        columns = []
        for _, row in schema_result.iterrows():
            columns.append({
                'name': row['name'],
                'type': row['type'],
                'notnull': bool(row['notnull']),
                'default_value': row['dflt_value'],
                'primary_key': bool(row['pk'])
            })
        
        return jsonify({
            'table': table_name,
            'columns': columns
        })
    except NotFound:
        raise
    except Exception as e:
        current_app.logger.error(f"Error getting table schema: {e}")
        raise BadRequest(f"Error getting table schema: {str(e)}")


@database_bp.route('/stats', methods=['GET'])
def get_database_stats():
    """Get database statistics.
    
    Returns:
        JSON response with database statistics.
    """
    try:
        # Get tables
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        tables_result = execute_query(tables_query)
        
        if tables_result.empty:
            return jsonify({
                'table_count': 0,
                'tables': [],
                'total_rows': 0
            })
        
        tables = tables_result['name'].tolist()
        table_stats = []
        total_rows = 0
        
        # Get statistics for each table
        for table in tables:
            count_query = f"SELECT COUNT(*) as count FROM {table}"
            count_result = execute_query(count_query)
            row_count = int(count_result['count'].iloc[0]) if not count_result.empty else 0
            total_rows += row_count
            
            # Get column count
            schema_query = f"PRAGMA table_info({table})"
            schema_result = execute_query(schema_query)
            column_count = len(schema_result) if not schema_result.empty else 0
            
            table_stats.append({
                'name': table,
                'row_count': row_count,
                'column_count': column_count
            })
        
        return jsonify({
            'table_count': len(tables),
            'tables': table_stats,
            'total_rows': total_rows
        })
    except Exception as e:
        current_app.logger.error(f"Error getting database stats: {e}")
        raise BadRequest(f"Error getting database stats: {str(e)}")