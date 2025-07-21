import os
import re
import time
import requests
import pandas as pd
import json
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
from pathlib import Path
from datetime import datetime
from llama_index.core import VectorStoreIndex, Document
from llama_index.llms.ollama import Ollama
from llama_index.experimental.query_engine import PandasQueryEngine
from llama_index.core.schema import TextNode
import argparse
import sqlite3

# Import improved AI if available
try:
    from improved_medical_billing_ai import ImprovedMedicalBillingAI
    IMPROVED_AI_AVAILABLE = True
except ImportError:
    IMPROVED_AI_AVAILABLE = False

# Import SQL agent if available
try:
    from agents.sql_agent import MedicalBillingSQLAgent
    SQL_AGENT_AVAILABLE = True
except ImportError:
    SQL_AGENT_AVAILABLE = False

# Import configuration
from utils.config import get_config
from utils.logger import get_logger

# Get configuration and logger
config = get_config()
logger = get_logger()

# === CONFIG ===
# Get Ollama server settings from config
HOMELAB_OLLAMA_URL = config.get("ollama.homelab_url")
HOMELAB_MODEL = config.get("ollama.homelab_model")
LAPTOP_OLLAMA_URL = config.get("ollama.laptop_url")
LAPTOP_MODEL = config.get("ollama.laptop_model")

# Get file paths from config
CSV_ROOT = config.get("paths.csv_root")
META_DIR = Path(CSV_ROOT) / "meta"
LOG_FILE = config.get("logging.query_log")
CLARIFICATION_LOG = config.get("logging.clarification_log")
DB_PATH = config.get("database.db_path")

# CLI Argument Parsing
parser = argparse.ArgumentParser(description="Medical Billing AI Assistant")
parser.add_argument("--model", help="Specify the model to use (e.g., llama3:70b or llama3.3:70b)", default="llama3.3:70b")
parser.add_argument("--chat", action="store_true", help="Launch MedicalBillingAI assistant on startup")
parser.add_argument("--improved", action="store_true", help="Use improved AI engine with better timeout handling")
parser.add_argument("--timeout", type=int, default=60, help="Set query timeout in seconds (default: 60)")
parser.add_argument("--web", action="store_true", help="Launch the web UI")
parser.add_argument("--web-port", type=int, default=5000, help="Port for the web UI (default: 5000)")

# === Enhanced Ollama Server and Model Selection ===
def get_ollama_url_and_model():
    """Get best available Ollama URL and model with automatic fallback
    
    Returns:
        Tuple of (ollama_url, model_name)
    """
    # First check homelab server
    if HOMELAB_OLLAMA_URL:
        try:
            logger.debug(f"Testing homelab Ollama at {HOMELAB_OLLAMA_URL}")
            res = requests.get(f"{HOMELAB_OLLAMA_URL}/api/tags", timeout=3)
            
            if res.status_code == 200:
                # Get available models
                available_models = [m["name"] for m in res.json().get("models", [])]
                
                # Check if configured model is available
                if HOMELAB_MODEL in available_models:
                    logger.info(f"Using homelab Ollama at {HOMELAB_OLLAMA_URL} with model {HOMELAB_MODEL}")
                    print(f"✅ Using Homelab Ollama server with {HOMELAB_MODEL}")
                    return HOMELAB_OLLAMA_URL, HOMELAB_MODEL
                
                # Use first available model as fallback
                elif available_models:
                    logger.info(f"Model {HOMELAB_MODEL} not found on homelab. Using {available_models[0]}")
                    print(f"⚠️ Model {HOMELAB_MODEL} not found on homelab.")
                    print(f"✅ Using alternate model: {available_models[0]}")
                    return HOMELAB_OLLAMA_URL, available_models[0]
        except Exception as e:
            logger.warning(f"Homelab Ollama not available: {e}")
    
    # Then check laptop server
    if LAPTOP_OLLAMA_URL:
        try:
            logger.debug(f"Testing laptop Ollama at {LAPTOP_OLLAMA_URL}")
            res = requests.get(f"{LAPTOP_OLLAMA_URL}/api/tags", timeout=3)
            
            if res.status_code == 200:
                # Get available models
                available_models = [m["name"] for m in res.json().get("models", [])]
                
                # Check if configured model is available
                if LAPTOP_MODEL in available_models:
                    logger.info(f"Using laptop Ollama at {LAPTOP_OLLAMA_URL} with model {LAPTOP_MODEL}")
                    print(f"✅ Using Laptop Ollama server with {LAPTOP_MODEL}")
                    return LAPTOP_OLLAMA_URL, LAPTOP_MODEL
                
                # Use first available model as fallback
                elif available_models:
                    logger.info(f"Model {LAPTOP_MODEL} not found on laptop. Using {available_models[0]}")
                    print(f"⚠️ Model {LAPTOP_MODEL} not found on laptop.")
                    print(f"✅ Using alternate model: {available_models[0]}")
                    return LAPTOP_OLLAMA_URL, available_models[0]
        except Exception as e:
            logger.warning(f"Laptop Ollama not available: {e}")
    
    # If we get here, use default values as last resort
    logger.error("No Ollama servers available, using laptop URL and default model as last resort")
    print("⚠️ No Ollama servers available.")
    print(f"ℹ️ Using default settings: {LAPTOP_OLLAMA_URL} with model llama3.1:8b")
    print("ℹ️ You can override these with the --model parameter.")
    return LAPTOP_OLLAMA_URL or "http://localhost:11434", "llama3.1:8b"

# Parse command line arguments
args = parser.parse_args()

# Get best available Ollama URL and model
try:
    OLLAMA_URL, MODEL_NAME = get_ollama_url_and_model()
    
    # Override with command line arguments if provided and verify it exists
    if args.model:
        try:
            logger.debug(f"Verifying model from command line: {args.model}")
            res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            
            if res.status_code == 200:
                available_models = [m["name"] for m in res.json().get("models", [])]
                
                if args.model in available_models:
                    MODEL_NAME = args.model
                    logger.info(f"Using model from command line: {MODEL_NAME}")
                    print(f"ℹ️ Using model from command line: {MODEL_NAME}")
                else:
                    logger.warning(f"Model {args.model} not found. Available models: {', '.join(available_models[:5])}")
                    print(f"⚠️ Model {args.model} not found. Using {MODEL_NAME} instead.")
                    print(f"Available models: {', '.join(available_models[:5])}")
        except Exception as e:
            logger.warning(f"Could not verify model availability: {e}")
            print(f"⚠️ Could not verify model {args.model} availability: {e}")
            print(f"ℹ️ Using {MODEL_NAME} instead")
