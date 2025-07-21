#!/usr/bin/env python3
"""
Advanced Analytics Queries for Medical Billing Data

This module provides comprehensive analytics queries to extract business insights
from historical medical billing data. Designed to work with the MedicalBillingDB
schema and provide both high-level trends and granular analysis.
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

from medical_billing_db import MedicalBillingDB
from utils.logger import get_logger
from utils.config import get_config

logger = get_logger()
config = get_config()

class AdvancedAnalytics:
    """Advanced analytics engine for medical billing data"""
    
    def __init__(self, db_path: str = None):
        """Initialize analytics engine"""
        self.db_path = db_path or config.get("database.db_path", "medical_billing.db")
        self.db = MedicalBillingDB(self.db_path)
        
    def get_overall_business_summary(self, years: List[str] = None) -> Dict:
        """Get comprehensive business overview across all years"""
        
        year_filter = ""
        params = []
        if years:
            placeholders = ",".join(["?" for _ in years])
            year_filter = f"WHERE strftime('%Y', pt.transaction_date) IN ({placeholders})"
            params = years
        
        query = f"""
        SELECT 
            COUNT(DISTINCT strftime('%Y', pt.transaction_date)) as years_covered,
            COUNT(DISTINCT pt.provider_id) as unique_providers,
            COUNT(DISTINCT pt.payer_name) as unique_payers,
            COUNT(*) as total_transactions,
            SUM(pt.cash_applied) as total_revenue,
            AVG(pt.cash_applied) as avg_transaction_value,
            MIN(pt.transaction_date) as earliest_date,
            MAX(pt.transaction_date) as latest_date,
            SUM(CASE WHEN pt.cash_applied > 0 THEN 1 ELSE 0 END) as positive_transactions,
            SUM(CASE WHEN pt.cash_applied <= 0 THEN 1 ELSE 0 END) as zero_negative_transactions
        FROM payment_transactions pt
        {year_filter}
        """
        
        conn = sqlite3.connect(self.db_path)
        result = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if result.empty:
            return {"error": "No data found"}
        
        summary = result.iloc[0].to_dict()
        
        # Add calculated metrics
        summary['revenue_per_transaction'] = summary['total_revenue'] / summary['total_transactions']
        summary['revenue_per_provider'] = summary['total_revenue'] / summary['unique_providers']
        summary['success_rate'] = summary['positive_transactions'] / summary['total_transactions'] * 100
        
        return summary
    
    def get_yearly_trends(self) -> pd.DataFrame:
        """Get year-over-year trends and growth rates"""
        
        query = """
        SELECT 
            strftime('%Y', pt.transaction_date) as year,
            COUNT(*) as transaction_count,
            SUM(pt.cash_applied) as total_revenue,
            AVG(pt.cash_applied) as avg_transaction_value,
            COUNT(DISTINCT pt.provider_id) as active_providers,
            COUNT(DISTINCT pt.payer_name) as active_payers,
            COUNT(DISTINCT pt.patient_id) as unique_patients,
            SUM(pt.cash_applied) / COUNT(DISTINCT pt.provider_id) as revenue_per_provider,
            COUNT(*) / COUNT(DISTINCT pt.provider_id) as transactions_per_provider
        FROM payment_transactions pt
        WHERE pt.transaction_date IS NOT NULL
        GROUP BY year
        ORDER BY year
        """
        
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) > 1:
            # Calculate year-over-year growth rates
            df['revenue_growth_rate'] = df['total_revenue'].pct_change() * 100
            df['transaction_growth_rate'] = df['transaction_count'].pct_change() * 100
            df['provider_growth_rate'] = df['active_providers'].pct_change() * 100
        
        return df
    
    def get_monthly_trends(self, years: List[str] = None) -> pd.DataFrame:
        """Get detailed monthly trends with seasonality analysis"""
        
        year_filter = ""
        params = []
        if years:
            placeholders = ",".join(["?" for _ in years])
            year_filter = f"AND strftime('%Y', pt.transaction_date) IN ({placeholders})"
            params = years
        
        query = f"""
        SELECT 
            strftime('%Y-%m', pt.transaction_date) as year_month,
            strftime('%Y', pt.transaction_date) as year,
            strftime('%m', pt.transaction_date) as month,
            CASE 
                WHEN CAST(strftime('%m', pt.transaction_date) AS INTEGER) IN (12,1,2) THEN 'Winter'
                WHEN CAST(strftime('%m', pt.transaction_date) AS INTEGER) IN (3,4,5) THEN 'Spring'
                WHEN CAST(strftime('%m', pt.transaction_date) AS INTEGER) IN (6,7,8) THEN 'Summer'
                ELSE 'Fall'
            END as season,
            COUNT(*) as transaction_count,
            SUM(pt.cash_applied) as total_revenue,
            AVG(pt.cash_applied) as avg_transaction_value,
            COUNT(DISTINCT pt.provider_id) as active_providers,
            COUNT(DISTINCT pt.patient_id) as unique_patients
        FROM payment_transactions pt
        WHERE pt.transaction_date IS NOT NULL {year_filter}
        GROUP BY year_month, year, month, season
        ORDER BY year_month
        """
        
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_provider_performance_evolution(self) -> pd.DataFrame:
        """Analyze how provider performance has evolved over time"""
        
        query = """
        SELECT 
            p.provider_name,
            strftime('%Y', pt.transaction_date) as year,
            strftime('%Y-%m', pt.transaction_date) as year_month,
            COUNT(*) as transaction_count,
            SUM(pt.cash_applied) as total_revenue,
            AVG(pt.cash_applied) as avg_transaction_value,
            COUNT(DISTINCT pt.patient_id) as unique_patients,
            MIN(pt.transaction_date) as first_transaction_date,
            MAX(pt.transaction_date) as last_transaction_date,
            
            -- Calculate running totals
            SUM(SUM(pt.cash_applied)) OVER (
                PARTITION BY p.provider_name 
                ORDER BY strftime('%Y-%m', pt.transaction_date)
                ROWS UNBOUNDED PRECEDING
            ) as cumulative_revenue,
            
            -- Calculate rank within year
            RANK() OVER (
                PARTITION BY strftime('%Y', pt.transaction_date)
                ORDER BY SUM(pt.cash_applied) DESC
            ) as yearly_revenue_rank
            
        FROM providers p
        JOIN payment_transactions pt ON p.provider_id = pt.provider_id
        WHERE pt.transaction_date IS NOT NULL
        GROUP BY p.provider_name, year, year_month
        ORDER BY p.provider_name, year_month
        """
        
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_payer_analysis(self) -> Dict:
        """Comprehensive payer analysis including trends and reliability"""
        
        # Overall payer performance
        payer_overview_query = """
        SELECT 
            pt.payer_name,
            COUNT(*) as total_claims,
            SUM(pt.cash_applied) as total_revenue,
            AVG(pt.cash_applied) as avg_claim_value,
            COUNT(DISTINCT pt.provider_id) as providers_used,
            COUNT(DISTINCT strftime('%Y-%m', pt.transaction_date)) as months_active,
            MIN(pt.transaction_date) as first_claim_date,
            MAX(pt.transaction_date) as last_claim_date,
            
            -- Payment reliability metrics
            SUM(CASE WHEN pt.cash_applied > 0 THEN 1 ELSE 0 END) as paid_claims,
            SUM(CASE WHEN pt.cash_applied <= 0 THEN 1 ELSE 0 END) as zero_paid_claims,
            
            -- Market share
            SUM(pt.cash_applied) * 100.0 / (
                SELECT SUM(cash_applied) FROM payment_transactions WHERE cash_applied > 0
            ) as revenue_market_share
            
        FROM payment_transactions pt
        WHERE pt.payer_name IS NOT NULL AND pt.payer_name != ''
        GROUP BY pt.payer_name
        ORDER BY total_revenue DESC
        """
        
        # Payer trends over time
        payer_trends_query = """
        SELECT 
            pt.payer_name,
            strftime('%Y', pt.transaction_date) as year,
            COUNT(*) as yearly_claims,
            SUM(pt.cash_applied) as yearly_revenue,
            AVG(pt.cash_applied) as yearly_avg_claim
        FROM payment_transactions pt
        WHERE pt.payer_name IS NOT NULL AND pt.payer_name != ''
        GROUP BY pt.payer_name, year
        ORDER BY pt.payer_name, year
        """
        
        conn = sqlite3.connect(self.db_path)
        
        payer_overview = pd.read_sql_query(payer_overview_query, conn)
        payer_trends = pd.read_sql_query(payer_trends_query, conn)
        
        conn.close()
        
        # Calculate additional metrics
        payer_overview['payment_success_rate'] = (payer_overview['paid_claims'] / payer_overview['total_claims'] * 100)
        payer_overview['consistency_score'] = payer_overview['months_active'] / payer_overview['months_active'].max() * 100
        
        return {
            'overview': payer_overview,
            'trends': payer_trends
        }
    
    def get_seasonal_analysis(self) -> Dict:
        """Analyze seasonal patterns in revenue and activity"""
        
        seasonal_query = """
        SELECT 
            CASE 
                WHEN CAST(strftime('%m', pt.transaction_date) AS INTEGER) IN (12,1,2) THEN 'Winter'
                WHEN CAST(strftime('%m', pt.transaction_date) AS INTEGER) IN (3,4,5) THEN 'Spring'
                WHEN CAST(strftime('%m', pt.transaction_date) AS INTEGER) IN (6,7,8) THEN 'Summer'
                ELSE 'Fall'
            END as season,
            strftime('%m', pt.transaction_date) as month,
            COUNT(*) as total_transactions,
            SUM(pt.cash_applied) as total_revenue,
            AVG(pt.cash_applied) as avg_transaction_value,
            COUNT(DISTINCT pt.provider_id) as active_providers
        FROM payment_transactions pt
        WHERE pt.transaction_date IS NOT NULL
        GROUP BY season, month
        ORDER BY month
        """
        
        monthly_patterns_query = """
        SELECT 
            strftime('%m', pt.transaction_date) as month_num,
            CASE strftime('%m', pt.transaction_date)
                WHEN '01' THEN 'January'
                WHEN '02' THEN 'February'
                WHEN '03' THEN 'March'
                WHEN '04' THEN 'April'
                WHEN '05' THEN 'May'
                WHEN '06' THEN 'June'
                WHEN '07' THEN 'July'
                WHEN '08' THEN 'August'
                WHEN '09' THEN 'September'
                WHEN '10' THEN 'October'
                WHEN '11' THEN 'November'
                WHEN '12' THEN 'December'
            END as month_name,
            AVG(monthly_revenue) as avg_monthly_revenue,
            AVG(monthly_transactions) as avg_monthly_transactions
        FROM (
            SELECT 
                strftime('%Y-%m', pt.transaction_date) as year_month,
                strftime('%m', pt.transaction_date) as month,
                SUM(pt.cash_applied) as monthly_revenue,
                COUNT(*) as monthly_transactions
            FROM payment_transactions pt
            WHERE pt.transaction_date IS NOT NULL
            GROUP BY year_month, month
        ) monthly_data
        GROUP BY month_num, month_name
        ORDER BY month_num
        """
        
        conn = sqlite3.connect(self.db_path)
        
        seasonal_data = pd.read_sql_query(seasonal_query, conn)
        monthly_patterns = pd.read_sql_query(monthly_patterns_query, conn)
        
        conn.close()
        
        return {
            'seasonal_summary': seasonal_data,
            'monthly_averages': monthly_patterns
        }
    
    def get_business_growth_metrics(self) -> Dict:
        """Calculate key business growth and health metrics"""
        
        # Growth trajectory analysis
        growth_query = """
        WITH yearly_metrics AS (
            SELECT 
                strftime('%Y', pt.transaction_date) as year,
                SUM(pt.cash_applied) as annual_revenue,
                COUNT(*) as annual_transactions,
                COUNT(DISTINCT pt.provider_id) as annual_providers,
                COUNT(DISTINCT pt.patient_id) as annual_patients
            FROM payment_transactions pt
            WHERE pt.transaction_date IS NOT NULL
            GROUP BY year
            ORDER BY year
        ),
        growth_rates AS (
            SELECT 
                year,
                annual_revenue,
                annual_transactions,
                annual_providers,
                annual_patients,
                LAG(annual_revenue) OVER (ORDER BY year) as prev_revenue,
                LAG(annual_transactions) OVER (ORDER BY year) as prev_transactions,
                LAG(annual_providers) OVER (ORDER BY year) as prev_providers
            FROM yearly_metrics
        )
        SELECT 
            year,
            annual_revenue,
            annual_transactions,
            annual_providers,
            annual_patients,
            CASE 
                WHEN prev_revenue > 0 THEN 
                    ((annual_revenue - prev_revenue) / prev_revenue) * 100
                ELSE NULL 
            END as revenue_growth_rate,
            CASE 
                WHEN prev_transactions > 0 THEN 
                    ((annual_transactions - prev_transactions) / prev_transactions) * 100
                ELSE NULL 
            END as transaction_growth_rate,
            CASE 
                WHEN prev_providers > 0 THEN 
                    ((annual_providers - prev_providers) / prev_providers) * 100
                ELSE NULL 
            END as provider_growth_rate
        FROM growth_rates
        ORDER BY year
        """
        
        # Performance efficiency metrics
        efficiency_query = """
        SELECT 
            strftime('%Y', pt.transaction_date) as year,
            SUM(pt.cash_applied) / COUNT(DISTINCT pt.provider_id) as revenue_per_provider,
            COUNT(*) / COUNT(DISTINCT pt.provider_id) as transactions_per_provider,
            SUM(pt.cash_applied) / COUNT(DISTINCT pt.patient_id) as revenue_per_patient,
            COUNT(*) / COUNT(DISTINCT pt.patient_id) as transactions_per_patient,
            AVG(pt.cash_applied) as avg_transaction_value
        FROM payment_transactions pt
        WHERE pt.transaction_date IS NOT NULL
        GROUP BY year
        ORDER BY year
        """
        
        conn = sqlite3.connect(self.db_path)
        
        growth_data = pd.read_sql_query(growth_query, conn)
        efficiency_data = pd.read_sql_query(efficiency_query, conn)
        
        conn.close()
        
        return {
            'growth_trajectory': growth_data,
            'efficiency_metrics': efficiency_data
        }
    
    def get_provider_lifecycle_analysis(self) -> pd.DataFrame:
        """Analyze provider lifecycle: when they started, peak performance, current status"""
        
        query = """
        WITH provider_timeline AS (
            SELECT 
                p.provider_name,
                MIN(pt.transaction_date) as start_date,
                MAX(pt.transaction_date) as last_transaction_date,
                COUNT(*) as total_transactions,
                SUM(pt.cash_applied) as lifetime_revenue,
                AVG(pt.cash_applied) as avg_transaction_value,
                
                -- Peak performance period (best 6-month period)
                (
                    SELECT MAX(six_month_revenue)
                    FROM (
                        SELECT 
                            SUM(pt2.cash_applied) as six_month_revenue
                        FROM payment_transactions pt2
                        WHERE pt2.provider_id = p.provider_id
                            AND pt2.transaction_date BETWEEN pt.transaction_date 
                            AND date(pt.transaction_date, '+6 months')
                        GROUP BY strftime('%Y-%m', pt2.transaction_date)
                    )
                ) as peak_six_month_revenue,
                
                -- Recent performance (last 6 months)
                (
                    SELECT COALESCE(SUM(pt3.cash_applied), 0)
                    FROM payment_transactions pt3
                    WHERE pt3.provider_id = p.provider_id
                        AND pt3.transaction_date >= date('now', '-6 months')
                ) as recent_six_month_revenue,
                
                -- Activity status
                CASE 
                    WHEN MAX(pt.transaction_date) >= date('now', '-3 months') THEN 'Active'
                    WHEN MAX(pt.transaction_date) >= date('now', '-12 months') THEN 'Inactive'
                    ELSE 'Departed'
                END as status,
                
                -- Calculate days since first and last transaction
                julianday('now') - julianday(MIN(pt.transaction_date)) as days_since_start,
                julianday('now') - julianday(MAX(pt.transaction_date)) as days_since_last_transaction
                
            FROM providers p
            LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
            WHERE pt.transaction_date IS NOT NULL
            GROUP BY p.provider_id, p.provider_name
        )
        SELECT 
            *,
            CASE 
                WHEN days_since_start < 365 THEN 'New (< 1 year)'
                WHEN days_since_start < 1095 THEN 'Established (1-3 years)'
                ELSE 'Veteran (3+ years)'
            END as tenure_category,
            
            lifetime_revenue / (days_since_start / 365.0) as annual_revenue_rate,
            
            CASE 
                WHEN recent_six_month_revenue > 0 AND peak_six_month_revenue > 0 THEN
                    (recent_six_month_revenue / peak_six_month_revenue) * 100
                ELSE 0
            END as performance_relative_to_peak
            
        FROM provider_timeline
        ORDER BY lifetime_revenue DESC
        """
        
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def generate_executive_summary(self) -> Dict:
        """Generate a comprehensive executive summary of the business"""
        
        # Get all the key metrics
        overall_summary = self.get_overall_business_summary()
        yearly_trends = self.get_yearly_trends()
        growth_metrics = self.get_business_growth_metrics()
        payer_analysis = self.get_payer_analysis()
        provider_lifecycle = self.get_provider_lifecycle_analysis()
        seasonal_analysis = self.get_seasonal_analysis()
        
        # Calculate key insights
        insights = []
        
        # Revenue growth insight
        if len(yearly_trends) > 1:
            latest_growth = yearly_trends.iloc[-1]['revenue_growth_rate']
            if pd.notna(latest_growth):
                if latest_growth > 10:
                    insights.append(f"Strong growth: Revenue increased by {latest_growth:.1f}% year-over-year")
                elif latest_growth > 0:
                    insights.append(f"Modest growth: Revenue increased by {latest_growth:.1f}% year-over-year")
                else:
                    insights.append(f"Revenue declined by {abs(latest_growth):.1f}% year-over-year")
        
        # Provider insights
        active_providers = len(provider_lifecycle[provider_lifecycle['status'] == 'Active'])
        total_providers = len(provider_lifecycle)
        if total_providers > 0:
            retention_rate = (active_providers / total_providers) * 100
            insights.append(f"Provider retention: {retention_rate:.1f}% of providers are currently active")
        
        # Top payer insight
        if not payer_analysis['overview'].empty:
            top_payer = payer_analysis['overview'].iloc[0]
            insights.append(f"Top payer: {top_payer['payer_name']} represents {top_payer['revenue_market_share']:.1f}% of revenue")
        
        # Seasonality insight
        if not seasonal_analysis['monthly_averages'].empty:
            best_month = seasonal_analysis['monthly_averages'].loc[
                seasonal_analysis['monthly_averages']['avg_monthly_revenue'].idxmax()
            ]
            worst_month = seasonal_analysis['monthly_averages'].loc[
                seasonal_analysis['monthly_averages']['avg_monthly_revenue'].idxmin()
            ]
            insights.append(f"Seasonality: {best_month['month_name']} is typically the strongest month, {worst_month['month_name']} the weakest")
        
        return {
            'generated_at': datetime.now().isoformat(),
            'data_period': {
                'start_date': overall_summary.get('earliest_date'),
                'end_date': overall_summary.get('latest_date'),
                'years_covered': overall_summary.get('years_covered')
            },
            'key_metrics': {
                'total_revenue': overall_summary.get('total_revenue'),
                'total_transactions': overall_summary.get('total_transactions'),
                'unique_providers': overall_summary.get('unique_providers'),
                'unique_payers': overall_summary.get('unique_payers'),
                'avg_transaction_value': overall_summary.get('avg_transaction_value'),
                'success_rate': overall_summary.get('success_rate')
            },
            'growth_trends': {
                'yearly_data': yearly_trends.to_dict('records') if not yearly_trends.empty else [],
                'latest_revenue_growth': yearly_trends.iloc[-1]['revenue_growth_rate'] if len(yearly_trends) > 0 and pd.notna(yearly_trends.iloc[-1]['revenue_growth_rate']) else None
            },
            'provider_insights': {
                'total_providers': len(provider_lifecycle),
                'active_providers': active_providers,
                'top_performer': provider_lifecycle.iloc[0]['provider_name'] if not provider_lifecycle.empty else None,
                'top_performer_revenue': provider_lifecycle.iloc[0]['lifetime_revenue'] if not provider_lifecycle.empty else None
            },
            'payer_insights': {
                'total_payers': len(payer_analysis['overview']),
                'top_payer': payer_analysis['overview'].iloc[0]['payer_name'] if not payer_analysis['overview'].empty else None,
                'top_payer_share': payer_analysis['overview'].iloc[0]['revenue_market_share'] if not payer_analysis['overview'].empty else None
            },
            'key_insights': insights
        }
    
    def save_analysis_report(self, filename: str = None) -> str:
        """Save comprehensive analysis to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_reports/comprehensive_analysis_{timestamp}.json"
        
        # Generate all analysis
        report = {
            'executive_summary': self.generate_executive_summary(),
            'yearly_trends': self.get_yearly_trends().to_dict('records'),
            'monthly_trends': self.get_monthly_trends().to_dict('records'),
            'provider_performance': self.get_provider_performance_evolution().to_dict('records'),
            'payer_analysis': {
                'overview': self.get_payer_analysis()['overview'].to_dict('records'),
                'trends': self.get_payer_analysis()['trends'].to_dict('records')
            },
            'seasonal_analysis': {
                'seasonal_summary': self.get_seasonal_analysis()['seasonal_summary'].to_dict('records'),
                'monthly_averages': self.get_seasonal_analysis()['monthly_averages'].to_dict('records')
            },
            'provider_lifecycle': self.get_provider_lifecycle_analysis().to_dict('records'),
            'growth_metrics': {
                'trajectory': self.get_business_growth_metrics()['growth_trajectory'].to_dict('records'),
                'efficiency': self.get_business_growth_metrics()['efficiency_metrics'].to_dict('records')
            }
        }
        
        # Save to file
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Comprehensive analysis saved: {filename}")
        return filename
    
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'db'):
            self.db.close()

def main():
    """Command line interface for advanced analytics"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate advanced analytics for medical billing data')
    parser.add_argument('--summary', action='store_true', help='Generate executive summary')
    parser.add_argument('--full-report', action='store_true', help='Generate full analysis report')
    parser.add_argument('--years', nargs='+', help='Limit analysis to specific years')
    
    args = parser.parse_args()
    
    analytics = AdvancedAnalytics()
    
    try:
        if args.summary:
            summary = analytics.generate_executive_summary()
            print(json.dumps(summary, indent=2, default=str))
        elif args.full_report:
            filename = analytics.save_analysis_report()
            print(f"Full analysis report saved: {filename}")
        else:
            # Default: show business overview
            overview = analytics.get_overall_business_summary(args.years)
            print("Business Overview:")
            for key, value in overview.items():
                print(f"  {key}: {value}")
    finally:
        analytics.close()

if __name__ == "__main__":
    main() 