"""
Provider Compensation Calculator.

This module handles provider compensation calculations based on business rules:
- Tiered system for contractors: $0-$6,000 = 60%, $6,001-$8,000 = 65%, $8,000+ = 70%
- Owners get 100% minus fees: 2.9% credit card fee + $35 monthly jitsu fee
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP


class ProviderCompensationCalculator:
    """Calculate provider compensation based on business rules."""
    
    def __init__(self, db_path: str = 'medical_billing.db'):
        self.db_path = db_path
        
        # Tiered compensation structure
        self.tiered_rates = {
            (0, 6000): 0.60,      # $0-$6,000 = 60%
            (6001, 8000): 0.65,   # $6,001-$8,000 = 65%
            (8001, float('inf')): 0.70  # $8,000+ = 70%
        }
        
        # Owner fees
        self.credit_card_fee_rate = 0.029  # 2.9%
        self.monthly_jitsu_fee = 35.00     # $35
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict]:
        """Get provider contract information from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT provider_id, provider_name, contract_type, 
                       compensation_type, base_percentage, owner_fees
                FROM providers 
                WHERE provider_name = ? AND active = 1
            """, (provider_name,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            print(f"Error getting provider info: {e}")
            return None
    
    def calculate_monthly_revenue_from_csv(self, provider_name: str, year: int, month: int) -> float:
        """Calculate monthly revenue directly from CSV files as fallback."""
        try:
            import pandas as pd
            import os
            import glob
            
            # Look for CSV files matching the pattern - try multiple formats
            csv_folder = os.path.join(os.path.dirname(self.db_path), 'csv_folder', 'billing')
            
            # Try different patterns for the filename
            patterns = [
                f"{month}-31-{str(year)[-2:]}*{provider_name.split()[0]}*.csv",
                f"{month:02d}-31-{str(year)[-2:]}*{provider_name.split()[0]}*.csv", 
                f"{month}-31-{str(year)[-2:]}*Payments*{provider_name.split()[0]}*.csv",
                f"{month:02d}-31-{str(year)[-2:]}*Payments*{provider_name.split()[0]}*.csv",
                f"{month}-{str(year)[-2:]}*{provider_name.split()[0]}*.csv",
                f"{month:02d}-{str(year)[-2:]}*{provider_name.split()[0]}*.csv"
            ]
            
            csv_files = []
            for pattern in patterns:
                csv_files = glob.glob(os.path.join(csv_folder, pattern))
                if csv_files:
                    break
            
            if csv_files:
                csv_file = csv_files[0]
                print(f"Found CSV file: {csv_file}")
                df = pd.read_csv(csv_file)
                
                # Sum non-null Cash Applied values
                total_revenue = df['Cash Applied'].sum()
                return float(total_revenue)
            
            return 0.0
            
        except Exception as e:
            print(f"Error calculating revenue from CSV: {e}")
            return 0.0

    def calculate_monthly_revenue(self, provider_name: str, year: int, month: int) -> float:
        """Calculate total monthly revenue for a provider."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Format month with leading zero if needed
            month_str = f"{month:02d}"
            
            # Use a subquery to handle duplicate transactions by keeping only the first occurrence
            cursor.execute("""
                SELECT COALESCE(SUM(cash_applied), 0) as total_revenue
                FROM (
                    SELECT cash_applied,
                           ROW_NUMBER() OVER (
                               PARTITION BY transaction_date, cash_applied, COALESCE(payer_name, ''), COALESCE(claim_number, '')
                               ORDER BY transaction_id
                           ) as rn
                    FROM payment_transactions pt
                    JOIN providers p ON pt.provider_id = p.provider_id
                    WHERE p.provider_name = ? 
                    AND strftime('%Y-%m', pt.transaction_date) = ?
                ) deduplicated
                WHERE rn = 1
            """, (provider_name, f"{year}-{month_str}"))
            
            result = cursor.fetchone()
            db_revenue = float(result[0]) if result else 0.0
            conn.close()
            
            # If database revenue seems incorrect (too high), try CSV as fallback
            if db_revenue > 0:
                csv_revenue = self.calculate_monthly_revenue_from_csv(provider_name, year, month)
                
                # If CSV revenue is significantly different and lower, use CSV
                if csv_revenue > 0 and csv_revenue < db_revenue * 0.9:
                    print(f"Using CSV revenue ({csv_revenue}) instead of database revenue ({db_revenue}) due to import issues")
                    return csv_revenue
            else:
                # If database revenue is 0, check if CSV has data
                csv_revenue = self.calculate_monthly_revenue_from_csv(provider_name, year, month)
                if csv_revenue > 0:
                    print(f"Using CSV revenue ({csv_revenue}) because database has no data for this period")
                    return csv_revenue
            
            return db_revenue
            
        except Exception as e:
            print(f"Error calculating monthly revenue: {e}")
            return 0.0
    
    def get_tiered_percentage(self, monthly_revenue: float) -> float:
        """Get the appropriate percentage based on monthly revenue tier."""
        for (min_rev, max_rev), percentage in self.tiered_rates.items():
            if min_rev <= monthly_revenue <= max_rev:
                return percentage
        return 0.60  # Default to 60% if no tier matches
    
    def calculate_contractor_compensation(self, provider_name: str, year: int, month: int) -> Dict:
        """Calculate compensation for contractors using tiered system."""
        monthly_revenue = self.calculate_monthly_revenue(provider_name, year, month)
        percentage = self.get_tiered_percentage(monthly_revenue)
        compensation = monthly_revenue * percentage
        
        return {
            'provider_name': provider_name,
            'contract_type': 'Independent Contractor',
            'compensation_type': 'Tiered',
            'monthly_revenue': monthly_revenue,
            'percentage': percentage * 100,  # Convert to percentage for display
            'compensation': compensation,
            'fees': 0.0,
            'net_compensation': compensation
        }
    
    def calculate_owner_compensation(self, provider_name: str, year: int, month: int) -> Dict:
        """Calculate compensation for owners (100% minus fees)."""
        monthly_revenue = self.calculate_monthly_revenue(provider_name, year, month)
        
        # Calculate credit card fees (only on "paid at session" transactions)
        cc_fees = self.calculate_credit_card_fees(provider_name, year, month)
        
        # Monthly jitsu fee
        jitsu_fee = self.monthly_jitsu_fee
        
        total_fees = cc_fees + jitsu_fee
        net_compensation = monthly_revenue - total_fees
        
        return {
            'provider_name': provider_name,
            'contract_type': 'Owner',
            'compensation_type': '100%',
            'monthly_revenue': monthly_revenue,
            'percentage': 100.0,
            'compensation': monthly_revenue,
            'credit_card_fees': cc_fees,
            'jitsu_fee': jitsu_fee,
            'total_fees': total_fees,
            'net_compensation': net_compensation
        }
    
    def calculate_credit_card_fees(self, provider_name: str, year: int, month: int) -> float:
        """Calculate credit card fees on 'paid at session' transactions."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            month_str = f"{month:02d}"
            
            cursor.execute("""
                SELECT COALESCE(SUM(cash_applied), 0) as session_payments
                FROM payment_transactions pt
                JOIN providers p ON pt.provider_id = p.provider_id
                WHERE p.provider_name = ? 
                AND strftime('%Y-%m', pt.transaction_date) = ?
                AND LOWER(COALESCE(pt.notes, '')) LIKE '%paid at session%'
            """, (provider_name, f"{year}-{month_str}"))
            
            result = cursor.fetchone()
            conn.close()
            
            session_payments = float(result[0]) if result else 0.0
            return session_payments * self.credit_card_fee_rate
            
        except Exception as e:
            print(f"Error calculating credit card fees: {e}")
            return 0.0
    
    def calculate_provider_compensation(self, provider_name: str, year: int, month: int) -> Dict:
        """Main function to calculate provider compensation."""
        provider_info = self.get_provider_info(provider_name)
        
        if not provider_info:
            return {
                'error': f'Provider "{provider_name}" not found or inactive'
            }
        
        contract_type = provider_info['contract_type']
        
        if contract_type == 'Owner':
            return self.calculate_owner_compensation(provider_name, year, month)
        elif contract_type == 'Independent Contractor':
            return self.calculate_contractor_compensation(provider_name, year, month)
        else:
            return {
                'error': f'Unknown contract type: {contract_type}'
            }
    
    def get_all_provider_compensation(self, year: int, month: int) -> List[Dict]:
        """Get compensation for all active providers for a given month."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT provider_name FROM providers 
                WHERE active = 1 
                AND provider_name NOT IN ('Unknown', 'Test Provider', 'Another Provider')
            """)
            
            providers = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            results = []
            for provider in providers:
                compensation = self.calculate_provider_compensation(provider, year, month)
                if 'error' not in compensation:
                    results.append(compensation)
            
            return results
            
        except Exception as e:
            print(f"Error getting all provider compensation: {e}")
            return []
    
    def format_compensation_report(self, compensation_data: Dict) -> str:
        """Format compensation data into a readable report."""
        if 'error' in compensation_data:
            return f"Error: {compensation_data['error']}"
        
        report = f"**{compensation_data['provider_name']} - {compensation_data['contract_type']}**\n"
        report += f"Monthly Revenue: ${compensation_data['monthly_revenue']:,.2f}\n"
        
        if compensation_data['contract_type'] == 'Independent Contractor':
            report += f"Compensation Rate: {compensation_data['percentage']:.1f}%\n"
            report += f"Gross Compensation: ${compensation_data['compensation']:,.2f}\n"
            report += f"Net Compensation: ${compensation_data['net_compensation']:,.2f}\n"
        else:  # Owner
            report += f"Gross Compensation: ${compensation_data['compensation']:,.2f}\n"
            report += f"Credit Card Fees: ${compensation_data['credit_card_fees']:,.2f}\n"
            report += f"Jitsu Fee: ${compensation_data['jitsu_fee']:,.2f}\n"
            report += f"Total Fees: ${compensation_data['total_fees']:,.2f}\n"
            report += f"Net Compensation: ${compensation_data['net_compensation']:,.2f}\n"
        
        return report


# Convenience functions for easy use
def get_provider_compensation(provider_name: str, year: int, month: int) -> Dict:
    """Get compensation for a specific provider."""
    calculator = ProviderCompensationCalculator()
    return calculator.calculate_provider_compensation(provider_name, year, month)


def get_monthly_compensation_report(year: int, month: int) -> str:
    """Get a formatted report for all providers in a month."""
    calculator = ProviderCompensationCalculator()
    all_compensation = calculator.get_all_provider_compensation(year, month)
    
    if not all_compensation:
        return "No active providers found for the specified month."
    
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