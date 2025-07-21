"""
Provider Performance Analytics & Optimization System

Comprehensive analytics for provider performance, comfort zones, trends, and optimization.
Designed for data-driven decision making in multi-provider medical practice operations.

Features:
- Provider comfort zone analysis (optimal caseload without burnout)
- Monthly and yearly performance trends
- Minimum caseload calculations for profitability
- Growth potential analysis and recommendations
- Detailed business intelligence dashboards
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging
from dataclasses import dataclass, asdict
from utils.config import get_config
from utils.logger import get_logger
from utils.multi_office_operations import MultiOfficeOperations

logger = get_logger(__name__)

@dataclass
class ProviderComfortZone:
    """Provider comfort zone analysis data structure"""
    provider_id: str
    provider_name: str
    optimal_min_caseload: int  # Minimum for business profitability
    comfort_zone_min: int      # Lower bound of comfort zone (17-20 typical)
    comfort_zone_max: int      # Upper bound of comfort zone
    peak_performance: int      # Maximum sustainable (like wife's 25-29)
    burnout_threshold: int     # Warning threshold
    current_average: float
    comfort_zone_status: str   # "Below", "Optimal", "High", "Risk"

@dataclass
class PerformanceTrend:
    """Monthly performance trend data"""
    provider_id: str
    month: str
    sessions_count: int
    clients_served: int
    revenue_generated: float
    provider_payment: float
    company_profit: float
    utilization_rate: float
    efficiency_score: float    # Revenue per session
    trend_direction: str       # "Improving", "Stable", "Declining"

@dataclass
class GrowthRecommendation:
    """Growth and improvement recommendations"""
    provider_id: str
    provider_name: str
    current_performance: Dict
    growth_potential: Dict
    business_recommendations: List[str]
    provider_recommendations: List[str]
    timeline_suggestions: Dict
    risk_factors: List[str]

class ProviderPerformanceAnalytics:
    """
    Advanced provider performance analytics system
    
    Provides comprehensive analysis of:
    - Provider comfort zones and optimal caseloads
    - Performance trends and patterns
    - Growth potential and recommendations
    - Business intelligence for data-driven decisions
    """
    
    def __init__(self, db_path: str = None):
        config = get_config()
        self.db_path = db_path or config.get('database', {}).get('path', 'medical_billing.db')
        self.ops = MultiOfficeOperations(self.db_path)
        self.initialize_analytics_tables()
        
        # Industry standard comfort zones
        self.standard_comfort_zones = {
            'typical_provider': {'min': 17, 'max': 20},
            'high_performer': {'min': 22, 'max': 26},
            'owner_level': {'min': 25, 'max': 29},
            'burnout_threshold': 32
        }
    
    def initialize_analytics_tables(self):
        """Initialize provider analytics tracking tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Provider comfort zones and benchmarks
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS provider_comfort_zones (
                    provider_id TEXT PRIMARY KEY,
                    optimal_min_caseload INTEGER,
                    comfort_zone_min INTEGER,
                    comfort_zone_max INTEGER,
                    peak_performance INTEGER,
                    burnout_threshold INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Monthly performance tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS provider_monthly_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    sessions_count INTEGER,
                    clients_served INTEGER,
                    revenue_generated REAL,
                    provider_payment REAL,
                    company_profit REAL,
                    utilization_rate REAL,
                    efficiency_score REAL,
                    trend_direction TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(provider_id, year, month)
                )
            ''')
            
            # Performance benchmarks and goals
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS provider_performance_goals (
                    provider_id TEXT PRIMARY KEY,
                    minimum_sessions_monthly INTEGER,
                    target_sessions_monthly INTEGER,
                    optimal_sessions_monthly INTEGER,
                    minimum_revenue_monthly REAL,
                    target_revenue_monthly REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Company-wide performance metrics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS company_performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_date TEXT NOT NULL,
                    total_providers INTEGER,
                    average_caseload REAL,
                    total_revenue REAL,
                    total_profit REAL,
                    efficiency_rating REAL,
                    sustainability_score REAL,
                    growth_rate REAL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("Provider analytics tables initialized")
    
    def calculate_provider_comfort_zones(self, provider_id: str = None) -> List[ProviderComfortZone]:
        """
        Calculate comfort zones for providers based on historical data and industry standards
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get provider filter
                provider_filter = f"WHERE provider_id = '{provider_id}'" if provider_id else ""
                
                # Get historical performance data
                query = f'''
                    SELECT 
                        provider_id,
                        AVG(session_count) as avg_sessions,
                        MIN(session_count) as min_sessions,
                        MAX(session_count) as max_sessions,
                        COUNT(*) as data_points,
                        STDDEV(session_count) as session_variance
                    FROM office_provider_revenue
                    {provider_filter}
                    GROUP BY provider_id
                    HAVING COUNT(*) >= 5
                '''
                
                performance_df = pd.read_sql_query(query, conn)
                
                comfort_zones = []
                
                for _, provider in performance_df.iterrows():
                    provider_name = self._get_provider_name(provider['provider_id'])
                    
                    # Calculate optimal ranges based on data and industry standards
                    avg_sessions = provider['avg_sessions']
                    variance = provider['session_variance'] or 0
                    
                    # Determine comfort zone based on provider type
                    if provider['provider_id'].lower() == 'isabel':  # Wife/owner level
                        comfort_min = 25
                        comfort_max = 29
                        peak_performance = 32
                    elif avg_sessions >= 22:  # High performer
                        comfort_min = max(17, int(avg_sessions - variance))
                        comfort_max = min(26, int(avg_sessions + variance))
                        peak_performance = min(30, comfort_max + 4)
                    else:  # Typical provider
                        comfort_min = 17
                        comfort_max = 20
                        peak_performance = 24
                    
                    # Calculate minimum for business profitability
                    optimal_min = self._calculate_minimum_profitable_caseload(provider['provider_id'])
                    
                    # Determine current status
                    if avg_sessions < optimal_min:
                        status = "Below Minimum"
                    elif avg_sessions < comfort_min:
                        status = "Below Comfort"
                    elif comfort_min <= avg_sessions <= comfort_max:
                        status = "Optimal"
                    elif avg_sessions <= peak_performance:
                        status = "High Performance"
                    else:
                        status = "Burnout Risk"
                    
                    comfort_zone = ProviderComfortZone(
                        provider_id=provider['provider_id'],
                        provider_name=provider_name,
                        optimal_min_caseload=optimal_min,
                        comfort_zone_min=comfort_min,
                        comfort_zone_max=comfort_max,
                        peak_performance=peak_performance,
                        burnout_threshold=peak_performance + 3,
                        current_average=round(avg_sessions, 1),
                        comfort_zone_status=status
                    )
                    
                    comfort_zones.append(comfort_zone)
                    
                    # Store in database
                    self._save_comfort_zone(comfort_zone)
                
                return comfort_zones
                
        except Exception as e:
            logger.error(f"Error calculating comfort zones: {e}")
            return []
    
    def analyze_performance_trends(self, provider_id: str = None, 
                                 months_back: int = 12) -> List[PerformanceTrend]:
        """
        Analyze month-to-month performance trends for providers
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Calculate date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=months_back * 30)
                
                provider_filter = f"AND provider_id = '{provider_id}'" if provider_id else ""
                
                # Get monthly aggregated data
                query = f'''
                    SELECT 
                        provider_id,
                        strftime('%Y', service_date) as year,
                        strftime('%m', service_date) as month,
                        SUM(session_count) as sessions_count,
                        COUNT(DISTINCT service_date) as working_days,
                        SUM(gross_revenue) as revenue_generated,
                        SUM(provider_cut) as provider_payment,
                        SUM(company_cut) as company_profit
                    FROM office_provider_revenue
                    WHERE service_date >= ? {provider_filter}
                    GROUP BY provider_id, year, month
                    ORDER BY provider_id, year, month
                '''
                
                trends_df = pd.read_sql_query(query, conn, params=[start_date.strftime('%Y-%m-%d')])
                
                performance_trends = []
                
                # Group by provider for trend analysis
                for provider_id, provider_data in trends_df.groupby('provider_id'):
                    provider_data = provider_data.sort_values(['year', 'month'])
                    
                    for i, row in provider_data.iterrows():
                        # Calculate performance metrics
                        utilization_rate = self._calculate_utilization_rate(
                            provider_id, row['sessions_count'], row['working_days']
                        )
                        
                        efficiency_score = (row['revenue_generated'] / row['sessions_count'] 
                                          if row['sessions_count'] > 0 else 0)
                        
                        # Determine trend direction (compare with previous month)
                        trend_direction = "Stable"
                        if i > 0:
                            prev_sessions = provider_data.iloc[i-1]['sessions_count']
                            change_percent = ((row['sessions_count'] - prev_sessions) / prev_sessions * 100 
                                            if prev_sessions > 0 else 0)
                            
                            if change_percent > 5:
                                trend_direction = "Improving"
                            elif change_percent < -5:
                                trend_direction = "Declining"
                        
                        # Estimate clients served (assuming ~4.5 sessions per client average)
                        clients_served = max(1, int(row['sessions_count'] / 4.5))
                        
                        trend = PerformanceTrend(
                            provider_id=provider_id,
                            month=f"{row['year']}-{row['month'].zfill(2)}",
                            sessions_count=row['sessions_count'],
                            clients_served=clients_served,
                            revenue_generated=round(row['revenue_generated'], 2),
                            provider_payment=round(row['provider_payment'], 2),
                            company_profit=round(row['company_profit'], 2),
                            utilization_rate=round(utilization_rate, 2),
                            efficiency_score=round(efficiency_score, 2),
                            trend_direction=trend_direction
                        )
                        
                        performance_trends.append(trend)
                        
                        # Store in database
                        self._save_monthly_performance(trend)
                
                return performance_trends
                
        except Exception as e:
            logger.error(f"Error analyzing performance trends: {e}")
            return []
    
    def calculate_minimum_caseload_requirements(self) -> Dict[str, Dict]:
        """
        Calculate absolute minimum caseload requirements for non-owner providers
        """
        try:
            minimum_requirements = {}
            
            # Get all non-owner providers
            providers = self._get_non_owner_providers()
            
            for provider_id in providers:
                # Get provider contract details
                contract = self.ops._get_provider_contract(provider_id)
                if not contract:
                    continue
                
                # Calculate minimum monthly expenses allocation per provider
                # Assume equal split of overhead among active providers
                monthly_overhead_per_provider = 1328.50 / len(providers)  # Base overhead split
                
                # Minimum revenue needed to cover overhead allocation + minimum profit
                minimum_profit_target = 500  # Minimum monthly profit per provider
                total_minimum_needed = monthly_overhead_per_provider + minimum_profit_target
                
                # Calculate gross revenue needed (company cut must cover overhead + profit)
                company_percentage = contract['company_percentage'] / 100
                minimum_gross_revenue = total_minimum_needed / company_percentage
                
                # Calculate sessions needed (assume average revenue per session)
                avg_revenue_per_session = self._get_average_revenue_per_session(provider_id)
                minimum_sessions_monthly = int(np.ceil(minimum_gross_revenue / avg_revenue_per_session))
                
                # Calculate recommended targets (comfort zone)
                comfort_zones = self.calculate_provider_comfort_zones(provider_id)
                comfort_zone = comfort_zones[0] if comfort_zones else None
                
                minimum_requirements[provider_id] = {
                    'provider_name': self._get_provider_name(provider_id),
                    'absolute_minimum_sessions': minimum_sessions_monthly,
                    'minimum_clients': max(1, minimum_sessions_monthly // 4),  # ~4 sessions per client
                    'comfort_zone_minimum': comfort_zone.comfort_zone_min if comfort_zone else 17,
                    'comfort_zone_maximum': comfort_zone.comfort_zone_max if comfort_zone else 20,
                    'overhead_allocation': round(monthly_overhead_per_provider, 2),
                    'minimum_gross_revenue': round(minimum_gross_revenue, 2),
                    'average_revenue_per_session': round(avg_revenue_per_session, 2),
                    'contract_company_percentage': contract['company_percentage'],
                    'gap_analysis': self._calculate_performance_gap(provider_id, minimum_sessions_monthly)
                }
            
            return minimum_requirements
            
        except Exception as e:
            logger.error(f"Error calculating minimum caseload requirements: {e}")
            return {}
    
    def generate_growth_recommendations(self, provider_id: str = None) -> List[GrowthRecommendation]:
        """
        Generate comprehensive growth potential and improvement recommendations
        """
        try:
            recommendations = []
            
            # Get providers to analyze
            providers = [provider_id] if provider_id else self._get_all_active_providers()
            
            for pid in providers:
                # Get current performance data
                current_performance = self._get_current_performance_metrics(pid)
                comfort_zones = self.calculate_provider_comfort_zones(pid)
                comfort_zone = comfort_zones[0] if comfort_zones else None
                
                if not current_performance or not comfort_zone:
                    continue
                
                # Calculate growth potential
                current_avg = current_performance['avg_monthly_sessions']
                growth_potential = {
                    'current_monthly_average': current_avg,
                    'comfort_zone_ceiling': comfort_zone.comfort_zone_max,
                    'peak_performance_potential': comfort_zone.peak_performance,
                    'sessions_to_comfort_max': max(0, comfort_zone.comfort_zone_max - current_avg),
                    'sessions_to_peak': max(0, comfort_zone.peak_performance - current_avg),
                    'revenue_growth_potential': 0,
                    'profit_growth_potential': 0
                }
                
                # Calculate revenue impact of growth
                avg_revenue_per_session = current_performance['avg_revenue_per_session']
                contract = self.ops._get_provider_contract(pid)
                company_percentage = contract['company_percentage'] / 100 if contract else 0.35
                
                if growth_potential['sessions_to_comfort_max'] > 0:
                    additional_monthly_revenue = (growth_potential['sessions_to_comfort_max'] * 
                                                avg_revenue_per_session)
                    growth_potential['revenue_growth_potential'] = round(additional_monthly_revenue, 2)
                    growth_potential['profit_growth_potential'] = round(
                        additional_monthly_revenue * company_percentage, 2
                    )
                
                # Generate business recommendations
                business_recommendations = []
                provider_recommendations = []
                risk_factors = []
                
                # Business perspective recommendations
                if current_avg < comfort_zone.optimal_min_caseload:
                    business_recommendations.append(
                        f"Critical: Provider below minimum profitable threshold. "
                        f"Need {comfort_zone.optimal_min_caseload - current_avg:.0f} more sessions monthly."
                    )
                    business_recommendations.append("Consider marketing support or referral incentives")
                
                if current_avg < comfort_zone.comfort_zone_min:
                    business_recommendations.append("Opportunity for significant growth within comfort zone")
                    business_recommendations.append("Focus on schedule optimization and client acquisition")
                elif current_avg > comfort_zone.peak_performance:
                    business_recommendations.append("Provider at risk of burnout - consider load balancing")
                    risk_factors.append("Burnout risk from excessive caseload")
                
                # Provider perspective recommendations
                if current_avg < comfort_zone.comfort_zone_max:
                    additional_potential = comfort_zone.comfort_zone_max - current_avg
                    provider_recommendations.append(
                        f"Can comfortably increase by {additional_potential:.0f} sessions/month"
                    )
                    provider_recommendations.append("Consider extending hours or improving scheduling efficiency")
                
                if current_performance['utilization_rate'] < 85:
                    provider_recommendations.append("Improve scheduling efficiency - low utilization detected")
                    provider_recommendations.append("Reduce gaps between appointments")
                
                # Timeline suggestions
                timeline_suggestions = {
                    'immediate_30_days': [],
                    'short_term_90_days': [],
                    'long_term_6_months': []
                }
                
                if growth_potential['sessions_to_comfort_max'] > 0:
                    if growth_potential['sessions_to_comfort_max'] <= 4:
                        timeline_suggestions['immediate_30_days'].append(
                            f"Add {growth_potential['sessions_to_comfort_max']:.0f} sessions this month"
                        )
                    elif growth_potential['sessions_to_comfort_max'] <= 8:
                        timeline_suggestions['short_term_90_days'].append(
                            "Gradual increase to comfort zone maximum"
                        )
                    else:
                        timeline_suggestions['long_term_6_months'].append(
                            "Systematic growth plan to reach optimal caseload"
                        )
                
                recommendation = GrowthRecommendation(
                    provider_id=pid,
                    provider_name=self._get_provider_name(pid),
                    current_performance=current_performance,
                    growth_potential=growth_potential,
                    business_recommendations=business_recommendations,
                    provider_recommendations=provider_recommendations,
                    timeline_suggestions=timeline_suggestions,
                    risk_factors=risk_factors
                )
                
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating growth recommendations: {e}")
            return []
    
    def get_company_performance_trends(self, months_back: int = 12) -> Dict:
        """
        Analyze overall company performance trends and metrics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=months_back * 30)
                
                # Get monthly company metrics
                query = '''
                    SELECT 
                        strftime('%Y-%m', service_date) as month,
                        COUNT(DISTINCT provider_id) as active_providers,
                        SUM(session_count) as total_sessions,
                        AVG(session_count) as avg_sessions_per_provider,
                        SUM(gross_revenue) as total_revenue,
                        SUM(company_cut) as total_profit,
                        AVG(gross_revenue / session_count) as avg_revenue_per_session
                    FROM office_provider_revenue
                    WHERE service_date >= ?
                    GROUP BY month
                    ORDER BY month
                '''
                
                trends_df = pd.read_sql_query(query, conn, params=[start_date.strftime('%Y-%m-%d')])
                
                # Calculate growth rates and trends
                monthly_trends = []
                for i, row in trends_df.iterrows():
                    growth_rate = 0
                    if i > 0:
                        prev_revenue = trends_df.iloc[i-1]['total_revenue']
                        if prev_revenue > 0:
                            growth_rate = ((row['total_revenue'] - prev_revenue) / prev_revenue) * 100
                    
                    # Calculate efficiency rating (revenue per provider per session)
                    efficiency_rating = (row['avg_revenue_per_session'] * row['avg_sessions_per_provider'] 
                                       if row['avg_sessions_per_provider'] > 0 else 0)
                    
                    # Calculate sustainability score (simplified metric)
                    # Based on profit margin and provider efficiency
                    profit_margin = (row['total_profit'] / row['total_revenue'] * 100 
                                   if row['total_revenue'] > 0 else 0)
                    sustainability_score = min(100, (profit_margin * 2 + efficiency_rating / 100))
                    
                    monthly_trends.append({
                        'month': row['month'],
                        'active_providers': row['active_providers'],
                        'total_sessions': row['total_sessions'],
                        'avg_caseload': round(row['avg_sessions_per_provider'], 1),
                        'total_revenue': round(row['total_revenue'], 2),
                        'total_profit': round(row['total_profit'], 2),
                        'profit_margin': round(profit_margin, 1),
                        'growth_rate': round(growth_rate, 1),
                        'efficiency_rating': round(efficiency_rating, 2),
                        'sustainability_score': round(sustainability_score, 1)
                    })
                
                # Calculate overall summary metrics
                if len(trends_df) > 0:
                    latest_month = trends_df.iloc[-1]
                    first_month = trends_df.iloc[0]
                    
                    total_growth = ((latest_month['total_revenue'] - first_month['total_revenue']) 
                                  / first_month['total_revenue'] * 100 
                                  if first_month['total_revenue'] > 0 else 0)
                    
                    avg_monthly_growth = total_growth / len(trends_df) if len(trends_df) > 0 else 0
                    
                    summary = {
                        'period_analyzed': f"{start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}",
                        'total_revenue_growth': round(total_growth, 1),
                        'avg_monthly_growth': round(avg_monthly_growth, 1),
                        'current_active_providers': int(latest_month['active_providers']),
                        'current_avg_caseload': round(latest_month['avg_sessions_per_provider'], 1),
                        'current_monthly_revenue': round(latest_month['total_revenue'], 2),
                        'current_monthly_profit': round(latest_month['total_profit'], 2),
                        'best_month': max(monthly_trends, key=lambda x: x['total_revenue'])['month'],
                        'growth_trend': 'Positive' if avg_monthly_growth > 0 else 'Negative' if avg_monthly_growth < 0 else 'Stable'
                    }
                else:
                    summary = {'error': 'No data available for analysis period'}
                
                return {
                    'summary': summary,
                    'monthly_trends': monthly_trends,
                    'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except Exception as e:
            logger.error(f"Error analyzing company performance trends: {e}")
            return {'error': str(e)}
    
    def generate_comprehensive_analytics_report(self) -> Dict:
        """
        Generate comprehensive analytics report combining all metrics
        """
        try:
            # Get all analytics components
            comfort_zones = self.calculate_provider_comfort_zones()
            performance_trends = self.analyze_performance_trends()
            minimum_requirements = self.calculate_minimum_caseload_requirements()
            growth_recommendations = self.generate_growth_recommendations()
            company_trends = self.get_company_performance_trends()
            
            # Organize by provider for detailed view
            provider_details = {}
            
            for comfort_zone in comfort_zones:
                provider_id = comfort_zone.provider_id
                provider_details[provider_id] = {
                    'provider_name': comfort_zone.provider_name,
                    'comfort_zone': asdict(comfort_zone),
                    'minimum_requirements': minimum_requirements.get(provider_id, {}),
                    'monthly_trends': [
                        asdict(trend) for trend in performance_trends 
                        if trend.provider_id == provider_id
                    ],
                    'growth_analysis': None
                }
                
                # Add growth recommendations
                for rec in growth_recommendations:
                    if rec.provider_id == provider_id:
                        provider_details[provider_id]['growth_analysis'] = asdict(rec)
                        break
            
            # Generate executive summary
            executive_summary = self._generate_executive_summary(
                comfort_zones, minimum_requirements, company_trends
            )
            
            return {
                'executive_summary': executive_summary,
                'company_trends': company_trends,
                'provider_details': provider_details,
                'total_providers_analyzed': len(provider_details),
                'analysis_period': '12 months',
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error generating comprehensive analytics report: {e}")
            return {'error': str(e)}
    
    # Helper methods
    def _calculate_minimum_profitable_caseload(self, provider_id: str) -> int:
        """Calculate minimum caseload needed for business profitability"""
        try:
            contract = self.ops._get_provider_contract(provider_id)
            if not contract:
                return 15  # Default minimum
            
            # Minimum overhead allocation per provider (simplified)
            monthly_overhead_share = 1328.50 / 4  # Assume 4 active providers
            minimum_profit_needed = monthly_overhead_share + 200  # Small profit margin
            
            company_percentage = contract['company_percentage'] / 100
            avg_revenue_per_session = self._get_average_revenue_per_session(provider_id)
            
            # Calculate sessions needed
            gross_revenue_needed = minimum_profit_needed / company_percentage
            minimum_sessions = int(np.ceil(gross_revenue_needed / avg_revenue_per_session))
            
            return minimum_sessions
            
        except Exception as e:
            logger.error(f"Error calculating minimum profitable caseload: {e}")
            return 15
    
    def _get_average_revenue_per_session(self, provider_id: str) -> float:
        """Get average revenue per session for a provider"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT AVG(gross_revenue / session_count) as avg_revenue
                    FROM office_provider_revenue
                    WHERE provider_id = ? AND session_count > 0
                ''', (provider_id,))
                
                result = cursor.fetchone()
                return result[0] if result and result[0] else 138.61  # Default average
                
        except Exception as e:
            logger.error(f"Error getting average revenue per session: {e}")
            return 138.61
    
    def _calculate_utilization_rate(self, provider_id: str, sessions: int, working_days: int) -> float:
        """Calculate provider utilization rate"""
        try:
            # Get provider capacity from assignments
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT max_sessions_per_day, days_per_week
                    FROM provider_office_assignments
                    WHERE provider_id = ? AND end_date IS NULL
                    ORDER BY effective_date DESC
                    LIMIT 1
                ''', (provider_id,))
                
                result = cursor.fetchone()
                if result:
                    max_sessions_per_day, days_per_week = result
                    monthly_capacity = max_sessions_per_day * (working_days or 20)
                    return (sessions / monthly_capacity * 100) if monthly_capacity > 0 else 0
                
                # Default calculation if no assignment data
                estimated_capacity = 8 * (working_days or 20)  # 8 sessions per day
                return (sessions / estimated_capacity * 100) if estimated_capacity > 0 else 0
                
        except Exception as e:
            logger.error(f"Error calculating utilization rate: {e}")
            return 0
    
    def _get_non_owner_providers(self) -> List[str]:
        """Get list of non-owner providers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT provider_id
                    FROM office_provider_revenue
                    WHERE provider_id NOT IN ('isabel', 'tammy')
                ''')
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting non-owner providers: {e}")
            return []
    
    def _get_all_active_providers(self) -> List[str]:
        """Get all active providers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT provider_id
                    FROM office_provider_revenue
                    WHERE service_date >= date('now', '-3 months')
                ''')
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting active providers: {e}")
            return []
    
    def _get_current_performance_metrics(self, provider_id: str) -> Dict:
        """Get current performance metrics for a provider"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        AVG(session_count) as avg_monthly_sessions,
                        AVG(gross_revenue / session_count) as avg_revenue_per_session,
                        COUNT(*) as months_data
                    FROM office_provider_revenue
                    WHERE provider_id = ? 
                    AND service_date >= date('now', '-3 months')
                ''', (provider_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'avg_monthly_sessions': result[0] or 0,
                        'avg_revenue_per_session': result[1] or 0,
                        'months_data': result[2] or 0,
                        'utilization_rate': self._calculate_utilization_rate(provider_id, result[0] or 0, 20)
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"Error getting current performance metrics: {e}")
            return {}
    
    def _calculate_performance_gap(self, provider_id: str, minimum_sessions: int) -> Dict:
        """Calculate performance gap analysis"""
        try:
            current_metrics = self._get_current_performance_metrics(provider_id)
            current_avg = current_metrics.get('avg_monthly_sessions', 0)
            
            gap = minimum_sessions - current_avg
            gap_percentage = (gap / minimum_sessions * 100) if minimum_sessions > 0 else 0
            
            return {
                'current_average': round(current_avg, 1),
                'minimum_required': minimum_sessions,
                'session_gap': round(gap, 1),
                'gap_percentage': round(gap_percentage, 1),
                'status': 'Above Minimum' if gap <= 0 else 'Below Minimum'
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance gap: {e}")
            return {}
    
    def _generate_executive_summary(self, comfort_zones: List[ProviderComfortZone], 
                                   minimum_requirements: Dict, company_trends: Dict) -> Dict:
        """Generate executive summary of key insights"""
        try:
            # Analyze comfort zone distribution
            status_counts = {}
            for cz in comfort_zones:
                status = cz.comfort_zone_status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Find providers needing attention
            critical_providers = [
                cz.provider_name for cz in comfort_zones 
                if cz.comfort_zone_status in ['Below Minimum', 'Below Comfort']
            ]
            
            high_performers = [
                cz.provider_name for cz in comfort_zones 
                if cz.comfort_zone_status in ['High Performance', 'Optimal']
            ]
            
            # Calculate total growth potential
            total_growth_potential = 0
            for provider_id, req in minimum_requirements.items():
                gap = req.get('gap_analysis', {})
                if gap.get('session_gap', 0) > 0:
                    total_growth_potential += gap['session_gap']
            
            return {
                'total_providers_analyzed': len(comfort_zones),
                'providers_in_comfort_zone': len([cz for cz in comfort_zones if cz.comfort_zone_status == 'Optimal']),
                'providers_needing_attention': len(critical_providers),
                'high_performers': len(high_performers),
                'critical_providers': critical_providers,
                'high_performer_list': high_performers,
                'total_sessions_growth_potential': round(total_growth_potential, 1),
                'company_growth_trend': company_trends.get('summary', {}).get('growth_trend', 'Unknown'),
                'avg_company_caseload': company_trends.get('summary', {}).get('current_avg_caseload', 0),
                'key_insights': self._generate_key_insights(comfort_zones, minimum_requirements, company_trends)
            }
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return {}
    
    def _generate_key_insights(self, comfort_zones: List[ProviderComfortZone], 
                              minimum_requirements: Dict, company_trends: Dict) -> List[str]:
        """Generate key business insights"""
        insights = []
        
        # Comfort zone analysis
        below_comfort = [cz for cz in comfort_zones if cz.current_average < cz.comfort_zone_min]
        if below_comfort:
            insights.append(f"{len(below_comfort)} providers operating below industry comfort zone (17-20 clients)")
        
        # Performance gaps
        total_gap = sum(req.get('gap_analysis', {}).get('session_gap', 0) 
                       for req in minimum_requirements.values() 
                       if req.get('gap_analysis', {}).get('session_gap', 0) > 0)
        
        if total_gap > 0:
            insights.append(f"Total growth opportunity: {total_gap:.0f} additional sessions/month across all providers")
        
        # Company trends
        growth_trend = company_trends.get('summary', {}).get('growth_trend')
        if growth_trend == 'Positive':
            insights.append("Company showing positive growth trend - good momentum for expansion")
        elif growth_trend == 'Negative':
            insights.append("Company growth declining - focus on provider optimization critical")
        
        # Wife's performance benchmark
        isabel_comfort = next((cz for cz in comfort_zones if cz.provider_id == 'isabel'), None)
        if isabel_comfort:
            insights.append(f"Owner (Isabel) averaging {isabel_comfort.current_average} sessions - benchmark for high performance")
        
        return insights
    
    def _save_comfort_zone(self, comfort_zone: ProviderComfortZone):
        """Save comfort zone data to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO provider_comfort_zones
                    (provider_id, optimal_min_caseload, comfort_zone_min, comfort_zone_max,
                     peak_performance, burnout_threshold, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    comfort_zone.provider_id,
                    comfort_zone.optimal_min_caseload,
                    comfort_zone.comfort_zone_min,
                    comfort_zone.comfort_zone_max,
                    comfort_zone.peak_performance,
                    comfort_zone.burnout_threshold
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving comfort zone: {e}")
    
    def _save_monthly_performance(self, trend: PerformanceTrend):
        """Save monthly performance data to database"""
        try:
            year, month = trend.month.split('-')
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO provider_monthly_performance
                    (provider_id, year, month, sessions_count, clients_served,
                     revenue_generated, provider_payment, company_profit,
                     utilization_rate, efficiency_score, trend_direction)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trend.provider_id, int(year), int(month),
                    trend.sessions_count, trend.clients_served,
                    trend.revenue_generated, trend.provider_payment,
                    trend.company_profit, trend.utilization_rate,
                    trend.efficiency_score, trend.trend_direction
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving monthly performance: {e}")
    
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

def main():
    """Demo function showing provider analytics capabilities"""
    analytics = ProviderPerformanceAnalytics()
    
    print("🔍 Provider Performance Analytics Demo")
    print("="*50)
    
    # Generate comprehensive report
    report = analytics.generate_comprehensive_analytics_report()
    
    print("\n📊 Executive Summary:")
    summary = report.get('executive_summary', {})
    print(f"Total Providers: {summary.get('total_providers_analyzed', 0)}")
    print(f"In Comfort Zone: {summary.get('providers_in_comfort_zone', 0)}")
    print(f"Need Attention: {summary.get('providers_needing_attention', 0)}")
    print(f"Growth Potential: {summary.get('total_sessions_growth_potential', 0)} sessions/month")
    
    print("\n💡 Key Insights:")
    for insight in summary.get('key_insights', []):
        print(f"  • {insight}")
    
    print(f"\n📈 Company Trend: {summary.get('company_growth_trend', 'Unknown')}")

if __name__ == "__main__":
    main() 