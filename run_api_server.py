#!/usr/bin/env python3
"""
Run HVLC_DB API Server.

This script starts the API server for the HVLC_DB Medical Billing System.
"""

import os
import argparse
import logging
from api.app import create_app
from api.config import DevelopmentConfig, ProductionConfig

# Parse command line arguments
parser = argparse.ArgumentParser(description="Start HVLC_DB API Server")
parser.add_argument("--port", type=int, default=5000, help="Port to run the API server on")
parser.add_argument("--host", default="127.0.0.1", help="Host to run the API server on")
parser.add_argument("--prod", action="store_true", help="Run in production mode")
parser.add_argument("--debug", action="store_true", help="Run in debug mode")
args = parser.parse_args()

# Set environment variable for Flask
os.environ['FLASK_ENV'] = 'production' if args.prod else 'development'

# Create Flask app with appropriate config
config_class = ProductionConfig if args.prod else DevelopmentConfig
app = create_app(config_class)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if args.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run the app
if __name__ == '__main__':
    print(f"Starting HVLC_DB API Server at http://{args.host}:{args.port}")
    print(f"Running in {'production' if args.prod else 'development'} mode")
    print(f"Debug mode: {'enabled' if args.debug else 'disabled'}")
    print("Press Ctrl+C to stop")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )