# CNPI RAG System - Implementation Directory

This directory contains the working implementation of the
Comprehensive Non-National Educational Public Institution
Hybrid RAG System.

## Project Structure

```
cnpi_rag/
├── __init__.py                    # Package initialization
├── main.py                        # Main entry point
├── graph.py                       # LangGraph builder
├── state.py                       # State schema (from plan/)
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── README.md                      # This file
│
├── nodes/                         # RAG pipeline nodes
│   ├── __init__.py
│   ├── entry.py                   # Phase 1: Query rewriting
│   ├── router.py                  # Phase 1: Path routing
│   ├── sql_query.py               # Phase 2: SQL Query path
│   ├── sql_retrieve.py            # Phase 3: SQL Retrieve path
│   ├── web_search.py              # Phase 4: Web Search path
│   └── hybrid.py                  # Phase 5: Hybrid processing
│
├── utils/                         # Utility functions
│   ├── __init__.py
│   ├── llm_utils.py               # LLM wrapper (Groq)
│   ├── db_utils.py                # Database operations (PostgreSQL)
│   └── search_utils.py            # Search and embedding utilities
│
└── prompts/                       # LLM prompts
    ├── __init__.py
    └── node_prompts.py            # Prompts for SQL generation, validation, etc.
```

## Current Implementation Status

### ✅ Phase 1: Foundation + Entry + Router
- [x] Entry node (rewrite_query)
- [x] Router node (llm_decide_path)
- [x] Confidence-based routing
- [x] LLM wrapper functions
- [x] Graph builder
- [x] Database utilities
- [x] Prompt templates

### 🔲 Phase 2: SQL Query Path
- [ ] SQL Query Info Check node
- [ ] SQL Query Create node (with prompt)
- [ ] SQL Query DB Call node
- [ ] SQL Query Context Optimizer node
- [ ] SQL Query Response node
- [ ] SQL Query Support Check node
- [ ] Retry mechanisms

### 🔲 Phase 3: SQL Retrieve Path
- [ ] SQL Retrieve Check node
- [ ] SQL Retrieve Create node
- [ ] SQL Retrieve Context node
- [ ] SQL Retrieve Response node
- [ ] SQL Retrieve Support Check node
- [ ] Embedding model integration
- [ ] BM25 search functionality

### 🔲 Phase 4: Web Search Path
- [ ] Web Search Rewrite node
- [ ] Web Search Docs node
- [ ] Web Search Response node
- [ ] Web Search Support Check node
- [ ] External search API integration

### 🔲 Phase 5: Hybrid / Sub-Query System
- [ ] Hybrid Depth Check node
- [ ] Create Sub Queries node
- [ ] Parallel Dispatch node
- [ ] Append Sub Answer node
- [ ] All Sub Answers Ready node
- [ ] Merge Sub Answers node
- [ ] Merge Support Check node
- [ ] Merge Retry Check node
- [ ] LangGraph Send API for parallel execution

## Getting Started

### 1. Installation

Set up a Python virtual environment:

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On Linux/Mac
```

Install dependencies:

```bash
cd Cnpi_RAG
pip install -r requirements.txt
```

### 2. Configuration

Copy the environment template and fill in your credentials:

```bash
copy .env.example .env
```

Edit `.env` with your actual API keys and database settings:

```
DB_HOST=localhost
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=your_password
GROQ_API_KEY=your_groq_api_key
```

### 3. Database Setup

You'll need a PostgreSQL database. Create it and run the necessary migrations
(if available).

### 4. Run the System

Run the main entry point:

```bash
python main.py
```

For Phase 1 testing:

```python
from main import process_query

result = process_query("What is the principal's full name?")
print(f"Path: {result['decided_path']}")
print(f"Confidence: {result['confidence_score']}")
print(f"Query: {result['rewritten_query']}")
```

## Development Standards

This implementation follows the standards defined in `G:\CNPI_Hybrid_RAG\plan\Instruction.md`:

1. **Source of Truth**: All designs, flows, and states reference the plan directory
2. **Architecture Compliance**: Flow and node connections follow the planned architecture
3. **State Management**: State schema follows `state.py` exactly
4. **Performance**: Low latency and high efficiency are priorities
5. **Code Quality**: Clean, readable, modular, and production-ready
6. **Clarification First**: Never guess critical decisions - ask first

## Key Features

### Multi-Path Routing
- **SQL Query Path**: Direct structured database retrieval
- **SQL Retrieve Path**: Semantic search with embeddings and BM25
- **Web Search Path**: External information retrieval
- **Hybrid Path**: Parallel processing of complex multi-intent queries

### State Management
- Complete request lifecycle tracking
- Per-path state isolation
- Automatic retry mechanisms
- Support validation

### Performance Optimizations
- Minimal LLM calls
- Efficient database queries
- Parallel sub-query execution
- Context optimization

## Debugging

For development debugging, you can enable verbose logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

To trace graph execution:

```python
from utils.llm_utils import call_llm

# Enable debug mode in LLM calls
call_llm(system_message="...", user_prompt="...", debug=True)
```

## Future Extensions

The modular architecture makes it easy to extend:

- Add new retrieval paths
- Implement caching layers
- Add user authentication
- Integrate with web frameworks (Django/Flask)
- Add monitoring and metrics
- Implement user feedback loops

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Database connection established and tested
- [ ] API keys verified
- [ ] LLM provider connectivity tested
- [ ] Embedding model downloaded and tested
- [ ] Web search API configured (optional)
- [ ] Production configuration set
- [ ] Logging and monitoring configured
- [ ] Security patches applied
- [ ] Load testing conducted

## Support

For issues, questions, or contributions refer to:
- Main documentation: `G:\CNPI_Hybrid_RAG\plan\README.md`
- Development instructions: `G:\CNPI_Hybrid_RAG\plan\Instruction.md`
- Implementation roadmap: `G:\CNPI_Hybrid_RAG\plan\work Phase.txt`