# Enterprise Document Intelligence Platform

An agentic RAG (Retrieval-Augmented Generation) system built to handle secure document ingestion, hybrid search, explainable metadata extraction, and compliance auditing. 

This project was built from the ground up to demonstrate enterprise software engineering patterns, including robust schema versioning, fine-grained access control levels, hybrid vector search pipelines, and observable agentic workflows.

---

## Technical Stack & Architecture

The platform separates data storage, semantic indexing, relational state management, and the user interface into distinct layers:

- **Frontend**: Single Page Application built with React, Vite, TypeScript, and TailwindCSS.
- **Backend API**: FastAPI (Python 3.12) utilizing asynchronous endpoints and dependency injection.
- **Relational Storage**: PostgreSQL for transactional data (documents, users, ACL roles, policy rules).
- **Search & Vector Storage**: OpenSearch (KNN enabled) for hybrid lexical (BM25) and semantic vector search.
- **Embeddings Model**: `sentence-transformers/all-MiniLM-L6-v2` generating 384-dimensional dense vectors locally.
- **LLM Orchestration**: Gemini API for multi-agent workflows (document summarization, classification reasoning, and compliance auditing).
- **Caching**: Redis for caching executive briefing reports and search sessions.

```
[React/Vite App] ──(HTTPS)──> [FastAPI Backend] ──(Gemini API)──> [Intelligence Agents]
                                  │   │   │
                  ┌───────────────┘   │   └───────────────┐
                  ▼                   ▼                   ▼
            [PostgreSQL]        [OpenSearch]           [Redis]
          (Metadata & ACL)    (Hybrid Chunks)      (Advisory Cache)
```

---

## Core Engineering Features

### 1. Hybrid Search & RRF Retrieval
The search pipeline performs hybrid retrieval by query embedding matching against OpenSearch dense KNN vectors combined with BM25 keyword matching. Results are merged and ranked using Reciprocal Rank Fusion (RRF).

### 2. Document-Level Access Control (ACL)
Documents are tagged with hierarchical clearance levels (`public`, `internal`, `confidential`, `restricted`). The access control layer verifies the user's role-based clearance dynamically:
- OpenSearch search queries are wrapped with term filters corresponding to the user's maximum clearance.
- Results are double-checked post-query at the router level.
- Relational SQL filters join metadata (department, classification, liability caps) directly before returning data.

### 3. Schema Versioning via Alembic
Database schema additions (such as cost metrics, latency timers, and classification reasoning columns) are managed using Alembic versioning. Rather than modifying database schemas at runtime, standard migrations are run against the database during startup.

### 4. Node-by-Node Agent Observability
The multi-agent pipeline is designed for explainability. The backend tracks cost metrics, execution duration, and confidence thresholds for every step (summarizer, classifier, metadata extraction). These execution stages are visualized on the frontend in real time, showing the live status transition of each active node.

### 5. Caching & Advisory Exports
- **Redis Cache**: Cached advisory reports with a 1-hour TTL to save LLM usage costs.
- **PDF Compilation**: Streams compiled executive briefs dynamically using `reportlab`, providing PDF downloads containing risk scores, critical clauses, and recommendations.

### 6. Interactive Interview Sandbox
Includes a preloaded demo mode containing simulated logistics services contracts. This sandbox allows interviewers to visualize the multi-agent execution pipeline, telemetry graphs, cost logs, and document Q&A interfaces immediately without requiring active LLM API keys or local database setup.

### 7. Granular Explainability Engine
Rather than returning simple black-box predictions, the backend prompts LLM agents to output detailed, structured checkmarks explaining their decisions. The system computes and stores exact confidence metrics (keyword match density, semantic matching similarity, structural alignment) and granular missing/ambiguous checkmarks inside PostgreSQL database columns for every analyzed document.

### 8. Enterprise Transactional Audit Logging
Every security-sensitive action—user authentication, file uploads, search queries, access control denials, and document exports—is tracked via a structured auditing service that persists event records into a PostgreSQL `audit_logs` table.

---

## Directory Layout

```
.
├── src/                          # Backend application code
│   ├── main.py                   # FastAPI entrypoint
│   ├── config.py                 # Pydantic BaseSettings & Environment parsing
│   ├── models/                   # SQLAlchemy Database models
│   ├── schemas/                  # Pydantic API response & request schemas
│   ├── routers/                  # Endpoint routers (search, agents, uploads)
│   ├── services/                 # Embeddings, OpenSearch, Gemini, and Security clients
│   └── db/                       # Database engines & interface hooks
├── frontend/                     # React UI codebase
│   ├── src/pages/                # Upload, Search, Document Viewer, Dashboard components
│   └── src/lib/api.ts            # Client API client integrations
├── alembic/                      # Database migration versions and environments
└── data/                         # Temporary upload directory and sample documents
```

---

## Local Development Setup

### 1. Data Services (Docker)
Ensure Docker is running, then start the data layers:
```bash
docker compose up -d
```
This boots up PostgreSQL (on port 5432), OpenSearch (on port 9200), and Redis (on port 6379).

### 2. Backend API Setup
Create a virtual environment, install dependencies, and run migrations:
```bash
# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Run DB Migrations
alembic upgrade head

# Start Backend Server
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend UI Setup
In a new terminal window, navigate to the frontend directory, install dependencies, and run Vite:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Environment Configuration (`.env`)

Create a `.env` file in the root directory. Key configuration settings include:
```env
# Server
DEBUG=true
ENVIRONMENT=development

# PostgreSQL
POSTGRES_DATABASE_URL=postgresql+psycopg2://rag_user:rag_password@localhost:5432/rag_db

# OpenSearch Settings
OPENSEARCH__HOST=http://localhost:9200
OPENSEARCH__INDEX_NAME=enterprise-documents
OPENSEARCH__VECTOR_DIMENSION=384

# LLM Integrations
GEMINI__API_KEY=your_gemini_api_key_here
GEMINI__MODEL=gemini-2.0-flash
```

---

## Verification & Testing
To ensure the backend service and vector indexing are functional, you can run a health check:
```bash
curl http://localhost:8000/api/v1/health
```

To run the unit tests:
```bash
pytest tests/
```