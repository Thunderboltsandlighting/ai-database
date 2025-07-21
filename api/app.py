"""
HVLC_DB API Server.

This module provides the main Flask application for the HVLC_DB API.
"""

import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from api.routes.database import database_bp
from api.routes.ai import ai_bp
from api.routes.files import files_bp
from api.routes.analysis import analysis_bp
from api.routes.files_bridge import files_bridge_bp
from api.routes.business import business_bp
from api.routes.operations import operations_bp
from api.routes.analytics import analytics_bp
from api.config import Config
from api.utils.error_handlers import register_error_handlers

def create_app(config_class=Config):
    """Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use.
        
    Returns:
        Flask application instance.
    """
    # Initialize Flask app
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS for all routes and origins
    CORS(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(database_bp, url_prefix='/api/database')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(files_bp, url_prefix='/api/files')
    app.register_blueprint(files_bridge_bp, url_prefix='/api/files-bridge')
    app.register_blueprint(business_bp, url_prefix='/api/business')
    app.register_blueprint(operations_bp, url_prefix='/api/operations')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    
    # Register Ada configuration blueprint
    from api.routes.ada_config import ada_config_bp
    app.register_blueprint(ada_config_bp, url_prefix='/api/ada')
    
    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Root endpoint for API health check
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'ok',
            'version': app.config['API_VERSION'],
            'name': 'HVLC_DB API Server'
        })
    
    return app