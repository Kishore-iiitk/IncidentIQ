# IncidentIQ Data Architecture & Ingestion Pipeline

This document defines the data sources, ingestion pipelines, normalization rules, and data hygiene standards for **IncidentIQ**.

---

## 1. Dataset Hierarchy

```
IncidentIQ Data Architecture
├── Real Public Data
│   ├── IT Incident Dataset (Primary Historical Incident Log)
│   └── LogHub (Supplementary Log-Event Streams)
│       ├── HDFS
│       ├── OpenStack
│       ├── BGL
│       └── Apache
└── Synthetic Multimodal Data (Clearly Tagged)
    ├── Screenshots (UI errors, APM dashboards, console traces)
    ├── Voice Reports (Incident audio & transcripts)
    ├── Emails (Escalations, alerts, on-call handoffs)
    ├── Customer Complaints (Support tickets, user feedback)
    └── Incident Knowledge Base (Pre-computed postmortems)
```

---

## 2. Ingestion Principles & Source Data Handling

### 2.1 IT Incident Dataset (Kaggle)
- **Source**: `shamiulislamshifat/it-incident-log-dataset`
- **Schema Policy**: The raw schema must **not** be assumed a priori. The pipeline programmatically inspects column headers, infers data types, detects null ratios, and maps source fields into the normalized IncidentIQ schema.
- **Role**: Provides historical resolution timelines, incident categories, and team assignments for baseline model benchmarking and knowledge base seeding.

### 2.2 LogHub Sources
- **Sources**: HDFS, OpenStack, BGL, Apache log repositories.
- **Operational Classification**: Treated strictly as **supplementary log-event sources** for testing log anomaly extraction, timeline reconstruction, and parsing logic. They are **never** misrepresented as complete incident tickets.

### 2.3 Synthetic Multimodal Scenarios
To benchmark multimodal capabilities across diverse failure modes, IncidentIQ provides 10 realistic scenarios:
1. **Database connection failure**: Connection pool exhaustion, timeout cascades, connection queue saturation.
2. **API latency spike**: Upstream microservice degradation, thread contention, HTTP 504 surges.
3. **Kubernetes pod crash**: CrashLoopBackOff, OOMKilled events, liveness probe failures.
4. **Disk space exhaustion**: Log partition fill-up, write failure on WAL, I/O blocking.
5. **Authentication failure**: Expired JWT signing certificate, OAuth provider rate-limiting, 401/403 spikes.
6. **Network outage**: BGP route flapping, cross-AZ transit gateway failure, packet loss.
7. **Deployment failure**: Incompatible database migration, misconfigured environment variable, roll-forward abort.
8. **Memory leak**: Heap allocation creeping upward in Java/Go service until garbage collection pauses cause timeouts.
9. **Redis outage**: Memory limit reached (OOM command not allowed), sentinel failover delay, cache thundering herd.
10. **DNS resolution failure**: CoreDNS pod crash, upstream recursive resolver timeout, internal service discovery loss.

> [!NOTE]
> Every synthetic record includes metadata property `"is_synthetic": true` to prevent data leakage and ensure complete audit transparency.

---

## 3. Ingestion & Transformation Scripts (`scripts/`)

- **`inspect_dataset.py`**: Reads raw datasets without mutation; reports column profiles, null distributions, duplicate rates, and candidate date formats.
- **`clean_incidents.py`**: Cleans, deduplicates, parses dates into ISO-8601 UTC, normalizes category labels, and writes clean artifacts to `data/processed/incidents_cleaned.json`.
- **`ingest_logs.py`**: Parses LogHub log formats using standard log regular expressions into normalized log event structures.
- **`seed_database.py`**: Idempotently seeds the PostgreSQL database and pgvector knowledge base from processed datasets.
