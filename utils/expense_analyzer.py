"""
Expense Analysis Module for Month-to-Month Overhead Tracking

This module provides utilities for analyzing variable and fixed expenses
to support comprehensive profitability analysis.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from utils.logger import get_logger
from utils.config import get_config

logger = get_logger()
config = get_config()

class ExpenseAnalyzer:
    """Handles month-to-month expense analysis and profitability calculations"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.get_db_path()
    
    def create_expense_tables(self):
        """Create expense-related tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript("""
                -- Enhanced expense transactions table
                CREATE TABLE IF NOT EXISTS expense_transactions (
                    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category VARCHAR(50) NOT NULL,              
                    subcategory VARCHAR(100),                   
                    expense_date DATE NOT NULL,                 
                    amount DECIMAL(10,2) NOT NULL,             
                    budgeted_amount DECIMAL(10,2),             
                    variance DECIMAL(10,2),                    
                    due_date DATE,                             
                    frequency VARCHAR(20) DEFAULT 'monthly',    
                    status VARCHAR(20) DEFAULT 'active',       
                    is_variable BOOLEAN DEFAULT 0,             
                    usage_metric VARCHAR(50),                  
                    usage_count INTEGER,                       
                    rate_per_unit DECIMAL(10,4),              
                    notes TEXT,                                
                    upload_batch VARCHAR(50),                  
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Variable expense rate definitions
                CREATE TABLE IF NOT EXISTS variable_expense_rates (
                    rate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category VARCHAR(50) NOT NULL,
                    subcategory VARCHAR(100),
                    rate_type VARCHAR(30),                     
                    base_amount DECIMAL(10,2) DEFAULT 0,       
                    rate_per_unit DECIMAL(10,4),              
                    tier_breakpoints TEXT,                     
                    effective_date DATE,
                    end_date DATE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Monthly expense summaries
                CREATE TABLE IF NOT EXISTS monthly_expense_summary (
                    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    total_amount DECIMAL(12,2) NOT NULL,
                    budgeted_amount DECIMAL(12,2),
                    variance DECIMAL(12,2),
                    transaction_count INTEGER,
                    variable_portion DECIMAL(12,2) DEFAULT 0,
                    fixed_portion DECIMAL(12,2) DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year, month, category)
                );
                
                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_expense_date ON expense_transactions(expense_date);
                CREATE INDEX IF NOT EXISTS idx_expense_category ON expense_transactions(category, subcategory);
                CREATE INDEX IF NOT EXISTS idx_expense_variable ON expense_transactions(is_variable);
                CREATE INDEX IF NOT EXISTS idx_monthly_expense ON monthly_expense_summary(year, month);
            """)
            conn.commit()
            logger.info("Expense tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating expense tables: {e}")
            raise
        finally:
            conn.close()
    
    def calculate_monthly_variance(self, year: int, month: int) -> Dict[str, Any]:
        """Calculate expense variance for a specific month"""
        conn = sqlite3.connect(self.db_path)
        try:
            query = """
                SELECT 
                    category,
                    subcategory,
                    SUM(amount) as actual_amount,
                    SUM(budgeted_amount) as budgeted_amount,
                    SUM(amount - COALESCE(budgeted_amount, amount)) as variance,
                    CASE 
                        WHEN SUM(budgeted_amount) > 0 THEN 
                            ROUND((SUM(amount - COALESCE(budgeted_amount, amount)) / SUM(budgeted_amount) * 100), 2)
                        ELSE 0 
                    END as variance_percentage
                FROM expense_transactions
                WHERE strftime('%Y', expense_date) = ? AND strftime('%m', expense_date) = ?
                GROUP BY category, subcategory
                ORDER BY variance_percentage DESC
            """
            
            df = pd.read_sql_query(query, conn, params=(str(year), f"{month:02d}"))
            
            total_actual = df['actual_amount'].sum()
            total_budgeted = df['budgeted_amount'].sum()
            total_variance = df['variance'].sum()
            
            return {
                'year': year,
                'month': month,
                'total_actual': total_actual,
                'total_budgeted': total_budgeted,
                'total_variance': total_variance,
                'variance_percentage': (total_variance / total_budgeted * 100) if total_budgeted > 0 else 0,
                'category_details': df.to_dict('records')
            }
        finally:
            conn.close()
    
    def analyze_variable_cost_efficiency(self, provider_id: int = None) -> Dict[str, Any]:
        """Analyze variable cost efficiency by provider"""
        conn = sqlite3.connect(self.db_path)
        try:
            provider_filter = "AND pt.provider_id = ?" if provider_id else ""
            params = [provider_id] if provider_id else []
            
            query = f"""
                SELECT 
                    strftime('%Y-%m', pt.transaction_date) as month,
                    p.provider_name,
                    COUNT(DISTINCT pt.patient_id) as unique_patients,
                    COUNT(pt.transaction_id) as total_transactions,
                    SUM(pt.cash_applied) as revenue,
                    SUM(et.amount) as variable_costs,
                    ROUND(SUM(et.amount) / COUNT(DISTINCT pt.patient_id), 2) as cost_per_patient,
                    ROUND(SUM(et.amount) / COUNT(pt.transaction_id), 2) as cost_per_transaction,
                    ROUND((SUM(pt.cash_applied) - SUM(et.amount)) / SUM(pt.cash_applied) * 100, 2) as contribution_margin
                FROM payment_transactions pt
                JOIN providers p ON pt.provider_id = p.provider_id
                LEFT JOIN expense_transactions et ON strftime('%Y-%m', pt.transaction_date) = strftime('%Y-%m', et.expense_date)
                    AND et.is_variable = 1
                WHERE 1=1 {provider_filter}
                GROUP BY month, p.provider_name
                HAVING COUNT(pt.transaction_id) > 0
                ORDER BY month DESC, contribution_margin DESC
            """
            
            df = pd.read_sql_query(query, conn, params=params)
            
            return {
                'efficiency_analysis': df.to_dict('records'),
                'summary': {
                    'avg_cost_per_patient': df['cost_per_patient'].mean(),
                    'avg_contribution_margin': df['contribution_margin'].mean(),
                    'best_month': df.loc[df['contribution_margin'].idxmax()].to_dict() if not df.empty else None
                }
            }
        finally:
            conn.close()
    
    def calculate_break_even_analysis(self, target_month: str = None) -> Dict[str, Any]:
        """Calculate break-even analysis including variable costs"""
        conn = sqlite3.connect(self.db_path)
        try:
            month_filter = "AND strftime('%Y-%m', expense_date) = ?" if target_month else ""
            params = [target_month] if target_month else []
            
            query = f"""
                SELECT 
                    strftime('%Y-%m', expense_date) as month,
                    SUM(CASE WHEN is_variable = 0 THEN amount ELSE 0 END) as fixed_costs,
                    SUM(CASE WHEN is_variable = 1 THEN amount ELSE 0 END) as variable_costs,
                    SUM(amount) as total_costs,
                    AVG(CASE WHEN is_variable = 1 AND usage_count > 0 THEN amount/usage_count ELSE 0 END) as avg_variable_cost_per_unit
                FROM expense_transactions
                WHERE 1=1 {month_filter}
                GROUP BY month
                ORDER BY month DESC
            """
            
            expense_df = pd.read_sql_query(query, conn, params=params)
            
            # Get average revenue per transaction
            revenue_query = """
                SELECT 
                    strftime('%Y-%m', transaction_date) as month,
                    AVG(cash_applied) as avg_revenue_per_transaction,
                    COUNT(*) as transaction_count
                FROM payment_transactions
                GROUP BY month
                ORDER BY month DESC
            """
            
            revenue_df = pd.read_sql_query(revenue_query, conn)
            
            # Combine data
            combined = expense_df.merge(revenue_df, on='month', how='inner')
            
            # Calculate break-even points
            combined['transactions_for_fixed_costs'] = combined['fixed_costs'] / combined['avg_revenue_per_transaction']
            combined['total_transactions_break_even'] = combined['total_costs'] / combined['avg_revenue_per_transaction']
            
            return {
                'break_even_analysis': combined.to_dict('records'),
                'current_performance': {
                    'avg_monthly_fixed_costs': expense_df['fixed_costs'].mean(),
                    'avg_monthly_variable_costs': expense_df['variable_costs'].mean(),
                    'avg_revenue_per_transaction': revenue_df['avg_revenue_per_transaction'].mean()
                }
            }
        finally:
            conn.close()
    
    def get_expense_trends(self, months_back: int = 12) -> Dict[str, Any]:
        """Get expense trends over time"""
        conn = sqlite3.connect(self.db_path)
        try:
            query = """
                SELECT 
                    strftime('%Y-%m', expense_date) as month,
                    category,
                    SUM(amount) as total_amount,
                    SUM(CASE WHEN is_variable = 1 THEN amount ELSE 0 END) as variable_amount,
                    SUM(CASE WHEN is_variable = 0 THEN amount ELSE 0 END) as fixed_amount,
                    AVG(amount) as avg_amount,
                    COUNT(*) as transaction_count
                FROM expense_transactions
                WHERE expense_date >= date('now', '-{} months')
                GROUP BY month, category
                ORDER BY month DESC, category
            """.format(months_back)
            
            df = pd.read_sql_query(query, conn)
            
            # Calculate month-over-month changes
            df_pivot = df.pivot(index='month', columns='category', values='total_amount').fillna(0)
            df_change = df_pivot.pct_change().fillna(0) * 100
            
            return {
                'expense_trends': df.to_dict('records'),
                'month_over_month_changes': df_change.to_dict('index'),
                'category_totals': df.groupby('category')['total_amount'].sum().to_dict()
            }
        finally:
            conn.close()
    
    def update_monthly_summaries(self):
        """Update monthly expense summary table"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Clear existing summaries
            conn.execute("DELETE FROM monthly_expense_summary")
            
            # Rebuild summaries
            query = """
                INSERT INTO monthly_expense_summary 
                (year, month, category, total_amount, budgeted_amount, variance, 
                 transaction_count, variable_portion, fixed_portion)
                SELECT 
                    CAST(strftime('%Y', expense_date) AS INTEGER) as year,
                    CAST(strftime('%m', expense_date) AS INTEGER) as month,
                    category,
                    SUM(amount) as total_amount,
                    SUM(budgeted_amount) as budgeted_amount,
                    SUM(amount - COALESCE(budgeted_amount, amount)) as variance,
                    COUNT(*) as transaction_count,
                    SUM(CASE WHEN is_variable = 1 THEN amount ELSE 0 END) as variable_portion,
                    SUM(CASE WHEN is_variable = 0 THEN amount ELSE 0 END) as fixed_portion
                FROM expense_transactions
                GROUP BY year, month, category
            """
            
            conn.execute(query)
            conn.commit()
            logger.info("Monthly expense summaries updated successfully")
        except sqlite3.Error as e:
            logger.error(f"Error updating monthly summaries: {e}")
            raise
        finally:
            conn.close()

def get_expense_analyzer() -> ExpenseAnalyzer:
    """Get a configured expense analyzer instance"""
    return ExpenseAnalyzer() 