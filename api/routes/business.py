#!/usr/bin/env python3
"""
Business Analysis API Routes
Financial analysis and growth planning endpoints
"""

from flask import Blueprint, request, jsonify
import sys
import os

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.business_intelligence import business_intelligence

business_bp = Blueprint('business', __name__)

@business_bp.route('/financial-summary', methods=['GET'])
def get_financial_summary():
    """Get comprehensive financial summary"""
    try:
        summary = business_intelligence.get_financial_summary()
        analysis = business_intelligence.calculate_break_even_analysis()
        
        return jsonify({
            'success': True,
            'summary': summary,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@business_bp.route('/break-even-analysis', methods=['GET'])
def get_break_even_analysis():
    """Get detailed break-even analysis"""
    try:
        analysis = business_intelligence.calculate_break_even_analysis()
        return jsonify({
            'success': True,
            'data': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@business_bp.route('/dustin-growth-target', methods=['GET'])
def get_dustin_growth_target():
    """Get Dustin's specific growth requirements"""
    try:
        growth_analysis = business_intelligence.get_dustin_growth_requirements()
        return jsonify({
            'success': True,
            'data': growth_analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@business_bp.route('/provider-performance', methods=['GET'])
def get_provider_performance():
    """Get current provider performance metrics"""
    try:
        performance = business_intelligence.get_current_provider_performance()
        return jsonify({
            'success': True,
            'data': performance
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@business_bp.route('/update-contract', methods=['POST'])
def update_provider_contract():
    """Update provider contract terms"""
    try:
        data = request.get_json()
        provider_name = data.get('provider_name')
        updates = data.get('updates', {})
        
        if not provider_name:
            return jsonify({
                'success': False,
                'error': 'Provider name required'
            }), 400
        
        success = business_intelligence.update_provider_contract(provider_name, updates)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Contract updated for {provider_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Provider {provider_name} not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@business_bp.route('/update-financial-structure', methods=['POST'])
def update_financial_structure():
    """Update financial structure (overhead, payments, etc.)"""
    try:
        data = request.get_json()
        
        # Update financial structure
        if 'monthly_overhead' in data:
            business_intelligence.financial_structure.monthly_overhead = float(data['monthly_overhead'])
        if 'tammy_asset_payment' in data:
            business_intelligence.financial_structure.tammy_asset_payment = float(data['tammy_asset_payment'])
        if 'tammy_mortgage_payment' in data:
            business_intelligence.financial_structure.tammy_mortgage_payment = float(data['tammy_mortgage_payment'])
        
        # Recalculate total costs
        business_intelligence.financial_structure.total_monthly_costs = (
            business_intelligence.financial_structure.monthly_overhead +
            business_intelligence.financial_structure.tammy_asset_payment +
            business_intelligence.financial_structure.tammy_mortgage_payment
        )
        
        # Save to memory
        business_intelligence.save_business_memory()
        
        return jsonify({
            'success': True,
            'message': 'Financial structure updated',
            'new_structure': {
                'monthly_overhead': business_intelligence.financial_structure.monthly_overhead,
                'tammy_asset_payment': business_intelligence.financial_structure.tammy_asset_payment,
                'tammy_mortgage_payment': business_intelligence.financial_structure.tammy_mortgage_payment,
                'total_monthly_costs': business_intelligence.financial_structure.total_monthly_costs
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@business_bp.route('/analyze', methods=['POST'])
def analyze_business_question():
    """Analyze business questions using the intelligence module"""
    try:
        data = request.get_json()
        question = data.get('question', '').lower()
        
        # Route questions to appropriate analysis
        if 'break even' in question or 'break-even' in question:
            analysis = business_intelligence.calculate_break_even_analysis()
            summary = business_intelligence.get_financial_summary()
            
            return jsonify({
                'success': True,
                'question': question,
                'analysis_type': 'break_even',
                'data': analysis,
                'summary': summary,
                'recommendations': [
                    f"Monthly shortfall: ${analysis['monthly_shortfall']:,.2f}",
                    "Focus on Dustin's client growth (Sidney at capacity)",
                    "Consider adding new provider on percentage scale",
                    "Monitor Tammy's financing payments timeline"
                ]
            })
            
        elif 'dustin' in question and ('growth' in question or 'need' in question):
            dustin_analysis = business_intelligence.get_dustin_growth_requirements()
            
            return jsonify({
                'success': True,
                'question': question,
                'analysis_type': 'dustin_growth',
                'data': dustin_analysis,
                'recommendations': [
                    f"Dustin needs {dustin_analysis.get('growth_percentage_needed', 0):.1f}% growth",
                    f"Add {dustin_analysis.get('additional_sessions_needed', 0)} sessions/month",
                    f"Target: {dustin_analysis.get('target_sessions_per_day', 0)} sessions/day"
                ]
            })
            
        elif 'provider' in question and 'performance' in question:
            performance = business_intelligence.get_current_provider_performance()
            
            return jsonify({
                'success': True,
                'question': question,
                'analysis_type': 'provider_performance',
                'data': performance
            })
            
        else:
            # General financial analysis
            analysis = business_intelligence.calculate_break_even_analysis()
            summary = business_intelligence.get_financial_summary()
            
            return jsonify({
                'success': True,
                'question': question,
                'analysis_type': 'general',
                'data': analysis,
                'summary': summary
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 