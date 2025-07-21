"""
API Configuration Module.

This module provides configuration for the HVLC_DB API.
"""

import os
import sys
import json
from pathlib import Path

# Try to get configuration from main HVLC_DB config
def get_main_config():
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return {}

hvlc_config = get_main_config()

class Config:
    """Base configuration."""
    # API settings
    API_VERSION = '1.0.0'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hvlc_db_secret_key')
    
    # Database settings
    DATABASE_PATH = hvlc_config.get('database_path', 'medical_billing.db')
    DATABASE_TYPE = hvlc_config.get('database_type', 'sqlite')
    DATABASE_URL = hvlc_config.get('database_url', f'sqlite:///{DATABASE_PATH}')
    
    # Ollama settings
    OLLAMA_URL = hvlc_config.get('ollama_laptop_url', 'http://localhost:11434')
    OLLAMA_MODEL = hvlc_config.get('ollama_laptop_model', 'llama3.1:8b')
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB max upload size
    ALLOWED_EXTENSIONS = {'csv', 'txt', 'pdf', 'xlsx', 'xls'}
    
    # Logging settings
    LOG_LEVEL = hvlc_config.get('log_level', 'INFO')
    
    # CORS settings
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5173', 'http://127.0.0.1:3000', 'http://127.0.0.1:5173']
    
    # Feature flags
    FEATURE_MULTI_DB = hvlc_config.get('feature_multi_db', True)
    FEATURE_FORMAT_DETECTION = hvlc_config.get('feature_format_detection', True)
    FEATURE_DOCUMENT_PROCESSING = hvlc_config.get('feature_document_processing', True)
    FEATURE_DATA_QUALITY = hvlc_config.get('feature_data_quality', True)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    CORS_ORIGINS = ['https://hvlc-db.example.com']  # Restrict to production domain


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DATABASE_PATH = ':memory:'
    DATABASE_URL = 'sqlite:///:memory:'


# Determine which config to use based on environment
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

config_name = os.environ.get('FLASK_ENV', 'development')
AppConfig = config_map.get(config_name, DevelopmentConfig)