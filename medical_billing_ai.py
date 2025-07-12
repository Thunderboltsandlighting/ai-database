import sqlite3
import json
import time
import logging
from datetime import datetime
from pathlib import Path
import requests
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalBillingAI:
    def __init__(self, db_instance=None, ollama_url="http://localhost:11434", model="llama3.1:8b", timeout=30):
        """Initialize Medical Billing AI with robust timeout handling"""
        self.db = db_instance
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout
        self.knowledge_base = self.load_knowledge_base()
        self.clarifications = self.load_clarifications()
        
        # Initialize database connection
        if self.db:
            logger.info("Database connection established")
        else:
            logger.warning("No database instance provided")
            
    def load_knowledge_base(self) -> str:
        """Load knowledge base from markdown file"""
        try:
            kb_path = Path("medical_billing_knowledge.md")
            if kb_path.exists():
                with open(kb_path, 'r') as f:
                    content = f.read()
                logger.info(f"Knowledge base loaded: {len(content)} bytes")
                return content
            else:
                logger.warning("Knowledge base file not found")
                return ""
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            return ""
    
    def load_clarifications(self) -> Dict[str, str]:
        """Load clarifications from log file"""
        try:
            with open("clarification_log.txt", 'r') as f:
                clarifications = json.load(f)
            logger.info(f"Loaded {len(clarifications)} clarifications")
            return clarifications
        except Exception as e:
            logger.info("No existing clarifications found")
            return {}
    
    def query_ollama_with_timeout(self, prompt: str, timeout_seconds: int = 30) -> Optional[str]:
        """Query Ollama with timeout handling and fallback"""
        try:
            logger.info(f"Querying Ollama at {self.ollama_url} with model {self.model}")
            logger.info(f"Using timeout: {timeout_seconds} seconds")
            
            # Prepare the request
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 2000
                }
            }
            
            # Make the request with timeout
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=timeout_seconds,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                logger.error(f"Ollama returned status code: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout error after {timeout_seconds} seconds")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Connection error - Ollama server may be unavailable")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying Ollama: {e}")
            return None
    
    def fallback_response(self, question: str) -> str:
        """Provide a fallback response when AI and database fail"""
        question_lower = question.lower()
        
        # Try to provide helpful responses based on question patterns
        if "clients" in question_lower and "isabel" in question_lower and "june" in question_lower:
            return """Based on your question about Isabel's clients in June 2025, I would need to query the database directly. 
            
Here's what you can try:
1. Check if there's billing data for Isabel in June 2025
2. Look for records where provider name contains 'Isabel' and date is between 2025-06-01 and 2025-06-30
3. Count distinct patient names for that period

The timeout issue suggests either:
- The Ollama server is overloaded
- The query is too complex for the current timeout setting
- There's a connectivity issue

Try using a direct database query instead of the AI interface."""
        
        elif "revenue" in question_lower:
            return """For revenue questions, you can try:
1. Direct database queries for faster results
2. Break down the question into smaller parts
3. Use specific date ranges
4. Check the billing_data table directly"""
        
        return f"""I encountered a timeout while processing your question: "{question}"

This could be due to:
1. Ollama server timeout (current setting: {self.timeout} seconds)
2. Complex query requiring more processing time
3. Database connectivity issues
4. Server overload

**Immediate Solutions:**
- Try simpler, more specific questions
- Use direct database queries
- Check Ollama server status
- Restart the Ollama service if needed

**For your specific question, consider:**
- Breaking it into smaller parts
- Using more specific criteria
- Trying the same query during off-peak hours"""
    
    def process_query(self, question: str) -> str:
        """Process a query with timeout handling and fallbacks"""
        start_time = time.time()
        
        # Try AI query first with short timeout
        logger.info("Attempting AI query with reduced timeout...")
        ai_response = self.query_ollama_with_timeout(
            f"Answer this medical billing question briefly: {question}",
            timeout_seconds=30
        )
        
        if ai_response:
            elapsed = time.time() - start_time
            logger.info(f"AI query successful in {elapsed:.2f} seconds")
            return ai_response
        
        # If AI fails, provide fallback response
        logger.info("AI query failed, providing fallback response...")
        fallback_response = self.fallback_response(question)
        
        elapsed = time.time() - start_time
        logger.info(f"Fallback response provided in {elapsed:.2f} seconds")
        return fallback_response
    
    def chat_interface(self):
        """Interactive chat interface with improved error handling"""
        print("\n🏥 Medical Billing AI Assistant")
        print("=" * 60)
        print("🚀 Optimized for timeout handling and fallback responses")
        print("🎯 Key Features:")
        print("• 30-second timeout for faster responses")
        print("• Automatic fallback when AI is unavailable")
        print("• Specific guidance for common queries")
        print("• Direct database query suggestions")
        print()
        print("Type 'help' for assistance or 'quit' to exit.")
        print("=" * 60)
        
        while True:
            try:
                question = input("\n💬 Your Question: ").strip()
                
                if question.lower() in ['quit', 'exit', 'bye']:
                    print("👋 Goodbye!")
                    break
                    
                if question.lower() == 'help':
                    self.show_help()
                    continue
                    
                if not question:
                    continue
                
                print("🤔 Processing your query...")
                response = self.process_query(question)
                print(f"\n{'='*70}")
                print(response)
                print('='*70)
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Unexpected error in chat interface: {e}")
                print(f"❌ An unexpected error occurred: {e}")
                print("💡 Please try again or type 'quit' to exit.")
    
    def show_help(self):
        """Show help information"""
        print("""
🆘 HELP - Medical Billing AI Assistant

TIMEOUT FIXES:
• System now uses 30-second timeout (down from 180 seconds)
• Automatic fallback when AI is unavailable
• Specific guidance for common query types

SAMPLE QUERIES:
• "How many clients did Isabel see in June 2025?"
• "What was the total revenue in June 2025?"
• "Show me provider performance data"

TROUBLESHOOTING:
• If you get timeout errors, the system will provide specific guidance
• Questions are processed with reduced timeout for faster responses
• Fallback responses include direct database query suggestions

TIPS:
• Be specific with dates and provider names
• Try simpler questions if complex ones timeout
• Use the suggestions in fallback responses
• Consider using direct database queries for complex analysis

The system is now optimized to handle timeout issues gracefully!
        """)