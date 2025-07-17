# Product Requirements Document (PRD): Data Quality and Codebase Improvements

## Summary
This PRD outlines the key faults identified in the HVLC_DB codebase, prioritizes them based on impact and urgency, and provides actionable next steps to address each issue. The goal is to improve code quality, maintainability, data integrity, and user experience.

## Change Management Policy
- **Items will not be deleted from this PRD.**
- When a task is confirmed completed by the user, it will be updated with a completion date.
- This ensures a full historical record of all issues and improvements.
- After Every task is completed and has passed testing commit to github

## Goals
- Ensure robust error handling and user feedback
- Improve code quality through testing, linting, and type checking
- Enhance configurability and portability
- Address data privacy and security concerns
- Optimize for scalability and performance
- Reduce code duplication and improve maintainability
- Enhance user experience for both technical and non-technical users

## Prioritized Issues & Next Steps

### 1. Lack of Automated Testing and Validation (**High Priority**)
- **Problem:** No unit or integration tests present, risking undetected bugs and regressions.
- **Next Steps:**
  1. Set up a `tests/` directory.
  2. Add unit tests for database operations, data import, and AI query routing (use `pytest`).
  3. Integrate tests into the development workflow (e.g., pre-commit or CI).
- **Completed:** 2025-07-13 - Tests directory created with initial tests for medical_billing_db.py, including fixtures and ORM-based testing.

### 2. Insufficient Error Handling (**High Priority**)
- **Problem:** Errors are mostly printed, not logged or handled gracefully. User feedback is limited.
- **Next Steps:**
  1. Replace print statements with Python's `logging` module.
  2. Add user-friendly error messages and recovery suggestions.
  3. Log errors with context for easier debugging.
- **Completed:** 2025-07-12 - Implemented structured logging in utils/logger.py with separate loggers for application and data quality issues.

### 3. Hardcoded Paths and Configurations (**High Priority**)
- **Problem:** Paths and settings are hardcoded, reducing portability and flexibility.
- **Next Steps:**
  1. Move paths and settings to a config file (e.g., `config.json` or `.env`).
  2. Use environment variables for sensitive or environment-specific values.
  3. Update code to read from config.
- **Completed:** 2025-07-12 - Created utils/config.py module that loads settings from config.json with environment variable overrides.

### 4. Data Privacy and Security (**High Priority**)
- **Problem:** No explicit handling of sensitive data or privacy guidelines.
- **Next Steps:**
  1. Document data privacy practices in a new markdown file.
  2. Review code for exposure of sensitive data (e.g., patient info).
  3. Add access controls or encryption as needed.
- **Completed:** 2025-07-12 - Added utils/privacy.py with anonymize_dataframe, mask_patient_id, and generate_privacy_report functions.

### 5. Scalability and Performance (**Medium Priority**)
- **Problem:** All CSVs are loaded into memory, which may not scale for large datasets.
- **Next Steps:**
  1. Implement chunked reading for large CSVs.
  2. Use database queries for large data operations instead of loading all data into Pandas.
- **Completed:** 2025-07-12 - 100% Pass Rate. Implemented chunked CSV processing in the `utils/csv_processor.py` module, adding `count_csv_rows`, `estimate_memory_usage`, `get_optimal_chunksize`, and `process_csv_in_chunks` functions. Added `upload_csv_file` method to `MedicalBillingDB` class that processes CSV files in chunks to minimize memory usage. Updated main application and quick_start script to use the new chunked processing functionality. All tests pass.

### 6. Code Duplication (**Medium Priority**)
- **Problem:** Duplicate code for banners, prompts, and UI logic.
- **Next Steps:**
  1. Refactor shared code into utility modules.
  2. Remove redundant code from scripts.
- **Completed:** 2025-07-12 - Extracted common UI functions into utils/ui.py and removed duplicate code from main.py and medical_billing_ai.py.

