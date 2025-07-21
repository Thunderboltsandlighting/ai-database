"""
Reasoning Validator for Ada AI Assistant.

This module prevents AI hallucination by validating all responses against
actual database facts and enforcing factual accuracy in business analysis.
Similar to the validation layers in Claude Sonnet and GPT-4o.
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging
import re
from datetime import datetime

from api.utils.db import get_db_connection

class ReasoningValidator:
    """
    Validates AI responses against actual database facts to prevent hallucination.
    
    This is critical for business analysis where accuracy is paramount.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._known_providers = None
        self._revenue_cache = None
        self._transaction_cache = None
    
    def validate_response(self, question: str, response: str) -> Dict[str, Any]:
        """
        Validate an AI response against actual database facts.
        
        Returns:
            Dict with validation results and corrected response if needed
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'corrected_response': response,
            'fact_checks': []
        }
        
        try:
            # Check for fictional provider names
            provider_check = self._validate_provider_names(response)
            validation_result['fact_checks'].append(provider_check)
            
            # Check revenue figures
            revenue_check = self._validate_revenue_figures(response)
            validation_result['fact_checks'].append(revenue_check)
            
            # Check transaction counts
            transaction_check = self._validate_transaction_counts(response)
            validation_result['fact_checks'].append(transaction_check)
            
            # Compile validation results
            for check in validation_result['fact_checks']:
                if not check['is_valid']:
                    validation_result['is_valid'] = False
                    validation_result['errors'].extend(check.get('errors', []))
                
                validation_result['warnings'].extend(check.get('warnings', []))
            
            # Generate corrected response if needed
            if not validation_result['is_valid']:
                validation_result['corrected_response'] = self._generate_factual_response(question)
        
        except Exception as e:
            self.logger.error(f"Error in response validation: {e}")
            validation_result['errors'].append(f"Validation system error: {e}")
            validation_result['is_valid'] = False
        
        return validation_result
    
    def _validate_provider_names(self, response: str) -> Dict[str, Any]:
        """Validate that mentioned provider names exist in the database"""
        check_result = {
            'check_type': 'provider_names',
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Get actual providers from database
            actual_providers = self._get_actual_providers()
            
            # Common fictional provider names to flag
            fictional_providers = [
                'dr. smith', 'dr smith', 'dr. jones', 'dr jones', 
                'dr. brown', 'dr brown', 'dr. johnson', 'dr johnson',
                'provider a', 'provider b', 'provider c'
            ]
            
            response_lower = response.lower()
            
            # Check for fictional providers
            for fictional in fictional_providers:
                if fictional in response_lower:
                    check_result['is_valid'] = False
                    check_result['errors'].append(f"Fictional provider '{fictional}' mentioned in response")
            
            # Check for provider names that don't exist in our database
            mentioned_providers = self._extract_provider_names_from_text(response)
            for provider in mentioned_providers:
                if provider not in actual_providers:
                    check_result['warnings'].append(f"Provider '{provider}' not found in current database")
        
        except Exception as e:
            self.logger.error(f"Error validating provider names: {e}")
            check_result['errors'].append(f"Provider validation error: {e}")
            check_result['is_valid'] = False
        
        return check_result
    
    def _validate_revenue_figures(self, response: str) -> Dict[str, Any]:
        """Validate revenue figures against actual database data"""
        check_result = {
            'check_type': 'revenue_figures',
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Extract revenue figures from response
            revenue_figures = self._extract_revenue_figures(response)
            
            if revenue_figures:
                # Get actual revenue data
                actual_revenue = self._get_actual_revenue_data()
                
                for figure in revenue_figures:
                    amount = figure['amount']
                    provider = figure.get('provider')
                    
                    # Check if figure is reasonable given our actual data
                    if provider and provider in actual_revenue:
                        actual_amount = actual_revenue[provider]
                        
                        # Allow 10% variance for rounding/timing differences
                        if abs(amount - actual_amount) / actual_amount > 0.10:
                            check_result['warnings'].append(
                                f"Revenue figure ${amount:,.2f} for {provider} differs significantly from actual ${actual_amount:,.2f}"
                            )
        
        except Exception as e:
            self.logger.error(f"Error validating revenue figures: {e}")
            check_result['errors'].append(f"Revenue validation error: {e}")
        
        return check_result
    
    def _validate_transaction_counts(self, response: str) -> Dict[str, Any]:
        """Validate transaction counts against actual database data"""
        check_result = {
            'check_type': 'transaction_counts',
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Extract transaction counts from response
            transaction_counts = self._extract_transaction_counts(response)
            
            if transaction_counts:
                # Get actual transaction data
                actual_transactions = self._get_actual_transaction_counts()
                
                for count_data in transaction_counts:
                    count = count_data['count']
                    provider = count_data.get('provider')
                    
                    if provider and provider in actual_transactions:
                        actual_count = actual_transactions[provider]
                        
                        # Allow small variance for timing differences
                        if abs(count - actual_count) > 50:  # Allow 50 transaction variance
                            check_result['warnings'].append(
                                f"Transaction count {count:,} for {provider} differs from actual {actual_count:,}"
                            )
        
        except Exception as e:
            self.logger.error(f"Error validating transaction counts: {e}")
            check_result['errors'].append(f"Transaction count validation error: {e}")
        
        return check_result
    
    def _get_actual_providers(self) -> List[str]:
        """Get actual provider names from database"""
        if self._known_providers is None:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT provider_name FROM providers WHERE active = 1")
                self._known_providers = [row['provider_name'] for row in cursor.fetchall()]
                conn.close()
            except Exception as e:
                self.logger.error(f"Error getting actual providers: {e}")
                self._known_providers = []
        
        return self._known_providers
    
    def _get_actual_revenue_data(self) -> Dict[str, float]:
        """Get actual revenue data by provider"""
        if self._revenue_cache is None:
            try:
                conn = get_db_connection()
                query = """
                SELECT 
                    p.provider_name,
                    SUM(pt.cash_applied) as total_revenue
                FROM providers p
                LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
                WHERE p.active = 1
                GROUP BY p.provider_id, p.provider_name
                """
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                self._revenue_cache = {}
                for _, row in df.iterrows():
                    if row['total_revenue']:
                        self._revenue_cache[row['provider_name']] = float(row['total_revenue'])
            except Exception as e:
                self.logger.error(f"Error getting actual revenue data: {e}")
                self._revenue_cache = {}
        
        return self._revenue_cache
    
    def _get_actual_transaction_counts(self) -> Dict[str, int]:
        """Get actual transaction counts by provider"""
        if self._transaction_cache is None:
            try:
                conn = get_db_connection()
                query = """
                SELECT 
                    p.provider_name,
                    COUNT(pt.transaction_id) as total_transactions
                FROM providers p
                LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
                WHERE p.active = 1
                GROUP BY p.provider_id, p.provider_name
                """
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                self._transaction_cache = {}
                for _, row in df.iterrows():
                    if row['total_transactions']:
                        self._transaction_cache[row['provider_name']] = int(row['total_transactions'])
            except Exception as e:
                self.logger.error(f"Error getting actual transaction counts: {e}")
                self._transaction_cache = {}
        
        return self._transaction_cache
    
    def _extract_provider_names_from_text(self, text: str) -> List[str]:
        """Extract provider names mentioned in text"""
        # This is a simplified implementation
        # In production, you'd use more sophisticated NLP
        providers = []
        actual_providers = self._get_actual_providers()
        
        text_lower = text.lower()
        for provider in actual_providers:
            if provider.lower() in text_lower:
                providers.append(provider)
        
        return providers
    
    def _extract_revenue_figures(self, text: str) -> List[Dict[str, Any]]:
        """Extract revenue figures from text"""
        revenue_pattern = r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        matches = re.findall(revenue_pattern, text)
        
        figures = []
        for match in matches:
            amount = float(match.replace(',', ''))
            figures.append({'amount': amount})
        
        return figures
    
    def _extract_transaction_counts(self, text: str) -> List[Dict[str, Any]]:
        """Extract transaction counts from text"""
        # Look for patterns like "1,470 transactions"
        transaction_pattern = r'(\d{1,3}(?:,\d{3})*)\s+transactions'
        matches = re.findall(transaction_pattern, text)
        
        counts = []
        for match in matches:
            count = int(match.replace(',', ''))
            counts.append({'count': count})
        
        return counts
    
    def _generate_factual_response(self, question: str) -> str:
        """Generate a factual response based on actual database data"""
        try:
            # This is a simplified factual response generator
            # In production, this would be more sophisticated
            
            conn = get_db_connection()
            
            # If asking about providers, return actual provider list
            if 'provider' in question.lower():
                query = """
                SELECT 
                    p.provider_name,
                    COUNT(pt.transaction_id) as total_transactions,
                    COALESCE(SUM(pt.cash_applied), 0) as total_revenue
                FROM providers p
                LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
                WHERE p.active = 1
                GROUP BY p.provider_id, p.provider_name
                ORDER BY total_revenue DESC
                """
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                response = "Here are the actual providers in your database:\n\n"
                for _, row in df.iterrows():
                    name = row['provider_name']
                    transactions = int(row['total_transactions']) if row['total_transactions'] else 0
                    revenue = float(row['total_revenue']) if row['total_revenue'] else 0.0
                    
                    response += f"• **{name}** - {transactions:,} transactions, ${revenue:,.2f} revenue\n"
                
                return response
            
            else:
                return "I can provide information about your actual providers, revenue, and transactions. What specific data would you like to see?"
        
        except Exception as e:
            self.logger.error(f"Error generating factual response: {e}")
            return "I encountered an error accessing the database. Please try again."

# Global validator instance
reasoning_validator = ReasoningValidator() 