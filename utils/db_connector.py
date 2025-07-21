"""
Enhanced database connector supporting SQLite and PostgreSQL.

This module provides a unified interface for connecting to different 
database types while maintaining compatibility with the existing system.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from utils.logger import get_logger
from utils.config import get_config

logger = get_logger()
config = get_config()

class DBConnector:
    """Enhanced database connector supporting SQLite and PostgreSQL"""
    
    def __init__(self, db_url: Optional[str] = None):
        """Initialize database connection
        
        Args:
            db_url: SQLAlchemy connection string (default: from config)
        """
        # If no db_url is provided, use SQLite with the configured path
        if db_url is None:
            db_path = config.get("database.db_path")
            self.db_url = f"sqlite:///{db_path}"
        else:
            self.db_url = db_url
        
        logger.info(f"Initializing DB connector with: {self.db_url}")
        
        # Create engine and session
        try:
            self.engine = create_engine(self.db_url)
            self.Session = sessionmaker(bind=self.engine)
            logger.debug("DB connector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DB connector: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a SQL query
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Query results
        """
        try:
            logger.debug(f"Executing query: {query}")
            
            with self.engine.connect() as conn:
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                
                # Get column names
                columns = result.keys()
                
                # Get rows
                rows = result.fetchall()
                
                # Convert to list of dicts
                data = [dict(zip(columns, row)) for row in rows]
                
                logger.debug(f"Query returned {len(data)} rows")
                
                return {
                    "success": True,
                    "rows": data,
                    "row_count": len(data),
                    "columns": columns
                }
                
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_query_df(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute a SQL query and return results as a DataFrame
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            DataFrame with query results
        """
        try:
            logger.debug(f"Executing query to DataFrame: {query}")
            
            if params:
                df = pd.read_sql_query(query, self.engine, params=params)
            else:
                df = pd.read_sql_query(query, self.engine)
            
            logger.debug(f"Query returned DataFrame with {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error executing query to DataFrame: {e}")
            # Return empty DataFrame on error
            return pd.DataFrame()
    
    def get_session(self):
        """Get a SQLAlchemy session
        
        Returns:
            SQLAlchemy session
        """
        return self.Session()
    
    def get_table_schema(self, table_name: str) -> List[Tuple[str, str]]:
        """Get schema information for a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of (column_name, type) tuples
        """
        try:
            logger.debug(f"Getting schema for table: {table_name}")
            
            # For SQLite, use pragma table_info
            if self.db_url.startswith("sqlite"):
                query = f"PRAGMA table_info({table_name})"
                result = self.execute_query(query)
                
                if result["success"]:
                    # Extract column names and types
                    schema = [(row["name"], row["type"]) for row in result["rows"]]
                    return schema
            
            # For other databases, use information_schema
            else:
                query = f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                """
                result = self.execute_query(query)
                
                if result["success"]:
                    # Extract column names and types
                    schema = [(row["column_name"], row["data_type"]) for row in result["rows"]]
                    return schema
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting table schema: {e}")
            return []
    
    def list_tables(self) -> List[str]:
        """List all tables in the database
        
        Returns:
            List of table names
        """
        try:
            logger.debug("Listing tables in database")
            
            # For SQLite, use sqlite_master
            if self.db_url.startswith("sqlite"):
                query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                result = self.execute_query(query)
                
                if result["success"]:
                    return [row["name"] for row in result["rows"]]
            
            # For other databases, use information_schema
            else:
                query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                """
                result = self.execute_query(query)
                
                if result["success"]:
                    return [row["table_name"] for row in result["rows"]]
            
            return []
            
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return []
    
    def close(self):
        """Close the database connection
        """
        try:
            logger.debug("Closing database connection")
            self.engine.dispose()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")