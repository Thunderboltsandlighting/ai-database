# Month-to-Month Expense Tracking Guide

## Overview

This guide helps you set up month-to-month expense tracking in your HVLC_DB system, enabling complete profitability analysis with variable cost management.

## Key Features

✅ **Variable vs Fixed Cost Tracking**  
✅ **Budget Variance Analysis**  
✅ **Usage-Based Expense Calculation**  
✅ **Monthly Profit/Loss Analysis**  
✅ **Break-Even Point Calculation**  
✅ **Provider Profitability Assessment**

## Setup Process

### Step 1: Database Migration

First, add the expense tracking tables to your existing database:

```bash
./migrate_expense_tables.py
```

This will:
- Create backup of your current database
- Add expense tracking tables
- Set up sample expense categories
- Validate the migration

### Step 2: Prepare Your Expense Data

Based on your expense table, create a CSV file with this structure:

#### Required Columns:
- `expense_date` - Date of expense (YYYY-MM-DD format)
- `category` - Expense category (Utilities, Services, Property, etc.)
- `subcategory` - Specific expense item (Dominion, EMR, Mortgage, etc.)
- `amount` - Actual expense amount

#### Optional Columns (for advanced tracking):
- `budgeted_amount` - Expected/budgeted amount
- `is_variable` - 1 for variable costs, 0 for fixed costs
- `usage_count` - Number of units used (patients, transactions, etc.)
- `rate_per_unit` - Cost per unit of usage
- `due_date` - When payment is due
- `frequency` - monthly, yearly, quarterly
- `status` - active, inactive, pending
- `notes` - Additional information

### Step 3: Upload Your Data

Preview your data first:
```bash
./expense_upload_utility.py csv_folder/templates/expense_template.csv --preview
```

Upload when ready:
```bash
./expense_upload_utility.py your_expense_file.csv --analyze
```

## Month-to-Month Variations

### Handling Variable Costs

Your table shows several variable expenses that change month-to-month:

1. **EMR Costs** - Based on patient visits
   ```csv
   2024-01-01,Services,EMR,125.00,100.00,1,250,0.50,,"EMR usage - 250 patients @ $0.50 each"
   2024-02-01,Services,EMR,175.00,100.00,1,350,0.50,,"EMR usage - 350 patients @ $0.50 each"
   ```

2. **Utility Variations** - Seasonal changes
   ```csv
   2024-01-01,Utilities,Dominion,35.00,35.00,0,,,"Normal usage"
   2024-02-01,Utilities,Dominion,42.00,35.00,1,,,"Higher usage - cold weather"
   ```

3. **Usage-Based Services** - QR codes, processing fees
   ```csv
   2024-01-01,Services,QR,3.50,5.00,1,7,0.50,,"7 QR codes @ $0.50 each"
   ```

### Budget Variance Tracking

The system automatically calculates:
- **Variance** = Actual Amount - Budgeted Amount
- **Variance Percentage** = (Variance / Budgeted Amount) × 100

### Monthly Analysis Capabilities

Once uploaded, you can analyze:

1. **Break-Even Analysis**
   ```python
   analyzer = ExpenseAnalyzer()
   breakeven = analyzer.calculate_break_even_analysis('2024-01')
   ```

2. **Variable Cost Efficiency**
   ```python
   efficiency = analyzer.analyze_variable_cost_efficiency()
   ```

3. **Expense Trends**
   ```python
   trends = analyzer.get_expense_trends(months_back=12)
   ```

## Business Intelligence Questions

With expense data uploaded, you can ask sophisticated business questions:

### Profitability Analysis
- "What's our net profit margin for January 2024?"
- "How many patients does each provider need to see to break even?"
- "What's our monthly fixed cost coverage ratio?"

### Cost Optimization
- "Which variable expenses are trending upward?"
- "What's our cost per patient visit by provider?"
- "How do seasonal variations affect our profitability?"

### Strategic Planning
- "If we see 20% more patients, how will that affect our costs?"
- "What's the optimal provider client distribution for maximum profit?"
- "How much can we spend on marketing while maintaining profit margins?"

## Advanced Analysis Examples

### 1. Provider Contribution Margin
```sql
SELECT 
    p.provider_name,
    SUM(pt.cash_applied) as revenue,
    SUM(et.amount * (pt.provider_id = p.provider_id)) as allocated_variable_costs,
    (SUM(pt.cash_applied) - SUM(et.amount * (pt.provider_id = p.provider_id))) as contribution_margin
FROM providers p
JOIN payment_transactions pt ON p.provider_id = pt.provider_id
LEFT JOIN expense_transactions et ON et.is_variable = 1
WHERE pt.transaction_date >= '2024-01-01'
GROUP BY p.provider_name
```

### 2. Monthly Profit & Loss
```sql
SELECT 
    strftime('%Y-%m', pt.transaction_date) as month,
    SUM(pt.cash_applied) as revenue,
    SUM(et.amount) as expenses,
    (SUM(pt.cash_applied) - SUM(et.amount)) as net_profit,
    ((SUM(pt.cash_applied) - SUM(et.amount)) / SUM(pt.cash_applied) * 100) as profit_margin
FROM payment_transactions pt
LEFT JOIN expense_transactions et ON strftime('%Y-%m', pt.transaction_date) = strftime('%Y-%m', et.expense_date)
GROUP BY month
ORDER BY month
```

### 3. Break-Even Patient Volume
```sql
SELECT 
    strftime('%Y-%m', expense_date) as month,
    SUM(CASE WHEN is_variable = 0 THEN amount ELSE 0 END) as fixed_costs,
    (SELECT AVG(cash_applied) FROM payment_transactions) as avg_revenue_per_patient,
    ROUND(SUM(CASE WHEN is_variable = 0 THEN amount ELSE 0 END) / 
          (SELECT AVG(cash_applied) FROM payment_transactions)) as patients_needed_for_breakeven
FROM expense_transactions
GROUP BY month
```

## Data Structure Summary

Your expense tracking now supports:

### Fixed Expenses (is_variable = 0)
- Mortgage: $800/month
- POA: $300/month  
- Insurance: $45/month
- Base utilities: varies by month

### Variable Expenses (is_variable = 1)
- EMR: $0.50 per patient visit
- QR codes: $0.50 per code
- Utility overages: varies by usage

### Revenue Credits
- Property Income: -$1,325/month (treated as negative expense)

## Integration with Business Reasoning

The expense system integrates with your existing business reasoning engine to provide:

1. **Structured Analysis** - Step-by-step reasoning through complex profitability questions
2. **Fact Validation** - Ensures all analysis uses real data, not hallucinated numbers
3. **Actionable Recommendations** - Provides specific suggestions for improving profitability

## Commands Reference

```bash
# Setup
./migrate_expense_tables.py

# Preview data
./expense_upload_utility.py your_file.csv --preview

# Upload data
./expense_upload_utility.py your_file.csv --analyze

# Use business reasoning
python main.py
# Then ask: "What's our monthly break-even point including overhead?"
```

## Next Steps

1. **Run the migration** to add expense tables
2. **Format your expense data** using the template
3. **Upload your data** with the utility
4. **Start asking business questions** using the AI system

Your system will now provide complete profit analysis including:
- True net profit margins
- Provider-specific profitability
- Break-even analysis with overhead
- Cost optimization opportunities
- Strategic planning insights

This gives you the complete financial picture needed to optimize your practice's profitability! 🎯 