# IncidentIQ REST API Specification

This document details the REST API endpoints, schemas, parameters, and HTTP response contracts for **IncidentIQ**.

---

## 1. Global Conventions & Standards

- **Base URL**: `/api`
- **Content-Type**: `application/json` (except multipart file upload endpoints: `multipart/form-data`)
- **Error Responses**: All error responses return RFC 7807 compliant JSON:
  ```json
  {
    "detail": "Descriptive error message",
    "status_code": 400,
    "error_code": "INVALID_EVIDENCE_PAYLOAD",
    "timestamp": "2026-09-25T10:00:00Z"
  }
  ```

---

## 2. Incident Management Endpoints

### 2.1 Create Incident
- **Method / Path**: `POST /api/incidents`
- **Request Body**:
  ```json
  {
    "title": "Payment gateway latency spike",
    "description": "Customers reporting 504 errors during checkout flow",
    "source": "WEB_UI",
    "priority": "P2",
    "category": "API_SERVICE"
  }
  ```
- **Response**: `201 Created` with full Incident object.

### 2.2 List Incidents
- **Method / Path**: `GET /api/incidents`
- **Query Parameters**:
  - `status`: Filter by status (`OPEN`, `INVESTIGATING`, `RESOLVED`, `CLOSED`)
  - `severity`: Filter by severity (`P1`, `P2`, `P3`, `P4`)
  - `team`: Filter by assignment team (`DevOps`, `Database`, `Backend`, etc.)
  - `page`: Page index (default: `1`)
  - `page_size`: Items per page (default: `20`, max: `100`)
- **Response**: `200 OK` with paginated list and total count metadata.

### 2.3 Get Incident by ID
- **Method / Path**: `GET /api/incidents/{id}`
- **Response**: `200 OK` with incident entity and associated evidence summaries.

### 2.4 Update Incident
- **Method / Path**: `PATCH /api/incidents/{id}`
- **Request Body**: Partial update fields (`status`, `severity`, `assignment_team`, `title`, `resolved_at`).
- **Response**: `200 OK` with updated Incident.

---

## 3. Evidence Ingestion Endpoints

### 3.1 Upload Evidence Files
- **Method / Path**: `POST /api/incidents/{id}/evidence`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Binary file stream
  - `evidence_type`: `LOG`, `SCREENSHOT`, `AUDIO`, `EMAIL`, `CUSTOMER_COMPLAINT`, `TEXT`, `DOCUMENT`
  - `description`: Optional text annotation
- **Validation**: Enforces allowed MIME types, extension checking, and 50MB file size ceiling.
- **Response**: `201 Created` with Evidence record.

---

## 4. Multimodal AI Analysis & Intelligence Endpoints

### 4.1 Trigger Full AI Analysis
- **Method / Path**: `POST /api/incidents/{id}/analyze`
- **Description**: Triggers content extraction, OCR/transcription, feature normalization, classification, RCA, routing, RAG retrieval, and artifact generation.
- **Response**: `202 Accepted` or `200 OK` with consolidated analysis snapshot.

### 4.2 Retrieve AI Analysis
- **Method / Path**: `GET /api/incidents/{id}/analysis`
- **Response**: `200 OK` with root cause hypotheses, severity assessment, affected systems, and explainable team routing.

### 4.3 Retrieve Incident Timeline
- **Method / Path**: `GET /api/incidents/{id}/timeline`
- **Response**: `200 OK` with chronologically ordered list of normalized events extracted from logs, communications, and system events.

### 4.4 Retrieve Recommendations & Playbooks
- **Method / Path**: `GET /api/incidents/{id}/recommendations`
- **Response**: `200 OK` with immediate containment steps, short-term workarounds, long-term preventions, risks, and rollback instructions.

---

## 5. Knowledge Base & RAG Endpoints

### 5.1 Index Resolved Incident
- **Method / Path**: `POST /api/knowledge-base/index`
- **Request Body**:
  ```json
  {
    "incident_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "PostgreSQL connection pool exhaustion",
    "problem_description": "Excessive idle connections from payment service",
    "root_cause": "Missing connection close in batch checkout worker",
    "solution": "Updated connection pool config and wrapped checkout worker in context manager",
    "affected_systems": ["payment-service", "postgres-primary"],
    "category": "DATABASE",
    "severity": "P1"
  }
  ```
- **Response**: `201 Created` with indexed knowledge document and vector ID.

### 5.2 Search Knowledge Base
- **Method / Path**: `GET /api/knowledge-base/search`
- **Query Parameters**:
  - `query`: Free-text search string
  - `category`: Optional domain filter
  - `top_k`: Number of similar records (default: `5`, max: `20`)
- **Response**: `200 OK` with ranked similar historical incidents and similarity scores.

---

## 6. Dashboard & Metrics Endpoints

### 6.1 Get SOC Operations Statistics
- **Method / Path**: `GET /api/dashboard/stats`
- **Response**: `200 OK`
  ```json
  {
    "total_incidents": 142,
    "open_incidents": 8,
    "critical_incidents": 2,
    "avg_resolution_time_min": 43.5,
    "by_severity": { "P1": 5, "P2": 18, "P3": 64, "P4": 55 },
    "by_category": { "DATABASE": 28, "API_SERVICE": 44, "NETWORK": 16, "INFRASTRUCTURE": 54 },
    "by_team": { "DevOps": 40, "Database": 28, "Backend": 50, "Network": 14, "Security": 10 },
    "recent_incidents": []
  }
  ```
