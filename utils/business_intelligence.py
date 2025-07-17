#!/usr/bin/env python3
"""
Business Intelligence Module
Comprehensive financial analysis and growth planning for HVLC practice
"""

import sqlite3
import json
from datetime import datetime, date
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

@dataclass
class ProviderContract:
    """Provider contract structure"""
    name: str
    contract_type: str
    provider_percentage: float
    company_percentage: float
    status: str
    role: str  # 'owner', 'contractor', 'previous_owner'
    target_monthly: Optional[float] = None
    notes: str = ""

@dataclass
class FinancialStructure:
    """Complete financial structure"""
    monthly_overhead: float
    tammy_asset_payment: float
    tammy_mortgage_payment: float
    total_monthly_costs: float
    break_even_target: float

@dataclass
class GrowthTarget:
    """Growth targets for providers"""
    provider_name: str
    current_monthly_revenue: float
    target_monthly_revenue: float
    growth_needed_percentage: float
    additional_sessions_needed: int
    avg_session_value: float

class BusinessIntelligence:
    def __init__(self, db_path='medical_billing.db'):
        self.db_path = db_path
        
        # Core financial structure
        self.financial_structure = FinancialStructure(
            monthly_overhead=1328.50,
            tammy_asset_payment=1000.00,
            tammy_mortgage_payment=750.00,
            total_monthly_costs=3078.50,
            break_even_target=3078.50
        )
        
        # Provider contracts with ownership structure
        self.provider_contracts = {
            'Dustin Nisley': ProviderContract(
                name='Dustin Nisley',
                contract_type='Independent Contractor',
                provider_percentage=65.0,
                company_percentage=35.0,
                status='active',
                role='contractor',
                notes='Top performer, key growth target'
            ),
            'Sidney Snipes': ProviderContract(
                name='Sidney Snipes', 
                contract_type='Independent Contractor',
                provider_percentage=60.0,
                company_percentage=40.0,
                status='active',
                role='contractor',
                notes='Capped out/retired, at maximum capacity'
            ),
            'Tammy Maxey': ProviderContract(
                name='Tammy Maxey',
                contract_type='Previous Owner',
                provider_percentage=91.1,
                company_percentage=8.9,
                status='active',
                role='previous_owner',
                notes='Owner financing - 6% billing + 2.9% CC fees + misc'
            ),
            'Isabel Rehak': ProviderContract(
                name='Isabel Rehak',
                contract_type='Owner',
                provider_percentage=100.0,
                company_percentage=0.0,
                status='active', 
                role='owner',
                target_monthly=9700.00,
                notes='Co-owner, will transition to W2 salary'
            )
        }
        
        # Load business memory from database
        self._load_business_memory()
    
    def _get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _load_business_memory(self):
        """Load business intelligence memory from database"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Create business_memory table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_memory (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Load stored financial structure
            cursor.execute('SELECT value FROM business_memory WHERE key = ?', ('financial_structure',))
            result = cursor.fetchone()
            if result:
                stored_data = json.loads(result['value'])
                self.financial_structure = FinancialStructure(**stored_data)
            
            # Load provider contracts
            cursor.execute('SELECT value FROM business_memory WHERE key = ?', ('provider_contracts',))
            result = cursor.fetchone()
            if result:
                stored_contracts = json.loads(result['value'])
                for name, contract_data in stored_contracts.items():
                    self.provider_contracts[name] = ProviderContract(**contract_data)
            
            conn.close()
        except Exception as e:
            print(f"Warning: Could not load business memory: {e}")
    
    def save_business_memory(self):
        """Save business intelligence memory to database"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Save financial structure
            cursor.execute('''
                INSERT OR REPLACE INTO business_memory (key, value)
                VALUES (?, ?)
            ''', ('financial_structure', json.dumps(asdict(self.financial_structure))))
            
            # Save provider contracts
            contracts_dict = {name: asdict(contract) for name, contract in self.provider_contracts.items()}
            cursor.execute('''
                INSERT OR REPLACE INTO business_memory (key, value)
                VALUES (?, ?)
            ''', ('provider_contracts', json.dumps(contracts_dict)))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving business memory: {e}")
            return False
    
    def get_current_provider_performance(self) -> Dict[str, Dict]:
        """Get current monthly performance for all providers"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Get recent monthly performance (last 3 months average)
        cursor.execute('''
            SELECT 
                provider_name,
                AVG(total_cash_applied) as avg_monthly_revenue,
                AVG(company_income) as avg_company_revenue,
                COUNT(*) as months_tracked
            FROM provider_monthly_summary
            WHERE year_month >= date('now', '-3 months')
            GROUP BY provider_name
        ''')
        
        performance = {}
        for row in cursor.fetchall():
            provider = row['provider_name']
            if provider in self.provider_contracts:
                contract = self.provider_contracts[provider]
                avg_revenue = row['avg_monthly_revenue'] or 0
                avg_company = row['avg_company_revenue'] or 0
                
                performance[provider] = {
                    'avg_monthly_revenue': avg_revenue,
                    'avg_company_revenue': avg_company,
                    'contract_percentage': contract.company_percentage,
                    'role': contract.role,
                    'status': contract.status,
                    'months_tracked': row['months_tracked']
                }
        
        conn.close()
        return performance
    
    def calculate_break_even_analysis(self) -> Dict:
        """Calculate comprehensive break-even analysis"""
        performance = self.get_current_provider_performance()
        
        # Calculate current company revenue
        total_company_revenue = sum(
            perf['avg_company_revenue'] for perf in performance.values()
        )
        
        # Calculate shortfall/surplus
        shortfall = self.financial_structure.total_monthly_costs - total_company_revenue
        
        # Calculate growth targets
        growth_targets = []
        for provider_name, contract in self.provider_contracts.items():
            if contract.role == 'contractor' and contract.status == 'active':
                perf = performance.get(provider_name, {})
                current_revenue = perf.get('avg_monthly_revenue', 0)
                
                if current_revenue > 0:
                    # Calculate how much this provider needs to grow
                    revenue_needed = shortfall / (contract.company_percentage / 100)
                    target_revenue = current_revenue + revenue_needed
                    growth_percentage = (revenue_needed / current_revenue) * 100
                    
                    # Estimate sessions (assuming $68 average per session)
                    avg_session_value = 68.0
                    additional_sessions = int(revenue_needed / avg_session_value)
                    
                    growth_targets.append(GrowthTarget(
                        provider_name=provider_name,
                        current_monthly_revenue=current_revenue,
                        target_monthly_revenue=target_revenue,
                        growth_needed_percentage=growth_percentage,
                        additional_sessions_needed=additional_sessions,
                        avg_session_value=avg_session_value
                    ))
        
        return {
            'financial_structure': self.financial_structure,
            'current_company_revenue': total_company_revenue,
            'monthly_shortfall': shortfall,
            'break_even_status': 'profitable' if shortfall <= 0 else 'needs_growth',
            'provider_performance': performance,
            'growth_targets': [asdict(target) for target in growth_targets],
            'analysis_date': datetime.now().isoformat()
        }
    
    def get_dustin_growth_requirements(self) -> Dict:
        """Specific analysis for Dustin as the primary growth target"""
        analysis = self.calculate_break_even_analysis()
        shortfall = analysis['monthly_shortfall']
        
        if shortfall <= 0:
            return {
                'status': 'break_even_achieved',
                'message': 'Practice is already profitable!'
            }
        
        # Dustin-specific calculation
        dustin_contract = self.provider_contracts.get('Dustin Nisley')
        if not dustin_contract:
            return {'error': 'Dustin contract not found'}
        
        dustin_perf = analysis['provider_performance'].get('Dustin Nisley', {})
        current_revenue = dustin_perf.get('avg_monthly_revenue', 0)
        
        # Calculate required growth for Dustin to cover entire shortfall
        company_percentage = dustin_contract.company_percentage / 100
        revenue_needed = shortfall / company_percentage
        target_revenue = current_revenue + revenue_needed
        growth_percentage = (revenue_needed / current_revenue) * 100 if current_revenue > 0 else 0
        
        # Session calculations
        avg_session_value = 68.0
        current_sessions = int(current_revenue / avg_session_value)
        additional_sessions = int(revenue_needed / avg_session_value)
        target_sessions = current_sessions + additional_sessions
        sessions_per_day = target_sessions / 22  # ~22 business days per month
        
        return {
            'shortfall_to_cover': shortfall,
            'current_monthly_revenue': current_revenue,
            'additional_revenue_needed': revenue_needed,
            'target_monthly_revenue': target_revenue,
            'growth_percentage_needed': growth_percentage,
            'current_sessions_per_month': current_sessions,
            'additional_sessions_needed': additional_sessions,
            'target_sessions_per_month': target_sessions,
            'target_sessions_per_day': round(sessions_per_day, 1),
            'avg_session_value': avg_session_value,
            'analysis_date': datetime.now().isoformat()
        }
    
    def update_provider_contract(self, provider_name: str, updates: Dict):
        """Update provider contract terms"""
        if provider_name in self.provider_contracts:
            contract = self.provider_contracts[provider_name]
            for key, value in updates.items():
                if hasattr(contract, key):
                    setattr(contract, key, value)
            
            self.save_business_memory()
            return True
        return False
    
    def get_financial_summary(self) -> str:
        """Get formatted financial summary"""
        analysis = self.calculate_break_even_analysis()
        dustin_growth = self.get_dustin_growth_requirements()
        
        summary = f"""
