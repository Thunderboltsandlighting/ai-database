"""
SQL Agent for HVLC_DB Medical Billing

This module implements a LangChain-based SQL agent that translates natural language
queries into SQL and executes them against the medical billing database.
"""

import os
from typing import Optional, Dict, Any, List
import logging
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_ollama import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from sqlalchemy import create_engine, text
from utils.logger import get_logger
from utils.config import get_config

logger = get_logger()
config = get_config()

class MedicalBillingSQLAgent:
    """SQL Agent for natural language queries to medical billing database"""
    
    def __init__(self, db_url: Optional[str] = None, ollama_url: Optional[str] = None, 
                 model: Optional[str] = None, verbose: bool = False):
        """Initialize the SQL Agent with database and LLM configuration
        
        Args:
            db_url: SQLAlchemy connection string (default: from config)
            ollama_url: Ollama API URL (default: from config)
            model: Ollama model name (default: from config)
            verbose: Whether to output detailed logs and streaming responses
        """
        # Get configuration
        self.db_url = db_url or f"sqlite:///{config.get('database.db_path')}"
        self.ollama_url = ollama_url or config.get("ollama.homelab_url") or config.get("ollama.laptop_url")
        self.model = model or config.get("ollama.homelab_model") or config.get("ollama.laptop_model")
        self.verbose = verbose
        
        logger.info(f"Initializing SQL Agent with DB: {self.db_url}")
        logger.info(f"Using Ollama at {self.ollama_url} with model {self.model}")
        
        # Configure callbacks for streaming output if verbose
        callbacks = None
        if self.verbose:
            callbacks = CallbackManager([StreamingStdOutCallbackHandler()])
        
        try:
            # Initialize database connection
            self.db = SQLDatabase.from_uri(self.db_url)
            
            # Configure LLM
            self.llm = Ollama(
                model=self.model,
                base_url=self.ollama_url,
                # langchain_ollama doesn't support request_timeout directly
                # Configure other parameters as needed
                callbacks=callbacks if callbacks else None
            )
            
            # Create SQL toolkit and agent
            self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
            
            # Initialize the SQL agent
            self.agent = create_sql_agent(
                llm=self.llm,
                toolkit=self.toolkit,
                verbose=self.verbose,
                agent_type="zero-shot-react-description",
                handle_parsing_errors=True,
                top_k=10  # Return top 10 rows by default
            )
            
            logger.info("SQL Agent initialization complete")
        except Exception as e:
            logger.error(f"Error initializing SQL Agent: {e}")
            raise
    
    def get_schema_str(self) -> str:
        """Get the database schema as a string
        
        Returns:
            A string representation of the database schema
        """
        return self.db.get_table_info()
    
    def process_query(self, query: str) -> str:
        """Process a natural language query using the SQL agent
        
        Args:
            query: The natural language query to process
            
        Returns:
            The formatted response from the SQL agent
        """
        try:
            logger.info(f"Processing SQL agent query: {query}")
            
            # Format the query with medical billing context
            enhanced_query = f"""
            You are analyzing medical billing data. The database contains information about
            healthcare providers, payment transactions, and billing terminology.
            
            Answer the following question using SQL queries:
            {query}
            
            Format your final answer in a clear, concise way with any relevant numbers.
            Use bullet points for multiple items and include summary statistics where appropriate.
            """
            
            # Execute the query
            result = self.agent.run(enhanced_query)
            logger.info(f"SQL agent query completed successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing SQL agent query: {e}")
            return f"I encountered an error while processing your query: {str(e)}"
    
    def execute_direct_sql(self, sql_query: str) -> Dict[str, Any]:
        """Execute a raw SQL query directly
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            Dictionary with query results
        """
        try:
            logger.info(f"Executing direct SQL query: {sql_query}")
            
            # Create an engine directly for this query
            engine = create_engine(self.db_url)
            
            # Execute the query
            with engine.connect() as conn:
                result = conn.execute(text(sql_query))
                
                # Get column names
                columns = result.keys()
                
                # Get rows
                rows = result.fetchall()
                
                # Convert to list of dicts
                data = [dict(zip(columns, row)) for row in rows]
                
                logger.info(f"Direct SQL query returned {len(data)} rows")
                
                return {
                    "success": True,
                    "rows": data,
                    "row_count": len(data),
                    "columns": columns
                }
        
        except Exception as e:
            logger.error(f"Error executing direct SQL query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_tables(self) -> List[str]:
        """Get list of tables in the database
        
        Returns:
            List of table names
        """
        return self.db.get_usable_table_names()
    
    def get_table_info(self, table_name: str) -> str:
        """Get information about a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            String with table information
        """
        return self.db.get_table_info_no_sample([table_name])