"""
Configuration manager for HVLC_DB.

Handles loading and access to configuration settings from JSON file.
"""

import os
import json
import logging
from pathlib import Path

# Default configuration file path
DEFAULT_CONFIG_PATH = 'config.json'

# Default configuration values
DEFAULT_CONFIG = {
    "ollama": {
        "homelab_url": "http://192.168.1.100:11434",
        "homelab_model": "llama3.3:70b",
        "laptop_url": "http://localhost:11434",
        "laptop_model": "llama3.1:8b",
        "timeout": 180
    },
    "database": {
        "type": "sqlite",  # sqlite or postgresql
        "db_path": "medical_billing.db",
        "postgresql": {
            "host": "localhost",
            "port": 5432,
            "database": "medical_billing",
            "user": "postgres",
            "password": "",  # Should be set via environment variable
            "ssl_mode": "prefer"
        },
        "connection_pool_size": 5,
        "connection_timeout": 30,
        "enable_foreign_keys": True,
        "echo_sql": False
    },
    "paths": {
        "csv_root": "csv_folder",
        "docs_root": "docs",
        "log_dir": "logs"
    },
    "logging": {
        "level": "INFO",
        "query_log": "query_log.txt",
        "clarification_log": "clarification_log.txt",
        "data_quality_log": "data_quality_issues.log"
    },
    "features": {
        "sql_agent_enabled": True,
        "vector_search_enabled": True,
        "improved_ai_enabled": True
    }
}

# Global configuration object
_config = None

def get_config(config_path=None):
    """Get configuration, loading it if not already loaded
    
    Args:
        config_path: Optional path to config file. If None, uses default path.
        
    Returns:
        Configuration dictionary with dot notation access
    """
    global _config
    
    if _config is None:
        _config = Config(config_path)
    
    return _config

class Config:
    """Configuration manager with dot notation access"""
    
    def __init__(self, config_path=None):
        """Initialize configuration
        
        Args:
            config_path: Path to config file (default: 'config.json')
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config_data = DEFAULT_CONFIG.copy()
        self.load()
        
        # Override with environment variables if present
        self._load_from_environment()
    
    def load(self):
        """Load configuration from file"""
        try:
            # Check if config file exists
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    # Load and merge with defaults
                    user_config = json.load(f)
                    self._deep_update(self.config_data, user_config)
                    
                print(f"✅ Loaded configuration from {self.config_path}")
            else:
                # Create default config file
                self.save()
                print(f"ℹ️ Created default configuration at {self.config_path}")
                
        except Exception as e:
            print(f"⚠️ Error loading configuration: {e}")
            print(f"ℹ️ Using default configuration")
    
    def save(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving configuration: {e}")
    
    def get(self, key_path, default=None):
        """Get configuration value using dot notation
        
        Args:
            key_path: Key path using dot notation (e.g., 'ollama.homelab_url')
            default: Default value to return if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path, value):
        """Set configuration value using dot notation
        
        Args:
            key_path: Key path using dot notation (e.g., 'ollama.homelab_url')
            value: Value to set
        """
        keys = key_path.split('.')
        target = self.config_data
        
        # Navigate to the last parent
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Set the value
        target[keys[-1]] = value
    
    def _deep_update(self, target, source):
        """Recursively update nested dictionaries
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
                
    def _load_from_environment(self):
        """Override configuration with environment variables
        
        Environment variables should be prefixed with HVLC_DB_
        and use double underscore as separator for nested keys.
        
        Examples:
            - HVLC_DB_DATABASE__TYPE="postgresql"
            - HVLC_DB_DATABASE__POSTGRESQL__HOST="db.example.com"
            - HVLC_DB_DATABASE__POSTGRESQL__PASSWORD="password123"
        """
        prefix = "HVLC_DB_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and split into parts
                config_path = key[len(prefix):].lower().replace("__", ".")
                
                # Convert value to appropriate type
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit() and value.count(".") == 1:
                    value = float(value)
                
                # Set configuration value
                self.set(config_path, value)
                
    def get_db_url(self):
        """Get database URL based on configuration
        
        Returns:
            SQLAlchemy database URL
        """
        db_type = self.get("database.type", "sqlite")
        
        if db_type == "sqlite":
            db_path = self.get("database.db_path", "medical_billing.db")
            return f"sqlite:///{db_path}"
        elif db_type == "postgresql":
            host = self.get("database.postgresql.host", "localhost")
            port = self.get("database.postgresql.port", 5432)
            database = self.get("database.postgresql.database", "medical_billing")
            user = self.get("database.postgresql.user", "postgres")
            password = self.get("database.postgresql.password", "")
            ssl_mode = self.get("database.postgresql.ssl_mode", "prefer")
            
            # Check for password in environment variable
            env_password = os.environ.get("HVLC_DB_POSTGRESQL_PASSWORD")
            if env_password:
                password = env_password
                
            return f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode={ssl_mode}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
            
    def get_db_path(self):
        """Get database path for SQLite
        
        Returns:
            Path to SQLite database file
        """
        return self.get("database.db_path", "medical_billing.db")