"""
Multi-Office Operations API Routes

Provides REST API endpoints for multi-office medical practice operations,
including automated billing sheet processing, provider analytics, and P&L reporting.
"""

from flask import Blueprint, request, jsonify
from utils.multi_office_operations import MultiOfficeOperations, Office, ProviderAssignment
from utils.logger import get_logger
import json
from datetime import datetime, timedelta

logger = get_logger(__name__)

operations_bp = Blueprint('operations', __name__)

@operations_bp.route('/offices', methods=['GET'])
def get_offices():
    """Get all office locations"""
    try:
        ops = MultiOfficeOperations()
        
        # Get offices from database
        import sqlite3
        with sqlite3.connect(ops.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT office_id, name, address, phone, capacity_sessions_per_day,
                       overhead_monthly, rent_monthly, active
                FROM offices
                WHERE active = 1
                ORDER BY name
            ''')
            
            offices = []
            for row in cursor.fetchall():
                offices.append({
                    'office_id': row[0],
                    'name': row[1],
                    'address': row[2],
                    'phone': row[3],
                    'capacity_sessions_per_day': row[4],
                    'overhead_monthly': row[5],
                    'rent_monthly': row[6],
                    'active': bool(row[7])
                })
            
            return jsonify({
                'success': True,
                'offices': offices,
                'count': len(offices)
            })
            
    except Exception as e:
        logger.error(f"Error getting offices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@operations_bp.route('/offices', methods=['POST'])
def add_office():
    """Add a new office location"""
    try:
        data = request.get_json()
        
        office = Office(
            office_id=data['office_id'],
            name=data['name'],
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            capacity_sessions_per_day=data.get('capacity_sessions_per_day', 30),
            overhead_monthly=data.get('overhead_monthly', 0),
            rent_monthly=data.get('rent_monthly', 0),
            active=data.get('active', True)
        )
        
        ops = MultiOfficeOperations()
        success = ops.add_office(office)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Office {office.name} added successfully',
                'office': data
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to add office'}), 500
            
    except Exception as e:
        logger.error(f"Error adding office: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@operations_bp.route('/providers/<provider_id>/assign', methods=['POST'])
def assign_provider():
    """Assign a provider to an office"""
    try:
        provider_id = request.view_args['provider_id']
        data = request.get_json()
        
        assignment = ProviderAssignment(
            provider_id=provider_id,
            office_id=data['office_id'],
            days_per_week=data.get('days_per_week', 5),
            hours_per_day=data.get('hours_per_day', 8),
            max_sessions_per_day=data.get('max_sessions_per_day', 8),
            effective_date=data.get('effective_date', datetime.now().strftime('%Y-%m-%d')),
            end_date=data.get('end_date')
        )
        
        ops = MultiOfficeOperations()
        success = ops.assign_provider_to_office(assignment)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Provider {provider_id} assigned to office {data["office_id"]}',
                'assignment': data
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to assign provider'}), 500
            
    except Exception as e:
        logger.error(f"Error assigning provider: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@operations_bp.route('/billing-sheet/process', methods=['POST'])
def process_billing_sheet():
    """
    Process billing sheet and calculate revenue distribution
    
    Expected JSON format:
    {
        "provider_id": "dustin",
        "office_id": "main",
        "service_date": "2025-07-16",
        "sessions": [
            {"amount": 138.61, "service_code": "90837", "patient_id": "12345"},
            {"amount": 120.00, "service_code": "90834", "patient_id": "67890"}
        ]
    }
    """
    try:
        data = request.get_json()
        
        required_fields = ['provider_id', 'office_id', 'service_date', 'sessions']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        ops = MultiOfficeOperations()
        result = ops.process_billing_sheet(
            provider_id=data['provider_id'],
            office_id=data['office_id'],
            service_date=data['service_date'],
            sessions=data['sessions']
        )
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Billing sheet processed successfully',
                'revenue_breakdown': result
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to process billing sheet'}), 500
            
    except Exception as e:
        logger.error(f"Error processing billing sheet: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@operations_bp.route('/providers/<provider_id>/caseload', methods=['GET'])
def get_provider_caseload():
    """Get comprehensive caseload analysis for a provider"""
    try:
        provider_id = request.view_args['provider_id']
        
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        ops = MultiOfficeOperations()
        analysis = ops.get_provider_caseload_analysis(provider_id, start_date, end_date)
        
        if 'error' in analysis:
            return jsonify({'success': False, 'error': analysis['error']}), 404
        
        return jsonify({
            'success': True,
            'provider_analysis': analysis
        })
        
    except Exception as e:
        logger.error(f"Error getting provider caseload: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@operations_bp.route('/profitability/office/<office_id>', methods=['GET'])
def get_office_profitability():
    """Get profitability report for a specific office"""
    try:
        office_id = request.view_args['office_id']
        
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        ops = MultiOfficeOperations()
        report = ops.generate_office_profitability_report(office_id, start_date, end_date)
        
        if 'error' in report:
            return jsonify({'success': False, 'error': report['error']}), 500
        
        return jsonify({
            'success': True,
            'profitability_report': report
        })
        
    except Exception as e:
        logger.error(f"Error getting office profitability: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@operations_bp.route('/profitability/all-offices', methods=['GET'])
def get_all_offices_profitability():
    """Get profitability report for all offices"""
    try:
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        ops = MultiOfficeOperations()
        report = ops.generate_office_profitability_report(None, start_date, end_date)
        
        if 'error' in report:
            return jsonify({'success': False, 'error': report['error']}), 500
        
        return jsonify({
            'success': True,
            'profitability_report': report
        })
        
    except Exception as e:
        logger.error(f"Error getting all offices profitability: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@operations_bp.route('/sustainability', methods=['GET'])
def get_business_sustainability():
    """
    Get business sustainability metrics to determine if practice can support
    both owner and operations admin salaries
    """
    try:
        ops = MultiOfficeOperations()
        metrics = ops.get_business_sustainability_metrics()
        
        if 'error' in metrics:
            return jsonify({'success': False, 'error': metrics['error']}), 500
        
        return jsonify({
            'success': True,
            'sustainability_metrics': metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting sustainability metrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@operations_bp.route('/dashboard/operations', methods=['GET'])
def get_operations_dashboard():
    """Get comprehensive operations dashboard data"""
    try:
        ops = MultiOfficeOperations()
        
        # Get sustainability metrics
        sustainability = ops.get_business_sustainability_metrics()
        
        # Get profitability for all offices (last 30 days)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        profitability = ops.generate_office_profitability_report(None, start_date, end_date)
        
        # Get provider caseload for active providers
        provider_analyses = []
        if 'provider_metrics' in sustainability:
            for provider in sustainability['provider_metrics']:
                analysis = ops.get_provider_caseload_analysis(
                    provider['provider_id'], start_date, end_date
                )
                if 'error' not in analysis:
                    provider_analyses.append(analysis)
        
        dashboard_data = {
            'summary': {
                'sustainability_achieved': sustainability.get('sustainability_analysis', {}).get('sustainability_achieved', False),
                'projected_monthly_profit': sustainability.get('sustainability_analysis', {}).get('projected_monthly_profit', 0),
                'growth_required': sustainability.get('sustainability_analysis', {}).get('growth_required_percent', 0),
                'total_offices': len(profitability.get('offices', [])),
                'total_providers': len(provider_analyses),
                'total_monthly_revenue': profitability.get('summary', {}).get('total_revenue', 0)
            },
            'sustainability_metrics': sustainability,
            'office_profitability': profitability,
            'provider_analyses': provider_analyses,
            'recommendations': sustainability.get('recommendations', []),
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({
            'success': True,
            'dashboard': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"Error getting operations dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@operations_bp.route('/quick-report', methods=['POST'])
def generate_quick_report():
    """
    Generate a quick revenue and profit report when uploading billing sheets
    
    Expected format:
    {
        "reports": [
            {
                "provider_id": "dustin",
                "office_id": "main", 
                "service_date": "2025-07-16",
                "sessions": [...]
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if 'reports' not in data:
            return jsonify({'success': False, 'error': 'Missing reports data'}), 400
        
        ops = MultiOfficeOperations()
        processed_reports = []
        total_revenue = 0
        total_company_cut = 0
        total_provider_payments = 0
        
        for report_data in data['reports']:
            result = ops.process_billing_sheet(
                provider_id=report_data['provider_id'],
                office_id=report_data['office_id'],
                service_date=report_data['service_date'],
                sessions=report_data['sessions']
            )
            
            if result:
                processed_reports.append(result)
                total_revenue += result['gross_revenue']
                total_company_cut += result['company_cut']
                total_provider_payments += result['provider_cut']
        
        summary = {
            'total_reports_processed': len(processed_reports),
            'total_revenue': round(total_revenue, 2),
            'total_company_cut': round(total_company_cut, 2),
            'total_provider_payments': round(total_provider_payments, 2),
            'net_profit_today': round(total_company_cut, 2),  # Simplified - would subtract daily overhead
            'avg_revenue_per_session': round(
                total_revenue / sum(len(r['sessions']) for r in data['reports']) 
                if sum(len(r['sessions']) for r in data['reports']) > 0 else 0, 2
            )
        }
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(processed_reports)} billing reports',
            'summary': summary,
            'detailed_reports': processed_reports
        })
        
    except Exception as e:
        logger.error(f"Error generating quick report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500 