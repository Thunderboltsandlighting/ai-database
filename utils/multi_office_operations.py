"""
Multi-Office Operations Management System

This module provides comprehensive tracking and analysis for multi-office medical practice operations,
including provider revenue optimization, caseload management, and automated P&L reporting.

Designed to support operational efficiency and cash flow management for expanding practices.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging
from dataclasses import dataclass, asdict
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class Office:
    """Office location data structure"""
    office_id: str
    name: str
    address: str
    phone: str
    capacity_sessions_per_day: int
    overhead_monthly: float
    rent_monthly: float
    active: bool = True
    
@dataclass
class ProviderAssignment:
    """Provider-to-office assignment data structure"""
    provider_id: str
    office_id: str
    days_per_week: int
    hours_per_day: float
    max_sessions_per_day: int
    effective_date: str
    end_date: Optional[str] = None
    
@dataclass
class ProviderRevenue:
    """Provider revenue and profitability analysis"""
    provider_id: str
    provider_name: str
    office_id: str
    office_name: str
    total_sessions: int
    total_revenue: float
    provider_cut: float
    company_cut: float
    profit_margin: float
    avg_sessions_per_day: float
    capacity_utilization: float
    revenue_per_session: float

class MultiOfficeOperations:
    """
    Comprehensive multi-office operations management system
    
    Features:
    - Office location management
    - Provider assignments and capacity tracking
    - Real-time revenue and profitability analysis
    - Automated P&L reporting
    - Caseload optimization recommendations
    - Business sustainability metrics
    """
    
    def __init__(self, db_path: str = None):
        config = get_config()
        self.db_path = db_path or config.get('database', {}).get('path', 'medical_billing.db')
        self.initialize_tables()
        
    def initialize_tables(self):
        """Initialize multi-office operations tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Offices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS offices (
                    office_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    address TEXT,
                    phone TEXT,
                    capacity_sessions_per_day INTEGER,
                    overhead_monthly REAL,
                    rent_monthly REAL,
                    active BOOLEAN DEFAULT 1,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Provider office assignments
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS provider_office_assignments (
                    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id TEXT NOT NULL,
                    office_id TEXT NOT NULL,
                    days_per_week INTEGER,
                    hours_per_day REAL,
                    max_sessions_per_day INTEGER,
                    effective_date TEXT NOT NULL,
                    end_date TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (office_id) REFERENCES offices (office_id)
                )
            ''')
            
            # Revenue tracking by office and provider
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS office_provider_revenue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id TEXT NOT NULL,
                    office_id TEXT NOT NULL,
                    service_date TEXT NOT NULL,
                    session_count INTEGER DEFAULT 1,
                    gross_revenue REAL,
                    provider_cut REAL,
                    company_cut REAL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (office_id) REFERENCES offices (office_id)
                )
            ''')
            
            # Business metrics tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_date TEXT NOT NULL,
                    total_revenue REAL,
                    total_provider_payments REAL,
                    total_overhead REAL,
                    net_profit REAL,
                    provider_count INTEGER,
                    office_count INTEGER,
                    total_sessions INTEGER,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("Multi-office operations tables initialized")
    
    def add_office(self, office: Office) -> bool:
        """Add a new office location"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO offices 
                    (office_id, name, address, phone, capacity_sessions_per_day, 
                     overhead_monthly, rent_monthly, active, updated_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    office.office_id, office.name, office.address, office.phone,
                    office.capacity_sessions_per_day, office.overhead_monthly,
                    office.rent_monthly, office.active
                ))
                conn.commit()
                logger.info(f"Added office: {office.name}")
                return True
        except Exception as e:
            logger.error(f"Error adding office: {e}")
            return False
    
    def assign_provider_to_office(self, assignment: ProviderAssignment) -> bool:
        """Assign a provider to an office with capacity details"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # End any existing assignments for this provider/office
                cursor.execute('''
                    UPDATE provider_office_assignments 
                    SET end_date = ? 
                    WHERE provider_id = ? AND office_id = ? AND end_date IS NULL
                ''', (assignment.effective_date, assignment.provider_id, assignment.office_id))
                
                # Add new assignment
                cursor.execute('''
                    INSERT INTO provider_office_assignments
                    (provider_id, office_id, days_per_week, hours_per_day, 
                     max_sessions_per_day, effective_date, end_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    assignment.provider_id, assignment.office_id, assignment.days_per_week,
                    assignment.hours_per_day, assignment.max_sessions_per_day,
                    assignment.effective_date, assignment.end_date
                ))
                conn.commit()
                logger.info(f"Assigned provider {assignment.provider_id} to office {assignment.office_id}")
                return True
        except Exception as e:
            logger.error(f"Error assigning provider to office: {e}")
            return False
    
    def process_billing_sheet(self, provider_id: str, office_id: str, 
                            service_date: str, sessions: List[Dict]) -> Dict:
        """
        Process billing sheet and calculate revenue distribution
        
        Args:
            provider_id: Provider identifier
            office_id: Office identifier
            service_date: Date of service
            sessions: List of session data with revenue amounts
            
        Returns:
            Dict with revenue breakdown and profit analysis
        """
        try:
            # Get provider contract details
            provider_contract = self._get_provider_contract(provider_id)
            if not provider_contract:
                raise ValueError(f"No contract found for provider {provider_id}")
            
            # Calculate totals
            total_sessions = len(sessions)
            gross_revenue = sum(session.get('amount', 0) for session in sessions)
            
            # Apply provider contract percentages
            provider_percentage = provider_contract['provider_percentage'] / 100
            company_percentage = provider_contract['company_percentage'] / 100
            
            provider_cut = gross_revenue * provider_percentage
            company_cut = gross_revenue * company_percentage
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO office_provider_revenue
                    (provider_id, office_id, service_date, session_count, 
                     gross_revenue, provider_cut, company_cut)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (provider_id, office_id, service_date, total_sessions, 
                      gross_revenue, provider_cut, company_cut))
                conn.commit()
            
            # Get provider and office names for reporting
            provider_name = self._get_provider_name(provider_id)
            office_name = self._get_office_name(office_id)
            
            result = {
                'provider_id': provider_id,
                'provider_name': provider_name,
                'office_id': office_id,
                'office_name': office_name,
                'service_date': service_date,
                'total_sessions': total_sessions,
                'gross_revenue': gross_revenue,
                'provider_cut': provider_cut,
                'company_cut': company_cut,
                'provider_percentage': provider_contract['provider_percentage'],
                'company_percentage': provider_contract['company_percentage'],
                'revenue_per_session': gross_revenue / total_sessions if total_sessions > 0 else 0
            }
            
            logger.info(f"Processed billing sheet for {provider_name} at {office_name}: ${gross_revenue:.2f} revenue")
            return result
            
        except Exception as e:
            logger.error(f"Error processing billing sheet: {e}")
            return {}
    
    def get_provider_caseload_analysis(self, provider_id: str, 
                                     start_date: str = None, end_date: str = None) -> Dict:
        """Get comprehensive caseload analysis for a provider"""
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                # Get provider revenue data
                revenue_df = pd.read_sql_query('''
                    SELECT 
                        opr.*,
                        o.name as office_name,
                        o.capacity_sessions_per_day
                    FROM office_provider_revenue opr
                    JOIN offices o ON opr.office_id = o.office_id
                    WHERE opr.provider_id = ? 
                    AND opr.service_date BETWEEN ? AND ?
                    ORDER BY opr.service_date
                ''', conn, params=[provider_id, start_date, end_date])
                
                if revenue_df.empty:
                    return {'error': f'No data found for provider {provider_id}'}
                
                # Get provider assignments
                assignments_df = pd.read_sql_query('''
                    SELECT poa.*, o.name as office_name
                    FROM provider_office_assignments poa
                    JOIN offices o ON poa.office_id = o.office_id
                    WHERE poa.provider_id = ?
                    AND (poa.end_date IS NULL OR poa.end_date >= ?)
                    AND poa.effective_date <= ?
                ''', conn, params=[provider_id, start_date, end_date])
            
            # Calculate metrics
            total_sessions = revenue_df['session_count'].sum()
            total_revenue = revenue_df['gross_revenue'].sum()
            total_provider_cut = revenue_df['provider_cut'].sum()
            total_company_cut = revenue_df['company_cut'].sum()
            
            working_days = len(revenue_df)
            avg_sessions_per_day = total_sessions / working_days if working_days > 0 else 0
            avg_revenue_per_session = total_revenue / total_sessions if total_sessions > 0 else 0
            
            # Calculate capacity utilization
            total_capacity = 0
            for _, assignment in assignments_df.iterrows():
                days_in_period = min(working_days, assignment['days_per_week'] * 4)  # Approximate month
                total_capacity += days_in_period * assignment['max_sessions_per_day']
            
            capacity_utilization = (total_sessions / total_capacity * 100) if total_capacity > 0 else 0
            
            # Get provider name
            provider_name = self._get_provider_name(provider_id)
            
            return {
                'provider_id': provider_id,
                'provider_name': provider_name,
                'period': f"{start_date} to {end_date}",
                'total_sessions': total_sessions,
                'working_days': working_days,
                'avg_sessions_per_day': round(avg_sessions_per_day, 2),
                'total_revenue': round(total_revenue, 2),
                'total_provider_cut': round(total_provider_cut, 2),
                'total_company_cut': round(total_company_cut, 2),
                'avg_revenue_per_session': round(avg_revenue_per_session, 2),
                'capacity_utilization': round(capacity_utilization, 2),
                'total_capacity': total_capacity,
                'office_assignments': assignments_df.to_dict('records'),
                'daily_breakdown': revenue_df[['service_date', 'office_name', 'session_count', 
                                             'gross_revenue', 'provider_cut', 'company_cut']].to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Error getting provider caseload analysis: {e}")
            return {'error': str(e)}
    
    def generate_office_profitability_report(self, office_id: str = None, 
                                           start_date: str = None, end_date: str = None) -> Dict:
        """Generate comprehensive profitability report for offices"""
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                # Base query for all offices or specific office
                office_filter = f"AND o.office_id = '{office_id}'" if office_id else ""
                
                query = f'''
                    SELECT 
                        o.office_id,
                        o.name as office_name,
                        o.overhead_monthly,
                        o.rent_monthly,
                        o.capacity_sessions_per_day,
                        COUNT(DISTINCT opr.provider_id) as provider_count,
                        SUM(opr.session_count) as total_sessions,
                        SUM(opr.gross_revenue) as total_revenue,
                        SUM(opr.provider_cut) as total_provider_payments,
                        SUM(opr.company_cut) as total_company_revenue
                    FROM offices o
                    LEFT JOIN office_provider_revenue opr ON o.office_id = opr.office_id
                        AND opr.service_date BETWEEN ? AND ?
                    WHERE o.active = 1 {office_filter}
                    GROUP BY o.office_id, o.name, o.overhead_monthly, o.rent_monthly, o.capacity_sessions_per_day
                '''
                
                office_df = pd.read_sql_query(query, conn, params=[start_date, end_date])
                
                # Calculate profitability metrics
                report_data = []
                
                for _, office in office_df.iterrows():
                    monthly_overhead = office['overhead_monthly'] or 0
                    monthly_rent = office['rent_monthly'] or 0
                    total_monthly_costs = monthly_overhead + monthly_rent
                    
                    # Calculate daily cost (assuming 30-day month)
                    daily_cost = total_monthly_costs / 30
                    period_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
                    period_overhead = daily_cost * period_days
                    
                    gross_profit = (office['total_company_revenue'] or 0) - period_overhead
                    profit_margin = (gross_profit / (office['total_revenue'] or 1)) * 100
                    
                    # Capacity analysis
                    working_days = period_days  # Simplified - could be more sophisticated
                    total_capacity = office['capacity_sessions_per_day'] * working_days
                    capacity_utilization = ((office['total_sessions'] or 0) / total_capacity * 100) if total_capacity > 0 else 0
                    
                    office_data = {
                        'office_id': office['office_id'],
                        'office_name': office['office_name'],
                        'provider_count': office['provider_count'] or 0,
                        'total_sessions': office['total_sessions'] or 0,
                        'total_revenue': round(office['total_revenue'] or 0, 2),
                        'total_provider_payments': round(office['total_provider_payments'] or 0, 2),
                        'total_company_revenue': round(office['total_company_revenue'] or 0, 2),
                        'period_overhead': round(period_overhead, 2),
                        'gross_profit': round(gross_profit, 2),
                        'profit_margin': round(profit_margin, 2),
                        'capacity_utilization': round(capacity_utilization, 2),
                        'avg_revenue_per_session': round((office['total_revenue'] or 0) / (office['total_sessions'] or 1), 2),
                        'monthly_overhead': monthly_overhead,
                        'monthly_rent': monthly_rent,
                        'total_monthly_costs': total_monthly_costs
                    }
                    
                    report_data.append(office_data)
                
                # Overall summary
                total_revenue = sum(office['total_revenue'] for office in report_data)
                total_company_revenue = sum(office['total_company_revenue'] for office in report_data)
                total_overhead = sum(office['period_overhead'] for office in report_data)
                total_gross_profit = sum(office['gross_profit'] for office in report_data)
                
                summary = {
                    'period': f"{start_date} to {end_date}",
                    'total_offices': len(report_data),
                    'total_revenue': round(total_revenue, 2),
                    'total_company_revenue': round(total_company_revenue, 2),
                    'total_overhead': round(total_overhead, 2),
                    'total_gross_profit': round(total_gross_profit, 2),
                    'overall_profit_margin': round((total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0, 2)
                }
                
                return {
                    'summary': summary,
                    'offices': report_data,
                    'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except Exception as e:
            logger.error(f"Error generating office profitability report: {e}")
            return {'error': str(e)}
    
    def get_business_sustainability_metrics(self) -> Dict:
        """
        Calculate business sustainability metrics to determine if the practice
        can support both owners and operations admin role
        """
        try:
            # Get current month data
            current_month = datetime.now().strftime('%Y-%m')
            start_date = f"{current_month}-01"
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Get profitability report
            profit_report = self.generate_office_profitability_report(start_date=start_date, end_date=end_date)
            
            # Project monthly figures
            days_in_month = 30
            current_day = datetime.now().day
            projection_factor = days_in_month / current_day
            
            projected_monthly_profit = profit_report['summary']['total_gross_profit'] * projection_factor
            projected_monthly_revenue = profit_report['summary']['total_revenue'] * projection_factor
            
            # Business sustainability thresholds
            min_owner_salary = 5000  # Minimum monthly salary for owner
            min_admin_salary = 4000  # Minimum monthly salary for operations admin
            min_business_reserve = 2000  # Minimum monthly reserve for business
            
            total_salary_requirement = min_owner_salary + min_admin_salary + min_business_reserve
            
            sustainability_gap = total_salary_requirement - projected_monthly_profit
            sustainability_achieved = sustainability_gap <= 0
            
            # Calculate required growth
            if not sustainability_achieved:
                current_monthly_revenue = projected_monthly_revenue
                required_revenue = current_monthly_revenue + sustainability_gap
                growth_required = (required_revenue - current_monthly_revenue) / current_monthly_revenue * 100
            else:
                growth_required = 0
            
            # Get provider metrics for growth recommendations
            with sqlite3.connect(self.db_path) as conn:
                provider_df = pd.read_sql_query('''
                    SELECT 
                        provider_id,
                        SUM(session_count) as total_sessions,
                        SUM(gross_revenue) as total_revenue,
                        COUNT(DISTINCT service_date) as working_days
                    FROM office_provider_revenue
                    WHERE service_date >= ?
                    GROUP BY provider_id
                ''', conn, params=[start_date])
            
            provider_metrics = []
            for _, provider in provider_df.iterrows():
                avg_sessions_per_day = provider['total_sessions'] / provider['working_days'] if provider['working_days'] > 0 else 0
                provider_metrics.append({
                    'provider_id': provider['provider_id'],
                    'provider_name': self._get_provider_name(provider['provider_id']),
                    'total_sessions': provider['total_sessions'],
                    'total_revenue': provider['total_revenue'],
                    'avg_sessions_per_day': round(avg_sessions_per_day, 2),
                    'working_days': provider['working_days']
                })
            
            return {
                'sustainability_analysis': {
                    'sustainability_achieved': sustainability_achieved,
                    'projected_monthly_profit': round(projected_monthly_profit, 2),
                    'projected_monthly_revenue': round(projected_monthly_revenue, 2),
                    'total_salary_requirement': total_salary_requirement,
                    'sustainability_gap': round(sustainability_gap, 2),
                    'growth_required_percent': round(growth_required, 2) if not sustainability_achieved else 0
                },
                'salary_breakdown': {
                    'min_owner_salary': min_owner_salary,
                    'min_admin_salary': min_admin_salary,
                    'min_business_reserve': min_business_reserve,
                    'total_requirement': total_salary_requirement
                },
                'current_performance': {
                    'offices_analyzed': len(profit_report['offices']),
                    'total_providers': len(provider_metrics),
                    'monthly_projection_factor': round(projection_factor, 2)
                },
                'provider_metrics': provider_metrics,
                'recommendations': self._generate_sustainability_recommendations(
                    sustainability_achieved, growth_required, provider_metrics
                ),
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error calculating business sustainability metrics: {e}")
            return {'error': str(e)}
    
    def _generate_sustainability_recommendations(self, achieved: bool, growth_required: float, 
                                               provider_metrics: List[Dict]) -> List[str]:
        """Generate actionable recommendations for business sustainability"""
        recommendations = []
        
        if achieved:
            recommendations.append("✅ Business is sustainable for both owner and admin salaries!")
            recommendations.append("Consider building additional reserves or expanding services")
        else:
            recommendations.append(f"🎯 Need {growth_required:.1f}% revenue growth to achieve sustainability")
            
            # Provider-specific recommendations
            for provider in provider_metrics:
                if provider['avg_sessions_per_day'] < 6:
                    recommendations.append(
                        f"📈 {provider['provider_name']}: Increase from {provider['avg_sessions_per_day']:.1f} to 6+ sessions/day"
                    )
            
            recommendations.append("🏢 Consider adding new providers or expanding office hours")
            recommendations.append("💰 Review fee schedules and insurance contract rates")
            recommendations.append("📊 Focus on high-revenue service lines")
        
        return recommendations
    
    def _get_provider_contract(self, provider_id: str) -> Optional[Dict]:
        """Get provider contract details from business intelligence system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT provider_percentage, company_percentage
                    FROM business_memory 
                    WHERE key = ?
                ''', (f'provider_contract_{provider_id}',))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'provider_percentage': result[0],
                        'company_percentage': result[1]
                    }
                
                # Fallback to default contracts if not found in memory
                default_contracts = {
                    'dustin': {'provider_percentage': 65, 'company_percentage': 35},
                    'sidney': {'provider_percentage': 60, 'company_percentage': 40},
                    'tammy': {'provider_percentage': 91.1, 'company_percentage': 8.9},
                    'isabel': {'provider_percentage': 100, 'company_percentage': 0}
                }
                
                return default_contracts.get(provider_id.lower())
                
        except Exception as e:
            logger.error(f"Error getting provider contract: {e}")
            return None
    
    def _get_provider_name(self, provider_id: str) -> str:
        """Get provider name from database or return formatted ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT provider_name FROM medical_data 
                    WHERE provider_name LIKE ? 
                    LIMIT 1
                ''', (f'%{provider_id}%',))
                
                result = cursor.fetchone()
                return result[0] if result else provider_id.title()
                
        except Exception as e:
            logger.error(f"Error getting provider name: {e}")
            return provider_id.title()
    
    def _get_office_name(self, office_id: str) -> str:
        """Get office name from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM offices WHERE office_id = ?', (office_id,))
                result = cursor.fetchone()
                return result[0] if result else office_id
                
        except Exception as e:
            logger.error(f"Error getting office name: {e}")
            return office_id