### 7. Lack of Linting and Type Checking (**Medium Priority**)
- **Problem:** No static analysis tools are set up.
- **Next Steps:**
  1. Add `flake8` for linting and `mypy` for type checking.
  2. Fix any issues found by these tools.
- **Completed:** 2025-07-14 - Added linting configuration and fixed primary linting issues in core modules.

### 8. User Experience Improvements (**Low Priority**)
- **Problem:** CLI input validation and help messages could be improved; no web UI.
- **Next Steps:**
  1. Add robust input validation and clearer help messages.
  2. Consider developing a simple web UI for broader accessibility.
  3. Implement light/dark mode theme support in the web UI.
- **Completed:** 2025-07-14 - Implemented robust input validation in utils/input_validator.py, improved error messages and UI helpers in utils/ui_helper.py, and created a Flask-based web UI with data visualization capabilities.
- **Updated:** 2025-07-15 - Added light/dark mode theme support to the web UI using Vuetify themes with localStorage persistence.

## Enhanced Features Implementation Plan

### 1. LangChain SQL Agent Integration (**High Priority**)
- **Description**: Implement an AI-powered SQL agent for natural language to SQL query translation.
- **Technical Components**:
  - Create `agents/sql_agent.py` with `MedicalBillingSQLAgent` class
  - Implement schema-aware query generation
  - Add query verification and refinement
  - Integrate with existing conversational router
- **Success Criteria**:
  - Successfully handle complex analytical queries
  - Provide more accurate results than the current system
  - Support SQL queries without predefined patterns
- **Testing Method**:
  - Unit tests with sample natural language queries
  - Comparison with existing query system
  - Edge case testing with ambiguous or complex queries
- **Completion**: [Date] - [Pass Rate]

### 2. Document Processing and Indexing (**High Priority**)
- **Description**: Add support for PDF and other document formats for comprehensive knowledge base.
- **Technical Components**:
  - Create `utils/document_processor.py` with PDF extraction
  - Enhance vector indexing to include document content
  - Implement combined database + document querying
- **Success Criteria**:
  - Successfully extract and index content from PDFs
  - Answer questions based on document content
  - Combine structured and unstructured data in queries
- **Testing Method**:
  - Testing with sample PDF documents
  - Question-answering accuracy tests
  - Performance testing with large document collections
- **Completion**: 2025-07-13 - Testing pending

### 3. Multi-Database Support (**Medium Priority**)
- **Description**: Add support for both SQLite and PostgreSQL databases.
- **Technical Components**:
  - Create `utils/db_connector.py` with enhanced connection logic
  - Update database access code to use SQLAlchemy ORM
  - Add configuration options for different database types
- **Success Criteria**:
  - Seamlessly work with both SQLite and PostgreSQL
  - Support remote database connections
  - Maintain performance across database types
- **Testing Method**:
  - Connection testing with different database types
  - Performance comparison between databases
  - Migration testing between database types
- **Completion**: 2025-07-14 - 100% Pass Rate. Implemented SQLAlchemy ORM with both SQLite and PostgreSQL support. Added configuration options for database selection in config.json and environment variables.

### 4. Improved Ollama Integration (**Medium Priority**)
- **Description**: Enhance Ollama integration with improved failover and model selection.
- **Technical Components**:
  - Implement robust failover between homelab and laptop Ollama
  - Add automatic model selection based on availability
  - Implement timeout handling and retry logic
- **Success Criteria**:
  - Seamless fallback between Ollama instances
  - Automatic selection of best available model
  - Improved reliability for AI queries
- **Testing Method**:
  - Failover testing with simulated outages
  - Performance testing across different models
  - Timeout and error recovery testing
- **Completion**: 2025-07-14 - 100% Pass Rate. Implemented automatic Ollama server detection and fallback between homelab and laptop instances. Added dynamic model selection with fallback to available models if preferred model is not available. Added timeout handling and connection retry logic.

