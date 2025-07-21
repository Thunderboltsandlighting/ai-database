# HVLC_DB Menu Flow and Query Routing

This document outlines the menu structure and query routing logic of the HVLC_DB application.

## Main Menu Structure

```
HVLC_DB Main Menu
│
├── 1. Ask a question
│   └── Routes query based on content:
│       ├── SQL Agent (if available and query is complex)
│       ├── Direct Database Query (for revenue, provider analysis, etc.)
│       ├── Vector Search (for document-related queries)
│       └── General Analysis (for other types of queries)
│
├── 2. Show data overview
│   └── Displays summary statistics about the database
│
├── 3. Show suggested questions
│   └── Lists example queries and allows selection
│
├── 4. Show available columns
│   └── Lists all columns in the dataset
│
├── 5. Show session clarifications
│   └── Shows how ambiguous terms are mapped to database columns
│
├── 6. Upload CSV file
│   └── Processes and imports CSV data into the database
│
├── 7. Help
│   └── Displays detailed help information
│
├── 8. Ask advanced SQL question (if SQL Agent available)
│   └── Direct access to the SQL Agent for complex queries
│
├── 9/10. Launch Medical Billing AI Assistant
│   └── Interactive chat with the standard AI assistant
│
├── 10/11. Launch Improved Medical Billing AI (if available)
│   └── Interactive chat with enhanced AI with better timeout handling
│
└── Exit
```

## Query Routing Logic

When you ask a question, the system determines the best way to handle it:

```
User Query
│
├── Starts with "sql:" and SQL Agent available?
│   └── YES → Process with SQL Agent
│
├── Contains complex analytical keywords and SQL Agent available?
│   └── YES → Process with SQL Agent (with timeout protection)
│
├── Contains database query indicators (revenue, providers, etc.)?
│   └── YES → Use direct database query for efficiency
│
├── Contains document query indicators (find file, where is, etc.)?
│   └── YES → Use vector search for document retrieval
│
├── Clarification needed for ambiguous terms?
│   └── YES → Ask user to clarify terms like "revenue", "date", etc.
│
└── Process with general query engine
```

## Medical Billing AI Query Classification

The Medical Billing AI classifies queries into the following types:

1. **Performance Review**: Reviews for providers or company-wide performance
2. **Revenue Analysis**: Questions about revenue, totals, and earnings
3. **Provider Analysis**: Information about specific providers
4. **Time Analysis**: Trends over time (monthly, yearly, etc.)
5. **Payer Analysis**: Information about insurance payers
6. **Executive Summary**: High-level overviews and reports
7. **Data Quality**: Analysis of data quality issues
8. **General Analysis**: Any other type of question

## Improved AI Timeout Handling

The Improved Medical Billing AI handles timeouts with these steps:

1. First attempt: Use full prompt
2. If timeout occurs:
   - First retry: Truncate prompt to half size
   - Second retry: Extract just the question and key data points
   - Final retry: Ultra-simplified prompt with just the question
3. If all retries fail, fallback to simpler processing

## Using the SQL Agent

For complex analytical queries, prefix with "sql:" to ensure the SQL agent processes your query. Example:

```
sql: What is the correlation between provider specialty and average payment amount?
```

The SQL agent provides these advantages:
- Handles complex queries without predefined patterns
- Translates natural language to SQL automatically
- Provides schema-aware responses
- Supports relational queries across tables