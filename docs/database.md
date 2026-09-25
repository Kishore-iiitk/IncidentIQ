# IncidentIQ Database & Persistence Specification

This document details the relational and vector database schema for **IncidentIQ**, utilizing PostgreSQL 15+ and the `pgvector` extension.

---

## 1. Entity-Relationship Model

```mermaid
erDiagram
    USERS ||--o{ INCIDENTS : "reports / manages"
    INCIDENTS ||--o{ EVIDENCE : "contains"
    INCIDENTS ||--o{ INCIDENT_EVENTS : "tracks"
    INCIDENTS ||--o| INCIDENT_ANALYSIS : "evaluates to"
    INCIDENTS ||--o| RECOMMENDATIONS : "generates"
    INCIDENTS ||--o| KNOWLEDGE_DOCUMENTS : "publishes to"
    ASSIGNMENT_TEAMS ||--o{ INCIDENTS : "assigned"
    KNOWLEDGE_DOCUMENTS ||--o| EMBEDDING_RECORDS : "indexed by"

    INCIDENTS {
        uuid id PK
        varchar title
        text description
        varchar status
        varchar severity
        varchar priority
        varchar category
        varchar[] affected_systems
        uuid assignment_team_id FK
        varchar source
        float confidence
        text root_cause
        text recommended_solution
        text executive_summary
        jsonb bug_report
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
        timestamptz resolved_at
    }

    EVIDENCE {
        uuid id PK
        uuid incident_id FK
        varchar type
        varchar source
        varchar file_name
        varchar mime_type
        text content
        varchar storage_path
        text extracted_text
        jsonb metadata
        timestamptz created_at
    }

    INCIDENT_EVENTS {
        uuid id PK
        uuid incident_id FK
        timestamptz event_timestamp
        boolean is_approximate
        varchar source_type
        text description
        varchar severity_hint
        jsonb metadata
    }

    INCIDENT_ANALYSIS {
        uuid id PK
        uuid incident_id FK
        text probable_root_cause
        float root_cause_confidence
        jsonb supporting_evidence
        jsonb contradicting_evidence
        jsonb alternative_hypotheses
        jsonb next_checks
        varchar severity_assigned
        float severity_confidence
        jsonb severity_factors
        uuid routed_team_id FK
        jsonb routing_reasons
        timestamptz analyzed_at
    }

    RECOMMENDATIONS {
        uuid id PK
        uuid incident_id FK
        jsonb immediate_actions
        jsonb short_term_actions
        jsonb long_term_actions
        text risk_if_unresolved
        text rollback_option
        jsonb verification_steps
        timestamptz created_at
    }

    KNOWLEDGE_DOCUMENTS {
        uuid id PK
        uuid incident_id FK
        varchar title
        text problem_description
        text root_cause
        text solution
        varchar[] affected_systems
        varchar category
        varchar severity
        int resolution_time_min
        vector embedding
        jsonb metadata
        timestamptz created_at
    }

    EMBEDDING_RECORDS {
        uuid id PK
        varchar entity_type
        uuid entity_id
        varchar model_name
        int dimensions
        vector vector_data
        timestamptz created_at
    }

    ASSIGNMENT_TEAMS {
        uuid id PK
        varchar name
        varchar lead_email
        varchar slack_channel
        boolean is_active
    }

    USERS {
        uuid id PK
        varchar email
        varchar full_name
        varchar role
        boolean is_active
        timestamptz created_at
    }
```

---

## 2. Table Specifications & Indexing Strategy

### 2.1 `incidents`
- Stores primary normalized incident state.
- **Indexes**:
  - `idx_incidents_status` (`status`) for operational queues.
  - `idx_incidents_severity` (`severity`) for prioritization.
  - `idx_incidents_created_at` (`created_at DESC`) for timeline sorting.
  - `idx_incidents_team` (`assignment_team_id`) for routing queries.

### 2.2 `evidence`
- Stores normalized pointers to uploaded evidence and OCR/transcripts.
- Foreign key: `incident_id` REFERENCES `incidents(id)` ON DELETE CASCADE.
- **Indexes**:
  - `idx_evidence_incident_id` (`incident_id`)
  - `idx_evidence_type` (`type`)

### 2.3 `incident_events`
- Chronological timeline events extracted across logs, communications, and system alarms.
- Foreign key: `incident_id` REFERENCES `incidents(id)` ON DELETE CASCADE.
- **Indexes**:
  - `idx_incident_events_time` (`incident_id`, `event_timestamp ASC`)

### 2.4 `knowledge_documents` & Vector Indexing
- Stores verified postmortems for similarity search.
- Field: `embedding vector(1536)`
- **Index**:
  - HNSW (Hierarchical Navigable Small World) index for fast approximate nearest neighbor (ANN) retrieval:
    ```sql
    CREATE INDEX idx_knowledge_docs_embedding_hnsw 
    ON knowledge_documents 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    ```
  - B-Tree index on `category` and `affected_systems` (using GIN) for filtered hybrid vector queries.
