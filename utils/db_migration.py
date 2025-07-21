"""
Database migration utilities for HVLC_DB.

This module provides tools for migrating data between different database types,
such as SQLite and PostgreSQL.
"""

import os
import sys
import argparse
import time
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, text
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from utils.config import get_config
from utils.logger import get_logger
from utils.db_connector import DBConnector
from utils.db_models import Base, create_all_tables

# Configure logging
logger = get_logger()
config = get_config()


class DatabaseMigrator:
    """Utility for migrating data between databases"""
    
    def __init__(self, source_url: str, target_url: str):
        """Initialize migrator
        
        Args:
            source_url: SQLAlchemy URL for source database
            target_url: SQLAlchemy URL for target database
        """
        self.source_url = source_url
        self.target_url = target_url
        
        # Create engines
        self.source_engine = create_engine(source_url)
        self.target_engine = create_engine(target_url)
        
        logger.info(f"Initialized database migrator from {source_url} to {target_url}")
    
    def check_compatibility(self) -> Tuple[bool, List[str]]:
        """Check compatibility between source and target databases
        
        Returns:
            Tuple of (is_compatible, issues)
        """
        issues = []
        
        # Check source database
        try:
            source_inspector = inspect(self.source_engine)
            source_tables = source_inspector.get_table_names()
            
            if not source_tables:
                issues.append("Source database has no tables")
                
            logger.info(f"Source database has {len(source_tables)} tables")
            
        except Exception as e:
            issues.append(f"Error inspecting source database: {e}")
            return False, issues
        
        # Check target database
        try:
            target_inspector = inspect(self.target_engine)
            target_tables = target_inspector.get_table_names()
            
            logger.info(f"Target database has {len(target_tables)} tables")
            
        except Exception as e:
            issues.append(f"Error inspecting target database: {e}")
            return False, issues
        
        return len(issues) == 0, issues
    
    def create_target_schema(self) -> bool:
        """Create schema in target database using SQLAlchemy models
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Creating schema in target database")
            
            # Create all tables
            create_all_tables(self.target_engine)
            
            logger.info("Schema created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating schema: {e}")
            return False
    
    def get_table_rowcount(self, engine, table_name: str) -> int:
        """Get row count for a table
        
        Args:
            engine: SQLAlchemy engine
            table_name: Table name
            
        Returns:
            Row count
        """
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
        except Exception as e:
            logger.warning(f"Error getting row count for {table_name}: {e}")
            return 0
    
    def migrate_table(self, table_name: str, batch_size: int = 1000) -> Dict[str, Any]:
        """Migrate data from one table
        
        Args:
            table_name: Table name
            batch_size: Number of rows to migrate in each batch
            
        Returns:
            Migration statistics
        """
        start_time = time.time()
        
        try:
            # Get source table
            source_inspector = inspect(self.source_engine)
            
            if table_name not in source_inspector.get_table_names():
                return {
                    "table": table_name,
                    "success": False,
                    "error": f"Table {table_name} not found in source database",
                    "rows_migrated": 0,
                    "elapsed_time": time.time() - start_time
                }
            
            # Get row count
            total_rows = self.get_table_rowcount(self.source_engine, table_name)
            
            if total_rows == 0:
                logger.info(f"Table {table_name} is empty, skipping")
                return {
                    "table": table_name,
                    "success": True,
                    "rows_migrated": 0,
                    "elapsed_time": time.time() - start_time
                }
            
            logger.info(f"Migrating {total_rows} rows from {table_name}")
            
            # Get primary key columns
            pk_columns = source_inspector.get_pk_constraint(table_name).get("constrained_columns", [])
            if not pk_columns:
                logger.warning(f"Table {table_name} has no primary key, using all columns for ordering")
                pk_columns = [c["name"] for c in source_inspector.get_columns(table_name)]
            
            # Create table metadata
            source_meta = MetaData()
            source_table = Table(table_name, source_meta, autoload_with=self.source_engine)
            
            # Process in batches
            offset = 0
            migrated_rows = 0
            
            with tqdm(total=total_rows, desc=f"Migrating {table_name}", unit="rows") as pbar:
                while offset < total_rows:
                    # Build query for batch
                    order_by = ", ".join(pk_columns)
                    query = f"SELECT * FROM {table_name} ORDER BY {order_by} LIMIT {batch_size} OFFSET {offset}"
                    
                    # Get batch data
                    batch_df = pd.read_sql(query, self.source_engine)
                    
                    if batch_df.empty:
                        break
                    
                    # Insert into target
                    batch_df.to_sql(
                        table_name, 
                        self.target_engine, 
                        if_exists="append", 
                        index=False,
                        method="multi"
                    )
                    
                    # Update counters
                    batch_rows = len(batch_df)
                    migrated_rows += batch_rows
                    offset += batch_size
                    pbar.update(batch_rows)
            
            # Verify migration
            target_rows = self.get_table_rowcount(self.target_engine, table_name)
            
            logger.info(f"Migrated {migrated_rows} rows from {table_name} ({target_rows} in target)")
            
            return {
                "table": table_name,
                "success": True,
                "rows_migrated": migrated_rows,
                "rows_in_target": target_rows,
                "elapsed_time": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error migrating table {table_name}: {e}")
            return {
                "table": table_name,
                "success": False,
                "error": str(e),
                "rows_migrated": 0,
                "elapsed_time": time.time() - start_time
            }
    
    def migrate_all(self, tables: List[str] = None, batch_size: int = 1000) -> Dict[str, Any]:
        """Migrate all tables from source to target
        
        Args:
            tables: List of tables to migrate (all if None)
            batch_size: Number of rows to migrate in each batch
            
        Returns:
            Migration statistics
        """
        start_time = time.time()
        
        # Check compatibility
        compatible, issues = self.check_compatibility()
        
        if not compatible:
            return {
                "success": False,
                "error": "Compatibility check failed",
                "issues": issues,
                "elapsed_time": time.time() - start_time
            }
        
        # Create schema in target database
        if not self.create_target_schema():
            return {
                "success": False,
                "error": "Failed to create schema in target database",
                "elapsed_time": time.time() - start_time
            }
        
        # Get tables to migrate
        if tables is None:
            source_inspector = inspect(self.source_engine)
            tables = source_inspector.get_table_names()
        
        logger.info(f"Migrating {len(tables)} tables")
        
        # Migrate each table
        results = {}
        success_count = 0
        
        for table in tables:
            result = self.migrate_table(table, batch_size)
            results[table] = result
            
            if result["success"]:
                success_count += 1
        
        # Return statistics
        return {
            "success": success_count == len(tables),
            "tables_total": len(tables),
            "tables_migrated": success_count,
            "table_results": results,
            "elapsed_time": time.time() - start_time
        }


def get_migrator_from_config(source_type: str = None, target_type: str = None) -> DatabaseMigrator:
    """Create migrator from configuration
    
    Args:
        source_type: Source database type (sqlite, postgresql)
        target_type: Target database type (sqlite, postgresql)
        
    Returns:
        DatabaseMigrator instance
    """
    cfg = get_config()
    
    # Set default types
    if source_type is None:
        source_type = cfg.get("database.type", "sqlite")
    
    if target_type is None:
        if source_type == "sqlite":
            target_type = "postgresql"
        else:
            target_type = "sqlite"
    
    # Create temporary config for source and target
    source_cfg = get_config()
    source_cfg.set("database.type", source_type)
    
    target_cfg = get_config()
    target_cfg.set("database.type", target_type)
    
    # Get URLs
    source_url = source_cfg.get_db_url()
    target_url = target_cfg.get_db_url()
    
    return DatabaseMigrator(source_url, target_url)


def main():
    """Command-line interface for database migration"""
    parser = argparse.ArgumentParser(description="Database Migration Tool")
    
    parser.add_argument(
        "--source", 
        choices=["sqlite", "postgresql"], 
        help="Source database type (default: from config)"
    )
    
    parser.add_argument(
        "--target", 
        choices=["sqlite", "postgresql"], 
        help="Target database type (default: opposite of source)"
    )
    
    parser.add_argument(
        "--tables", 
        nargs="+", 
        help="Specific tables to migrate (default: all tables)"
    )
    
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=1000, 
        help="Rows to migrate in each batch (default: 1000)"
    )
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = get_migrator_from_config(args.source, args.target)
    
    # Run migration
    print(f"Starting migration from {args.source or 'current config'} to {args.target or 'opposite type'}...")
    
    result = migrator.migrate_all(args.tables, args.batch_size)
    
    if result["success"]:
        print(f"Migration completed successfully in {result['elapsed_time']:.1f} seconds")
        print(f"Migrated {result['tables_migrated']}/{result['tables_total']} tables")
        
        # Show failed tables
        failed_tables = [t for t, r in result["table_results"].items() if not r["success"]]
        if failed_tables:
            print(f"Failed tables: {', '.join(failed_tables)}")
    else:
        print(f"Migration failed: {result.get('error', 'Unknown error')}")
        if "issues" in result:
            print("Issues:")
            for issue in result["issues"]:
                print(f"- {issue}")


if __name__ == "__main__":
    main()