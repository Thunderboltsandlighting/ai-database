from pathlib import Path

# Re-create the meta directory
meta_dir = Path("/mnt/data/HVLC_DB/csv_folder/meta")
meta_dir.mkdir(parents=True, exist_ok=True)

# Standardized .md content for each folder
md_files = {
    "billing.md": {
        "folder": "billing",
        "purpose": "Contains CSVs related to insurance claims, credit card co-pays, and patient billing transactions.",
        "files": [
            "insurance_claims_*.csv",
            "credit_card_copay_*.csv"
        ],
        "questions": [
            "What was the total amount billed vs. collected in June?",
            "Which patients had unpaid balances over 60 days?",
            "Which payers denied the most claims?"
        ],
        "tags": "billing, claims, copay, insurance"
    },
    "finance.md": {
        "folder": "finance",
        "purpose": "Holds financial transaction data, including business credit cards, overhead costs, taxes, and reimbursements.",
        "files": [
            "credit_card_expenses_*.csv",
            "overhead_costs_*.csv",
            "tax_payments_*.csv"
        ],
        "questions": [
            "What were the top 3 overhead categories last month?",
            "How much was spent on credit cards in Q2?",
            "What’s the monthly trend in tax payments?"
        ],
        "tags": "finance, expenses, taxes, reimbursements, credit"
    },
    "meta.md": {
        "folder": "meta",
        "purpose": "This folder contains markdown documentation for all other data folders in the system.",
        "files": [
            "*.md"
        ],
        "questions": [
            "What kind of data is in the billing folder?",
            "How should I categorize new CSVs?"
        ],
        "tags": "meta, documentation, folder-descriptions"
    },
    "payroll.md": {
        "folder": "payroll",
        "purpose": "Stores W2 employee payroll runs and 1099 contractor payouts. Includes gross pay, deductions, and net amounts.",
        "files": [
            "w2_payroll_*.csv",
            "contractor_payouts_*.csv"
        ],
        "questions": [
            "What was the total payroll for W2 staff last month?",
            "How much did each contractor receive in Q2?",
            "Who had the most deductions applied?"
        ],
        "tags": "payroll, w2, contractors, compensation, earnings"
    },
    "performance.md": {
        "folder": "performance",
        "purpose": "Includes productivity reports, provider goals, and performance tracking for compensation/bonus purposes.",
        "files": [
            "monthly_goals_*.csv",
            "provider_sessions_*.csv",
            "performance_metrics_*.csv"
        ],
        "questions": [
            "Which provider exceeded their goals in May?",
            "How many sessions were billed per provider?",
            "What’s the trend in provider productivity?"
        ],
        "tags": "performance, goals, productivity, metrics"
    },
    "tracking.md": {
        "folder": "tracking",
        "purpose": "Holds datasets related to tracking patient balances, session logs, reimbursements, and referrals.",
        "files": [
            "client_balances_*.csv",
            "referrals_*.csv",
            "reimbursements_*.csv",
            "session_logs_*.csv"
        ],
        "questions": [
            "What are the average outstanding client balances?",
            "Which referral sources sent the most clients?",
            "How much has been reimbursed to staff YTD?"
        ],
        "tags": "tracking, reimbursements, referrals, balances"
    }
}

# Write each .md file with standardized content
for filename, content in md_files.items():
    text = f"""# Folder: {content['folder']}

## Purpose
{content['purpose']}

## Common Files
{chr(10).join(f"- {f}" for f in content['files'])}

## Example Questions
{chr(10).join(f"- {q}" for q in content['questions'])}

## AI Tags
{content['tags']}
"""
    with open(meta_dir / filename, "w") as f:
        f.write(text)

"✅ All .md files standardized and saved to meta/."
