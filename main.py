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

# === CONFIG ===
# Homelab (preferred)
HOMELAB_OLLAMA_URL = "http://ada.tailf21bf8.ts.net:11434"
HOMELAB_MODEL = "llama3.3:70b"

# Laptop (fallback)
LAPTOP_OLLAMA_URL = "http://localhost:11434"
LAPTOP_MODEL = "llama3.1:8b"
CSV_ROOT = "csv_folder"
META_DIR = Path(CSV_ROOT) / "meta"
LOG_FILE = "query_log.txt"
CLARIFICATION_LOG = "clarification_log.txt"

# CLI Argument Parsing
parser = argparse.ArgumentParser(description="Medical Billing AI Assistant")
parser.add_argument("--model", help="Specify the model to use (e.g., llama3:70b or llama3.3:70b)", default="llama3.3:70b")
parser.add_argument("--chat", action="store_true", help="Launch MedicalBillingAI assistant on startup")
args = parser.parse_args()

MODEL_NAME = args.model

# === Helper: Check Remote Ollama ===
def is_ollama_running(url):
    try:
        res = requests.get(f"{url}/api/tags", timeout=3)
        return res.status_code == 200
    except Exception:
        return False

if is_ollama_running(HOMELAB_OLLAMA_URL):
    OLLAMA_URL = HOMELAB_OLLAMA_URL
    MODEL_NAME = HOMELAB_MODEL
    print("✅ Using Homelab Ollama server.")
elif is_ollama_running(LAPTOP_OLLAMA_URL):
    OLLAMA_URL = LAPTOP_OLLAMA_URL
    MODEL_NAME = LAPTOP_MODEL
    print("✅ Using Laptop Ollama server.")
else:
    raise RuntimeError("❌ No Ollama server is available. Please start one on your homelab or laptop.")

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

# === DataFrame Preprocessing ===
def preprocess_dataframe(df):
    df = df.copy()
    df.columns = [col.strip().replace(' ', '_').lower() for col in df.columns]
    for col in df.columns:
        if 'date' in col:
            try:
                df[col] = pd.to_datetime(df[col], format='%m-%d-%Y', errors='coerce')
            except Exception:
                pass
    return df

# === Load All Documents and DataFrame ===
def load_all_documents(csv_root, descriptions):
    all_docs = []
    all_rows = []
    for dirpath, _, filenames in os.walk(csv_root):
        if "meta" in dirpath:
            continue
        for filename in filenames:
            if filename.endswith(".csv"):
                file_path = Path(dirpath) / filename
                category = Path(dirpath).name
                context = descriptions.get(category, "")
                date = parse_date_from_filename(filename)
                try:
                    df = pd.read_csv(file_path)
                    df["source"] = str(file_path)
                    df["category"] = category
                    df["description"] = context
                    df["parsed_date"] = date
                    all_rows.append(df)
                except Exception as e:
                    print(f"⚠️ Could not read {file_path}: {e}")
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                doc = Document(
                    text=text,
                    metadata={
                        "source": str(file_path),
                        "category": category,
                        "description": context,
                        "date": date
                    }
                )
                all_docs.append(doc)
    combined_df = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    return all_docs, combined_df

# === Load Data ===
descriptions = load_md_descriptions(META_DIR)
documents, combined_df = load_all_documents(CSV_ROOT, descriptions)
combined_df = preprocess_dataframe(combined_df)

# === LlamaIndex Engines ===
llm = Ollama(model=MODEL_NAME, base_url=OLLAMA_URL)
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(llm=llm)

# === Pandas Engine for Structured Queries ===
column_context = """
This table contains financial records. Look for fields like Patient, Date, Amount, Cash Applied, Provider, Service Date, etc.
The goal is to answer structured questions like "Who earned the most?", "Total earned per provider", or "Sum of payments in June 2025".
"""
pandas_engine = PandasQueryEngine(df=combined_df, llm=llm, context_str=column_context)

# === Load Clarifications for Session ===
session_clarifications = load_clarifications(CLARIFICATION_LOG)