🏢 HVLC PRACTICE FINANCIAL SUMMARY
{'='*50}

💰 MONTHLY FINANCIAL STRUCTURE:
   Base Overhead: ${self.financial_structure.monthly_overhead:,.2f}
   Asset Payment (Tammy): ${self.financial_structure.tammy_asset_payment:,.2f}
   Mortgage Payment (Tammy): ${self.financial_structure.tammy_mortgage_payment:,.2f}
   TOTAL MONTHLY COSTS: ${self.financial_structure.total_monthly_costs:,.2f}

📊 CURRENT PERFORMANCE:
   Company Revenue: ${analysis['current_company_revenue']:,.2f}
   Monthly Gap: ${analysis['monthly_shortfall']:,.2f}
   Status: {analysis['break_even_status'].upper()}

👥 PROVIDER STRUCTURE:
   • Dustin Nisley: 35% company share (key growth target)
   • Sidney Snipes: 40% company share (at capacity)
   • Tammy Maxey: 8.9% company share (owner financing)
   • Isabel Rehak: 0% company share (co-owner)

🎯 DUSTIN'S GROWTH TARGET:
   Current Revenue: ${dustin_growth.get('current_monthly_revenue', 0):,.2f}
   Target Revenue: ${dustin_growth.get('target_monthly_revenue', 0):,.2f}
   Growth Needed: {dustin_growth.get('growth_percentage_needed', 0):.1f}%
   Additional Sessions: {dustin_growth.get('additional_sessions_needed', 0)}/month
   Target: {dustin_growth.get('target_sessions_per_day', 0)} sessions/day

📈 BREAK-EVEN STRATEGY:
   - Focus on Dustin's client growth (Sidney at capacity)
   - Consider new provider addition for faster growth
   - Monitor Tammy's transition timeline
   - Plan Isabel's salary transition
"""
        return summary

# Global instance for app usage
business_intelligence = BusinessIntelligence() 