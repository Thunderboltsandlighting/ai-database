"""
Provider Performance Analytics API Routes

Provides REST API endpoints for comprehensive provider performance analytics,
comfort zone analysis, trend tracking, and growth recommendations.
"""

from flask import Blueprint, request, jsonify, current_app
from utils.provider_performance_analytics import ProviderPerformanceAnalytics
from utils.logger import get_logger
import json
from datetime import datetime

logger = get_logger(__name__)

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/provider-comfort-zones', methods=['GET'])
def get_provider_comfort_zones():
    """Get comfort zone analysis for all providers or specific provider"""
    try:
        provider_id = request.args.get('provider_id')
        
        analytics = ProviderPerformanceAnalytics()
        comfort_zones = analytics.calculate_provider_comfort_zones(provider_id)
        
        # Convert dataclass objects to dictionaries
        comfort_zones_data = []
        for cz in comfort_zones:
            comfort_zones_data.append({
                'provider_id': cz.provider_id,
                'provider_name': cz.provider_name,
                'optimal_min_caseload': cz.optimal_min_caseload,
                'comfort_zone_min': cz.comfort_zone_min,
                'comfort_zone_max': cz.comfort_zone_max,
                'peak_performance': cz.peak_performance,
                'burnout_threshold': cz.burnout_threshold,
                'current_average': cz.current_average,
                'comfort_zone_status': cz.comfort_zone_status
            })
        
        return jsonify({
            'success': True,
            'comfort_zones': comfort_zones_data,
            'total_providers': len(comfort_zones_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting provider comfort zones: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/performance-trends', methods=['GET'])
def get_performance_trends():
    """Get performance trends analysis"""
    try:
        provider_id = request.args.get('provider_id')
        months_back = int(request.args.get('months_back', 12))
        
        analytics = ProviderPerformanceAnalytics()
        trends = analytics.analyze_performance_trends(provider_id, months_back)
        
        # Convert dataclass objects to dictionaries
        trends_data = []
        for trend in trends:
            trends_data.append({
                'provider_id': trend.provider_id,
                'month': trend.month,
                'sessions_count': trend.sessions_count,
                'clients_served': trend.clients_served,
                'revenue_generated': trend.revenue_generated,
                'provider_payment': trend.provider_payment,
                'company_profit': trend.company_profit,
                'utilization_rate': trend.utilization_rate,
                'efficiency_score': trend.efficiency_score,
                'trend_direction': trend.trend_direction
            })
        
        return jsonify({
            'success': True,
            'performance_trends': trends_data,
            'period_analyzed': f'{months_back} months',
            'total_data_points': len(trends_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/minimum-caseload-requirements', methods=['GET'])
def get_minimum_caseload_requirements():
    """Get minimum caseload requirements for providers"""
    try:
        analytics = ProviderPerformanceAnalytics()
        requirements = analytics.calculate_minimum_caseload_requirements()
        
        return jsonify({
            'success': True,
            'minimum_requirements': requirements,
            'providers_analyzed': len(requirements)
        })
        
    except Exception as e:
        logger.error(f"Error getting minimum caseload requirements: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/growth-recommendations', methods=['GET'])
def get_growth_recommendations():
    """Get growth potential and recommendations"""
    try:
        provider_id = request.args.get('provider_id')
        
        analytics = ProviderPerformanceAnalytics()
        recommendations = analytics.generate_growth_recommendations(provider_id)
        
        # Convert dataclass objects to dictionaries
        recommendations_data = []
        for rec in recommendations:
            recommendations_data.append({
                'provider_id': rec.provider_id,
                'provider_name': rec.provider_name,
                'current_performance': rec.current_performance,
                'growth_potential': rec.growth_potential,
                'business_recommendations': rec.business_recommendations,
                'provider_recommendations': rec.provider_recommendations,
                'timeline_suggestions': rec.timeline_suggestions,
                'risk_factors': rec.risk_factors
            })
        
        return jsonify({
            'success': True,
            'growth_recommendations': recommendations_data,
            'providers_analyzed': len(recommendations_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting growth recommendations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/company-performance-trends', methods=['GET'])
def get_company_performance_trends():
    """Get overall company performance trends"""
    try:
        months_back = int(request.args.get('months_back', 12))
        
        analytics = ProviderPerformanceAnalytics()
        company_trends = analytics.get_company_performance_trends(months_back)
        
        return jsonify({
            'success': True,
            'company_trends': company_trends
        })
        
    except Exception as e:
        logger.error(f"Error getting company performance trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/comprehensive-report', methods=['GET'])
def get_comprehensive_analytics_report():
    """Get comprehensive analytics report with all metrics"""
    try:
        analytics = ProviderPerformanceAnalytics()
        report = analytics.generate_comprehensive_analytics_report()
        
        return jsonify({
            'success': True,
            'comprehensive_report': report
        })
        
    except Exception as e:
        logger.error(f"Error getting comprehensive analytics report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/provider-dashboard/<provider_id>', methods=['GET'])
def get_provider_dashboard(provider_id):
    """Get comprehensive dashboard for a specific provider"""
    try:
        analytics = ProviderPerformanceAnalytics()
        
        # Get all relevant data for the provider
        comfort_zones = analytics.calculate_provider_comfort_zones(provider_id)
        performance_trends = analytics.analyze_performance_trends(provider_id, 12)
        minimum_requirements = analytics.calculate_minimum_caseload_requirements()
        growth_recommendations = analytics.generate_growth_recommendations(provider_id)
        
        # Extract provider-specific data
        comfort_zone = comfort_zones[0] if comfort_zones else None
        provider_requirements = minimum_requirements.get(provider_id, {})
        provider_growth = growth_recommendations[0] if growth_recommendations else None
        
        # Convert to dictionaries
        dashboard_data = {
            'provider_id': provider_id,
            'provider_name': comfort_zone.provider_name if comfort_zone else provider_id.title(),
            'comfort_zone': {
                'optimal_min_caseload': comfort_zone.optimal_min_caseload,
                'comfort_zone_min': comfort_zone.comfort_zone_min,
                'comfort_zone_max': comfort_zone.comfort_zone_max,
                'peak_performance': comfort_zone.peak_performance,
                'burnout_threshold': comfort_zone.burnout_threshold,
                'current_average': comfort_zone.current_average,
                'comfort_zone_status': comfort_zone.comfort_zone_status
            } if comfort_zone else {},
            'minimum_requirements': provider_requirements,
            'performance_trends': [
                {
                    'month': trend.month,
                    'sessions_count': trend.sessions_count,
                    'clients_served': trend.clients_served,
                    'revenue_generated': trend.revenue_generated,
                    'provider_payment': trend.provider_payment,
                    'company_profit': trend.company_profit,
                    'utilization_rate': trend.utilization_rate,
                    'efficiency_score': trend.efficiency_score,
                    'trend_direction': trend.trend_direction
                } for trend in performance_trends
            ],
            'growth_analysis': {
                'current_performance': provider_growth.current_performance,
                'growth_potential': provider_growth.growth_potential,
                'business_recommendations': provider_growth.business_recommendations,
                'provider_recommendations': provider_growth.provider_recommendations,
                'timeline_suggestions': provider_growth.timeline_suggestions,
                'risk_factors': provider_growth.risk_factors
            } if provider_growth else {},
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({
            'success': True,
            'provider_dashboard': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"Error getting provider dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/industry-benchmarks', methods=['GET'])
def get_industry_benchmarks():
    """Get industry benchmark data for comparison"""
    try:
        benchmarks = {
            'typical_provider_comfort_zone': {
                'min_sessions_weekly': 17,
                'max_sessions_weekly': 20,
                'description': 'Standard industry comfort zone for most therapists'
            },
            'high_performer_range': {
                'min_sessions_weekly': 22,
                'max_sessions_weekly': 26,
                'description': 'High-performing providers range'
            },
            'owner_level_performance': {
                'min_sessions_weekly': 25,
                'max_sessions_weekly': 29,
                'description': 'Owner/exceptional performer level (like Isabel)'
            },
            'burnout_risk_threshold': {
                'sessions_weekly': 32,
                'description': 'Above this level indicates potential burnout risk'
            },
            'revenue_benchmarks': {
                'average_session_value': 138.61,
                'target_monthly_sessions': 80,
                'minimum_viable_sessions': 60
            },
            'utilization_targets': {
                'excellent': 85,
                'good': 75,
                'acceptable': 65,
                'needs_improvement': 50
            }
        }
        
        return jsonify({
            'success': True,
            'industry_benchmarks': benchmarks
        })
        
    except Exception as e:
        logger.error(f"Error getting industry benchmarks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/performance-alerts', methods=['GET'])
def get_performance_alerts():
    """Get performance alerts and warnings for providers"""
    try:
        analytics = ProviderPerformanceAnalytics()
        
        # Get current data
        comfort_zones = analytics.calculate_provider_comfort_zones()
        minimum_requirements = analytics.calculate_minimum_caseload_requirements()
        
        alerts = []
        
        for comfort_zone in comfort_zones:
            provider_id = comfort_zone.provider_id
            provider_name = comfort_zone.provider_name
            
            # Check for various alert conditions
            if comfort_zone.comfort_zone_status == "Below Minimum":
                alerts.append({
                    'type': 'critical',
                    'provider_id': provider_id,
                    'provider_name': provider_name,
                    'message': f'{provider_name} is below minimum profitable threshold',
                    'current_value': comfort_zone.current_average,
                    'target_value': comfort_zone.optimal_min_caseload,
                    'action_required': 'Immediate intervention needed'
                })
            
            elif comfort_zone.comfort_zone_status == "Below Comfort":
                alerts.append({
                    'type': 'warning',
                    'provider_id': provider_id,
                    'provider_name': provider_name,
                    'message': f'{provider_name} is below comfort zone',
                    'current_value': comfort_zone.current_average,
                    'target_value': comfort_zone.comfort_zone_min,
                    'action_required': 'Growth opportunity available'
                })
            
            elif comfort_zone.comfort_zone_status == "Burnout Risk":
                alerts.append({
                    'type': 'warning',
                    'provider_id': provider_id,
                    'provider_name': provider_name,
                    'message': f'{provider_name} may be at risk of burnout',
                    'current_value': comfort_zone.current_average,
                    'target_value': comfort_zone.peak_performance,
                    'action_required': 'Consider load balancing'
                })
        
        # Sort alerts by priority (critical first)
        alerts.sort(key=lambda x: {'critical': 0, 'warning': 1, 'info': 2}.get(x['type'], 3))
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'total_alerts': len(alerts),
            'critical_count': len([a for a in alerts if a['type'] == 'critical']),
            'warning_count': len([a for a in alerts if a['type'] == 'warning'])
        })
        
    except Exception as e:
        logger.error(f"Error getting performance alerts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500 

@analytics_bp.route('/provider-overhead-analysis/<provider_name>', methods=['GET'])
def get_provider_overhead_analysis(provider_name):
    """Get any provider's overhead coverage analysis with chart data."""
    try:
        from api.routes.ai_functions import analyze_dustin_overhead_coverage
        from api.utils.db import get_db_connection
        
        # Get structured data for charts
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get monthly overhead from expenses
        cursor.execute("SELECT SUM(amount) FROM expense_transactions WHERE status = 'active' AND frequency = 'monthly'")
        monthly_overhead = cursor.fetchone()[0] or 0
        
        # Get provider's contract percentage
        cursor.execute("""
            SELECT split_percentage 
            FROM provider_contracts 
            WHERE provider_name LIKE ? OR provider_name LIKE ?
            ORDER BY effective_date DESC 
            LIMIT 1
        """, (f'%{provider_name}%', f'%{provider_name.split()[0]}%'))
        contract_result = cursor.fetchone()
        company_percentage = (contract_result[0] / 100) if contract_result else 0.35
        
        # Get provider's ID
        cursor.execute("""
            SELECT provider_id 
            FROM providers 
            WHERE provider_name LIKE ? OR provider_name LIKE ?
        """, (f'%{provider_name}%', f'%{provider_name.split()[0]}%'))
        provider_id_result = cursor.fetchone()
        
        if not provider_id_result:
            return jsonify({
                'success': False,
                'error': f'Provider "{provider_name}" not found'
            }), 404
            
        provider_id = provider_id_result[0]
        
        # Get yearly performance data
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
        """, (provider_id,))
        
        yearly_data = cursor.fetchall()
        
        # Calculate structured data for charts
        yearly_performance = []
        for year_row in yearly_data:
            year, transactions, total_revenue, avg_transaction = year_row
            company_share = total_revenue * company_percentage
            monthly_contribution = company_share / 12
            coverage_percentage = (monthly_contribution / monthly_overhead) * 100 if monthly_overhead > 0 else 0
            
            yearly_performance.append({
                'year': year,
                'transactions': transactions,
                'total_revenue': float(total_revenue),
                'company_share': float(company_share),
                'monthly_contribution': float(monthly_contribution),
                'coverage_percentage': float(coverage_percentage),
                'shortfall': float(monthly_overhead - monthly_contribution) if monthly_contribution < monthly_overhead else 0,
                'surplus': float(monthly_contribution - monthly_overhead) if monthly_contribution > monthly_overhead else 0
            })
        
        # Get expense breakdown
        cursor.execute("""
            SELECT category, subcategory, amount, notes
            FROM expense_transactions
            WHERE status = 'active' AND frequency = 'monthly'
            ORDER BY amount DESC
        """)
        
        expenses = cursor.fetchall()
        expense_breakdown = []
        for exp in expenses:
            expense_breakdown.append({
                'category': exp[0],
                'subcategory': exp[1],
                'amount': float(exp[2]),
                'notes': exp[3] or ''
            })
        
        # Calculate break-even requirements
        needed_total_revenue = monthly_overhead / company_percentage if company_percentage > 0 else 0
        avg_transaction = sum(year['total_revenue'] / year['transactions'] for year in yearly_performance) / len(yearly_performance) if yearly_performance else 65
        needed_transactions = needed_total_revenue / avg_transaction if avg_transaction > 0 else 0
        
        # Generate analysis text using the provider name
        if provider_name.lower() in ['dustin', 'dustin nisley', 'nisley']:
            analysis_text = analyze_dustin_overhead_coverage()
        else:
            # Generate generic analysis for other providers
            latest_year = yearly_performance[-1] if yearly_performance else None
            if latest_year:
                analysis_text = f"""=== {provider_name.upper()} OVERHEAD COVERAGE ANALYSIS ===

Monthly Overhead: ${monthly_overhead:,.2f}
{provider_name}'s Contract: {company_percentage*100:.1f}% to company

PERFORMANCE SUMMARY:
Latest Year ({latest_year['year']}): {latest_year['coverage_percentage']:.1f}% coverage
Monthly Contribution: ${latest_year['monthly_contribution']:,.2f}
{'✅ COVERING overhead' if latest_year['coverage_percentage'] >= 100 else '❌ NOT COVERING overhead'}

BREAK-EVEN REQUIREMENTS:
Monthly revenue needed: ${needed_total_revenue:,.2f}
Transactions needed per month: {needed_transactions:.0f}"""
            else:
                analysis_text = f"No transaction data found for {provider_name}"
        
        conn.close()
        
        # Return structured data
        return jsonify({
            'success': True,
            'provider_name': provider_name,
            'overhead_analysis': {
                'monthly_overhead': float(monthly_overhead),
                'annual_overhead': float(monthly_overhead * 12),
                'company_percentage': float(company_percentage * 100),
                'provider_percentage': float((1 - company_percentage) * 100),
                'yearly_performance': yearly_performance,
                'expense_breakdown': expense_breakdown,
                'break_even': {
                    'needed_monthly_revenue': float(needed_total_revenue),
                    'needed_transactions_per_month': int(needed_transactions),
                    'current_avg_transaction': float(avg_transaction)
                },
                'current_status': {
                    'latest_year': yearly_performance[-1]['year'] if yearly_performance else None,
                    'latest_coverage': yearly_performance[-1]['coverage_percentage'] if yearly_performance else 0,
                    'is_covering_overhead': yearly_performance[-1]['coverage_percentage'] >= 100 if yearly_performance else False
                }
            },
            'analysis_text': analysis_text
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in provider overhead analysis endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/universal-analysis', methods=['POST'])
def get_universal_analysis():
    """Universal analysis endpoint that can answer any question about any data with charts."""
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({
                'success': False,
                'error': 'Question is required'
            }), 400
        
        # Use the AI routing system to determine what kind of analysis to perform
        from api.routes.ai import build_universal_data_context
        
        # Build data context for the question
        data_context = build_universal_data_context(question)
        
        # Determine what visualizations would be helpful
        visualizations = []
        chart_data = {}
        
        question_lower = question.lower()
        
        # Provider analysis
        if any(name in question_lower for name in ['dustin', 'tammy', 'sidney', 'isabel']):
            provider_names = []
            for name in ['dustin', 'tammy', 'sidney', 'isabel']:
                if name in question_lower:
                    provider_names.append(name)
            
            visualizations.append('provider_performance')
            
            # Get provider data for charts
            conn = get_db_connection()
            cursor = conn.cursor()
            
            for provider in provider_names:
                cursor.execute("""
                    SELECT provider_id FROM providers 
                    WHERE provider_name LIKE ?
                """, (f'%{provider}%',))
                result = cursor.fetchone()
                
                if result:
                    provider_id = result[0]
                    cursor.execute("""
                        SELECT 
                            strftime('%Y', transaction_date) as year,
                            COUNT(*) as transactions,
                            SUM(cash_applied) as total_revenue
                        FROM payment_transactions 
                        WHERE provider_id = ?
                        GROUP BY year
                        ORDER BY year
                    """, (provider_id,))
                    
                    provider_data = cursor.fetchall()
                    chart_data[provider] = [
                        {
                            'year': row[0],
                            'transactions': row[1],
                            'revenue': float(row[2])
                        } for row in provider_data
                    ]
            
            conn.close()
        
        # Expense analysis
        if any(term in question_lower for term in ['expense', 'cost', 'overhead', 'spending']):
            visualizations.append('expense_breakdown')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category, SUM(amount) as total
                FROM expense_transactions
                WHERE status = 'active'
                GROUP BY category
                ORDER BY total DESC
            """)
            
            expense_data = cursor.fetchall()
            chart_data['expenses'] = [
                {
                    'category': row[0],
                    'amount': float(row[1])
                } for row in expense_data
            ]
            conn.close()
        
        # Revenue trends
        if any(term in question_lower for term in ['trend', 'growth', 'performance', 'revenue']):
            visualizations.append('revenue_trends')
            # Add revenue trend data here
        
        return jsonify({
            'success': True,
            'question': question,
            'data_context': data_context,
            'visualizations': visualizations,
            'chart_data': chart_data,
            'analysis_type': 'universal'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in universal analysis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 