# Medical Billing AI: Command & Request Reference

This document lists key commands, keywords, and requests you can use with your medical billing AI system. Each entry includes a brief description of what the request or function will do.

---

## Data Quality & Troubleshooting

- **get_rows_with_missing_cash_applied()**
  - *Description:* Shows all records in the database where the `cash_applied` value is missing. Useful for identifying incomplete data that may affect reports.

- **Show data quality issues**
  - *Description:* Lists all logged data quality problems (e.g., missing values, negative payments, processing errors) found during import.

- **Analyze data quality**
  - *Description:* Summarizes the current state of data quality, highlights priority issues, and offers recommendations for improvement.

- **Check data quality dashboard**
  - *Description:* Opens the web-based data quality dashboard showing visualizations of quality metrics and trends.

- **Run quality checks on [table]**
  - *Description:* Executes all quality rules against the specified table and reports issues.

---

## Revenue & Financial Analysis

- **Total revenue for [year]**
  - *Description:* Calculates the sum of all `cash_applied` values for the specified year, by provider or overall.

- **Revenue by provider**
  - *Description:* Breaks down total revenue by each provider for a given period.

- **Monthly revenue trends**
  - *Description:* Shows how revenue changes month-to-month, either overall or for a specific provider.

- **Top earners / Highest collections**
  - *Description:* Identifies providers with the highest total revenue in a given period.

---

## Provider & Payer Insights

- **Compare providers**
  - *Description:* Ranks providers by revenue, transaction count, or average payment size.

- **Provider performance report**
  - *Description:* Generates a summary of key metrics (revenue, transactions, patients) for one or more providers.

- **Payer analysis**
  - *Description:* Breaks down revenue or transaction counts by payer (insurance company, etc.).

---

## Knowledge & Document Search

- **Define [term]**
  - *Description:* Returns the definition and context for a medical billing term (e.g., CPT code, NPI, adjustment).

- **Search knowledge base for [keyword]**
  - *Description:* Finds relevant entries in the domain knowledge base.

- **Find in documents: [topic]**
  - *Description:* Searches through all PDF, text, and markdown documents for information on the specified topic.

- **What do the documents say about [subject]?**
  - *Description:* Retrieves and summarizes information from documents related to the specified subject.

---

## General & Executive Summary

- **Executive summary**
  - *Description:* Provides a high-level overview of financial performance, trends, and data quality.

- **Help**
  - *Description:* Lists example questions and tips for interacting with the AI.

- **Show available columns**
  - *Description:* Lists all columns currently available in your loaded data.

- **Show session clarifications**
  - *Description:* Displays which columns the agent is using for ambiguous terms (e.g., revenue, date, provider).

---

## Data Import & Format Detection

- **Detect format of [file]**
  - *Description:* Analyzes a CSV file and automatically determines its format type with confidence scoring.

- **Transform [file] to canonical format**
  - *Description:* Converts a CSV file from its original format to the standardized database format.

- **Import [file]**
  - *Description:* Automatically detects format, transforms, and imports a CSV file into the database.

- **Import all files in [directory]**
  - *Description:* Processes all CSV files in a directory, detecting formats and importing in batch mode.

## Database Management

- **Switch database to [type]**
  - *Description:* Changes the database connection type between SQLite and PostgreSQL.

- **Migrate database to [type]**
  - *Description:* Migrates all data from the current database type to the specified type.

- **Show database configuration**
  - *Description:* Displays the current database connection settings and statistics.

- **List all tables**
  - *Description:* Shows all tables in the current database with row counts.

---

## Web Interface Commands

- **Launch web interface**
  - *Description:* Starts the web UI server and opens it in a browser.

- **Start web UI**
  - *Description:* Same as "Launch web interface" - starts the web server.

- **python start_web_ui.py**
  - *Description:* Command to start the web interface from the command line.

- **Open analytics dashboard**
  - *Description:* Opens the analytics dashboard page in the web interface.

- **Upload through web interface**
  - *Description:* Launches the web UI's file upload page for importing CSV files.

---

## Example Natural Language Requests

- "What was the total revenue for 2024?"
- "Show me all rows with missing cash applied values."
- "Which provider had the highest collections last quarter?"
- "Are there any data quality issues in the latest upload?"
- "Compare monthly revenue trends for Dr. Smith and Dr. Lee."
- "Define CPT code."
- "Give me an executive summary." 
- "What do the documents say about revenue cycle management?"
- "Find information in the PDFs about billing codes."
- "Search the docs for denial management procedures."
- "Detect the format of the new insurance claims file."
- "Import all CSVs from the billing directory."
- "Switch database to PostgreSQL."
- "Migrate database from SQLite to PostgreSQL."
- "Show me the current database configuration."
- "Launch the web interface."
- "Show me analytics in the web dashboard."