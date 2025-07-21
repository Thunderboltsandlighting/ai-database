# CSV Header Format Guidelines

To ensure optimal compatibility with the HVLC_DB system, CSV files should follow specific header formatting conventions. This document provides guidance on how to format CSV headers for best results.

## Recommended Header Format

Headers should:
1. Use underscore separators instead of spaces
2. Be lowercase
3. Avoid special characters
4. Use descriptive but concise names

## Header Conversion Examples

### Insurance Claims Data CSV

**Original Headers:**
```
RowId,Check Date,Date Posted,Check Number,Payment From,Reference,Check Amount,Cash Applied,Provider
```

**Recommended Headers:**
```
row_id,check_date,date_posted,check_number,payment_from,reference,check_amount,cash_applied,provider
```

### Credit Card Co-Pay CSV

**Original Headers:**
```
Trans. #,Trans. Date,Settle Date,Gross Amt,Disc. Fee,Per Trans. Fee,Net Amt,Acct Type,Acct Details,Trans. Type,Payer Name,Client Name,Provider
```

**Recommended Headers:**
```
trans_number,trans_date,settle_date,gross_amt,disc_fee,per_trans_fee,net_amt,acct_type,acct_details,trans_type,payer_name,client_name,provider
```

## How the System Handles Headers

The HVLC_DB system:
1. Automatically converts spaces to underscores
2. Converts headers to lowercase
3. However, direct matching with underscore_format is more reliable

## Important Fields

These fields are particularly important for proper functionality:
- `provider` - For linking transactions to providers
- `cash_applied` - For revenue calculations
- `transaction_date` or `date` - For time-based analysis
- `patient_id` - For patient tracking
- `payer_name` - For insurance analysis

## Updating Existing CSV Files

To update an existing CSV file with properly formatted headers:

1. Open the CSV in a text editor or spreadsheet program
2. Replace the header row with the recommended format
3. Save the file with the same name
4. Re-import the file into the system

You can also use Python scripts to reformat CSV headers automatically:

```python
import pandas as pd

# Read CSV with original headers
df = pd.read_csv('original.csv')

# Rename columns
df.columns = [col.lower().replace(' ', '_').replace('.', '').replace('#', 'number') for col in df.columns]

# Save with new headers
df.to_csv('formatted.csv', index=False)
```