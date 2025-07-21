"""
AI Assistant Functions.

This module provides helper functions for the AI assistant.
"""

import sqlite3
import re
from datetime import datetime
from flask import current_app
import sys
import os

# Add the utils directory to the path so we can import our compensation calculator
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))
from provider_compensation import ProviderCompensationCalculator

def get_provider_revenue(provider_name, month_year=None, start_date=None, end_date=None):
    """Get revenue for a specific provider, optionally for a specific month or date range.
    
    Args:
        provider_name (str): Provider name to look up
        month_year (str, optional): Month in YYYY-MM format
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format
        
    Returns:
        str: Response with provider revenue information
    """
    try:
        # Initialize the compensation calculator
        calculator = ProviderCompensationCalculator(current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
        
        # Get provider info to determine contract type
        provider_info = calculator.get_provider_info(provider_name)
        if not provider_info:
            return f"I couldn't find a provider named '{provider_name}' in the database. Please check the spelling or try another provider name."
        
        # Handle different date formats
        if month_year:
            # Parse month_year format (e.g., "2023-01")
            year = int(month_year[:4])
            month = int(month_year[5:])
            time_description = f"in {year}-{month:02d}"
            
            # Use our compensation calculator for accurate revenue
            compensation_data = calculator.calculate_provider_compensation(provider_name, year, month)
            
            if 'error' in compensation_data:
                return f"Error calculating revenue for {provider_name}: {compensation_data['error']}"
            
            # Build response based on contract type
            if compensation_data['contract_type'] == 'Owner':
                response = f"{provider_name}'s {time_description} revenue is ${compensation_data['monthly_revenue']:,.2f}.\n\n"
                response += f"**Owner Compensation Breakdown:**\n"
                response += f"• Gross Revenue: ${compensation_data['compensation']:,.2f}\n"
                response += f"• Credit Card Fees: ${compensation_data['credit_card_fees']:,.2f}\n"
                response += f"• Monthly Jitsu Fee: ${compensation_data['jitsu_fee']:,.2f}\n"
                response += f"• **Net Compensation: ${compensation_data['net_compensation']:,.2f}**\n"
            else:  # Independent Contractor
                response = f"{provider_name}'s {time_description} revenue is ${compensation_data['monthly_revenue']:,.2f}.\n\n"
                response += f"**Contractor Compensation Breakdown:**\n"
                response += f"• Monthly Revenue: ${compensation_data['monthly_revenue']:,.2f}\n"
                response += f"• Compensation Rate: {compensation_data['percentage']:.1f}%\n"
                response += f"• **Net Compensation: ${compensation_data['net_compensation']:,.2f}**\n"
            
            return response
            
        elif start_date and end_date:
            # For date ranges, we need to calculate month by month
            # This is a simplified approach - you might want to enhance this
            conn = sqlite3.connect(current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get total revenue for the date range
            cursor.execute("""
                SELECT 
                    p.provider_name, 
                    SUM(pt.cash_applied) as total_revenue, 
                    COUNT(DISTINCT pt.transaction_date || '|' || pt.cash_applied) as transaction_count,
                    SUM(pt.cash_applied) / COUNT(DISTINCT pt.transaction_date || '|' || pt.cash_applied) as avg_payment
                FROM providers p
                JOIN payment_transactions pt ON p.provider_id = pt.provider_id
                WHERE p.provider_name = ? AND pt.transaction_date >= ? AND pt.transaction_date <= ?
                GROUP BY p.provider_id
            """, (provider_name, start_date, end_date))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result['total_revenue']:
                response = f"{provider_name}'s revenue from {start_date} to {end_date} is ${float(result['total_revenue']):,.2f} from {result['transaction_count']} transactions (average of ${float(result['avg_payment']):,.2f} per transaction).\n\n"
                response += f"**Note:** For detailed compensation breakdown by month, please specify a specific month (e.g., 'January 2023')."
                return response
            else:
                return f"I couldn't find any revenue data for {provider_name} in the requested period ({start_date} to {end_date})."
        else:
            # Overall revenue - get all available data
            conn = sqlite3.connect(current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    p.provider_name, 
                    SUM(pt.cash_applied) as total_revenue, 
                    COUNT(DISTINCT pt.transaction_date || '|' || pt.cash_applied) as transaction_count,
                    SUM(pt.cash_applied) / COUNT(DISTINCT pt.transaction_date || '|' || pt.cash_applied) as avg_payment
                FROM providers p
                JOIN payment_transactions pt ON p.provider_id = pt.provider_id
                WHERE p.provider_name = ?
                GROUP BY p.provider_id
            """, (provider_name,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result['total_revenue']:
                response = f"{provider_name}'s overall revenue is ${float(result['total_revenue']):,.2f} from {result['transaction_count']} transactions (average of ${float(result['avg_payment']):,.2f} per transaction).\n\n"
                response += f"**Note:** For detailed compensation breakdown by month, please specify a specific month (e.g., 'January 2023')."
                return response
            else:
                return f"{provider_name} has no revenue data recorded in the database."
        
    except Exception as e:
        current_app.logger.error(f"Error getting provider revenue: {e}")
        return f"I encountered an error while looking up revenue data: {str(e)}"

def get_provider_compensation(provider_name, year, month):
    """Get detailed compensation information for a provider in a specific month."""
    try:
        calculator = ProviderCompensationCalculator(current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
        compensation_data = calculator.calculate_provider_compensation(provider_name, year, month)
        
        if 'error' in compensation_data:
            return f"Error: {compensation_data['error']}"
        
        return calculator.format_compensation_report(compensation_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting provider compensation: {e}")
        return f"I encountered an error while calculating compensation: {str(e)}"

def get_monthly_compensation_report(year, month):
    """Get a complete compensation report for all providers in a month."""
    try:
        calculator = ProviderCompensationCalculator(current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
        all_compensation = calculator.get_all_provider_compensation(year, month)
        
        if not all_compensation:
            return f"No active providers found for {year}-{month:02d}."
        
        report = f"**Monthly Compensation Report - {year}-{month:02d}**\n\n"
        
        total_revenue = sum(c['monthly_revenue'] for c in all_compensation)
        total_compensation = sum(c['net_compensation'] for c in all_compensation)
        
        for comp in all_compensation:
            report += calculator.format_compensation_report(comp) + "\n\n"
        
        report += f"**Summary:**\n"
        report += f"Total Revenue: ${total_revenue:,.2f}\n"
        report += f"Total Compensation: ${total_compensation:,.2f}\n"
        report += f"Company Retained: ${total_revenue - total_compensation:,.2f}\n"
        
        return report
        
    except Exception as e:
        current_app.logger.error(f"Error getting monthly compensation report: {e}")
        return f"I encountered an error while generating the compensation report: {str(e)}"

def get_data_quality_issues():
    """Get data quality issues from the database."""
    try:
        conn = sqlite3.connect(current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if data_quality_issues table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_quality_issues'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            cursor.execute("""
                SELECT issue_type, COUNT(*) as issue_count 
                FROM data_quality_issues 
                GROUP BY issue_type
            """)
            issues = cursor.fetchall()
            
            if issues:
                issue_text = ", ".join([f"{row['issue_count']} {row['issue_type'].lower()}" for row in issues])
                total_count = sum(row['issue_count'] for row in issues)
                return f"There are currently {total_count} data quality issues in the database: {issue_text}."
        
        # If no table or no issues, check for missing data directly
        cursor.execute("SELECT COUNT(*) as count FROM payment_transactions WHERE provider_id IS NULL OR provider_id = ''")
        missing_providers = cursor.fetchone()['count']
        
        if missing_providers > 0:
            return f"There are {missing_providers} payment transactions with missing provider IDs in the database."
        else:
            return "I couldn't find any significant data quality issues in the database."
    except Exception as e:
        current_app.logger.error(f"Error getting data quality issues: {e}")
        return "I encountered an error while trying to check data quality issues. Please check the database connection and schema."
    finally:
        if conn:
            conn.close()

def compare_payers():
    """Compare different payers by transaction volume and revenue."""
    try:
        conn = sqlite3.connect(current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                payer_name,
                COUNT(*) as transaction_count,
                SUM(cash_applied) as total_revenue,
                AVG(cash_applied) as avg_payment
            FROM payment_transactions
            WHERE payer_name IS NOT NULL
            GROUP BY payer_name
            ORDER BY total_revenue DESC
            LIMIT 10
        """)
        
        payers = cursor.fetchall()
        conn.close()
        
        if payers:
            response = "Here's a comparison of your top payers by revenue:\n\n"
            for i, payer in enumerate(payers, 1):
                response += f"{i}. {payer['payer_name']}: ${float(payer['total_revenue']):,.2f} from {payer['transaction_count']} transactions (avg: ${float(payer['avg_payment']):,.2f})\n"
            return response
        else:
            return "I couldn't find any payer data in the database."
    except Exception as e:
        current_app.logger.error(f"Error comparing payers: {e}")
        return "I encountered an error while comparing payers. Please check the database connection and schema."

def compare_providers(provider1, provider2, start_date=None, end_date=None):
    """Compare two providers comprehensively with detailed analysis.
    
    Args:
        provider1 (str): First provider name
        provider2 (str): Second provider name
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format
        
    Returns:
        str: Comprehensive comparison analysis
    """
    try:
        # Get database path from Flask app context or use default
        try:
            db_path = current_app.config.get('DATABASE_PATH', 'medical_billing.db')
        except RuntimeError:
            # Working outside of application context
            db_path = 'medical_billing.db'
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Set default date range if not provided
        if not start_date:
            start_date = '2024-12-01'
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get comprehensive monthly data for both providers
        query = """
        SELECT 
            p.provider_name,
            strftime('%Y-%m', pt.transaction_date) as month,
            COUNT(*) as sessions,
            SUM(pt.cash_applied) as revenue,
            AVG(pt.cash_applied) as avg_session,
            COUNT(DISTINCT pt.patient_id) as unique_patients
        FROM payment_transactions pt
        JOIN providers p ON pt.provider_id = p.provider_id
        WHERE p.provider_name IN (?, ?)
            AND pt.transaction_date >= ?
            AND pt.transaction_date <= ?
        GROUP BY p.provider_name, strftime('%Y-%m', pt.transaction_date)
        ORDER BY p.provider_name, month DESC
        """
        
        cursor.execute(query, (provider1, provider2, start_date, end_date))
        monthly_data = cursor.fetchall()
        
        if not monthly_data:
            return f"I couldn't find any data for {provider1} and {provider2} in the specified period."
        
        # Get overall performance summary
        summary_query = """
        SELECT 
            p.provider_name,
            SUM(pt.cash_applied) as total_revenue,
            COUNT(*) as total_sessions,
            AVG(pt.cash_applied) as avg_session_value,
            COUNT(DISTINCT strftime('%Y-%m', pt.transaction_date)) as active_months,
            ROUND(CAST(SUM(pt.cash_applied) AS FLOAT) / COUNT(DISTINCT strftime('%Y-%m', pt.transaction_date)), 2) as avg_monthly_revenue,
            ROUND(CAST(COUNT(*) AS FLOAT) / COUNT(DISTINCT strftime('%Y-%m', pt.transaction_date)), 1) as avg_monthly_sessions
        FROM payment_transactions pt
        JOIN providers p ON pt.provider_id = p.provider_id
        WHERE p.provider_name IN (?, ?)
            AND pt.transaction_date >= ?
            AND pt.transaction_date <= ?
        GROUP BY p.provider_name
        """
        
        cursor.execute(summary_query, (provider1, provider2, start_date, end_date))
        summary_data = cursor.fetchall()
        
        conn.close()
        
        # Build comprehensive analysis
        response = f"🏥 **COMPREHENSIVE PROVIDER COMPARISON**\n"
        response += f"Comparing {provider1} vs {provider2}\n"
        response += f"Period: {start_date} to {end_date}\n"
        response += "=" * 60 + "\n\n"
        
        # Monthly Performance Comparison
        response += "📊 **MONTHLY PERFORMANCE COMPARISON**\n"
        response += "-" * 40 + "\n"
        
        # Group data by provider
        provider_data = {}
        for row in monthly_data:
            if row['provider_name'] not in provider_data:
                provider_data[row['provider_name']] = []
            provider_data[row['provider_name']].append(dict(row))
        
        # Display monthly data
        for provider in [provider1, provider2]:
            if provider in provider_data:
                response += f"\n{provider.upper()}:\n"
                for month_data in provider_data[provider]:
                    response += f"  {month_data['month']}: {month_data['sessions']} sessions, ${month_data['revenue']:.2f} revenue (${month_data['avg_session']:.2f}/session)\n"
        
        # Growth Trend Analysis
        response += "\n📈 **GROWTH TREND ANALYSIS**\n"
        response += "-" * 40 + "\n"
        
        for provider in [provider1, provider2]:
            if provider in provider_data and len(provider_data[provider]) > 1:
                first_month = provider_data[provider][-1]  # Earliest month
                last_month = provider_data[provider][0]   # Most recent month
                
                session_change = last_month['sessions'] - first_month['sessions']
                revenue_change = last_month['revenue'] - first_month['revenue']
                session_pct = (session_change / first_month['sessions']) * 100 if first_month['sessions'] > 0 else 0
                revenue_pct = (revenue_change / first_month['revenue']) * 100 if first_month['revenue'] > 0 else 0
                
                response += f"\n{provider.upper()}:\n"
                response += f"  Sessions: {first_month['sessions']} → {last_month['sessions']} ({session_change:+d}, {session_pct:+.1f}%)\n"
                response += f"  Revenue: ${first_month['revenue']:.2f} → ${last_month['revenue']:.2f} (${revenue_change:+.2f}, {revenue_pct:+.1f}%)\n"
                response += f"  Avg Session: ${first_month['avg_session']:.2f} → ${last_month['avg_session']:.2f}\n"
        
        # Business Impact Analysis
        response += "\n💰 **BUSINESS IMPACT ANALYSIS**\n"
        response += "-" * 40 + "\n"
        
        for summary in summary_data:
            response += f"\n{summary['provider_name'].upper()}:\n"
            response += f"  Total Revenue: ${summary['total_revenue']:,.2f}\n"
            response += f"  Total Sessions: {summary['total_sessions']:,}\n"
            response += f"  Avg Session Value: ${summary['avg_session_value']:.2f}\n"
            response += f"  Active Months: {summary['active_months']}\n"
            response += f"  Avg Monthly Revenue: ${summary['avg_monthly_revenue']:.2f}\n"
            response += f"  Avg Monthly Sessions: {summary['avg_monthly_sessions']:.1f}\n"
        
        # Strategic Recommendations
        response += "\n🎯 **STRATEGIC RECOMMENDATIONS**\n"
        response += "-" * 40 + "\n"
        
        # Find current performance for recommendations
        current_data = {}
        for provider in [provider1, provider2]:
            if provider in provider_data:
                current_data[provider] = provider_data[provider][0]  # Most recent month
        
        for provider in [provider1, provider2]:
            if provider in current_data:
                current = current_data[provider]
                response += f"\nFOR {provider.upper()}:\n"
                response += f"  • Current: {current['sessions']} sessions/month, ${current['revenue']:.2f}/month\n"
                response += f"  • Avg Session Value: ${current['avg_session']:.2f}\n"
                
                # Generate specific recommendations
                if current['sessions'] < 50:
                    response += "  • Action Items:\n"
                    response += "    - Focus on increasing session frequency\n"
                    response += "    - Implement patient retention strategies\n"
                    if current['avg_session'] < 60:
                        response += "    - Optimize session value and pricing\n"
                    response += "    - Review scheduling and availability\n"
                else:
                    response += "  • Action Items:\n"
                    response += "    - Maintain current momentum\n"
                    response += "    - Focus on session value optimization\n"
                    response += "    - Consider capacity expansion\n"
        
        # Practice-Level Impact
        total_revenue = sum(s['total_revenue'] for s in summary_data)
        total_sessions = sum(s['total_sessions'] for s in summary_data)
        
        response += "\n🏢 **PRACTICE-LEVEL IMPACT**\n"
        response += "-" * 40 + "\n"
        response += f"Combined Revenue: ${total_revenue:,.2f}\n"
        response += f"Combined Sessions: {total_sessions:,}\n"
        response += f"Average Session Value: ${total_revenue/total_sessions:.2f}\n"
        
        # Calculate growth opportunities
        if len(summary_data) == 2:
            avg_monthly_revenue = sum(s['avg_monthly_revenue'] for s in summary_data)
            response += f"\nCurrent Monthly Average: ${avg_monthly_revenue:.2f}\n"
            response += "Growth Opportunities:\n"
            response += "  - Patient retention and engagement\n"
            response += "  - Session value optimization\n"
            response += "  - Scheduling efficiency improvements\n"
        
        return response
        
    except Exception as e:
        # Handle logging outside of Flask context
        try:
            current_app.logger.error(f"Error comparing providers: {e}")
        except RuntimeError:
            print(f"Error comparing providers: {e}")
        return f"I encountered an error while comparing providers: {str(e)}"

def compare_providers_enhanced(provider1, provider2, start_date=None, end_date=None):
    """Enhanced provider comparison using analytics tables.
    
    Args:
        provider1 (str): First provider name
        provider2 (str): Second provider name
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format
        
    Returns:
        str: Enhanced comprehensive comparison analysis
    """
    try:
        # Get database path from Flask app context or use default
        try:
            db_path = current_app.config.get('DATABASE_PATH', 'medical_billing.db')
        except RuntimeError:
            # Working outside of application context
            db_path = 'medical_billing.db'
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Set default date range if not provided
        if not start_date:
            start_date = '2024-12-01'
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check if analytics tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='provider_monthly_summary'")
        if not cursor.fetchone():
            # Fall back to basic comparison if analytics tables don't exist
            return compare_providers(provider1, provider2, start_date, end_date)
        
        # Get enhanced monthly data from analytics tables
        monthly_query = """
        SELECT 
            pms.provider_name,
            pms.year_month,
            pms.total_cash_applied,
            pms.session_count,
            pms.provider_cut_percentage,
            pms.provider_income,
            pms.company_income,
            pms.avg_payment_per_session,
            pms.credit_card_transactions,
            pms.insurance_payments,
            pms.cash_payments
        FROM provider_monthly_summary pms
        WHERE pms.provider_name IN (?, ?)
            AND pms.year_month >= strftime('%Y-%m', ?)
            AND pms.year_month <= strftime('%Y-%m', ?)
        ORDER BY pms.provider_name, pms.year_month DESC
        """
        
        cursor.execute(monthly_query, (provider1, provider2, start_date, end_date))
        monthly_data = cursor.fetchall()
        
        if not monthly_data:
            return f"I couldn't find any analytics data for {provider1} and {provider2} in the specified period."
        
        # Get contract information
        contract_query = """
        SELECT 
            provider_name,
            split_percentage,
            contract_type,
            notes,
            effective_date,
            end_date
        FROM provider_contracts
        WHERE provider_name IN (?, ?)
        ORDER BY effective_date DESC
        """
        
        cursor.execute(contract_query, (provider1, provider2))
        contract_data = cursor.fetchall()
        
        # Get annual summary data
        annual_query = """
        SELECT 
            provider_name,
            year,
            total_revenue,
            total_provider_income,
            total_company_income,
            months_active,
            avg_monthly_revenue
        FROM provider_annual_summary
        WHERE provider_name IN (?, ?)
        ORDER BY provider_name, year DESC
        """
        
        cursor.execute(annual_query, (provider1, provider2))
        annual_data = cursor.fetchall()
        
        conn.close()
        
        # Build enhanced analysis
        response = f"🏥 **ENHANCED PROVIDER COMPARISON**\n"
        response += f"Comparing {provider1} vs {provider2}\n"
        response += f"Period: {start_date} to {end_date}\n"
        response += "=" * 60 + "\n\n"
        
        # Contract Information
        response += "📋 **CONTRACT INFORMATION**\n"
        response += "-" * 40 + "\n"
        
        contracts = {row['provider_name']: row for row in contract_data}
        for provider in [provider1, provider2]:
            if provider in contracts:
                contract = contracts[provider]
                response += f"\n{provider.upper()}:\n"
                response += f"  Split: {contract['split_percentage']}% ({contract['contract_type']})\n"
                response += f"  Effective: {contract['effective_date']}\n"
                if contract['end_date']:
                    response += f"  End Date: {contract['end_date']}\n"
                response += f"  Notes: {contract['notes']}\n"
        
        # Enhanced Monthly Performance
        response += "\n📊 **ENHANCED MONTHLY PERFORMANCE**\n"
        response += "-" * 40 + "\n"
        
        # Group data by provider
        provider_data = {}
        for row in monthly_data:
            if row['provider_name'] not in provider_data:
                provider_data[row['provider_name']] = []
            provider_data[row['provider_name']].append(dict(row))
        
        # Display monthly data with enhanced metrics
        for provider in [provider1, provider2]:
            if provider in provider_data:
                response += f"\n{provider.upper()}:\n"
                for month_data in provider_data[provider]:
                    response += f"  {month_data['year_month']}:\n"
                    response += f"    Revenue: ${month_data['total_cash_applied']:.2f}\n"
                    response += f"    Sessions: {month_data['session_count']}\n"
                    response += f"    Provider Income: ${month_data['provider_income']:.2f}\n"
                    response += f"    Company Income: ${month_data['company_income']:.2f}\n"
                    response += f"    Avg/Session: ${month_data['avg_payment_per_session']:.2f}\n"
                    response += f"    Payment Sources:\n"
                    response += f"      - Credit Card: ${month_data['credit_card_transactions']:.2f}\n"
                    response += f"      - Insurance: ${month_data['insurance_payments']:.2f}\n"
                    response += f"      - Cash: ${month_data['cash_payments']:.2f}\n"
        
        # Growth Trend Analysis
        response += "\n📈 **ENHANCED GROWTH TREND ANALYSIS**\n"
        response += "-" * 40 + "\n"
        
        for provider in [provider1, provider2]:
            if provider in provider_data and len(provider_data[provider]) > 1:
                first_month = provider_data[provider][-1]  # Earliest month
                last_month = provider_data[provider][0]   # Most recent month
                
                revenue_change = last_month['total_cash_applied'] - first_month['total_cash_applied']
                session_change = last_month['session_count'] - first_month['session_count']
                income_change = last_month['provider_income'] - first_month['provider_income']
                
                revenue_pct = (revenue_change / first_month['total_cash_applied']) * 100 if first_month['total_cash_applied'] > 0 else 0
                session_pct = (session_change / first_month['session_count']) * 100 if first_month['session_count'] > 0 else 0
                income_pct = (income_change / first_month['provider_income']) * 100 if first_month['provider_income'] > 0 else 0
                
                response += f"\n{provider.upper()}:\n"
                response += f"  Revenue: ${first_month['total_cash_applied']:.2f} → ${last_month['total_cash_applied']:.2f} (${revenue_change:+.2f}, {revenue_pct:+.1f}%)\n"
                response += f"  Sessions: {first_month['session_count']} → {last_month['session_count']} ({session_change:+d}, {session_pct:+.1f}%)\n"
                response += f"  Provider Income: ${first_month['provider_income']:.2f} → ${last_month['provider_income']:.2f} (${income_change:+.2f}, {income_pct:+.1f}%)\n"
                response += f"  Avg Session: ${first_month['avg_payment_per_session']:.2f} → ${last_month['avg_payment_per_session']:.2f}\n"
        
        # Annual Performance Summary
        response += "\n📅 **ANNUAL PERFORMANCE SUMMARY**\n"
        response += "-" * 40 + "\n"
        
        annual_summary = {row['provider_name']: row for row in annual_data}
        for provider in [provider1, provider2]:
            if provider in annual_summary:
                annual = annual_summary[provider]
                response += f"\n{provider.upper()} ({annual['year']}):\n"
                response += f"  Total Revenue: ${annual['total_revenue']:,.2f}\n"
                response += f"  Provider Income: ${annual['total_provider_income']:,.2f}\n"
                response += f"  Company Income: ${annual['total_company_income']:,.2f}\n"
                response += f"  Months Active: {annual['months_active']}\n"
                response += f"  Avg Monthly Revenue: ${annual['avg_monthly_revenue']:,.2f}\n"
        
        # Enhanced Strategic Recommendations
        response += "\n🎯 **ENHANCED STRATEGIC RECOMMENDATIONS**\n"
        response += "-" * 40 + "\n"
        
        # Find current performance for recommendations
        current_data = {}
        for provider in [provider1, provider2]:
            if provider in provider_data:
                current_data[provider] = provider_data[provider][0]  # Most recent month
        
        for provider in [provider1, provider2]:
            if provider in current_data:
                current = current_data[provider]
                contract = contracts.get(provider, {})
                
                response += f"\nFOR {provider.upper()}:\n"
                response += f"  • Current: {current['session_count']} sessions/month, ${current['total_cash_applied']:.2f}/month\n"
                response += f"  • Provider Income: ${current['provider_income']:.2f}/month ({current['provider_cut_percentage']}% split)\n"
                response += f"  • Avg Session Value: ${current['avg_payment_per_session']:.2f}\n"
                
                # Payment source analysis
                total_payments = current['credit_card_transactions'] + current['insurance_payments'] + current['cash_payments']
                if total_payments > 0:
                    cc_pct = (current['credit_card_transactions'] / total_payments) * 100
                    ins_pct = (current['insurance_payments'] / total_payments) * 100
                    cash_pct = (current['cash_payments'] / total_payments) * 100
                    
                    response += f"  • Payment Mix:\n"
                    response += f"    - Credit Card: {cc_pct:.1f}%\n"
                    response += f"    - Insurance: {ins_pct:.1f}%\n"
                    response += f"    - Cash: {cash_pct:.1f}%\n"
                
                # Generate specific recommendations
                response += "  • Action Items:\n"
                if current['session_count'] < 50:
                    response += "    - Focus on increasing session frequency\n"
                    response += "    - Implement patient retention strategies\n"
                if current['avg_payment_per_session'] < 60:
                    response += "    - Optimize session value and pricing\n"
                if current['insurance_payments'] < current['total_cash_applied'] * 0.3:
                    response += "    - Increase insurance payment optimization\n"
                if current['credit_card_transactions'] > current['total_cash_applied'] * 0.7:
                    response += "    - Consider diversifying payment sources\n"
                response += "    - Review scheduling and availability\n"
        
        # Business Impact Analysis
        response += "\n💰 **ENHANCED BUSINESS IMPACT**\n"
        response += "-" * 40 + "\n"
        
        total_revenue = sum(m['total_cash_applied'] for m in monthly_data)
        total_provider_income = sum(m['provider_income'] for m in monthly_data)
        total_company_income = sum(m['company_income'] for m in monthly_data)
        total_sessions = sum(m['session_count'] for m in monthly_data)
        
        response += f"Combined Revenue: ${total_revenue:,.2f}\n"
        response += f"Combined Provider Income: ${total_provider_income:,.2f}\n"
        response += f"Combined Company Income: ${total_company_income:,.2f}\n"
        response += f"Combined Sessions: {total_sessions:,}\n"
        response += f"Average Session Value: ${total_revenue/total_sessions:.2f}\n"
        
        # Calculate efficiency metrics
        if len(monthly_data) > 0:
            avg_monthly_revenue = total_revenue / len(set(m['year_month'] for m in monthly_data))
            response += f"\nAverage Monthly Revenue: ${avg_monthly_revenue:.2f}\n"
            response += "Growth Opportunities:\n"
            response += "  - Optimize payment source mix\n"
            response += "  - Increase session value through pricing\n"
            response += "  - Improve patient retention and scheduling\n"
            response += "  - Focus on high-value service offerings\n"
        
        return response
        
    except Exception as e:
        # Handle logging outside of Flask context
        try:
            current_app.logger.error(f"Error in enhanced provider comparison: {e}")
        except RuntimeError:
            print(f"Error in enhanced provider comparison: {e}")
        return f"I encountered an error while performing the enhanced comparison: {str(e)}"

def analyze_dustin_overhead_coverage():
    """Analyze whether Dustin's revenue contribution covers monthly overhead expenses."""
    try:
        conn = sqlite3.connect(current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
        cursor = conn.cursor()
        
        # Get monthly overhead from expenses
        cursor.execute("SELECT SUM(amount) FROM expense_transactions WHERE status = 'active' AND frequency = 'monthly'")
        monthly_overhead = cursor.fetchone()[0] or 0
        
        # Get Dustin's contract percentage
        cursor.execute("""
            SELECT split_percentage 
            FROM provider_contracts 
            WHERE provider_name LIKE '%Dustin%' OR provider_name LIKE '%Nisley%'
            ORDER BY effective_date DESC 
            LIMIT 1
        """)
        contract_result = cursor.fetchone()
        company_percentage = (contract_result[0] / 100) if contract_result else 0.35
        
        # Get Dustin's provider_id
        cursor.execute("SELECT provider_id FROM providers WHERE provider_name LIKE '%Dustin%' OR provider_name LIKE '%Nisley%'")
        dustin_id_result = cursor.fetchone()
        dustin_id = dustin_id_result[0] if dustin_id_result else 38
        
        # Get Dustin's yearly performance
        cursor.execute("""
            SELECT 
                strftime('%Y', transaction_date) as year,
                COUNT(*) as transactions,
                SUM(cash_applied) as total_revenue,
                AVG(cash_applied) as avg_per_transaction
            FROM payment_transactions 
            WHERE provider_id = ?
            GROUP BY strftime('%Y', transaction_date)
            ORDER BY year
        """, (dustin_id,))
        
        dustin_yearly = cursor.fetchall()
        
        result = f"=== DUSTIN OVERHEAD COVERAGE ANALYSIS ===\n\n"
        result += f"Monthly Overhead: ${monthly_overhead:,.2f}\n"
        result += f"Annual Overhead: ${monthly_overhead * 12:,.2f}\n\n"
        result += f"Dustin's Contract: {company_percentage*100:.1f}% to company, {(1-company_percentage)*100:.1f}% to provider\n\n"
        
        result += "YEAR-BY-YEAR ANALYSIS:\n"
        
        for year_data in dustin_yearly:
            year, transactions, total_revenue, avg_transaction = year_data
            
            # Calculate company's share from Dustin
            company_share = total_revenue * company_percentage
            
            # Calculate monthly averages
            monthly_revenue_contribution = company_share / 12
            
            # Calculate coverage percentage
            overhead_coverage = (monthly_revenue_contribution / monthly_overhead) * 100 if monthly_overhead > 0 else 0
            
            result += f"\n{year}:\n"
            result += f"  • Transactions: {transactions:,}\n"
            result += f"  • Total Revenue: ${total_revenue:,.2f}\n"
            result += f"  • Company Share ({company_percentage*100:.1f}%): ${company_share:,.2f}\n"
            result += f"  • Monthly Contribution: ${monthly_revenue_contribution:,.2f}\n"
            result += f"  • Overhead Coverage: {overhead_coverage:.1f}%\n"
            
            if overhead_coverage >= 100:
                surplus = monthly_revenue_contribution - monthly_overhead
                result += f"  • ✅ COVERS overhead with ${surplus:,.2f} monthly surplus\n"
            else:
                shortfall = monthly_overhead - monthly_revenue_contribution
                result += f"  • ❌ SHORTFALL of ${shortfall:,.2f} per month\n"
        
        # Get 2025 YTD data
        cursor.execute("""
            SELECT 
                COUNT(*) as transactions,
                SUM(cash_applied) as total_revenue,
                MIN(transaction_date) as first_date,
                MAX(transaction_date) as last_date
            FROM payment_transactions 
            WHERE provider_id = ?
            AND strftime('%Y', transaction_date) = '2025'
        """, (dustin_id,))
        
        dustin_2025 = cursor.fetchone()
        
        if dustin_2025 and dustin_2025[1]:
            transactions, total_revenue, first_date, last_date = dustin_2025
            company_share = total_revenue * company_percentage
            
            # Calculate months active in 2025
            from datetime import datetime
            start = datetime.strptime(first_date, '%Y-%m-%d')
            end = datetime.strptime(last_date, '%Y-%m-%d')
            months_active = ((end.year - start.year) * 12 + end.month - start.month) + 1
            
            monthly_contribution = company_share / months_active if months_active > 0 else 0
            coverage = (monthly_contribution / monthly_overhead) * 100 if monthly_overhead > 0 else 0
            
            result += f"\n2025 YEAR-TO-DATE:\n"
            result += f"  • Period: {first_date} to {last_date} ({months_active} months)\n"
            result += f"  • Transactions: {transactions:,}\n"
            result += f"  • Total Revenue: ${total_revenue:,.2f}\n"
            result += f"  • Company Share: ${company_share:,.2f}\n"
            result += f"  • Monthly Contribution: ${monthly_contribution:,.2f}\n"
            result += f"  • Overhead Coverage: {coverage:.1f}%\n"
        
        # Break-even analysis
        needed_total_revenue = monthly_overhead / company_percentage
        avg_transaction = sum(year[3] for year in dustin_yearly) / len(dustin_yearly) if dustin_yearly else 65
        needed_transactions = needed_total_revenue / avg_transaction
        
        result += f"\nBREAK-EVEN REQUIREMENTS:\n"
        result += f"  • Monthly revenue needed: ${needed_total_revenue:,.2f}\n"
        result += f"  • Transactions needed per month: {needed_transactions:.0f}\n"
        result += f"  • Current avg transaction: ${avg_transaction:.2f}\n"
        
        # Summary conclusion
        latest_year = dustin_yearly[-1] if dustin_yearly else None
        if latest_year:
            latest_coverage = (latest_year[2] * company_percentage / 12 / monthly_overhead) * 100
            if latest_coverage >= 100:
                result += f"\n🎯 CONCLUSION: Dustin IS covering overhead expenses ({latest_coverage:.1f}% coverage)\n"
            else:
                result += f"\n⚠️ CONCLUSION: Dustin is NOT covering overhead expenses ({latest_coverage:.1f}% coverage)\n"
                result += f"Performance has declined significantly from 2023 levels.\n"
        
        conn.close()
        return result
        
    except Exception as e:
        return f"Error analyzing Dustin's overhead coverage: {e}"