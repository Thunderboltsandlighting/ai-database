#!/usr/bin/env python3
"""
Provider Billing CSV Processor
Processes billing CSV files to extract session date vs payment date mapping
and generate monthly/annual provider analytics
"""

import os
import csv
import sqlite3
import re
from datetime import datetime, date
from collections import defaultdict

class ProviderBillingProcessor:
    def __init__(self, db_path='medical_billing.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Session reference patterns
        self.session_patterns = [
            r'Sess:(\d{2}-\d{2}-\d{4})',  # Sess:MM-DD-YYYY
            r'Sess:(\d{4}-\d{2}-\d{2})',  # Sess:YYYY-MM-DD
        ]
        
        # Provider contracts lookup
        self.provider_contracts = self._load_provider_contracts()
    
    def _load_provider_contracts(self):
        """Load provider contract percentages"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT provider_name, split_percentage, effective_date, end_date
            FROM provider_contracts
            ORDER BY effective_date DESC
        ''')
        
        contracts = {}
        for row in cursor.fetchall():
            provider = row['provider_name']
            if provider not in contracts:
                contracts[provider] = []
            contracts[provider].append({
                'percentage': row['split_percentage'],
                'effective_date': row['effective_date'],
                'end_date': row['end_date']
            })
        
        return contracts
    
    def _extract_session_date(self, session_reference):
        """Extract session date from session reference string"""
        if not session_reference:
            return None
            
        for pattern in self.session_patterns:
            match = re.search(pattern, session_reference)
            if match:
                date_str = match.group(1)
                try:
                    # Try different date formats
                    for fmt in ['%m-%d-%Y', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(date_str, fmt).date()
                        except ValueError:
                            continue
                except:
                    continue
        
        return None
    
    def _get_provider_percentage(self, provider_name, session_date):
        """Get provider split percentage for a given date"""
        if provider_name not in self.provider_contracts:
            print(f"⚠️ Warning: No contract found for provider {provider_name}, using 65% default")
            return 65.0
        
        contracts = self.provider_contracts[provider_name]
        for contract in contracts:
            effective_date = datetime.strptime(contract['effective_date'], '%Y-%m-%d').date()
            end_date = None
            if contract['end_date']:
                end_date = datetime.strptime(contract['end_date'], '%Y-%m-%d').date()
            
            if session_date >= effective_date:
                if end_date is None or session_date <= end_date:
                    return contract['percentage']
        
        # Fallback to first contract
        return contracts[0]['percentage']
    
    def process_csv_file(self, csv_file_path):
        """Process a single CSV file and extract payment-session mappings"""
        print(f"📄 Processing: {csv_file_path}")
        
        mappings = []
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                current_payment_info = {}
                
                for row in reader:
                    # Skip empty rows
                    if not any(row.values()):
                        continue
                    
                    # Check if this is a payment header row (has Check Date, Payment From, etc.)
                    if row.get('Check Date') and row.get('Payment From'):
                        current_payment_info = {
                            'check_date': row.get('Check Date', '').strip(),
                            'date_posted': row.get('Date Posted', '').strip(),
                            'check_number': row.get('Check Number', '').strip(),
                            'payment_from': row.get('Payment From', '').strip(),
                            'reference': row.get('Reference', '').strip(),
                            'check_amount': row.get('Check Amount', '').strip(),
                            'provider': row.get('Provider', '').strip()
                        }
                    
                    # Check if this is a session detail row (has session reference and cash applied)
                    cash_applied = row.get('Cash Applied', '').strip()
                    reference = row.get('Reference', '').strip()
                    provider = row.get('Provider', '').strip() or current_payment_info.get('provider', '')
                    
                    if cash_applied and reference and 'Sess:' in reference:
                        # Extract session date from reference
                        session_date = self._extract_session_date(reference)
                        
                        if session_date:
                            try:
                                cash_amount = float(cash_applied.replace(',', '').replace('$', ''))
                                
                                # Parse payment date
                                payment_date = None
                                date_posted = current_payment_info.get('date_posted') or row.get('Date Posted', '')
                                if date_posted:
                                    try:
                                        payment_date = datetime.strptime(date_posted, '%m/%d/%Y').date()
                                    except:
                                        try:
                                            payment_date = datetime.strptime(date_posted, '%m/%d/%y').date()
                                        except:
                                            payment_date = None
                                
                                mapping = {
                                    'payment_date': payment_date,
                                    'session_date': session_date,
                                    'provider_name': provider,
                                    'cash_applied': cash_amount,
                                    'payment_source': current_payment_info.get('payment_from', ''),
                                    'session_reference': reference,
                                    'check_number': current_payment_info.get('check_number', ''),
                                    'payment_from': current_payment_info.get('payment_from', '')
                                }
                                
                                mappings.append(mapping)
                                
                            except ValueError as e:
                                print(f"⚠️ Error parsing cash amount '{cash_applied}': {e}")
                        else:
                            print(f"⚠️ Could not extract session date from: {reference}")
        
        except Exception as e:
            print(f"❌ Error processing {csv_file_path}: {e}")
        
        return mappings
    
    def insert_payment_mappings(self, mappings):
        """Insert payment-session mappings into database"""
        cursor = self.conn.cursor()
        
        inserted = 0
        for mapping in mappings:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO payment_session_mapping
                    (payment_date, session_date, provider_name, cash_applied, 
                     payment_source, session_reference, check_number, payment_from)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    mapping['payment_date'],
                    mapping['session_date'],
                    mapping['provider_name'],
                    mapping['cash_applied'],
                    mapping['payment_source'],
                    mapping['session_reference'],
                    mapping['check_number'],
                    mapping['payment_from']
                ))
                
                if cursor.rowcount > 0:
                    inserted += 1
                    
            except Exception as e:
                print(f"❌ Error inserting mapping: {e}")
        
        self.conn.commit()
        return inserted
    
    def generate_monthly_summaries(self):
        """Generate monthly summaries from payment mappings"""
        print("📊 Generating monthly summaries...")
        
        cursor = self.conn.cursor()
        
        # Get all payment mappings grouped by provider and session month
        cursor.execute('''
            SELECT 
                provider_name,
                strftime('%Y-%m', session_date) as year_month,
                SUM(cash_applied) as total_cash_applied,
                COUNT(*) as session_count
            FROM payment_session_mapping
            WHERE session_date IS NOT NULL
            GROUP BY provider_name, year_month
            ORDER BY provider_name, year_month
        ''')
        
        monthly_data = cursor.fetchall()
        
        # Clear existing monthly summaries
        cursor.execute('DELETE FROM provider_monthly_summary')
        
        for row in monthly_data:
            provider = row['provider_name']
            year_month = row['year_month']
            total_cash = row['total_cash_applied']
            session_count = row['session_count']
            
            # Get session date for percentage lookup
            session_date = datetime.strptime(year_month + '-01', '%Y-%m-%d').date()
            percentage = self._get_provider_percentage(provider, session_date)
            
            cursor.execute('''
                INSERT OR REPLACE INTO provider_monthly_summary
                (provider_name, year_month, total_cash_applied, session_count, provider_cut_percentage)
                VALUES (?, ?, ?, ?, ?)
            ''', (provider, year_month, total_cash, session_count, percentage))
        
        self.conn.commit()
        print(f"✅ Generated {len(monthly_data)} monthly summaries")
    
    def generate_annual_summaries(self):
        """Generate annual summaries from monthly summaries"""
        print("📊 Generating annual summaries...")
        
        cursor = self.conn.cursor()
        
        # Get annual totals from monthly summaries
        cursor.execute('''
            SELECT 
                provider_name,
                substr(year_month, 1, 4) as year,
                SUM(total_cash_applied) as total_revenue,
                SUM(provider_income) as total_provider_income,
                SUM(company_income) as total_company_income,
                COUNT(*) as months_active
            FROM provider_monthly_summary
            GROUP BY provider_name, substr(year_month, 1, 4)
            ORDER BY provider_name, year
        ''')
        
        annual_data = cursor.fetchall()
        
        # Clear existing annual summaries
        cursor.execute('DELETE FROM provider_annual_summary')
        
        for row in annual_data:
            cursor.execute('''
                INSERT OR REPLACE INTO provider_annual_summary
                (provider_name, year, total_revenue, total_provider_income, 
                 total_company_income, months_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                row['provider_name'],
                int(row['year']),
                row['total_revenue'],
                row['total_provider_income'],
                row['total_company_income'],
                row['months_active']
            ))
        
        self.conn.commit()
        print(f"✅ Generated {len(annual_data)} annual summaries")
    
    def process_all_billing_csvs(self, csv_directory='csv_folder/billing'):
        """Process all CSV files in the billing directory"""
        print(f"🚀 Processing all CSV files in {csv_directory}")
        
        if not os.path.exists(csv_directory):
            print(f"❌ Directory not found: {csv_directory}")
            return
        
        total_mappings = 0
        
        for filename in sorted(os.listdir(csv_directory)):
            if filename.endswith('.csv'):
                file_path = os.path.join(csv_directory, filename)
                mappings = self.process_csv_file(file_path)
                inserted = self.insert_payment_mappings(mappings)
                total_mappings += inserted
                print(f"   ✅ {filename}: {inserted} mappings inserted")
        
        print(f"\n📊 Total mappings processed: {total_mappings}")
        
        # Generate summaries
        self.generate_monthly_summaries()
        self.generate_annual_summaries()
        
        # Show results
        self.show_summary_stats()
    
    def show_summary_stats(self):
        """Show summary statistics"""
        cursor = self.conn.cursor()
        
        print("\n📊 PROVIDER ANALYTICS SUMMARY")
        print("=" * 50)
        
        # Annual summaries
        cursor.execute('''
            SELECT provider_name, year, total_revenue, total_provider_income, 
                   total_company_income, months_active
            FROM provider_annual_summary
            ORDER BY year DESC, total_revenue DESC
        ''')
        
        print("\n🏆 ANNUAL PROVIDER PERFORMANCE:")
        for row in cursor.fetchall():
            print(f"{row['provider_name']} ({row['year']}):")
            print(f"   💰 Revenue: ${row['total_revenue']:,.2f}")
            print(f"   👤 Provider: ${row['total_provider_income']:,.2f}")
            print(f"   🏢 Company: ${row['total_company_income']:,.2f}")
            print(f"   📅 Active: {row['months_active']} months\n")
    
    def close(self):
        """Close database connection"""
        self.conn.close()

def main():
    print("🚀 Provider Billing CSV Processor")
    print("=" * 50)
    
    processor = ProviderBillingProcessor()
    
    try:
        processor.process_all_billing_csvs()
    finally:
        processor.close()

if __name__ == "__main__":
    main() 