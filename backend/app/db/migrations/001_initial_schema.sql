-- ==============================================================================
-- IncidentIQ: Core Relational and Vector Schema Definition
-- Engine: PostgreSQL 15+ with pgvector
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. Assignment Teams Table
CREATE TABLE IF NOT EXISTS assignment_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    lead_email VARCHAR(255),
    slack_channel VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'responder', -- admin, lead, responder, viewer
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. Incidents Table (Normalized Core Entity)
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Open', -- Open, Investigating, Mitigated, Resolved, Closed
    severity VARCHAR(10) NOT NULL DEFAULT 'P3', -- P1, P2, P3, P4
    priority VARCHAR(10) NOT NULL DEFAULT 'P3',
    category VARCHAR(100) NOT NULL DEFAULT 'Support', -- Database, Network, Security, DevOps, Infrastructure, Backend, Frontend, Cloud, Support
    affected_systems TEXT[] NOT NULL DEFAULT '{}',
    assignment_team_id UUID REFERENCES assignment_teams(id) ON DELETE SET NULL,
    source VARCHAR(100) NOT NULL DEFAULT 'manual', -- manual, api, email, monitoring, kaggle_it_incident, synthetic_multimodal
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    root_cause TEXT,
    recommended_solution TEXT,
    executive_summary TEXT,
    bug_report JSONB,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

-- 5. Evidence Table (Multimodal Evidence Attachments)
CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- LOG, SCREENSHOT, AUDIO, EMAIL, CUSTOMER_COMPLAINT, TEXT, DOCUMENT
    source VARCHAR(100) NOT NULL DEFAULT 'upload',
    file_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    content TEXT,
    storage_path VARCHAR(1000),
    extracted_text TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Incident Events Table (Chronological Timeline)
CREATE TABLE IF NOT EXISTS incident_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    event_timestamp TIMESTAMPTZ,
    is_approximate BOOLEAN NOT NULL DEFAULT FALSE,
    source_type VARCHAR(50) NOT NULL DEFAULT 'SYSTEM', -- LOG, SYSTEM, USER, ALERT, CALL
    description TEXT NOT NULL,
    severity_hint VARCHAR(50),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7. Incident Analysis Table (Multimodal AI Reasoning Results)
CREATE TABLE IF NOT EXISTS incident_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL UNIQUE REFERENCES incidents(id) ON DELETE CASCADE,
    probable_root_cause TEXT NOT NULL,
    root_cause_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    supporting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    contradicting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    alternative_hypotheses JSONB NOT NULL DEFAULT '[]'::jsonb,
    next_checks JSONB NOT NULL DEFAULT '[]'::jsonb,
    severity_assigned VARCHAR(10) NOT NULL,
    severity_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    severity_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
    routed_team_id UUID REFERENCES assignment_teams(id) ON DELETE SET NULL,
    routing_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_version VARCHAR(100) NOT NULL DEFAULT 'mock-engine-v1',
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. Recommendations Table (Tiered Action Items)
CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL UNIQUE REFERENCES incidents(id) ON DELETE CASCADE,
    immediate_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    short_term_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    long_term_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_if_unresolved TEXT,
    rollback_option TEXT,
    verification_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. Knowledge Documents Table (Historical Resolved Incidents for RAG)
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID REFERENCES incidents(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    problem_description TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    solution TEXT NOT NULL,
    affected_systems TEXT[] NOT NULL DEFAULT '{}',
    category VARCHAR(100) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    resolution_time_min INTEGER,
    embedding VECTOR(1536),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. Embedding Records Table (Generic Vector Storage)
CREATE TABLE IF NOT EXISTS embedding_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL, -- knowledge_doc, evidence, incident
    entity_id UUID NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    dimensions INTEGER NOT NULL,
    vector_data VECTOR(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- INDEXING STRATEGY
-- ==============================================================================

-- Incidents Indexes
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents (status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents (severity);
CREATE INDEX IF NOT EXISTS idx_incidents_category ON incidents (category);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_team_id ON incidents (assignment_team_id);
CREATE INDEX IF NOT EXISTS idx_incidents_affected_systems ON incidents USING GIN (affected_systems);

-- Evidence Indexes
CREATE INDEX IF NOT EXISTS idx_evidence_incident_id ON evidence (incident_id);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence (type);
CREATE INDEX IF NOT EXISTS idx_evidence_created_at ON evidence (created_at DESC);

-- Incident Events Indexes
CREATE INDEX IF NOT EXISTS idx_incident_events_incident_time ON incident_events (incident_id, event_timestamp ASC);

-- Knowledge Documents & Vector Indexing
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_category ON knowledge_documents (category);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_severity ON knowledge_documents (severity);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_systems ON knowledge_documents USING GIN (affected_systems);

-- HNSW Vector Index for Cosine Similarity Searches
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_embedding_hnsw 
ON knowledge_documents 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_embedding_records_entity 
ON embedding_records (entity_type, entity_id);
