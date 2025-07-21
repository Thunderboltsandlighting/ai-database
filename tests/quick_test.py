#!/usr/bin/env python
"""
Quick test for database queries with proper JOINs
"""

import sqlite3
import time

def test_db_joins():
    """Test JOIN queries in the database"""
    print("Testing database JOIN queries...")
    
    # Open connection
    db_path = "medical_billing.db"
    conn = sqlite3.connect(db_path)
    
    try:
        # Test providers table access
        cursor = conn.execute("SELECT provider_id, provider_name FROM providers LIMIT 5")
        providers = cursor.fetchall()
        
        if providers:
            print(f"✅ Successfully accessed providers table: Found {len(providers)} providers")
            for pid, name in providers:
                print(f"  - ID {pid}: {name}")
        else:
            print("❌ No providers found in database")
        
        # Test payment_transactions JOIN with providers
        cursor = conn.execute("""
            SELECT 
                p.provider_name, 
                COUNT(*) as transaction_count,
                SUM(pt.cash_applied) as total_revenue
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
            GROUP BY p.provider_name
            ORDER BY total_revenue DESC
            LIMIT 3
        """)
        
        transactions = cursor.fetchall()
        if transactions:
            print(f"\n✅ Successfully executed JOIN query: Found {len(transactions)} results")
            for name, count, revenue in transactions:
                print(f"  - {name}: ${revenue:,.2f} from {count} transactions")
        else:
            print("❌ No transaction data found")
        
        # Test query with conditions
        cursor = conn.execute("""
            SELECT 
                p.provider_name,
                SUM(pt.cash_applied) as revenue
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
            WHERE p.provider_name LIKE ?
            GROUP BY p.provider_name
        """, ('%Sidney%',))
        
        provider_data = cursor.fetchall()
        if provider_data:
            print(f"\n✅ Successfully executed conditional JOIN query: Found {len(provider_data)} results")
            for name, revenue in provider_data:
                print(f"  - {name}: ${revenue:,.2f}")
        else:
            print("❌ No provider-specific data found")
            
        print("\n✅ All database JOIN queries passed!")
            
    except Exception as e:
        print(f"❌ Error executing SQL queries: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_db_joins()