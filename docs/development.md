# IncidentIQ Development Guide

Welcome to the development guide for **IncidentIQ: AI-Powered Multimodal Incident Intelligence & Response System**.

This document outlines local environment setup, architectural conventions, Git practices, testing strategies, and the incremental milestone plan.

---

## 🛠️ System Prerequisites

Ensure you have the following installed on your development machine:
- **Operating System**: Windows, macOS, or Linux
- **Python**: 3.11+ (Detected: Python 3.14.0)
- **Node.js**: 20.x or higher (Detected: Node.js v24.15.0, npm 11.x)
- **Git**: 2.30+
- **Docker & Docker Compose**: Optional for containerized local services (PostgreSQL + pgvector)

---

## ⚙️ Environment Configuration

1. Copy the sample environment file to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Key settings in `.env`:
   - `ENVIRONMENT`: Set to `development` for verbose logging and live reloading.
   - `AI_PROVIDER`: Set to `mock` for deterministic offline testing without external API keys, or configure `openai`, `anthropic`, or `gemini`.
   - `DATABASE_URL`: Connection string for PostgreSQL with asyncpg (`postgresql+asyncpg://postgres:postgres@localhost:5432/incidentiq`).
   - `UPLOAD_DIR`: Local filesystem directory for uploaded evidence (`storage/uploads`).
   - `MAX_UPLOAD_SIZE_MB`: Enforced limit on evidence payloads (default: 50MB).

> [!IMPORTANT]
> Never commit `.env` or any production secrets to version control. The `.gitignore` file is pre-configured to exclude environment files and secret keys.

---

## 📐 Engineering Principles

1. **Separation of Concerns**:
   - AI and heuristic inference logic are strictly decoupled from API route handlers.
   - Raw data ingestion and ETL scripts are kept independent from inference engines.
   - SQLAlchemy ORM database models remain distinct from Pydantic/API schemas.
2. **Structured & Explainable AI**:
   - All AI service methods return validated Pydantic models with strict schemas.
   - Root cause analysis must include confidence scores, supporting evidence, contradicting evidence, and alternative hypotheses.
   - Routing decisions must provide human-readable routing reasons.
3. **Resilience & Local Execution**:
   - Provide local mock implementations behind clean interface abstractions for external dependencies (LLM APIs, embedding APIs, Whisper transcription).
   - The platform can run fully offline in development mode.
4. **Data Hygiene**:
   - Never permanently mutate raw source datasets.
   - Clearly delineate synthetic benchmark scenarios from real public incident datasets.

---

## 🧪 Testing Guidelines

Every core component must include unit or integration tests:
- **Unit tests**: Fast tests for normalization, parsing, routing heuristics, and schema validation (`pytest tests/unit`).
- **API tests**: Endpoint contract and validation tests using FastAPI `TestClient` or `httpx` (`pytest tests/api`).
- **Data tests**: Ingestion and schema transformation validation (`pytest tests/data`).

Running tests:
```bash
pytest -v
```

---

## 🔀 Git & Commit Workflow

We follow standard Conventional Commits:
- `feat(scope): description` - New functionality
- `fix(scope): description` - Bug fixes
- `chore(scope): description` - Maintenance, configuration, boilerplate
- `docs(scope): description` - Documentation updates
- `test(scope): description` - Adding or updating test suites
- `refactor(scope): description` - Code restructuring without behavioral changes

Before creating any commit:
1. Verify code formatting and linting.
2. Run relevant tests.
3. Check `git status` and `git diff` to ensure no transient files or credentials are staged.
