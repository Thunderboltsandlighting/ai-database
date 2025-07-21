#!/usr/bin/env python
"""
Script to fix the config.json file and ensure it's properly formatted
"""

import json
import os
import shutil

def fix_config_file():
    """Fix the config.json file and ensure it's properly formatted"""
    config_path = "config.json"
    backup_path = "config.json.bak"
    
    # Create a corrected config dictionary
    config = {
        "database": {
            "db_path": "medical_billing.db",
            "enable_foreign_keys": True
        },
        "ollama": {
            "homelab_url": "http://ada.tailf21bf8.ts.net:11434",
            "homelab_model": "llama3.3:70b",
            "laptop_url": "http://localhost:11434",
            "laptop_model": "llama3.1:8b",
            "timeout": 180,
            "max_tokens": 2000,
            "max_chars": 16000,
            "cache_timeout": 600
        },
        "paths": {
            "csv_root": "csv_folder",
            "meta_dir": "csv_folder/meta",
            "log_dir": "logs",
            "knowledge_file": "medical_billing_knowledge.md"
        },
        "logging": {
            "log_file": "medical_billing.log",
            "query_log": "query_log.txt",
            "clarification_log": "clarification_log.txt",
            "data_quality_log": "data_quality_issues.log",
            "log_level": "INFO",
            "max_log_size_mb": 5,
            "backup_count": 10
        }
    }
    
    # Make a backup
    if os.path.exists(config_path):
        print(f"Creating backup of {config_path} to {backup_path}")
        shutil.copy2(config_path, backup_path)
    
    # Write the corrected config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"Fixed {config_path} with correct JSON formatting")
    
    # Verify the file is valid JSON
    try:
        with open(config_path, 'r') as f:
            json.load(f)
        print("Verification successful: config.json is valid JSON")
    except json.JSONDecodeError as e:
        print(f"Error: Config file is still invalid: {e}")

if __name__ == "__main__":
    print("Fixing config.json file...")
    fix_config_file()