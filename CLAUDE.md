# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Application

```bash
# Run the main application with the default model
python main.py

# Run the application with a specific model
python main.py --model llama3.1:8b

# Start directly in chat mode
python main.py --chat

# Launch the web UI
python main.py --web

# Launch the web UI on a specific port
python main.py --web --web-port 8080

# Launch the web UI directly with the dedicated script
python start_web_ui.py

# Run the quick start script (loads CSVs to database and starts chat interface)
python quick_start.py
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_medical_billing_db.py

# Run tests with verbose output
pytest -v
```

### Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

## Code Architecture

The HVLC_DB (High Volume Low Cost Database) Medical Billing AI is a system for analyzing medical billing data using AI. It consists of several key components:

### Core Components

1. **Database Layer** (`medical_billing_db.py`):
   - Handles all database operations through the `MedicalBillingDB` class
   - Manages SQLite database for storing medical billing data
   - Provides methods for data import, queries, and analytics

2. **AI Assistant** (`medical_billing_ai.py`):
   - Implements `MedicalBillingAI` class that interfaces with Ollama LLM models
   - Routes user queries to appropriate analysis functions
   - Performs specialized analyses including performance reviews, revenue analysis, etc.
   - Provides a chat interface for interacting with the system

3. **Main Application** (`main.py`):
   - Entry point with CLI interface and argument handling
   - Provides data agent menu for querying and analyzing CSV data
   - Manages Ollama server/model selection with homelab (primary) and laptop (fallback) options
   - Handles conversational routing and user clarifications
   - Can launch the web UI for browser-based access

4. **Web UI** (`web_ui.py`):
   - Flask-based web interface for broader accessibility
   - Provides query execution, data browsing, and file upload capabilities
   - Features an interactive chat interface with the AI assistant
   - Includes data visualization capabilities with Plotly
   - Can be launched via main.py or directly with start_web_ui.py

5. **Quick Start** (`quick_start.py`):
   - Utility script for loading CSV data into the database
   - Initializes the AI assistant for immediate use

### Data Flow

1. CSV files in `csv_folder` are loaded into the SQLite database (`medical_billing.db`)
2. User queries are processed by either:
   - The main data agent interface (for direct CSV analysis)
   - The Medical Billing AI (for specialized medical billing analysis)
3. Queries are routed to appropriate analysis functions based on content
4. Results are returned to the user through the CLI interface

### Key Features

- Automatic Ollama model selection with fallback mechanism
- Smart query routing based on question content
- Performance reviews for providers and company-wide analysis
- Revenue, provider, time, and payer analysis capabilities
- Data quality checking and reporting
- Session-based clarifications for handling ambiguous terms
- Web-based interface with data visualization
- Format detection and automated CSV processing
- Multi-database support (SQLite and PostgreSQL)

### Database Schema

The system uses SQLite with tables for:
- Providers
- Payment transactions
- Monthly provider summaries
- Knowledge base (billing terminology)
- Data quality tracking

### Future Improvements

As outlined in `PRD_data_quality_and_code_improvements.md`, the project plans to address:
- Automated testing and validation
- Enhanced error handling
- Configuration management
- Data privacy and security
- Scalability optimizations
- Code duplication reduction
- Linting and type checking implementation
- User experience improvements