# === Function to Initialize Medical Billing AI ===
def initialize_medical_billing_ai():
    """Initialize and return MedicalBillingAI instance"""
    try:
        from medical_billing_ai import MedicalBillingAI
        from medical_billing_db import MedicalBillingDB
        
        print("🤖 Initializing Medical Billing AI Assistant...")
        db = MedicalBillingDB()
        ai = MedicalBillingAI(db_instance=db, ollama_url=OLLAMA_URL, model=MODEL_NAME)
        print("✅ Medical Billing AI Assistant ready!")
        return ai
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("💡 Make sure you have the medical_billing_ai.py and medical_billing_db.py files")
        return None
        
    except Exception as e:
        print(f"❌ Error initializing Medical Billing AI: {e}")
        print("💡 Check that your database and AI modules are properly configured")
        return None

# === Conversational CLI ===
def get_column_candidates(df, keywords):
    return [col for col in df.columns if any(word in col.lower() for word in keywords)]

def conversational_router(question, df, clarifications, log_path):
    q = question.lower()
    ambiguous_terms = {
        "revenue": ["revenue", "amount", "paid", "cash"],
        "date": ["date", "parsed"],
        "person": ["person", "patient", "provider", "name"],
        "payer": ["payer", "insurance", "company", "plan"],
    }
    for term, keywords in ambiguous_terms.items():
        if term in q or any(word in q for word in keywords):
            candidates = get_column_candidates(df, keywords)
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
        return pandas_engine.query(f"{question}\n{context}")
    else:
        return query_engine.query(question)

# === Menu and CLI Helpers ===
def print_menu():
    print("""
=== Data Agent Menu ===
1. Ask a question
2. Show available columns
3. Show session clarifications
4. Help
5. Exit
6. Launch Medical Billing AI Assistant (Chat Mode)
""")

def show_columns(df):
    print("\nAvailable columns:")
    for col in df.columns:
        print(f"- {col}")

def show_clarifications(clarifications):
    print("\nSession clarifications:")
    if not clarifications:
        print("(None yet)")
    for k, v in clarifications.items():
        print(f"- {k}: {v}")

def print_help():
    print("""
Type the number of the menu option you want to use.
- 'Ask a question' lets you interact with the agent about your data.
- 'Show available columns' lists all columns in your loaded CSVs.
- 'Show session clarifications' displays which columns the agent is using for ambiguous terms.
- 'Help' shows this message.
- 'Exit' quits the program. You can also type 'exit' or 'quit' at any prompt.
- 'Launch Medical Billing AI Assistant' starts the specialized medical billing chat interface.
""")

# === Main CLI Loop ===
if __name__ == "__main__":
    if args.chat:
        ai = initialize_medical_billing_ai()
        if ai:
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
    print("\n🤖 Welcome to your Data Agent!\nThe agent will clarify ambiguous terms and learn your preferences.\n")
    
    while True:
        print_menu()
        choice = input("Select an option (1-6): ").strip().lower()
        
        if choice in ('5', 'exit', 'quit', '/quit'):
            print("👋 Goodbye!")
            break
            
        elif choice == '1':
            question = input("\nAsk your question (or type 'exit' to return to menu): ")
            if question.lower() in ("exit", "quit", "/quit"):
                continue
            try:
                result = conversational_router(question, combined_df, session_clarifications, CLARIFICATION_LOG)
                print("\n=== AI Response ===\n")
                print(result)
                with open(LOG_FILE, "a") as log_file:
                    log_file.write(f"Q: {question}\nA: {result}\n{'-'*40}\n")
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == '2':
            show_columns(combined_df)
            
        elif choice == '3':
            show_clarifications(session_clarifications)
            
        elif choice == '4':
            print_help()
            
        elif choice == '6':
            # Initialize and launch Medical Billing AI
            ai = initialize_medical_billing_ai()
            if ai:
                ai.chat_interface()
            else:
                print("❌ Could not launch Medical Billing AI Assistant")
                print("💡 Make sure your medical_billing_ai.py and medical_billing_db.py files are present and working")
            continue
            
        else:
            print("Invalid option. Please select 1-6, or type 'exit' to quit.")