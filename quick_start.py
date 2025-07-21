import pandas as pd
from medical_billing_db import MedicalBillingDB
from medical_billing_ai import MedicalBillingAI
import os
from pathlib import Path
import json

print("""
             █████╗ ██████╗  █████╗                       
            ██╔══██╗██╔══██╗██╔══██╗                      
            ███████║██║  ██║███████║                      
            ██╔══██║██║  ██║██╔══██║                      
            ██║  ██║██████╔╝██║  ██║                      
            ╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝                      
                                                          
██████╗ ███████╗██████╗  ██████╗ ██████╗ ████████╗███████╗
██╔══██╗██╔════╝██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝
██████╔╝█████╗  ██████╔╝██║   ██║██████╔╝   ██║   ███████╗
██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║██╔══██╗   ██║   ╚════██║
██║  ██║███████╗██║     ╚██████╔╝██║  ██║   ██║   ███████║
╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
                                                          
""")

def load_csvs_to_db(db: MedicalBillingDB, csv_folder: str = "csv_folder"):
    all_issues = []
    for dirpath, _, filenames in os.walk(csv_folder):
        for filename in filenames:
            if filename.endswith(".csv"):
                file_path = Path(dirpath) / filename
                try:
                    # Use chunked CSV processing for memory efficiency
                    print(f"Uploading {file_path} using chunked processing...")
                    result = db.upload_csv_file(str(file_path))
                    
                    if result['success']:
                        print(f"  Processed {result['total_rows_processed']} rows in {result['chunks_processed']} chunks")
                        print(f"  Success: {result['successful_rows']}, Failed: {result['failed_rows']}")
                        print(f"  Processing speed: {result['rows_per_second']:.1f} rows/second")
                    else:
                        print(f"  [!] Failed to process {file_path}: {result.get('error', 'Unknown error')}")
                        
                    if 'issues' in result and result['issues']:
                        all_issues.extend(result['issues'])
                except Exception as e:
                    print(f"  [!] Error reading {file_path}: {e}")
    # === Log all issues to a file ===
    if all_issues:
        with open("data_quality_issues.log", "w") as f:
            json.dump(all_issues, f, indent=2)
        # Summarize issues for the user
        issue_types = {}
        for issue in all_issues:
            t = issue.get('type', 'unknown')
            issue_types[t] = issue_types.get(t, 0) + 1
        print(f"\n[!] {len(all_issues)} data quality issues found during import. See 'data_quality_issues.log' for details.")
        print("    Issue summary:")
        for t, count in issue_types.items():
            print(f"      - {t}: {count}")
    else:
        print("\n[✓] No data quality issues found during import.")

if __name__ == "__main__":
    db = MedicalBillingDB()
    load_csvs_to_db(db)
    ai = MedicalBillingAI(db)
    # Removed duplicate banner and prompt here; chat_interface() will handle it
    ai.chat_interface() 