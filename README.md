# HVLC_DB Medical Billing AI

## Web User Interface

The system includes a full-featured web interface for broader accessibility:

- **Interactive Dashboard:** View database statistics and system status
- **Query Interface:** Execute SQL and natural language queries with visualization
- **Data Browser:** Browse database tables with pagination
- **File Upload:** Upload and process CSV files with format detection
- **AI Chat:** Interact with the AI assistant through a web interface
- **Analytics:** View and create data visualizations
- **Settings:** Configure database and LLM settings

To launch the web interface:

```bash
# Launch the web UI through the main application
python main.py --web

# Launch on a specific port
python main.py --web --web-port 8080

# Or use the dedicated web UI script
python start_web_ui.py

# Start the modern web interface (API server + Vue.js frontend)
./start_dev_environment.sh
```

## Modern Web Application Architecture

The system now features a modern web application architecture:

- **Backend API Server:** Flask-based RESTful API
- **Frontend:** Vue.js with Vuetify components
- **Data Visualization:** Interactive charts with Chart.js
- **State Management:** Pinia store for reactive state
- **Responsive Design:** Works on desktop and mobile devices

To develop the web interface:

```bash
# Start both the API server and frontend development server
./start_dev_environment.sh

# Backend API will be available at http://localhost:5000/api
# Frontend will be available at http://localhost:5173
```

## Improved AI with Enhanced Timeout Handling

This application includes an improved AI engine with these enhancements:

- **Robust Timeout Handling:** Automatically retries queries that time out
- **Memory Optimization:** Processes large datasets in chunks to reduce memory usage
- **Smart Error Recovery:** Falls back to direct database queries when AI fails
- **Enhanced Query Classification:** Routes queries to optimized handlers

To use the improved AI engine:

```bash
# Launch directly in improved AI mode
python main.py --improved --chat

# Set a custom timeout (in seconds)
python main.py --improved --timeout 240 --chat

# Or use the convenience script
./start_improved_ai.sh
```

## Ollama Model Selection Logic

This application automatically selects the best available Ollama server and model:

- **Primary:** Tries to connect to your homelab Ollama server (`llama3.3:70b` at `ada.tailf21bf8.ts.net:11434`).
- **Fallback:** If the homelab is unavailable, it falls back to your laptop's local Ollama server (`llama3.1:8b` at `localhost:11434`).
- If neither server is available, the app will raise an error and prompt you to start an Ollama server.

This ensures you always use the most powerful model available, but can still run locally if your homelab is offline.

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install frontend dependencies (optional, for web UI):
   ```bash
   cd frontend
   npm install
   ```
4. Configure settings in `config.json` (will be created automatically on first run)

## Usage

### Command Line Interface

```bash
# Run the main application
python main.py

# Start in chat mode with the AI assistant
python main.py --chat

# Use a specific LLM model
python main.py --model llama3.1:8b

# Quick start - loads CSV data and starts the chat interface
python quick_start.py
```

## Core Components

1. **Database Layer** (`medical_billing_db.py`) - Handles database operations
2. **AI Assistant** (`medical_billing_ai.py`) - Processes natural language queries
3. **Main Application** (`main.py`) - CLI interface and routing
4. **API Server** (`api/`) - Backend API for web interface
5. **Frontend** (`frontend/`) - Vue.js web interface
6. **Format Detection** (`utils/format_detector.py`) - CSV format detection
7. **Report Transformation** (`utils/report_transformer.py`) - Data transformation
8. **Multi-Database Support** (`utils/db_connector.py`) - Database abstraction

## Documentation

- `CLAUDE.md` - Project overview and command reference
- `medical_billing_commands.md` - Detailed command documentation
- `PRD_data_quality_and_code_improvements.md` - Development roadmap