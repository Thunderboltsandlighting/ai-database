import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_config():
    """Load configuration from config.json"""
    config_path = Path("config.json")
    
    # Default configuration
    default_config = {
        "ollama": {
            "homelab_url": "http://ada.tailf21bf8.ts.net:11434",
            "homelab_model": "llama3.3:70b",
            "laptop_url": "http://localhost:11434",
            "laptop_model": "llama3.1:8b",
            "timeout": 30,
            "fallback_timeout": 60,
            "max_retries": 2
        },
        "database": {
            "path": "medical_billing.db",
            "backup_enabled": True,
            "backup_interval": 3600
        },
        "ai": {
            "max_tokens": 2000,
            "temperature": 0.7,
            "top_p": 0.9,
            "use_fallback": True,
            "fallback_method": "sql"
        }
    }
    
    try:
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        else:
            logger.warning("Config file not found, using defaults")
            return default_config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return default_config