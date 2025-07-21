#!/usr/bin/env python
"""
Run a specific query to test the fixes without interactive mode
"""

from medical_billing_db import MedicalBillingDB
from medical_billing_ai import MedicalBillingAI
import sys

def run_query(query):
    """Run a query and display the result"""
    print(f"Running query: '{query}'")
    
    # Initialize database and AI
    db = MedicalBillingDB()
    ai = MedicalBillingAI(db_instance=db)
    
    try:
        # Use answer_query which has the timeout handling
        import time
        start_time = time.time()
        result = ai.answer_query(query)
        end_time = time.time()
        
        print(f"\nQuery completed in {end_time - start_time:.2f} seconds")
        print("-" * 70)
        print(result)
        print("-" * 70)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Get query from command line argument
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "Who is the highest earning provider?"
    
    run_query(query)