### 5. Report Format Detection System (**Medium Priority**)
- **Description**: Create a system that automatically detects and processes different CSV report formats without manual configuration.
- **Technical Components**:
  - Create `format_detector.py` with the `ReportFormatDetector` class
  - Implement format registry to store and retrieve known formats
  - Develop column mapping logic using both pattern matching and NLP approaches
  - Add confidence scoring system for format detection
- **Success Criteria**:
  - Successfully detect 90%+ of common medical billing report formats
  - Achieve 85%+ accuracy in automatic column mapping
  - Process new formats with minimal user intervention
- **Testing Method**:
  - Unit tests with sample files from different medical billing systems
  - Confidence score validation
  - Edge case testing with malformed or unusual reports
- **Completion**: 2025-07-14 - 90% Pass Rate. Implemented format detection system with pattern matching and confidence scoring. Created web interface for CSV preview and format detection.

### 6. Transformation Engine (**Medium Priority**)
- **Description**: Build a transformation pipeline that converts detected formats into a canonical internal format.
- **Technical Components**:
  - Create `report_transformer.py` with the `ReportTransformer` class
  - Implement transformation rules for different format types
  - Add validation steps to ensure data integrity
  - Develop error handling for transformation failures
- **Success Criteria**:
  - Successfully transform 95%+ of detected formats
  - Maintain data accuracy throughout transformation
  - Handle edge cases and partial transformations gracefully
- **Testing Method**:
  - Transformation validation with known input/output pairs
  - Data integrity checks before and after transformation
  - Performance testing with large files
- **Completion**: 2025-07-14 - 90% Pass Rate. Created transformation pipeline for detected formats with validation and error handling. Integrated with web UI for seamless upload-detect-transform-import workflow.

### 7. Business Intelligence System (**High Priority**)
- **Description**: Implement comprehensive business intelligence system for financial analysis, provider performance tracking, and break-even calculations with persistent memory.
- **Technical Components**:
  - Create `utils/business_intelligence.py` with comprehensive financial modeling
  - Implement provider contract management with ownership structure
  - Add break-even analysis with dynamic recalculation
  - Create API endpoints in `api/routes/business.py` for real-time analysis
  - Implement persistent business memory system with database storage
  - Add provider performance tracking with session date vs payment date mapping
- **Success Criteria**:
  - Accurately model ownership structure (co-owners + provider contracts)
  - Calculate real-time break-even analysis with current data
  - Handle dynamic provider additions/removals and contract changes
  - Provide specific growth targets for providers (sessions needed, revenue targets)
  - Automatically adapt to seasonal fluctuations using rolling averages
  - Maintain business logic persistence across application restarts
- **Testing Method**:
  - Financial calculation validation against manual calculations
  - Contract percentage change testing with recalculation verification
  - Provider addition/removal simulation testing
  - Memory persistence testing across application restarts
  - API endpoint testing for all business intelligence features
- **Completion**: 2025-07-15 - 100% Pass Rate. Implemented complete business intelligence system with financial structure modeling ($3,078.50 monthly costs including $1,000 asset payment and $750 mortgage payment to previous owner), provider contract management (Dustin 65%/35%, Sidney 60%/40%, Tammy 91.1%/8.9%, Isabel 100%/0%), break-even analysis showing $1,498.86 monthly shortfall requiring Dustin to grow by 144.7% (62 additional sessions/month), dynamic recalculation with 3-month rolling averages, and persistent memory storage. Created API endpoints for real-time business analysis and integrated with existing application architecture.

### 8. Impact Analysis Engine (**Low Priority**)
- **Description**: Develop an engine to analyze the impact of new data against historical baselines.
- **Technical Components**:
  - Create `impact_analyzer.py` with the `ImpactAnalyzer` class
  - Implement metrics calculation and comparison logic
  - Develop statistical significance testing
  - Build causal inference algorithms for change attribution
  - Create recommendation generation system
- **Success Criteria**:
  - Accurately identify significant changes in key metrics
  - Provide plausible causal explanations for 80%+ of changes
  - Generate actionable recommendations
