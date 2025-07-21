"""
Error Handler Utility Functions.

This module provides error handler functions for the API.
"""

from flask import jsonify
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    """Register error handlers with Flask app.
    
    Args:
        app: Flask application.
    """
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions.
        
        Args:
            error: HTTP exception.
            
        Returns:
            JSON response with error details.
        """
        response = {
            'error': True,
            'message': error.description,
            'status_code': error.code
        }
        return jsonify(response), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle generic exceptions.
        
        Args:
            error: Exception object.
            
        Returns:
            JSON response with error details.
        """
        # Log the error
        app.logger.error(f"Unhandled exception: {error}")
        
        response = {
            'error': True,
            'message': str(error),
            'status_code': 500
        }
        return jsonify(response), 500