import subprocess
import time
import requests
import os
import re
from pathlib import Path
from datetime import datetime
from llama_index.core import VectorStoreIndex, Document
from llama_index.llms.ollama import Ollama

# === CONFIG ===
MODEL_NAME = "llama3.1:8b"
OLLAMA_URL = "http://localhost:11434"
CSV_ROOT = "csv_folder"
META_DIR = Path(CSV_ROOT) / "meta"
LOG_FILE = "query_log.txt"

# === Ollama Bootstrapping ===
def is_ollama_running():
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return res.status_code == 200
    except Exception:
        return False

def start_ollama_model(model_name):
    print(f"🦙 Starting Ollama model: {model_name}")
    subprocess.Popen(["ollama", "run", model_name])
    print("⏳ Waiting for Ollama to become available...")
    for _ in range(10):
        if is_ollama_running():
            print("✅ Ollama is running.")
            return
        time.sleep(2)
    raise RuntimeError("Ollama did not start in time.")

if not is_ollama_running():
    start_ollama_model(MODEL_NAME)

# === File & Metadata Utilities ===
def parse_date_from_filename(filename):
    patterns = [
        r"(\d{4})[-_](\d{1,2})[-_](\d{1,2})",  # 2025-06-30
        r"(\d{4})[-_](\d{1,2})",               # 2025-06
        r"(\d{4})[ -_]?([A-Za-z]+)"           # 2025_June
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

def load_md_descriptions(meta_dir):
    descriptions = {}
    if meta_dir.exists():
        for md_file in meta_dir.glob("*.md"):
            with open(md_file, "r") as f:
                descriptions[md_file.stem] = f.read()
    return descriptions

def load_all_documents(csv_root, descriptions):
    all_docs = []
    for dirpath, _, filenames in os.walk(csv_root):
        if "meta" in dirpath:
            continue  # Skip metadata
        for filename in filenames:
            if filename.endswith(".csv"):
                file_path = Path(dirpath) / filename
                category = Path(dirpath).name
                context = descriptions.get(category, "")
                date = parse_date_from_filename(filename)
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
    return all_docs

# === Load and Index Documents ===
md_descriptions = load_md_descriptions(META_DIR)
documents = load_all_documents(CSV_ROOT, md_descriptions)
index = VectorStoreIndex.from_documents(documents)
llm = Ollama(model=MODEL_NAME)
query_engine = index.as_query_engine(llm=llm)

from llama_index.core.query_engine import PandasQueryEngine
from llama_index.core.schema import TextNode

def summarize_category(category: str, date_prefix=None):
    filtered_docs = [
        doc for doc in documents
        if doc.metadata.get("category") == category and
        (not date_prefix or (doc.metadata.get("date") or "").startswith(date_prefix))
    ]
    if not filtered_docs:
        return f"No data found for category '{category}' with date '{date_prefix}'"
    
    nodes = [TextNode(text=doc.text) for doc in filtered_docs]
    temp_index = VectorStoreIndex(nodes)
    temp_engine = temp_index.as_query_engine(llm=llm)

    return temp_engine.query(f"Summarize the {category} data for {date_prefix or 'all available dates'}.")

# === Interactive CLI ===
print("\n🤖 Ask a question about your data (or type 'exit' to quit)")

while True:
    question = input("\n> ")
    if question.lower() in ("exit", "quit"):
        print("👋 Goodbye!")
        break

    response = query_engine.query(question)
    print("\n=== AI Response ===\n")
    print(response)

    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"Q: {question}\nA: {response}\n{'-'*40}\n")