except Exception as e:
    logger.error(f"Error setting up Ollama: {e}")
    print(f"⚠️ Error setting up Ollama: {e}")
    # Use default values
    OLLAMA_URL = LAPTOP_OLLAMA_URL or "http://localhost:11434"
    MODEL_NAME = "llama3.1:8b"  # Default to a common model

# === Helper: Parse Dates from Filenames ===
def parse_date_from_filename(filename):
    patterns = [
        r"(\d{4})[-_](\d{1,2})[-_](\d{1,2})",
        r"(\d{4})[-_](\d{1,2})",
        r"(\d{4})[ -_]?([A-Za-z]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                if len(match.groups()) == 3:
                    return datetime.strptime("-".join(match.groups()), "%Y-%m-%d").date().isoformat()
                elif len(match.groups()) == 2:
                    year, month = match.groups()
                    if month.isdigit():
                        return datetime.strptime(f"{year}-{int(month):02}", "%Y-%m").date().isoformat()
                    else:
                        return datetime.strptime(f"{year}-{month[:3]}", "%Y-%b").date().isoformat()
            except ValueError:
                pass
    return None

# === Helper: Load Markdown Descriptions ===
def load_md_descriptions(meta_dir):
    descriptions = {}
    if meta_dir.exists():
        for md_file in meta_dir.glob("*.md"):
            with open(md_file, "r") as f:
                descriptions[md_file.stem] = f.read()
    return descriptions

# === Helper: Load User Clarifications (persistent memory) ===
def load_clarifications(log_path):
    try:
        with open(log_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_clarification(log_path, key, value):
    clarifications = load_clarifications(log_path)
    clarifications[key] = value
    with open(log_path, "w") as f:
        json.dump(clarifications, f)

# === Helper: Ask for Clarification (with session memory) ===
def clarify(term, candidates, clarifications, log_path, friendly_name=None):
    friendly_name = friendly_name or term
    # Use previous clarification if available
    if term in clarifications and clarifications[term] in candidates:
        return clarifications[term]
    # If only one candidate, auto-select
    if len(candidates) == 1:
        save_clarification(log_path, term, candidates[0])
        return candidates[0]
    # Ask user
    print(f"🤔 I found multiple possible {friendly_name} columns: {candidates}")
    while True:
        choice = input(f"Which column should I use for {friendly_name}? Type the name exactly: ")
        if choice in candidates:
            save_clarification(log_path, term, choice)
            return choice
        else:
            print("Sorry, I didn't recognize that column. Please try again.")

# === OPTIMIZED: Database-First Data Access ===

# Create direct database connection for more efficient querying
def get_db_connection():
    """Get a direct database connection for optimized queries"""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Enable foreign keys if configured
        if config.get("database.enable_foreign_keys", True):
            conn.execute("PRAGMA foreign_keys = ON")
        logger.debug(f"Database connection established to {DB_PATH}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        print(f"❌ Error connecting to database: {e}")
        return None

# Smart query execution with size limiting
def execute_query(query, params=None, max_rows=100):
    """Execute SQL query with size limiting for LLM context management"""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        # Check if query might return large results (simple heuristic)
        if "LIMIT" not in query.upper():
            # Add limit to prevent excessive data
            query = f"{query} LIMIT {max_rows}"
            print(f"⚠️ Adding limit of {max_rows} rows to query for LLM processing")
        
        # Execute query
        df = pd.read_sql_query(query, conn, params=params)
        
        # Close connection
        conn.close()
        
        return df
    except Exception as e:
        print(f"❌ Query execution error: {e}")
        conn.close()
        return pd.DataFrame()

# === Load Minimal Data for CSV-based Queries ===
def load_csv_metadata(csv_root, descriptions):
    """Load just metadata about available CSVs without loading all content"""
    csv_metadata = []
    total_files = 0
    total_rows = 0
    
    for dirpath, _, filenames in os.walk(csv_root):
        if "meta" in dirpath:
            continue
        for filename in filenames:
            if filename.endswith(".csv"):
                file_path = Path(dirpath) / filename
                category = Path(dirpath).name
                context = descriptions.get(category, "")
                date = parse_date_from_filename(filename)
                
                # Get row count without loading entire file
                try:
                    row_count = sum(1 for _ in open(file_path)) - 1  # subtract header
                    total_rows += row_count
                    total_files += 1
                    
                    # Store metadata
                    csv_metadata.append({
                        "file_path": str(file_path),
                        "category": category,
                        "description": context,
                        "date": date,
                        "row_count": row_count
                    })
                except Exception as e:
                    print(f"⚠️ Could not read {file_path}: {e}")
    
    print(f"📊 Found {total_files} CSV files with approximately {total_rows} total rows")
    return csv_metadata

# === Function to get column names from CSVs without loading all data ===
def get_csv_columns(csv_metadata):
    """Get column names from CSV files without loading all data"""
    all_columns = set()
    
    for metadata in csv_metadata:
        try:
            # Read just the header row
            df_header = pd.read_csv(metadata["file_path"], nrows=0)
            columns = [col.strip().replace(' ', '_').lower() for col in df_header.columns]
            all_columns.update(columns)
        except Exception as e:
            print(f"⚠️ Could not get columns from {metadata['file_path']}: {e}")
    
    return sorted(list(all_columns))

# === Optimized Sample Data Loading ===
def load_sample_data(csv_metadata, sample_rows=10):
    """Load a small sample of data from each CSV for AI context"""
    sample_dfs = []
    
    for metadata in csv_metadata[:5]:  # Limit to first 5 files to avoid context size issues
        try:
            df = pd.read_csv(metadata["file_path"], nrows=sample_rows)
            df["source"] = metadata["file_path"]
            df["category"] = metadata["category"]
            df["parsed_date"] = metadata["date"]
            
            # Clean column names
            df.columns = [col.strip().replace(' ', '_').lower() for col in df.columns]
            
            sample_dfs.append(df)
        except Exception as e:
            print(f"⚠️ Could not sample {metadata['file_path']}: {e}")
    
    if not sample_dfs:
        return pd.DataFrame()
    
    # Combine samples
    combined_df = pd.concat(sample_dfs, ignore_index=True)
    
    # Process date columns
    for col in combined_df.columns:
        if 'date' in col:
            try:
                combined_df[col] = pd.to_datetime(combined_df[col], format='%m-%d-%Y', errors='coerce')
            except Exception:
                pass
    
    return combined_df

# === Load Data Descriptions ===
descriptions = load_md_descriptions(META_DIR)

# === Load CSV Metadata and Sample Data (instead of all data) ===
print("⚙️ Loading CSV metadata efficiently...")
csv_metadata = load_csv_metadata(CSV_ROOT, descriptions)
all_columns = get_csv_columns(csv_metadata)
sample_data = load_sample_data(csv_metadata)

# === LlamaIndex Engines (with smaller context) ===
# Configure timeout and other settings
timeout = config.get("ollama.timeout", 180)
print(f"ℹ️ Setting model timeout to {timeout} seconds")

# For LlamaIndex, we need a try-except to handle cases where Ollama can't get context window info
try:
    # For LlamaIndex, we still use its own Ollama implementation
    # Use a known model that definitely exists on the server
    print("🔄 Initializing LlamaIndex engine...")
    llm = Ollama(model=MODEL_NAME, base_url=OLLAMA_URL)
    # Test model access - this will fail early if there's an issue
    _ = llm.metadata
    print("✅ LlamaIndex engine initialized successfully")
except Exception as e:
    logger.error(f"Error initializing LlamaIndex engine: {e}")
    print(f"⚠️ Error initializing LlamaIndex engine: {e}")
    print("ℹ️ Using OpenAI-compatible API mode instead")
    
    # Import the generic LLM that doesn't require context window information
    from llama_index.llms.ollama import Ollama as LlamaIndexOllama
    
    # Create a simpler LLM with hardcoded parameters
    llm = LlamaIndexOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        request_timeout=timeout,
        context_window=4096,  # Reasonable default
        additional_kwargs={}
    )

# Initialize SQL agent if available
sql_agent = None
if SQL_AGENT_AVAILABLE:
    try:
        print("🔄 Initializing SQL Agent...")
        sql_agent = MedicalBillingSQLAgent(
            ollama_url=OLLAMA_URL,
            model=MODEL_NAME,
            verbose=False
        )
        print("✅ SQL Agent initialized successfully")
    except Exception as e:
        logger.error(f"SQL Agent initialization failed: {e}")
        print(f"⚠️ SQL Agent initialization failed: {e}")
        SQL_AGENT_AVAILABLE = False

# Create a smaller document set for vector indexing
sample_docs = []
for metadata in csv_metadata[:5]:  # Limit to first 5 files
    doc = Document(
        text=f"CSV file: {metadata['file_path']}\nCategory: {metadata['category']}\nDescription: {metadata['description']}\nDate: {metadata['date']}\nRow count: {metadata['row_count']}",
        metadata=metadata
    )
    sample_docs.append(doc)

# Create vector index from sample docs
index = VectorStoreIndex.from_documents(sample_docs)
query_engine = index.as_query_engine(llm=llm)

# === Pandas Engine with Sample Data ===
column_context = f"""
This table contains a SAMPLE of financial records from multiple CSV files.
The complete dataset is stored in a SQLite database for efficiency.
Available columns in the full dataset: {', '.join(all_columns)}
For large-scale queries, use the database_engine instead of this sample data.
"""
pandas_engine = PandasQueryEngine(df=sample_data, llm=llm, context_str=column_context)

# === Load Clarifications for Session ===
try:
    session_clarifications = load_clarifications(CLARIFICATION_LOG)
    logger.debug(f"Loaded {len(session_clarifications)} clarifications from {CLARIFICATION_LOG}")
except Exception as e:
    logger.error(f"Error loading clarifications: {e}")
    session_clarifications = {}

# === Function to Initialize Medical Billing AI ===
def initialize_medical_billing_ai(use_improved=False):
    """Initialize and return MedicalBillingAI instance"""
    try:
        from medical_billing_ai import MedicalBillingAI
        from medical_billing_db import MedicalBillingDB
        from utils.logger import get_quality_logger
        
        logger.info("Initializing Medical Billing AI Assistant")
        print("🤖 Initializing Medical Billing AI Assistant...")
        
        # Use the configured database path
        db_path = DB_PATH  # Use the already loaded DB_PATH from config
        db = MedicalBillingDB(db_path=db_path)
        
        # Use improved AI if requested and available
        if use_improved and IMPROVED_AI_AVAILABLE:
            from improved_medical_billing_ai import ImprovedMedicalBillingAI
            
            # Get timeout values from config
            timeout_value = config.get("ollama.timeout", 60)
            
            ai = ImprovedMedicalBillingAI(
                db_path=db_path,
                ollama_url=OLLAMA_URL,
                model=MODEL_NAME
            )
            print("✅ Using Improved Medical Billing AI with enhanced timeout handling")
            print(f"⚙️ Using progressive timeouts: {config.get('ollama.timeout', 60)}s → {config.get('ollama.retry_timeout', 30)}s → {config.get('ollama.final_timeout', 15)}s")
        else:
            # Use the standard AI
            ai = MedicalBillingAI(
                db_instance=db, 
                ollama_url=OLLAMA_URL, 
                model=MODEL_NAME
            )
        
        print("✅ Medical Billing AI Assistant ready!")
        logger.info("Medical Billing AI Assistant initialized successfully")
        return ai
        
    except ImportError as e:
        error_msg = f"Import Error: {e}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        print("💡 Make sure you have the medical_billing_ai.py and medical_billing_db.py files")
        return None
        
    except Exception as e:
        error_msg = f"Error initializing Medical Billing AI: {e}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        print("💡 Check that your database and AI modules are properly configured")
        return None

# === Optimized Database Query Engine ===
def fallback_query(question, conn=None):
    """Simpler direct database query without using LLM for when model times out"""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    if not conn:
        return "Database connection failed."
        
    question_lower = question.lower()
    
    try:
        # Simple highest provider query
        if "highest" in question_lower and "provider" in question_lower:
            query = """
                SELECT 
                    p.provider_name,
                    SUM(pt.cash_applied) as total_revenue
                FROM payment_transactions pt
                JOIN providers p ON pt.provider_id = p.provider_id
                GROUP BY p.provider_name
                ORDER BY total_revenue DESC
                LIMIT 1
            """
            
            cursor = conn.execute(query)
            row = cursor.fetchone()
            
            if row:
                return f"The highest earning provider is {row[0]} with ${row[1]:,.2f} in revenue."
            else:
                return "No provider revenue data found."
                
        # Simple total revenue query
        elif "total" in question_lower and "revenue" in question_lower:
            query = "SELECT SUM(cash_applied) as total_revenue FROM payment_transactions"
            cursor = conn.execute(query)
            row = cursor.fetchone()
            
            if row and row[0]:
                return f"The total revenue is ${row[0]:,.2f}."
            else:
                return "No revenue data found."
                
        # Simple provider list
        elif "providers" in question_lower:
            query = "SELECT provider_name FROM providers LIMIT 10"
            cursor = conn.execute(query)
            providers = [row[0] for row in cursor.fetchall()]
            
            if providers:
                return f"Providers: {', '.join(providers)}"
            else:
                return "No providers found."
                
        else:
            return "I'm sorry, but I couldn't process your complex query. Please try a simpler question."
            
    except Exception as e:
        return f"Error executing fallback query: {e}"
    finally:
        if close_conn and conn:
            conn.close()

def database_query(question, conn=None):
    """Route question to appropriate database query based on content"""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    
    if not conn:
        return "Database connection failed."
    
    question_lower = question.lower()
    
    try:
        result = ""
        
        # Revenue analysis
        if any(word in question_lower for word in ['revenue', 'cash', 'earned', 'total']):
            provider_name = extract_provider_name(question, conn)
            year, month = extract_date_params(question)
            
            query_conditions = []
            params = []
            
            if year:
                query_conditions.append("strftime('%Y', pt.transaction_date) = ?")
                params.append(year)
                
            if month:
                query_conditions.append("strftime('%m', pt.transaction_date) = ?")
                params.append(month)
                
            if provider_name:
                query_conditions.append("p.provider_name LIKE ?")
                params.append(f"%{provider_name}%")
            
            where_clause = ""
            if query_conditions:
                where_clause = "WHERE " + " AND ".join(query_conditions)
            
            query = f"""
                SELECT 
                    p.provider_name,
                    SUM(pt.cash_applied) as total_revenue,
                    COUNT(*) as transaction_count,
                    AVG(pt.cash_applied) as avg_payment
                FROM payment_transactions pt
                JOIN providers p ON pt.provider_id = p.provider_id
                {where_clause}
                GROUP BY p.provider_name 
                ORDER BY total_revenue DESC
                LIMIT 10
            """
            
            df = pd.read_sql_query(query, conn, params=params)
            
            # Format result
            title = "Revenue Analysis"
            if provider_name:
                title += f" for {provider_name}"
            if year:
                title += f" in {year}"
                if month:
                    title += f"-{month}"
            
            result = f"{title}:\n\n{df.to_string(index=False)}"
            
            # Add summary
            total_revenue = df['total_revenue'].sum() if not df.empty else 0
            result += f"\n\nTotal Revenue: ${total_revenue:,.2f}"
            
        # Provider analysis
        elif any(word in question_lower for word in ['provider', 'doctor', 'who']):
            query = """
                SELECT 
                    p.provider_name,
                    COUNT(*) as total_transactions,
                    SUM(pt.cash_applied) as total_revenue,
                    ROUND(AVG(pt.cash_applied), 2) as avg_payment,
                    COUNT(DISTINCT pt.patient_id) as unique_patients
                FROM payment_transactions pt
                JOIN providers p ON pt.provider_id = p.provider_id
                GROUP BY p.provider_name
                ORDER BY total_revenue DESC
                LIMIT 10
            """
            
            df = pd.read_sql_query(query, conn)
            result = f"Provider Analysis:\n\n{df.to_string(index=False)}"
            
        # Time analysis
        elif any(word in question_lower for word in ['month', 'year', 'trend', 'time']):
            query = """
                SELECT 
                    strftime('%Y-%m', pt.transaction_date) as month,
                    SUM(pt.cash_applied) as monthly_revenue,
                    COUNT(*) as transaction_count,
                    COUNT(DISTINCT p.provider_name) as active_providers
                FROM payment_transactions pt
                JOIN providers p ON pt.provider_id = p.provider_id
                WHERE pt.transaction_date IS NOT NULL
                GROUP BY strftime('%Y-%m', pt.transaction_date)
                ORDER BY month DESC
                LIMIT 12
            """
            
            df = pd.read_sql_query(query, conn)
            result = f"Monthly Trends (Last 12 Months):\n\n{df.to_string(index=False)}"
            
        # Payer analysis
        elif any(word in question_lower for word in ['payer', 'insurance']):
            query = """
                SELECT 
                    pt.payer_name,
                    COUNT(*) as claim_count,
                    SUM(pt.cash_applied) as total_paid,
                    ROUND(AVG(pt.cash_applied), 2) as avg_payment
                FROM payment_transactions pt
                WHERE pt.payer_name IS NOT NULL AND pt.payer_name != ''
                GROUP BY pt.payer_name
                ORDER BY total_paid DESC
                LIMIT 10
            """
            
            df = pd.read_sql_query(query, conn)
            result = f"Payer Analysis (Top 10):\n\n{df.to_string(index=False)}"
            
        # General statistics
        else:
            query = """
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(pt.cash_applied) as total_revenue,
                    COUNT(DISTINCT p.provider_name) as total_providers,
                    COUNT(DISTINCT pt.patient_id) as total_patients,
                    MIN(pt.transaction_date) as earliest_date,
                    MAX(pt.transaction_date) as latest_date
                FROM payment_transactions pt
                JOIN providers p ON pt.provider_id = p.provider_id
            """
            
            df = pd.read_sql_query(query, conn)
            result = f"Database Overview:\n\n{df.to_string(index=False)}"
        
        if close_conn:
            conn.close()
            
        # Send the data to LLM for explanation
        prompt = f"""
        QUESTION: {question}
        
        DATA RESULT:
        {result}
        
        Please analyze this data and answer the question in a clear, concise way. 
        Focus on the key insights from the data that address the specific question.
        """
        
        llm_response = llm.complete(prompt)
        return llm_response
        
    except Exception as e:
        if close_conn:
            conn.close()
        return f"Error executing database query: {e}"

def extract_provider_name(question, conn=None):
    """Extract provider name from question"""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    
    if not conn:
        return None
    
    try:
        # Get list of provider names from database
        query = "SELECT DISTINCT p.provider_name FROM payment_transactions pt JOIN providers p ON pt.provider_id = p.provider_id"
        providers_df = pd.read_sql_query(query, conn)
        
        # Check if any provider name appears in the question
        for provider in providers_df['provider_name']:
            if provider.lower() in question.lower():
                if close_conn:
                    conn.close()
                return provider
        
        if close_conn:
            conn.close()
        return None
    except Exception:
        if close_conn:
            conn.close()
        return None

def extract_date_params(question):
    """Extract year and month from question"""
    months = ['january', 'february', 'march', 'april', 'may', 'june', 
             'july', 'august', 'september', 'october', 'november', 'december']
    
    mentioned_month = None
    mentioned_year = None
    
    for month in months:
        if month in question.lower():
            mentioned_month = str(months.index(month) + 1).zfill(2)
            break
    
    for word in question.split():
        if word.isdigit() and len(word) == 4 and word.startswith('20'):
            mentioned_year = word
            break
    
    return mentioned_year, mentioned_month


def launch_web_ui(port=5000):
    """Launch the web UI
    
    Args:
        port: Port to run the web server on
        
    Returns:
        True if launched successfully, False otherwise
    """
    try:
        # Import web UI module
        try:
            from web_ui import app
        except ImportError as e:
            logger.error(f"Failed to import web_ui module: {e}")
            print(f"❌ Error: Could not launch web UI. {e}")
            print("Make sure you have installed the required packages:")
            print("pip install flask plotly werkzeug")
            return False
        
        # Import webbrowser for opening browser
        import webbrowser
        
        # Show launch message
        host = "127.0.0.1"
        url = f"http://{host}:{port}"
        print(f"\n✅ Starting HVLC_DB Web UI at {url}")
        print("💻 Opening browser...")
        
        # Open browser
        webbrowser.open(url)
        
        # Run the web server
        app.run(
            debug=False,  # Don't use debug mode in production
            host=host,
            port=port
        )
        
        return True
    except Exception as e:
        logger.error(f"Error launching web UI: {e}")
        print(f"❌ Error launching web UI: {e}")
        return False

# === Conversational CLI with Optimized Routing ===
def get_column_candidates(df, keywords):
    return [col for col in df.columns if any(word in col.lower() for word in keywords)]

def conversational_router(question, clarifications, log_path):
    try:
        q = question.lower()
        
        # Use short timeout for potentially complex queries
        short_timeout = 30  # 30 seconds maximum for complex queries
        
        # Check if this is an explicit SQL agent query
        if q.startswith("sql:") and SQL_AGENT_AVAILABLE and sql_agent:
            print("🤖 Using SQL Agent for explicit SQL query...")
            try:
                result = sql_agent.process_query(q.replace("sql:", "").strip())
                return result
            except Exception as e:
                logger.error(f"SQL Agent error: {e}")
                print(f"⚠️ SQL Agent error: {e}. Falling back to standard query.")
        
        # Check for complex analytical queries that would benefit from the SQL agent
        sql_query_indicators = [
            'analyze trends', 'complex query', 'relationship between', 
            'correlation', 'find all cases where', 'statistical', 
            'aggregate by', 'group results by', 'advanced query',
            'sql analysis', 'data mining', 'pattern in data'
        ]
        
        if SQL_AGENT_AVAILABLE and sql_agent and any(indicator in q for indicator in sql_query_indicators):
            print("📊 Query appears complex - trying SQL Agent...")
            try:
                # Create a thread for SQL agent with timeout
                import threading
                import time
                
                # Create a result container
                result_container = {'result': None, 'timeout': False}
                
                # Function to run SQL agent query
                def run_query():
                    try:
                        result_container['result'] = sql_agent.process_query(question)
                    except Exception as e:
                        logger.error(f"SQL agent thread error: {e}")
                        result_container['result'] = f"SQL agent error: {e}"
                
                # Create and start thread
                query_thread = threading.Thread(target=run_query)
                query_thread.daemon = True
                query_thread.start()
                
                # Wait for result with timeout
                short_timeout = 45  # 45 seconds for SQL agent
                query_thread.join(timeout=short_timeout)
                
                # Check if thread is still running (timeout)
                if query_thread.is_alive():
                    result_container['timeout'] = True
                    print(f"⚠️ SQL Agent query exceeded {short_timeout} second timeout, falling back to standard query")
                else:
                    # Return the result if we have one
                    if result_container['result']:
                        return result_container['result']
            except Exception as e:
                logger.error(f"Error in SQL agent with timeout: {e}")
                print(f"⚠️ Error in SQL agent: {e}. Using standard query.")
        
        # Check for direct database queries which need to handle large datasets efficiently
        db_query_indicators = [
            'total revenue', 'how much', 'top provider', 'revenue by', 
            'trends', 'highest earning', 'compare providers', 'insurance',
            'summary', 'most revenue', 'statistics', 'average payment'
        ]
        
        if any(indicator in q for indicator in db_query_indicators):
            print("📊 Using direct database query for efficiency...")
            try:
                import threading
                import time
                
                # Create a result container
                result_container = {'result': None, 'timeout': False}
                
                # Function to run database query with timeout
                def run_query():
                    try:
                        result_container['result'] = database_query(question)
                    except Exception as e:
                        logger.error(f"Database query thread error: {e}")
                        result_container['result'] = f"Database query error: {e}"
                
                # Create and start thread
                query_thread = threading.Thread(target=run_query)
                query_thread.daemon = True
                query_thread.start()
                
                # Wait for result with timeout
                query_thread.join(timeout=short_timeout)
                
                # Check if thread is still running (timeout)
                if query_thread.is_alive():
                    result_container['timeout'] = True
                    print(f"⚠️ Query exceeded {short_timeout} second timeout, using simpler fallback query")
                    return fallback_query(question)
                
                # Return the result
                return result_container['result']
            except Exception as e:
                logger.error(f"Error in database query with timeout: {e}")
                print(f"⚠️ Error in database query: {e}. Using fallback.")
                return fallback_query(question)
        
        # Use Vector DB for document-style questions
        doc_query_indicators = [
            'find file', 'where is', 'which file', 'look for document', 
            'search for', 'locate the'
        ]
        
        if any(indicator in q for indicator in doc_query_indicators):
            print("🔍 Using vector search for document retrieval...")
            try:
                response = query_engine.query(question)
                return response
            except Exception as e:
                logger.error(f"Vector search error: {e}")
                print(f"⚠️ Vector search failed: {e}. Falling back to general analysis.")
                # Fall back to simpler analysis
                return f"I'm sorry, I had trouble finding specific documents about '{question}'. Please try a more specific search term or phrase your question differently."
        
        # Handle clarifications for ambiguous terms in the remaining questions
        ambiguous_terms = {
            "revenue": ["revenue", "amount", "paid", "cash"],
            "date": ["date", "parsed"],
            "person": ["person", "patient", "provider", "name"],
            "payer": ["payer", "insurance", "company", "plan"],
        }
        
        for term, keywords in ambiguous_terms.items():
            if term in q or any(word in q for word in keywords):
                candidates = get_column_candidates(sample_data, keywords)
                if len(candidates) > 1:
                    chosen = clarify(term, candidates, clarifications, log_path, friendly_name=term)
                    clarifications[term] = chosen
                elif len(candidates) == 1:
                    clarifications[term] = candidates[0]
        
        context = ""
        for term, col in clarifications.items():
            context += f"For {term}, use column: {col}. "
        
        # Smart route depending on question type
        if any(kw in q for kw in ["who", "total", "sum", "highest", "revenue", "earned", "top", "most"]):
            print("📈 Using pandas engine for structured query...")
            try:
                import threading
                import time
                
                # Create a result container
                result_container = {'result': None, 'timeout': False}
                
                # Function to run query with timeout
                def run_query():
                    try:
                        result_container['result'] = pandas_engine.query(f"{question}\n{context}")
                    except Exception as e:
                        logger.error(f"Pandas engine thread error: {e}")
                        result_container['result'] = f"Pandas engine error: {e}"
                
                # Create and start thread
                query_thread = threading.Thread(target=run_query)
                query_thread.daemon = True
                query_thread.start()
                
                # Wait for result with timeout (30 seconds)
                short_timeout = 30
                query_thread.join(timeout=short_timeout)
                
                # Check if thread is still running (timeout)
                if query_thread.is_alive():
                    result_container['timeout'] = True
                    print(f"⚠️ Query exceeded {short_timeout} second timeout, using fallback query")
                    return fallback_query(question)
                
                # Return the result if we have one
                if result_container['result']:
                    return result_container['result']
                else:
                    return fallback_query(question)
                
            except Exception as e:
                logger.error(f"Pandas engine error: {e}")
                print(f"⚠️ Pandas engine failed: {e}. Falling back to fallback query.")
                # Fall back to simpler direct query
                return fallback_query(question)
        else:
            print("💬 Using general query engine...")
            try:
                import threading
                import time
                
                # Create a result container
                result_container = {'result': None, 'timeout': False}
                
                # Function to run query with timeout
                def run_query():
                    try:
                        result_container['result'] = query_engine.query(question)
                    except Exception as e:
                        logger.error(f"General query engine thread error: {e}")
                        result_container['result'] = f"General query engine error: {e}"
                
                # Create and start thread
                query_thread = threading.Thread(target=run_query)
                query_thread.daemon = True
                query_thread.start()
                
                # Wait for result with timeout (30 seconds)
                short_timeout = 30
                query_thread.join(timeout=short_timeout)
                
                # Check if thread is still running (timeout)
                if query_thread.is_alive():
                    result_container['timeout'] = True
                    print(f"⚠️ Query exceeded {short_timeout} second timeout, using fallback query")
                    return fallback_query(question)
                
                # Return the result if we have one
                if result_container['result']:
                    return result_container['result']
                else:
                    return fallback_query(question)
                
            except Exception as e:
                logger.error(f"General query engine error: {e}")
                print(f"⚠️ General query failed: {e}. Falling back to fallback query.")
                # Fall back to simpler direct query
                return fallback_query(question)
    except Exception as e:
        logger.error(f"Conversational router error: {e}")
        return f"I'm sorry, but I encountered an unexpected error: {e}. Please try again with a different question."

# === Menu and CLI Helpers ===
def print_menu():
    menu_text = """\n=== Data Agent Menu ===\n1. Ask a question\n2. Show data overview\n3. Show suggested questions\n4. Show available columns\n5. Show session clarifications\n6. Upload CSV file\n7. Help"""
    
    # Add SQL agent option if available
    if SQL_AGENT_AVAILABLE:
        menu_text += """\n8. Ask advanced SQL question (using SQL Agent)"""
        menu_option_offset = 1
    else:
        menu_option_offset = 0
    
    # We've integrated the improved AI directly into the main application,
    # so we now have a single Medical Billing AI option
    menu_text += f"""\n{8+menu_option_offset}. Launch Medical Billing AI Assistant (Chat Mode)"""
    menu_text += f"""\n{9+menu_option_offset}. Exit"""
    
    print(menu_text)

def show_columns(all_columns):
    print("\nAvailable columns in dataset:")
    for col in all_columns:
        print(f"- {col}")

def show_clarifications(clarifications):
    print("\nSession clarifications:")
    if not clarifications:
        print("(None yet)")
    for k, v in clarifications.items():
        print(f"- {k}: {v}")

def show_data_overview(csv_metadata):
    print("\n=== Data Overview ===")
    # Summarize CSV files by category
    categories = {}
    total_rows = 0
    
    for meta in csv_metadata:
        category = meta["category"]
        categories[category] = categories.get(category, 0) + 1
        total_rows += meta.get("row_count", 0)
    
    print(f"CSV files loaded by category:")
    for cat, count in categories.items():
        print(f"  - {cat}: {count} file(s)")
    
    # Show total rows
    print(f"\nTotal rows across all files: ~{total_rows}")
    
    # Show available columns
    print(f"Available columns: {len(all_columns)}")
    
    # Get high-level database stats
    conn = get_db_connection()
    if conn:
        try:
            # Date range
            date_query = """
                SELECT 
                    MIN(transaction_date) as earliest_date,
                    MAX(transaction_date) as latest_date
                FROM payment_transactions
                WHERE transaction_date IS NOT NULL
            """
            date_df = pd.read_sql_query(date_query, conn)
            
            if not date_df.empty:
                earliest = date_df.iloc[0]['earliest_date']
                latest = date_df.iloc[0]['latest_date']
                print(f"Date range: {earliest} to {latest}")
            
            # Provider and payer counts
            counts_query = """
                SELECT 
                    COUNT(DISTINCT p.provider_name) as provider_count,
                    COUNT(DISTINCT pt.payer_name) as payer_count,
                    COUNT(DISTINCT pt.patient_id) as patient_count
                FROM payment_transactions pt
                JOIN providers p ON pt.provider_id = p.provider_id
            """
            counts_df = pd.read_sql_query(counts_query, conn)
            
            if not counts_df.empty:
                print(f"Unique providers: {counts_df.iloc[0]['provider_count']}")
                print(f"Unique payers: {counts_df.iloc[0]['payer_count']}")
                print(f"Unique patients: {counts_df.iloc[0]['patient_count']}")
            
            # Data quality summary
            quality_query = """
                SELECT 
                    SUM(CASE WHEN pt.cash_applied IS NULL THEN 1 ELSE 0 END) as missing_cash_applied,
                    SUM(CASE WHEN pt.cash_applied < 0 THEN 1 ELSE 0 END) as negative_cash_applied
                FROM payment_transactions pt
            """
            quality_df = pd.read_sql_query(quality_query, conn)
            
            if not quality_df.empty:
                print("\nData quality summary:")
                print(f"  - Missing cash_applied: {quality_df.iloc[0]['missing_cash_applied']}")
                print(f"  - Negative cash_applied: {quality_df.iloc[0]['negative_cash_applied']}")
            
            conn.close()
        except Exception as e:
            print(f"Error retrieving database stats: {e}")
            conn.close()
    
    print("========================\n")

def show_suggested_questions(csv_metadata):
    print("\n=== Suggested Questions ===")
    suggestions = []
    
    # Get provider and payer examples from database
    conn = get_db_connection()
    provider_examples = []
    payer_examples = []
    
    if conn:
        try:
            # Top providers
            provider_query = """
                SELECT p.provider_name 
                FROM payment_transactions pt
                JOIN providers p ON pt.provider_id = p.provider_id
                GROUP BY p.provider_name
                ORDER BY SUM(pt.cash_applied) DESC
                LIMIT 3
            """
            provider_df = pd.read_sql_query(provider_query, conn)
            provider_examples = provider_df['provider_name'].tolist()
            
            # Top payers
            payer_query = """
                SELECT payer_name FROM payment_transactions
                WHERE payer_name IS NOT NULL AND payer_name != ''
                GROUP BY payer_name
                ORDER BY SUM(cash_applied) DESC
                LIMIT 3
            """
            payer_df = pd.read_sql_query(payer_query, conn)
            payer_examples = payer_df['payer_name'].tolist()
            
            conn.close()
        except Exception:
            if conn:
                conn.close()
    
    # Static and dynamic suggestions
    suggestions.append("What is the total revenue for this year?")
    suggestions.append("Show monthly revenue trends")
    
    if provider_examples:
        for p in provider_examples:
            suggestions.append(f"Show all transactions for provider {p}")
            suggestions.append(f"What is the average payment for provider {p}?")
    
    if payer_examples:
        for payer in payer_examples:
            suggestions.append(f"Compare performance for payer {payer}")
    
    suggestions.append("Which provider had the highest cash applied last month?")
    suggestions.append("Show top 10 providers by revenue")
    suggestions.append("Compare provider performance")
    
    # Print suggestions
    for i, q in enumerate(suggestions, 1):
        print(f"{i}. {q}")
    print("============================\n")
    
    # Prompt user to select a question
    choice = input("Enter the number of a question to ask it, or press Enter to return to the menu: ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(suggestions):
            question = suggestions[idx]
            try:
                start_time = time.time()
                result = conversational_router(question, session_clarifications, CLARIFICATION_LOG)
                end_time = time.time()
                print(f"⚡ Query processed in {end_time - start_time:.2f} seconds")
                
                print("\n=== AI Response ===\n")
                print(result)
                with open(LOG_FILE, "a") as log_file:
                    log_file.write(f"Q: {question}\nA: {result}\n{'-'*40}\n")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("Invalid selection. Returning to menu.")
    elif choice == "":
        return
    else:
        print("Invalid input. Returning to menu.")

def print_help():
    help_text = """
Type the number of the menu option you want to use.
- 'Ask a question' lets you interact with the agent about your data.
- 'Show data overview' provides a summary of the data in your system.
- 'Show suggested questions' gives examples of questions you can ask.
- 'Show available columns' lists all columns in your database.
- 'Show session clarifications' displays which columns the agent is using for ambiguous terms.
- 'Upload CSV file' allows you to load a CSV file using memory-efficient chunked processing.
- 'Help' shows this message."""

    if SQL_AGENT_AVAILABLE:
        help_text += """
- 'Ask advanced SQL question' uses the SQL Agent to handle complex analytical queries using natural language."""

    help_text += """
- 'Launch Medical Billing AI Assistant' starts the specialized medical billing chat interface."""

    if IMPROVED_AI_AVAILABLE:
        help_text += """
- 'Launch Improved Medical Billing AI' starts the enhanced AI with better timeout handling."""

    help_text += """
- 'Exit' quits the program. You can also type 'exit' or 'quit' at any prompt.

OPTIMIZED FOR SCALE:
This version uses database queries for most analysis and only loads sample data into memory.
It can efficiently handle 100+ CSV files by pre-aggregating data before sending to the AI model.
Large CSV files are processed in chunks to minimize memory usage.
"""
    
    if SQL_AGENT_AVAILABLE:
        help_text += """

SQL AGENT FEATURES:
- Natural language to SQL translation
- Complex analytical query support
- Schema-aware query generation
- Handles ambiguous terms intelligently
- For advanced questions, prefix with "sql:" (e.g., "sql: find providers with declining revenue trends")
"""
    
    if IMPROVED_AI_AVAILABLE:
        help_text += """

IMPROVED AI FEATURES:
- Robust timeout handling with automatic retries
- Memory-efficient processing of large datasets
- Smart error recovery with fallback mechanisms
- Enhanced query classification and optimization
"""

    print(help_text)

# === Main CLI Loop ===
if __name__ == "__main__":
    args = parser.parse_args()
    
    # Launch web UI if requested
    if args.web:
        launch_web_ui(port=args.web_port)
        exit(0)
    
    if args.chat:
        # Use improved AI if available
        use_improved = IMPROVED_AI_AVAILABLE
        ai = initialize_medical_billing_ai(use_improved=use_improved)
        if ai:
            if use_improved and hasattr(ai, 'process_query'):
                # Process welcome message and start chat loop
                welcome = ai.process_query("Welcome to the Medical Billing AI. How can I help you today?")
                print("\n" + "="*70)
                print(welcome)
                print("="*70 + "\n")
                
                try:
                    while True:
                        query = input("\n💬 Your Question: ").strip()
                        if query.lower() in ['quit', 'exit', 'bye']:
                            print("👋 Goodbye!")
                            break
                        if not query:
                            continue
                            
                        start_time = time.time()
                        result = ai.process_query(query)
                        end_time = time.time()
                        print(f"⚡ Query processed in {end_time - start_time:.2f} seconds")
                        
                        print("\n" + "="*70)
                        print(result)
                        print("="*70 + "\n")
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                finally:
                    if hasattr(ai, 'cleanup'):
                        ai.cleanup()
            else:
                # Use standard chat interface
                ai.chat_interface()
        exit(0)
        
    print("""
               █████╗ ██████╗  █████╗                       
              ██╔══██╗██╔══██╗██╔══██╗                      
              ███████║██║  ██║███████║                      
              ██╔══██║██║  ██║██╔══██║                      
              ██║  ██║██████╔╝██║  ██║                      
              ╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝                      
                                                        
██████╗ ███████╗██████╗  ██████╗ ██████╗ ████████╗███████╗
██╔══██╗██╔════╝██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝
██████╔╝█████╗  ██████╔╝██║   ██║██████╔╝   ██║   ███████╗
██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║██╔══██╗   ██║   ╚════██║
██║  ██║███████╗██║     ╚██████╔╝██║  ██║   ██║   ███████║
╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
""")
    print("\n🚀 Welcome to your Optimized Data Agent!")
    print("This version can efficiently handle 100+ CSV files using database-first queries")
    print("The agent will clarify ambiguous terms and learn your preferences.\n")
    
    while True:
        print_menu()
        
        # Calculate the exit option based on available features
        menu_option_offset = 1 if SQL_AGENT_AVAILABLE else 0
        exit_option = str(9 + menu_option_offset)
        
        choice = input(f"Select an option (1-{exit_option}): ").strip().lower()
        
        if choice in (exit_option, 'exit', 'quit', '/quit'):
            print("👋 Goodbye!")
            break
            
        elif choice == '1':
            question = input("\nAsk your question (or type 'exit' to return to menu): ")
            if question.lower() in ("exit", "quit", "/quit"):
                continue
            try:
                start_time = time.time()
                result = conversational_router(question, session_clarifications, CLARIFICATION_LOG)
                end_time = time.time()
                print(f"⚡ Query processed in {end_time - start_time:.2f} seconds")
                
                print("\n=== AI Response ===\n")
                print(result)
                with open(LOG_FILE, "a") as log_file:
                    log_file.write(f"Q: {question}\nA: {result}\n{'-'*40}\n")
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == '2':
            show_data_overview(csv_metadata)
            
        elif choice == '3':
            show_suggested_questions(csv_metadata)
            
        elif choice == '4':
            show_columns(all_columns)
            
        elif choice == '5':
            show_clarifications(session_clarifications)
            
        elif choice == '6':
            # Upload CSV file with chunked processing
            file_path = input("\nEnter the path to the CSV file: ").strip()
            if not file_path:
                continue
                
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                continue
                
            try:
                from medical_billing_db import MedicalBillingDB
                db = MedicalBillingDB()
                
                print(f"\n🔄 Processing {file_path} in chunks...")
                result = db.upload_csv_file(file_path)
                
                if result['success']:
                    print(f"\n✅ Successfully processed {result['total_rows_processed']} rows in {result['chunks_processed']} chunks:")
                    print(f"  - Successful rows: {result['successful_rows']}")
                    print(f"  - Failed rows: {result['failed_rows']}")
                    print(f"  - Processing time: {result['total_time_seconds']:.2f} seconds")
                    print(f"  - Rows per second: {result['rows_per_second']:.1f}")
                    
                    if result['issues']:
                        print(f"\n⚠️ Found {len(result['issues'])} data quality issues:")
                        for i, issue in enumerate(result['issues'][:5]):
                            print(f"  {i+1}. {issue['type']}: {issue['description']}")
                        if len(result['issues']) > 5:
                            print(f"     ... and {len(result['issues']) - 5} more issues")
                else:
                    print(f"\n❌ Error processing file: {result.get('error', 'Unknown error')}")
                    
                # Close the database connection
                db.close()
                
                # Reload metadata to reflect the new data
                print("\n🔄 Refreshing data overview...")
                show_data_overview(csv_metadata)
                
            except Exception as e:
                print(f"\n❌ Error processing CSV file: {e}")
            
        elif choice == '7':
            print_help()
            
        elif choice == '8' and SQL_AGENT_AVAILABLE:
            # Use SQL agent for advanced questions
            print("\n🤖 SQL Agent Mode - Ask complex analytical questions in natural language")
            print("Type your question below, or prefix with 'sql:' for direct SQL agent processing")
            print("Type 'exit' to return to the main menu\n")
            
            while True:
                sql_question = input("SQL Question: ").strip()
                
                if sql_question.lower() in ("exit", "quit", "/quit"):
                    break
                
                if not sql_question:
                    continue
                
                try:
                    print("🔄 Processing with SQL Agent...")
                    start_time = time.time()
                    
                    # Add sql: prefix if not already present
                    if not sql_question.lower().startswith("sql:"):
                        sql_question = "sql:" + sql_question
                    
                    result = conversational_router(sql_question, session_clarifications, CLARIFICATION_LOG)
                    end_time = time.time()
                    
                    print(f"⚡ Query processed in {end_time - start_time:.2f} seconds\n")
                    print("=== SQL Agent Response ===")
                    print(result)
                    print("="*50 + "\n")
                    
                    # Log the query
                    with open(LOG_FILE, "a") as log_file:
                        log_file.write(f"SQL Query: {sql_question}\nA: {result}\n{'-'*40}\n")
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            continue
            
        elif choice == '8' if not SQL_AGENT_AVAILABLE else choice == '9':
            # Initialize and launch Medical Billing AI (using improved version if available)
            ai = initialize_medical_billing_ai(use_improved=IMPROVED_AI_AVAILABLE)
            if ai:
                if IMPROVED_AI_AVAILABLE and hasattr(ai, 'process_query'):
                    # Run interactive chat mode for improved AI
                    print("\n🏥 Medical Billing AI Assistant")
                    print("=" * 60)
                    print("🚀 Using enhanced AI with robust timeout handling and memory optimization")
                    print("🎯 Ask questions about medical billing data for providers, revenue, etc.")
                    print("Type 'exit', 'quit', or 'bye' to end the session")
                    print("=" * 60)
                    
                    try:
                        while True:
                            query = input("\n💬 Your Question: ").strip()
                            
                            if query.lower() in ['quit', 'exit', 'bye']:
                                print("👋 Goodbye!")
                                break
                            
                            if not query:
                                continue
                                
                            # Check if input is just a number - likely a mistake
                            if query.isdigit():
                                print("⚠️ You entered just a number. Did you mean to select a menu option?")
                                print("Please enter a complete question or type 'help' to see example questions.")
                                continue
                                
                            print("🤔 Processing query...")
                            start_time = time.time()
                            result = ai.process_query(query)
                            end_time = time.time()
                            print(f"⚡ Query processed in {end_time - start_time:.2f} seconds")
                            
                            print("\n" + "="*70)
                            print(result)
                            print("="*70 + "\n")
                    except KeyboardInterrupt:
                        print("\n👋 Goodbye!")
                    finally:
                        if hasattr(ai, 'cleanup'):
                            ai.cleanup()
                else:
                    # Use standard chat interface for original AI
                    ai.chat_interface()
            else:
                print("❌ Could not launch Medical Billing AI Assistant")
                print("💡 Make sure your medical_billing_ai.py and medical_billing_db.py files are present and working")
            continue
            
        else:
            max_option = "9" if SQL_AGENT_AVAILABLE else "9"
            print(f"Invalid option. Please select 1-{max_option}, or type 'exit' to quit.")