def main():
    """Demo function showing multi-office operations capabilities"""
    ops = MultiOfficeOperations()
    
    # Sample office setup
    main_office = Office(
        office_id="main",
        name="Main Office - Downtown",
        address="123 Main St, City, State",
        phone="555-0001",
        capacity_sessions_per_day=40,
        overhead_monthly=8000,
        rent_monthly=3500
    )
    
    satellite_office = Office(
        office_id="satellite1",
        name="Satellite Office - North",
        address="456 North Ave, City, State", 
        phone="555-0002",
        capacity_sessions_per_day=25,
        overhead_monthly=5000,
        rent_monthly=2200
    )
    
    ops.add_office(main_office)
    ops.add_office(satellite_office)
    
    # Sample provider assignment
    dustin_assignment = ProviderAssignment(
        provider_id="dustin",
        office_id="main",
        days_per_week=5,
        hours_per_day=8,
        max_sessions_per_day=8,
        effective_date="2025-01-01"
    )
    
    ops.assign_provider_to_office(dustin_assignment)
    
    # Get sustainability metrics
    sustainability = ops.get_business_sustainability_metrics()
    print("\n🏢 Business Sustainability Analysis:")
    print(f"Sustainability Achieved: {sustainability['sustainability_analysis']['sustainability_achieved']}")
    print(f"Monthly Profit Projection: ${sustainability['sustainability_analysis']['projected_monthly_profit']:,.2f}")
    print(f"Growth Required: {sustainability['sustainability_analysis']['growth_required_percent']:.1f}%")
    
    print("\n📋 Recommendations:")
    for rec in sustainability['recommendations']:
        print(f"  {rec}")

if __name__ == "__main__":
    main() 