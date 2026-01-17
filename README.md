# Enterprise Knowledge Base - RAG System

<div align="center">

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![OpenSearch](https://img.shields.io/badge/OpenSearch-2.19+-00569B.svg)](https://opensearch.org/)

**Enterprise-Grade AI-Powered Document Search & Q&A Platform**

</div>

---

## 🤖 What is Enterprise Knowledge Base?

Enterprise Knowledge Base is a production-ready Retrieval-Augmented Generation (RAG) system that transforms your organization's documents into an intelligent, AI-powered knowledge platform. Built on modern LLM technology, it provides secure, audited, and scalable document search with natural language question answering.

### Problem It Solves

Organizations struggle with:
- Scattered knowledge across S3, SharePoint, and file systems
- Security and compliance requirements for document access
- Slow, manual document retrieval processes
- Lack of audit trails for sensitive information access
- Need for AI-powered insights while maintaining data privacy

### Key Features

- 🔐 **Enterprise Security**: JWT authentication, RBAC, document-level access control
- 🔍 **Hybrid Search**: BM25 + vector embeddings with reciprocal rank fusion
- 🤖 **Agentic RAG**: Intelligent query rewriting, document grading, and relevance filtering
- 📄 **Multi-Source Ingestion**: S3, SharePoint, local filesystem with automatic scanning
- 📊 **Audit & Compliance**: Comprehensive logging with Langfuse, GDPR-ready data export
- 📈 **Document Lifecycle**: Version control, retention policies, PII detection
- ⚡ **High Performance**: Async architecture, Redis caching, batched processing
- 🔍 **Observability**: Health checks, tracing, performance monitoring

---

## 📖 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [API Documentation](#-api-documentation)
- [Configuration](#-configuration)
- [Examples](#-examples)
- [Development](#-development)
- [Testing](#-testing)
- [Roadmap](#-roadmap)
- [Support](#-support)

---

## 🚀 Installation

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for development)
- 16GB+ RAM recommended (for Ollama models)
- Git

### Quick Install with Docker

```bash
# Clone the repository
git clone https://github.com/your-org/enterprise-kb.git
cd enterprise-kb

# Copy environment configuration
cp .env.example .env

# Edit the .env file with your settings (see Configuration section)
# nano .env

# Start all services
docker compose up -d

# Wait for services to be ready (2-3 minutes)
docker compose logs -f api
```

### Verify Installation

```bash
# Check health status
curl http://localhost:8000/health

# Expected response:
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "service_name": "enterprise-kb-api",
  "services": {
    "database": {"status": "healthy"},
    "opensearch": {"status": "healthy"},
    "ollama": {"status": "healthy"}
  }
}

# Try a search query
curl -X POST http://localhost:8000/api/v1/hybrid-search \
  -H "Content-Type: application/json" \
  -d '{"query": "enterprise security policy", "size": 5}'
```

### Development Setup

```bash
# Create virtual environment
uv venv --python 3.12
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Install pre-commit hooks
pre-commit install

# Run database migrations (coming soon)
# alembic upgrade head
```

---

## 🎯 Quick Start

### 1. Upload Your First Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/employee_handbook.pdf" \
  -F "title=Employee Handbook 2024" \
  -F "description=Complete employee policies and procedures" \
  -F "department=HR" \
  -F "access_level=internal" \
  -F "document_type=policy"
```

### 2. Ask a Question

```python
import httpx

async def ask_question():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/ask-agentic",
            headers={"Authorization": "Bearer YOUR_JWT_TOKEN"},
            json={
                "query": "What is the company's remote work policy?",
                "top_k": 3,
                "use_hybrid": True,
                "model": "llama3.2:1b"
            }
        )
        
        result = response.json()
        print(f"Answer: {result['answer']}")
        print(f"Sources: {result['sources']}")
        print(f"Reasoning: {result['reasoning_steps']}")

# Run with: python -m asyncio ask_question.py
```

### 3. Search Documents

```bash
curl -X POST http://localhost:8000/api/v1/hybrid-search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "query": "quarterly financial results",
    "size": 10,
    "department": ["finance", "executive"],
    "use_hybrid": true
  }'
```

### 4. Use the Gradio UI

Access the web interface at http://localhost:7861

```bash
# Launch Gradio separately (if not using Docker)
python gradio_launcher.py
```

---

## 📚 API Documentation

### Authentication

All endpoints (except `/health`) require JWT authentication:

```bash
# Login to get token
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {...}
}
```

### Core Endpoints

#### Document Management

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/documents/upload` | POST | Upload and ingest document | ✅ Yes |
| `/api/v1/documents/{id}` | GET | Get specific document | ✅ Yes |
| `/api/v1/documents/` | GET | List documents with filters | ✅ Yes |
| `/api/v1/documents/{id}` | PUT | Update document metadata | ✅ Yes (Owner/Admin) |
| `/api/v1/documents/{id}` | DELETE | Soft delete document | ✅ Yes (Owner/Admin) |

#### Search & Q&A

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/hybrid-search` | POST | Hybrid BM25 + vector search | ✅ Yes |
| `/api/v1/ask` | POST | RAG question answering | ✅ Yes |
| `/api/v1/stream` | POST | Streaming RAG response | ✅ Yes |
| `/api/v1/ask-agentic` | POST | Agentic RAG with reasoning | ✅ Yes |
| `/api/v1/feedback` | POST | Submit feedback on answers | ✅ Yes |

#### Admin & Audit

| Endpoint | Method | Description | Role Required |
|----------|--------|-------------|---------------|
| `/api/v1/admin/audit/logs` | GET | Query audit logs | Admin/Superuser |
| `/api/v1/admin/audit/export` | GET | Export audit logs (JSON/CSV) | Admin/Superuser |
| `/api/v1/admin/audit/stats` | GET | Audit statistics | Admin/Superuser |
| `/api/v1/admin/audit/gdpr/export` | GET | GDPR data export | Admin/Superuser |

### API Examples

#### Agentic RAG with Reasoning

```bash
curl -X POST http://localhost:8000/api/v1/ask-agentic \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "What are the Q3 financial projections for the engineering department?",
    "top_k": 5,
    "use_hybrid": true,
    "model": "llama3.2:1b"
  }'

# Response:
{
  "query": "What are the Q3 financial projections...",
  "answer": "Based on the strategic planning documents from Finance department...",
  "sources": [
    "https://company.com/docs/q3_strategy.pdf",
    "https://company.com/docs/engineering_budget.pdf"
  ],
  "chunks_used": 5,
  "search_mode": "hybrid",
  "reasoning_steps": [
    "Validated query scope (score: 85/100)",
    "Retrieved 5 relevant documents from Finance and Engineering",
    "Graded documents: 4 relevant, 1 low relevance",
    "Generated answer based on financial planning documents"
  ],
  "retrieval_attempts": 1,
  "trace_id": "lf_1234567890abcdef"
}
```

#### Document Upload with Metadata

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@annual_report.pdf" \
  -F "title=Annual Report 2024" \
  -F "description=Comprehensive annual financial and operational report" \
  -F "department=Finance" \
  -F "access_level=confidential" \
  -F "document_type=report" \
  -F "expiry_date=2025-12-31"
```

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

#### Required Core Settings

```bash
# Application
DEBUG=true
ENVIRONMENT=development
APP_VERSION=0.1.0

# PostgreSQL Database
POSTGRES_DATABASE_URL=postgresql+psycopg2://rag_user:rag_password@postgres:5432/rag_db

# OpenSearch
OPENSEARCH_HOST=http://opensearch:9200
OPENSEARCH__INDEX_NAME=enterprise-documents

# Jina AI Embeddings (Get from https://jina.ai/)
JINA_API_KEY=your_jina_api_key_here

# Ollama Configuration
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2:1b
```

#### Enterprise Features

```bash
# Document Sources
ENTERPRISE_SOURCE__SOURCE_TYPE=filesystem
ENTERPRISE_SOURCE__FILESYSTEM_PATH=./data/enterprise_documents
ENTERPRISE_SOURCE__SUPPORTED_EXTENSIONS=.pdf,.docx,.pptx,.xlsx,.txt,.md

# Security & RBAC
SECURITY__JWT_SECRET=change-me-in-production-at-least-32-characters
SECURITY__JWT_ALGORITHM=HS256
SECURITY__DEFAULT_ACCESS_LEVEL=internal
SECURITY__RBAC_ENABLED=true

# Document Lifecycle
DOCUMENT_LIFECYCLE__RETENTION_DAYS=2555  # 7 years
DOCUMENT_LIFECYCLE__AUTO_ARCHIVE_DAYS=365
DOCUMENT_LIFECYCLE__PII_SCAN_ENABLED=true

# Redis Cache
REDIS__HOST=redis
REDIS__PORT=6379
REDIS__TTL_HOURS=6

# Langfuse Tracing (Get from https://langfuse.com/)
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
LANGFUSE_HOST=http://langfuse-web:3000
```

#### Optional Integrations

```bash
# Telegram Bot (Optional)
TELEGRAM__ENABLED=false
TELEGRAM__BOT_TOKEN=your_telegram_bot_token_here

# Airflow Scheduling (Optional)
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__WEBSERVER__EXPOSE_CONFIG=true
```

### Configuration Files

#### Docker Compose Override

Create `compose.override.yml` for production:

```yaml
services:
  api:
    environment:
      - DEBUG=false
      - ENVIRONMENT=production
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
    restart: unless-stopped

  opensearch:
    environment:
      - OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g
    ulimits:
      memlock:
        soft: -1
        hard: -1
```

#### Database Configuration

Database settings are auto-configured via `POSTGRES_DATABASE_URL`. For connection pooling:

```bash
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=0
POSTGRES_ECHO_SQL=false
```

---

## 📝 Examples

### Example 1: HR Policy Assistant

**Scenario**: Employees need instant answers about company policies.

```python
import httpx

async def hr_policy_assistant(question: str):
    """Ask questions about HR policies."""
    
    # Ensure user can only access HR documents
    headers = {
        "Authorization": "Bearer employee_jwt_token",
        "X-Department-Filter": "HR"
    }
    
    async with httpx.AsyncClient() as client:
        # Search for relevant HR policies
        search_resp = await client.post(
            "http://localhost:8000/api/v1/hybrid-search",
            headers=headers,
            json={
                "query": question,
                "department": ["HR"],
                "access_level": "internal",
                "size": 3
            }
        )
        
        # Get AI-powered answer
        rag_resp = await client.post(
            "http://localhost:8000/api/v1/ask-agentic",
            headers=headers,
            json={
                "query": question,
                "top_k": 3,
                "use_hybrid": True
            }
        )
        
        result = rag_resp.json()
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "confidence": result.get("confidence", "medium")
        }

# Usage
response = await hr_policy_assistant("What is the parental leave policy?")
print(f"Answer: {response['answer']}")
```

### Example 2: Automated Document Ingestion

```python
from datetime import datetime, timedelta
import asyncio

async def ingest_recent_financial_docs():
    """Ingest financial documents modified in last 24 hours."""
    
    # Trigger Airflow DAG programmatically
    async with httpx.AsyncClient() as client:
        # Airflow REST API call
        response = await client.post(
            "http://localhost:8080/api/v1/dags/enterprise_document_ingestion/dagRuns",
            auth=("admin", "admin"),
            json={
                "conf": {
                    "since": (datetime.utcnow() - timedelta(hours=24)).isoformat(),
                    "department": "Finance"
                }
            }
        )
        
        print(f"Ingestion triggered: {response.json()['dag_run_id']}")

# Run ingestion every 4 hours as configured in Airflow DAG
```

### Example 3: Access Control Audit

```bash
# Get all access logs for a specific document
curl -X GET "http://localhost:8000/api/v1/admin/audit/logs?document_id=doc_123&limit=100" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Export audit trail for compliance review
curl -X GET "http://localhost:8000/api/v1/admin/audit/export?start_date=2024-01-01&end_date=2024-01-31&format=csv" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  --output audit_january_2024.csv
```

### Example 4: Multi-department Document Search

```python
# Search across Finance and Legal departments
search_request = {
    "query": "contract termination procedures",
    "size": 10,
    "department": ["Finance", "Legal"],
    "access_level": "confidential",
    "use_hybrid": True,
    "min_score": 0.7
}

# User will only see documents they have permission to access
# based on their JWT token's access_levels and department
```

---

## 💻 Development

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/enterprise-kb.git
cd enterprise-kb

# Install uv for dependency management
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv --python 3.12
source .venv/bin/activate

# Install in development mode
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests (when implemented)
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py

# Run linting
ruff check src/
ruff format src/

# Type checking
mypy src/
```

### Code Style

This project uses:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Pre-commit hooks** for quality enforcement
- **Conventional commits** for git messages

### Project Structure

```
enterprise-kb/
├── compose.yml                 # Docker Compose configuration
├── Dockerfile                  # API service Dockerfile
├── pyproject.toml             # Project dependencies
├── .env.example               # Environment variables template
├── airflow/                   # Airflow DAGs and configuration
│   ├── Dockerfile
│   ├── dags/
│   └── requirements-airflow.txt
├── src/                       # Main application code
│   ├── config.py             # Configuration management
│   ├── main.py               # FastAPI application
│   ├── gradio_app.py         # Gradio UI interface
│   ├── routers/              # API route handlers
│   ├── services/             # Business logic
│   ├── repositories/         # Data access layer
│   ├── models/               # Database models
│   └── schemas/              # Pydantic schemas
├── planning_docs/            # Architecture documentation
└── data/                     # Document storage
```

---

## 🧪 Testing

> **Note**: Comprehensive test suite is in development. Current test coverage is ~0%.

### Running Tests

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run end-to-end tests
pytest tests/e2e/

# Generate coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_services/
│   ├── test_repositories/
│   └── test_schemas/
├── integration/             # Integration tests between components
│   ├── test_ingestion/
│   └── test_search/
└── e2e/                     # End-to-end API tests
    └── test_api_flows.py
```

### Test Coverage Goals

Target coverage: **80%+**

Priority areas for testing:
- Authentication & authorization
- Document ingestion pipeline
- RAG query processing
- Access control enforcement
- Audit logging

### Manual Testing Checklist

Before pushing changes, manually verify:

- [ ] API starts without errors: `docker compose up -d`
- [ ] Health endpoint returns 200
- [ ] Document upload works
- [ ] Search returns relevant results
- [ ] RAG answering works with sources
- [ ] Access control blocks unauthorized access
- [ ] Audit logs capture all events
- [ ] Gradio UI is functional

---

## 📈 Roadmap

### Q1 2025

- [ ] **Security Hardening**: Fix critical vulnerabilities, add rate limiting
- [ ] **Test Suite**: Achieve 80% test coverage
- [ ] **Kubernetes Deployment**: Production k8s manifests and Helm charts
- [ ] **SSO Integration**: SAML/OIDC support (Keycloak, Auth0)
- [ ] **API Versioning**: v2 API with breaking changes

### Q2 2025

- [ ] **Advanced PII Detection**: ML-based PII scanning
- [ ] **Multi-language Support**: Document processing in multiple languages
- [ ] **Citations & References**: Structured citation extraction
- [ ] **Analytics Dashboard**: Document usage analytics
- [ ] **Enhanced Agents**: Support for multiple agent strategies

### Q3 2025

- [ ] **Workflow Orchestration**: Replace Airflow with Temporal for scalability
- [ ] **Advanced Chunking**: Semantic chunking with topic modeling
- [ ] **Model Management**: A/B testing for LLM models
- [ ] **Graph RAG**: Knowledge graph integration
- [ ] **Cloud-native**: AWS/GCP/Azure deployment guides

### Long-term Vision

- **Multi-modal RAG**: Support for images, audio, video
- **Real-time Collaboration**: Live document editing with AI assistance
- **Federated Search**: Cross-organizational knowledge discovery
- **Auto-labeling**: AI-powered document classification
- **Predictive Search**: Anticipatory information retrieval

---

### Inspiration

This project was inspired by the need for secure, private AI systems in enterprise environments. It builds upon the excellent work in the RAG community while adding enterprise-grade security and compliance features.

---

## 📞 Support & Contact

- **Email**: aglan0hattem@gmail.com

---

## ⚠️ Production Readiness Notice

**Current Status**: Beta - Suitable for pilot deployments with <100 users

**Minimum Requirements for Production**:
- [ ] Security audit completed
- [ ] Test coverage > 80%
- [ ] Rate limiting implemented
- [ ] Secrets management (Vault/AWS Secrets Manager)
- [ ] Kubernetes deployment manifests
- [ ] Monitoring & alerting (Prometheus/Grafana)
- [ ] Backup & disaster recovery procedures

**Estimated Timeline**: 4-6 weeks for production hardening

---

<div align="center">

**Made with ❤️ for secure, private AI in the enterprise**

⭐ Star us on GitHub to show your support!

</div>