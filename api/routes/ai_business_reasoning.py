"""
Business Reasoning Engine for Ada AI Assistant.

This module implements structured reasoning patterns for complex business analysis,
similar to Claude Sonnet's thinking mode and GPT-4's reasoning capabilities.
Prevents hallucination by enforcing deterministic database queries and step-by-step analysis.
"""

import sqlite3
import pandas as pd
from flask import Blueprint, request, jsonify, current_app
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging

from api.utils.db import get_db_connection
from utils.expense_analyzer import get_expense_analyzer

# Create blueprint
business_bp = Blueprint('business_reasoning', __name__)

@dataclass
class ReasoningStep:
    """Represents a single step in the reasoning process"""
    step_number: int
    description: str
    query_type: str  # 'database', 'calculation', 'analysis', 'conclusion'
    sql_query: Optional[str] = None
    result: Optional[Any] = None
    reasoning: Optional[str] = None

@dataclass
class BusinessQuestion:
    """Structured representation of a business question"""
    original_question: str
    question_type: str  # 'performance', 'profitability', 'optimization', 'comparison'
    entities: List[str]  # providers, time periods, metrics
    required_data: List[str]
    reasoning_steps: List[ReasoningStep]

class BusinessReasoningEngine:
    """
    Implements structured reasoning for business questions.
    Uses deterministic database queries and step-by-step analysis.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_question(self, question: str) -> BusinessQuestion:
        """
        Analyze a business question and create structured reasoning plan.
        
        This is similar to how Claude Sonnet's thinking mode works - break down
        the question into logical components and plan the analysis steps.
        """
        question_lower = question.lower()
        
        # Determine question type
        question_type = self._classify_question(question_lower)
        
        # Extract entities (providers, time periods, etc.)
        entities = self._extract_entities(question, question_lower)
        
        # Determine required data
        required_data = self._determine_required_data(question_type, entities)
        
        # Create reasoning steps
        reasoning_steps = self._plan_reasoning_steps(question_type, entities, required_data)
        
        return BusinessQuestion(
            original_question=question,
            question_type=question_type,
            entities=entities,
            required_data=required_data,
            reasoning_steps=reasoning_steps
        )
    
    def _classify_question(self, question_lower: str) -> str:
        """Classify the type of business question"""
        if any(term in question_lower for term in ['profit', 'margin', 'overhead', 'cost']):
            return 'profitability'
        elif any(term in question_lower for term in ['performance', 'optimize', 'improve', 'efficiency']):
            return 'performance'
        elif any(term in question_lower for term in ['compare', 'versus', 'vs', 'better', 'best']):
            return 'comparison'
        elif any(term in question_lower for term in ['revenue', 'earnings', 'income', 'total']):
            return 'financial'
        else:
            return 'general'
    
    def _extract_entities(self, question: str, question_lower: str) -> List[str]:
        """Extract specific entities mentioned in the question"""
        entities = []
        
        # Extract provider names
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT provider_name FROM providers WHERE active = 1")
            providers = [row['provider_name'] for row in cursor.fetchall()]
            conn.close()
            
            for provider in providers:
                if provider.lower() in question_lower:
                    entities.append(f"provider:{provider}")
                else:
                    # Check for first name matches
                    first_name = provider.split()[0].lower()
                    if len(first_name) > 3 and first_name in question_lower:
                        entities.append(f"provider:{provider}")
        except Exception as e:
            self.logger.error(f"Error extracting provider entities: {e}")
        
        # Extract time periods
        time_indicators = ['month', 'quarter', 'year', 'week', 'daily', 'annual']
        for indicator in time_indicators:
            if indicator in question_lower:
                entities.append(f"timeframe:{indicator}")
        
        # Extract specific months/years
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                 'july', 'august', 'september', 'october', 'november', 'december']
        for month in months:
            if month in question_lower:
                entities.append(f"month:{month}")
        
        return entities
    
    def _determine_required_data(self, question_type: str, entities: List[str]) -> List[str]:
        """Determine what data is needed to answer the question"""
        required_data = []
        
        if question_type in ['profitability', 'financial']:
            required_data.extend(['revenue', 'transactions', 'overhead_costs', 'expense_data'])
        elif question_type == 'performance':
            required_data.extend(['transaction_volume', 'revenue_per_transaction', 'payer_mix'])
        elif question_type == 'comparison':
            required_data.extend(['comparative_metrics', 'benchmarks'])
        
        # Always include basic provider data if providers are mentioned
        if any('provider:' in entity for entity in entities):
            required_data.extend(['provider_details', 'transaction_history'])
        
        return required_data
    
    def _plan_reasoning_steps(self, question_type: str, entities: List[str], required_data: List[str]) -> List[ReasoningStep]:
        """Plan the step-by-step reasoning process"""
        steps = []
        step_num = 1
        
        # Step 1: Always start with data validation
        steps.append(ReasoningStep(
            step_number=step_num,
            description="Validate available data and identify analysis scope",
            query_type="database",
            sql_query="SELECT COUNT(*) as total_transactions, MIN(transaction_date) as earliest_date, MAX(transaction_date) as latest_date FROM payment_transactions"
        ))
        step_num += 1
        
        # Step 2: Get provider baseline if providers are involved
        if any('provider:' in entity for entity in entities):
            provider_names = [entity.split(':')[1] for entity in entities if entity.startswith('provider:')]
            if provider_names:
                provider_filter = "', '".join(provider_names)
                steps.append(ReasoningStep(
                    step_number=step_num,
                    description=f"Get baseline performance for specified providers: {', '.join(provider_names)}",
                    query_type="database",
                    sql_query=f"""
                    SELECT 
                        p.provider_name,
                        COUNT(pt.transaction_id) as total_transactions,
                        SUM(pt.cash_applied) as total_revenue,
                        AVG(pt.cash_applied) as avg_payment,
                        COUNT(DISTINCT pt.payer_name) as unique_payers,
                        MIN(pt.transaction_date) as first_transaction,
                        MAX(pt.transaction_date) as last_transaction
                    FROM providers p
                    LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
                    WHERE p.provider_name IN ('{provider_filter}')
                    GROUP BY p.provider_id, p.provider_name
                    """
                ))
                step_num += 1
        
        # Step 3: Check for expense data availability
        steps.append(ReasoningStep(
            step_number=step_num,
            description="Check for expense/overhead data availability",
            query_type="database",
            sql_query="SELECT COUNT(*) as expense_records, MIN(expense_date) as earliest_expense, MAX(expense_date) as latest_expense FROM expense_transactions"
        ))
        step_num += 1
        
        # Step 4: Add question-specific analysis steps
        if question_type == 'profitability':
            steps.append(ReasoningStep(
                step_number=step_num,
                description="Calculate monthly profit margins if expense data available",
                query_type="database",
                sql_query="""
                SELECT 
                    strftime('%Y-%m', pt.transaction_date) as month,
                    SUM(pt.cash_applied) as total_revenue,
                    COUNT(pt.transaction_id) as transaction_count,
                    COALESCE(
                        (SELECT SUM(et.amount) 
                         FROM expense_transactions et 
                         WHERE strftime('%Y-%m', et.expense_date) = strftime('%Y-%m', pt.transaction_date)), 
                        0
                    ) as total_expenses,
                    (SUM(pt.cash_applied) - COALESCE(
                        (SELECT SUM(et.amount) 
                         FROM expense_transactions et 
                         WHERE strftime('%Y-%m', et.expense_date) = strftime('%Y-%m', pt.transaction_date)), 
                        0
                    )) as net_profit
                FROM payment_transactions pt
                WHERE pt.transaction_date >= date('now', '-12 months')
                GROUP BY month
                ORDER BY month DESC
                LIMIT 6
                """
            ))
            step_num += 1
            
            steps.append(ReasoningStep(
                step_number=step_num,
                description="Calculate break-even analysis by provider",
                query_type="analysis",
                reasoning="Determine how many transactions each provider needs to cover overhead costs"
            ))
        elif question_type == 'performance':
            steps.append(ReasoningStep(
                step_number=step_num,
                description="Analyze performance metrics and identify improvement areas",
                query_type="analysis",
                reasoning="Evaluate transaction patterns, revenue trends, and comparative performance"
            ))
        
        return steps
    
    def execute_reasoning(self, business_question: BusinessQuestion) -> Dict[str, Any]:
        """
        Execute the reasoning steps and return structured analysis.
        
        This implements the deterministic query execution that prevents hallucination.
        """
        results = {
            'question': business_question.original_question,
            'question_type': business_question.question_type,
            'entities': business_question.entities,
            'reasoning_steps': [],
            'conclusion': '',
            'recommendations': []
        }
        
        try:
            conn = get_db_connection()
            
            for step in business_question.reasoning_steps:
                step_result = self._execute_step(step, conn)
                results['reasoning_steps'].append({
                    'step_number': step.step_number,
                    'description': step.description,
                    'query_type': step.query_type,
                    'sql_query': step.sql_query,
                    'result': step_result,
                    'reasoning': step.reasoning
                })
            
            conn.close()
            
            # Generate conclusion based on results
            results['conclusion'] = self._generate_conclusion(business_question, results['reasoning_steps'])
            
            # Generate actionable recommendations
            results['recommendations'] = self._generate_recommendations(business_question, results['reasoning_steps'])
            
        except Exception as e:
            self.logger.error(f"Error executing reasoning: {e}")
            results['error'] = str(e)
        
        return results
    
    def _execute_step(self, step: ReasoningStep, conn) -> Any:
        """Execute a single reasoning step"""
        if step.query_type == 'database' and step.sql_query:
            try:
                df = pd.read_sql_query(step.sql_query, conn)
                return df.to_dict('records')
            except Exception as e:
                self.logger.error(f"Error executing SQL in step {step.step_number}: {e}")
                return {'error': str(e)}
        
        elif step.query_type == 'analysis':
            # Enhanced analysis logic with expense integration
            if 'break-even' in step.description.lower():
                return self._calculate_break_even_analysis(conn)
            elif 'overhead' in step.description.lower():
                return self._analyze_overhead_efficiency(conn)
            else:
                return {'analysis_type': 'pending', 'reasoning': step.reasoning}
        
        return None
    
    def _calculate_break_even_analysis(self, conn) -> Dict[str, Any]:
        """Calculate break-even points considering overhead costs"""
        try:
            # Get expense data
            expense_analyzer = get_expense_analyzer()
            
            # Check if expense data exists
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM expense_transactions")
            expense_count = cursor.fetchone()['count']
            
            if expense_count == 0:
                return {
                    'analysis_type': 'break_even',
                    'status': 'no_expense_data',
                    'message': 'Upload overhead/expense CSV data for complete break-even analysis',
                    'basic_analysis': self._basic_revenue_analysis(conn)
                }
            
            # Get break-even analysis with expense data
            breakeven_data = expense_analyzer.calculate_break_even_analysis()
            return {
                'analysis_type': 'break_even',
                'status': 'complete',
                'data': breakeven_data
            }
            
        except Exception as e:
            self.logger.error(f"Error in break-even analysis: {e}")
            return {'analysis_type': 'break_even', 'error': str(e)}
    
    def _analyze_overhead_efficiency(self, conn) -> Dict[str, Any]:
        """Analyze overhead cost efficiency"""
        try:
            expense_analyzer = get_expense_analyzer()
            
            # Get efficiency analysis
            efficiency_data = expense_analyzer.analyze_variable_cost_efficiency()
            
            return {
                'analysis_type': 'overhead_efficiency',
                'data': efficiency_data
            }
            
        except Exception as e:
            self.logger.error(f"Error in overhead analysis: {e}")
            return {'analysis_type': 'overhead_efficiency', 'error': str(e)}
    
    def _basic_revenue_analysis(self, conn) -> Dict[str, Any]:
        """Basic revenue analysis when no expense data is available"""
        try:
            query = """
            SELECT 
                p.provider_name,
                COUNT(pt.transaction_id) as total_transactions,
                SUM(pt.cash_applied) as total_revenue,
                AVG(pt.cash_applied) as avg_revenue_per_transaction
            FROM providers p
            LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
            WHERE p.active = 1
            GROUP BY p.provider_id, p.provider_name
            ORDER BY total_revenue DESC
            """
            df = pd.read_sql_query(query, conn)
            return df.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"Error in basic revenue analysis: {e}")
            return {'error': str(e)}
    
    def _generate_conclusion(self, question: BusinessQuestion, step_results: List[Dict]) -> str:
        """Generate a data-driven conclusion"""
        # This would implement sophisticated conclusion generation
        # For now, return a structured summary
        
        if question.question_type == 'profitability':
            return "Based on the transaction analysis, recommendations focus on optimizing revenue per transaction and payer efficiency."
        elif question.question_type == 'performance':
            return "Performance analysis reveals specific areas for provider optimization and efficiency improvements."
        else:
            return "Analysis complete with actionable insights identified."
    
    def _generate_recommendations(self, question: BusinessQuestion, step_results: List[Dict]) -> List[str]:
        """Generate actionable business recommendations"""
        recommendations = []
        
        # Extract data from step results
        for step in step_results:
            if step['query_type'] == 'database' and step['result'] and not isinstance(step['result'], dict):
                # This is real data, generate specific recommendations
                if question.question_type == 'performance':
                    recommendations.append("Review transaction patterns for optimization opportunities")
                    recommendations.append("Analyze payer mix for revenue enhancement")
        
        if not recommendations:
            recommendations.append("Upload overhead cost data for comprehensive profit margin analysis")
            recommendations.append("Consider monthly performance tracking for trend identification")
        
        return recommendations

# Initialize the reasoning engine
reasoning_engine = BusinessReasoningEngine()

@business_bp.route('/analyze', methods=['POST'])
def analyze_business_question():
    """
    Analyze a complex business question using structured reasoning.
    
    This is the main endpoint for business intelligence queries that require
    sophisticated analysis rather than simple database lookups.
    """
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Step 1: Analyze and plan
        business_question = reasoning_engine.analyze_question(question)
        
        # Step 2: Execute reasoning
        analysis_result = reasoning_engine.execute_reasoning(business_question)
        
        return jsonify(analysis_result)
        
    except Exception as e:
        current_app.logger.error(f"Error in business analysis: {e}")
        return jsonify({'error': str(e)}), 500

@business_bp.route('/profit-analysis', methods=['POST'])
def profit_analysis():
    """
    Specialized endpoint for profit margin and overhead analysis.
    
    This will be particularly useful once overhead CSV data is uploaded.
    """
    try:
        data = request.get_json()
        provider_name = data.get('provider_name')
        time_period = data.get('time_period', 'all')
        
        # Get revenue data
        conn = get_db_connection()
        
        if provider_name:
            query = """
            SELECT 
                p.provider_name,
                COUNT(pt.transaction_id) as total_transactions,
                SUM(pt.cash_applied) as total_revenue,
                AVG(pt.cash_applied) as avg_revenue_per_transaction
            FROM providers p
            LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
            WHERE p.provider_name = ?
            GROUP BY p.provider_id, p.provider_name
            """
            df = pd.read_sql_query(query, conn, params=[provider_name])
        else:
            query = """
            SELECT 
                p.provider_name,
                COUNT(pt.transaction_id) as total_transactions,
                SUM(pt.cash_applied) as total_revenue,
                AVG(pt.cash_applied) as avg_revenue_per_transaction
            FROM providers p
            LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
            GROUP BY p.provider_id, p.provider_name
            ORDER BY total_revenue DESC
            """
            df = pd.read_sql_query(query, conn)
        
        conn.close()
        
        # Calculate profit metrics (placeholder until overhead data is available)
        results = []
        for _, row in df.iterrows():
            results.append({
                'provider_name': row['provider_name'],
                'total_transactions': int(row['total_transactions']) if row['total_transactions'] else 0,
                'total_revenue': float(row['total_revenue']) if row['total_revenue'] else 0.0,
                'avg_revenue_per_transaction': float(row['avg_revenue_per_transaction']) if row['avg_revenue_per_transaction'] else 0.0,
                'profit_margin': 'Pending overhead data upload',
                'recommendations': [
                    'Upload overhead/cost CSV files for complete profit analysis',
                    'Consider tracking direct costs per provider',
                    'Monitor revenue per transaction trends'
                ]
            })
        
        return jsonify({
            'analysis_type': 'profit_analysis',
            'results': results,
            'note': 'Complete profit analysis available after overhead CSV upload'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in profit analysis: {e}")
        return jsonify({'error': str(e)}), 500 