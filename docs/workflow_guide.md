# HVLC_DB Workflow Guide

This guide explains each menu option in detail, including what it does and how to use it effectively.

## Menu Options Explained

### 1. Ask a question

**What it does**: Allows you to ask any question about your medical billing data.

**Behind the scenes**:
1. Your question is analyzed to determine the best processing method
2. Depending on the content, it might use:
   - SQL Agent for complex analytical questions
   - Direct database queries for revenue/provider questions
   - Vector search for document-related questions
   - General AI for other questions

**Examples**:
- "What was the total revenue last month?"
- "Which provider has the highest earnings?"
- "Show me trends in cash applied over time"

**Best for**: Quick questions about your data that need a single answer.

---

### 2. Show data overview

**What it does**: Provides a summary of all data in your system.

**Behind the scenes**:
1. Counts all CSV files by category
2. Calculates total rows across all files
3. Retrieves date range from database
4. Counts unique providers, payers, and patients
5. Checks data quality (missing values, etc.)

**Best for**: Getting a quick snapshot of your data before diving into analysis.

---

### 3. Show suggested questions

**What it does**: Displays a list of example questions you can ask the system.

**Behind the scenes**:
1. Analyzes your database to find real provider names
2. Generates relevant questions using those names
3. Adds general analytical questions
4. Allows you to select a question to execute

**Best for**: Learning what kinds of questions the system can answer or getting started quickly.

---

### 4. Show available columns

**What it does**: Lists all columns available in your dataset.

**Behind the scenes**:
1. Scans all CSV files for column names
2. Normalizes and deduplicates them
3. Displays the complete list

**Best for**: Understanding what data fields are available for querying.

---

### 5. Show session clarifications

**What it does**: Shows how ambiguous terms in your questions are mapped to specific database columns.

**Behind the scenes**:
1. During queries, the system tracks ambiguous terms (e.g., "revenue" could map to multiple columns)
2. When you select this option, it shows which specific columns these terms refer to
3. These mappings persist throughout your session

**Best for**: Understanding how the system interprets your questions when terms could have multiple meanings.

---

### 6. Upload CSV file

**What it does**: Processes and imports a CSV file into the database.

**Behind the scenes**:
1. Reads the CSV file in memory-efficient chunks
2. Maps columns to database fields
3. Performs data validation and quality checks
4. Inserts data into the database
5. Updates aggregated statistics

**Best for**: Adding new data to your system.

---

### 7. Help

**What it does**: Displays detailed help information about all features.

**Behind the scenes**:
1. Shows descriptions of all menu options
2. Explains special features like SQL Agent (if available)
3. Provides tips for effective use

**Best for**: Learning about all available features.

---

### 8. Ask advanced SQL question (if SQL Agent available)

**What it does**: Provides direct access to the SQL Agent for complex queries.

**Behind the scenes**:
1. Passes your question directly to the SQL Agent
2. The agent translates your natural language to SQL
3. Executes the SQL against your database
4. Formats and returns the results

**Best for**: Complex analytical questions that involve relationships between data.

**Examples**:
- "sql: Find the correlation between provider specialty and average payment amount"
- "sql: Which providers have shown declining revenue over the past three months?"

---

### 9/10. Launch Medical Billing AI Assistant

**What it does**: Opens an interactive chat with the standard AI assistant.

**Behind the scenes**:
1. Initializes the Medical Billing AI with your database
2. Provides a chat interface for asking multiple questions
3. Maintains context between questions

**Best for**: Extended conversations about your medical billing data.

---

### 10/11. Launch Improved Medical Billing AI

**What it does**: Opens an interactive chat with the enhanced AI that has better timeout handling.

**Behind the scenes**:
1. Initializes the Improved Medical Billing AI with your database
2. Uses enhanced timeout handling with retries and prompt simplification
3. Provides more robust error recovery

**Best for**: Complex analyses that might require longer processing time.

## Query Processing Workflow

```
┌───────────────┐
│  User Query   │
└───────┬───────┘
        │
        ▼
┌───────────────┐     ┌───────────────┐
│ SQL Prefixed? │─Yes─►  SQL Agent    │
└───────┬───────┘     └───────────────┘
        │ No
        ▼
┌───────────────┐     ┌───────────────┐
│   Complex     │─Yes─►  SQL Agent    │
│  Analytical?  │     │ (with timeout)│
└───────┬───────┘     └───────────────┘
        │ No
        ▼
┌───────────────┐     ┌───────────────┐
│   Database    │─Yes─►Direct Database│
│Query Indicator│     │     Query     │
└───────┬───────┘     └───────────────┘
        │ No
        ▼
┌───────────────┐     ┌───────────────┐
│   Document    │─Yes─►Vector Search  │
│    Query?     │     │               │
└───────┬───────┘     └───────────────┘
        │ No
        ▼
┌───────────────┐
│General Analysis│
└───────────────┘
```

## Improved AI Processing Workflow

```
┌───────────────┐
│ User Question │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Classify Query│
└───────┬───────┘
        │
        ▼
┌─────────────────────┐
│ Route to Specialist │
│    Query Handler    │
└─────────┬───────────┘
          │
┌─────────┴───────────┐
▼         ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐
│Revenue │ │Provider│ │  Time  │ ... etc
│Analysis│ │Analysis│ │Analysis│
└────┬───┘ └────┬───┘ └────┬───┘
     │          │          │
     └──────────┼──────────┘
                ▼
       ┌─────────────────┐
       │ Database Query  │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │  LLM Processing │
       └────────┬────────┘
                │
         ┌──────┴──────┐
         ▼             ▼
┌─────────────┐ ┌─────────────┐
│   Success   │ │   Timeout   │
└──────┬──────┘ └──────┬──────┘
       │               │
       │        ┌──────┴──────┐
       │        │ Retry with  │
       │        │ Simplified  │
       │        │   Prompt    │
       │        └──────┬──────┘
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│ Return AI   │ │Return Simple│
│  Response   │ │  Fallback   │
└─────────────┘ └─────────────┘
```

## SQL Agent Workflow

```
┌───────────────┐
│ User Question │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    Enhance    │
│ with Medical  │
│Billing Context│
└───────┬───────┘
        │
        ▼
┌───────────────────┐
│ LangChain Converts│
│Natural Language to│
│       SQL         │
└───────┬───────────┘
        │
        ▼
┌───────────────┐
│ Execute SQL   │
│  Against DB   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│Format Results │
│  as Natural   │
│   Language    │
└───────────────┘
```

## Tips for Effective Use

1. **For direct SQL Agent access**: Prefix your question with "sql:" (e.g., "sql: what is the average cash applied per provider?")

2. **For complex analytical questions**: Use the SQL Agent (menu option 8) for questions about relationships between different data points.

3. **For simple factual questions**: Use option 1 (Ask a question) for straightforward queries about revenue, providers, etc.

4. **For interactive analysis**: Use the Improved Medical Billing AI (option 10/11) for in-depth analysis with follow-up questions.

5. **If you get timeouts**: Try simplifying your question or using the Improved Medical Billing AI which has better timeout handling.

6. **To add new data**: Use option 6 (Upload CSV file) to import new data files.

7. **If unsure what to ask**: Use option 3 (Show suggested questions) to see examples based on your actual data.