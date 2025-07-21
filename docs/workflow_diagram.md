# HVLC_DB System Workflow Diagram

This document provides a visual representation of how data flows through the HVLC_DB system.

```
                                 ┌───────────────────────┐
                                 │                       │
                                 │   CSV Files           │
                                 │  (csv_folder/)        │
                                 │                       │
                                 └───────────┬───────────┘
                                             │
                                             │ Import
                                             ▼
┌───────────────────────┐         ┌───────────────────────┐         ┌───────────────────────┐
│                       │         │                       │         │                       │
│  Document Storage     │         │      SQLite DB        │         │  Knowledge Base       │
│  (Vector Index)       │◄────────┤  (medical_billing.db) │─────────►  (Billing Terms)      │
│                       │   Build │                       │  Load   │                       │
└───────────┬───────────┘  Index  └───────────┬───────────┘         └───────────────────────┘
            │                                 │
            │                                 │ Query
            │                                 ▼
┌───────────▼───────────┐         ┌───────────────────────┐         ┌───────────────────────┐
│                       │         │                       │         │                       │
│  Document Query       │         │   Query Router        │         │   SQL Agent           │
│  Engine               │◄────────┤                       │─────────►   (LangChain)         │
│                       │Document │                       │Complex  │                       │
└───────────────────────┘Queries  └───────────┬───────────┘Queries  └───────────────────────┘
                                             │
                                             │ Standard
                                             │ Queries
                                             ▼
                           ┌───────────────────────────────────┐
                           │                                   │
                           │     Query Type Classification     │
                           │                                   │
                           └───────────────┬───────────────────┘
                                           │
                                           │
          ┌────────────┬─────────────┬─────┴─────┬────────────┬────────────┐
          │            │             │           │            │            │
          ▼            ▼             ▼           ▼            ▼            ▼
┌───────────────┐ ┌─────────┐ ┌────────────┐ ┌────────┐ ┌────────────┐ ┌───────────┐
│               │ │         │ │            │ │        │ │            │ │           │
│ Performance   │ │ Revenue │ │  Provider  │ │  Time  │ │  Payer     │ │  Data     │
│ Review        │ │ Analysis│ │  Analysis  │ │Analysis│ │  Analysis  │ │  Quality  │
│               │ │         │ │            │ │        │ │            │ │           │
└───────┬───────┘ └────┬────┘ └──────┬─────┘ └───┬────┘ └──────┬─────┘ └─────┬─────┘
        │              │            │            │             │             │
        └──────────────┴─────┬──────┴────────────┴─────────────┴─────────────┘
                             │
                             │
                             ▼
                   ┌───────────────────────┐
                   │                       │
                   │     LLM Processor     │──┐
                   │     (Ollama)          │  │
                   │                       │  │
                   └───────────┬───────────┘  │ Timeout?
                               │              │ Retry with
                               │ Response     │ simpler prompt
                               │              │
                               ▼              │
                   ┌───────────────────────┐  │
                   │                       │  │
                   │     User Interface    │◄─┘
                   │                       │
                   └───────────────────────┘
```

## Data Flow Sequence

1. **Data Ingestion**
   - CSV files are loaded into the SQLite database
   - Document content is indexed in the vector store
   - Knowledge base terms are loaded

2. **Query Processing**
   - User submits a query through the interface
   - Query router determines the appropriate processing path:
     - Document queries → Vector search
     - Complex analytical queries → SQL Agent
     - Standard queries → Query type classification

3. **Specialized Processing**
   - Each query type has a specialized handler
   - Database queries are executed
   - Results are formatted for LLM processing

4. **LLM Processing**
   - Results are sent to the Ollama LLM
   - LLM generates natural language response
   - If timeout occurs, retry with simplified prompt

5. **Response Delivery**
   - Formatted response is presented to user
   - Results are cached for similar future queries

## System Components

- **SQLite Database**: Core storage for all structured data
- **Vector Index**: Document storage for unstructured content
- **Query Router**: Directs queries to appropriate handlers
- **SQL Agent**: Translates natural language to SQL
- **LLM Processor**: Generates natural language responses
- **Document Query Engine**: Searches document content
- **Specialized Analyzers**: Process specific query types

## Query Types

- **Performance Review**: Provider or company reviews
- **Revenue Analysis**: Revenue and financial metrics
- **Provider Analysis**: Provider-specific information
- **Time Analysis**: Trends over time periods
- **Payer Analysis**: Insurance payer information
- **Data Quality**: Data quality assessment