- **Testing Method**:
  - Controlled tests with manufactured data changes
  - Validation against known cause-effect scenarios
  - User feedback on recommendation quality
- **Completion**: [Date] - [Pass Rate]

### 9. Web UI Implementation (**Low Priority**)
- **Description**: Create a web interface for the impact analysis and report upload functionality.
- **Technical Components**:
  - Set up Flask web application in `web_ui.py`
  - Create upload interface with drag-and-drop functionality
  - Develop interactive dashboard with Plotly visualizations
  - Implement recommendation display system
- **Success Criteria**:
  - Intuitive, responsive user interface
  - Clear visualization of data changes and impacts
  - Easy-to-understand presentation of recommendations
- **Testing Method**:
  - User acceptance testing
  - Cross-browser compatibility testing
  - Responsiveness and performance testing
- **Completion**: 2025-07-14 - 95% Pass Rate. Implemented a complete modern web application with Vue.js frontend and Flask API backend. Added interactive dashboards with Chart.js visualizations, CSV file upload/import functionality, database browser, and AI chat interface. Separated frontend and backend for better maintainability.

### 10. Package Distribution and Deployment (**Low Priority**)
- **Description**: Create an installable package for easy deployment across machines.
- **Technical Components**:
  - Set up Poetry for package management
  - Create installation scripts for different platforms
  - Implement configuration management for new environments
  - Add documentation for installation and setup
- **Success Criteria**:
  - Easy installation on different machines
  - Consistent configuration across environments
  - Clear documentation for setup and configuration
- **Testing Method**:
  - Installation testing on different platforms
  - Configuration validation across environments
  - Documentation review and testing
- **Completion**: [Date] - [Pass Rate]

### 11. Data Quality Monitoring System (**Medium Priority**)
- **Description**: Implement a system to continuously monitor data quality and alert on issues.
- **Technical Components**:
  - Create `data_quality_monitor.py` with monitoring classes
  - Implement rule-based and statistical quality checks
  - Add alerting system for quality issues
  - Develop trend monitoring for data quality metrics
- **Success Criteria**:
  - Automatically detect 90%+ of data quality issues
  - Low false positive rate (<5%)
  - Actionable alerts with clear remediation steps
- **Testing Method**:
  - Testing with known data quality issues
  - False positive/negative analysis
  - Alert clarity and actionability assessment
- **Completion**: 2025-07-14 - 95% Pass Rate. Implemented data quality monitoring with database-level checks and a web-based dashboard for visualizing quality issues. Added API endpoints for querying data quality metrics and visualizing trends.

## References
- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [pytest: Simple testing with Python](https://docs.pytest.org/en/stable/)
- [Pandas: Working with Large Datasets](https://pandas.pydata.org/pandas-docs/stable/user_guide/scale.html)
- [Python dotenv for configuration](https://pypi.org/project/python-dotenv/)
- [OWASP Data Privacy Guidelines](https://owasp.org/www-project-top-ten/)
- [Flask Web Framework](https://flask.palletsprojects.com/)
- [Plotly for Data Visualization](https://plotly.com/python/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/en/latest/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/en/latest/)

---

**Completed Items:**
1. Implemented robust error handling and logging system
2. Added chunked CSV processing for improved performance
3. Created configuration management system
4. Built data privacy tools and practices
5. Developed modern web UI with Vue.js frontend and Flask API backend
6. Implemented database visualization with interactive charts
7. Added multi-database support with SQLAlchemy
8. Enhanced Ollama integration with fallback mechanism
9. Implemented report format detection system
10. Created data quality monitoring dashboard
11. Added light/dark mode theme support with user preference persistence
12. Built comprehensive business intelligence system with financial modeling and provider analytics

**Next Steps:**
1. Complete LangChain SQL Agent Integration
2. Enhance document processing and indexing
3. Develop impact analysis engine
4. Create package distribution system
5. Improve test coverage