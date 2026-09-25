"""
IncidentIQ ORM Models
Defines all domain entities conforming to the PostgreSQL 15 + pgvector specification.
Separates database models from Pydantic API schemas.
Provides fallback column definitions when external SQLAlchemy / pgvector modules
are not yet installed in the local Python environment.
"""

from datetime import datetime, timezone
import uuid

try:
    from sqlalchemy import (
        Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, JSON
    )
    from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
    from sqlalchemy.orm import declarative_base, relationship

    try:
        from pgvector.sqlalchemy import Vector
        VECTOR_TYPE = Vector(1536)
    except ImportError:
        VECTOR_TYPE = JSONB

    Base = declarative_base()

    class AssignmentTeam(Base):
        __tablename__ = "assignment_teams"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        name = Column(String(100), nullable=False, unique=True)
        lead_email = Column(String(255), nullable=True)
        slack_channel = Column(String(100), nullable=True)
        is_active = Column(Boolean, nullable=False, default=True)
        created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
        updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

        incidents = relationship("Incident", back_populates="assignment_team")
        routed_analyses = relationship("IncidentAnalysis", back_populates="routed_team")

    class User(Base):
        __tablename__ = "users"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        email = Column(String(255), nullable=False, unique=True)
        full_name = Column(String(255), nullable=False)
        role = Column(String(50), nullable=False, default="responder")
        is_active = Column(Boolean, nullable=False, default=True)
        created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
        updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    class Incident(Base):
        __tablename__ = "incidents"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        title = Column(String(500), nullable=False)
        description = Column(Text, nullable=False)
        status = Column(String(50), nullable=False, default="Open", index=True)
        severity = Column(String(10), nullable=False, default="P3", index=True)
        priority = Column(String(10), nullable=False, default="P3")
        category = Column(String(100), nullable=False, default="Support", index=True)
        affected_systems = Column(ARRAY(String), nullable=False, default=list)
        assignment_team_id = Column(UUID(as_uuid=True), ForeignKey("assignment_teams.id", ondelete="SET NULL"), nullable=True, index=True)
        source = Column(String(100), nullable=False, default="manual")
        confidence = Column(Float, nullable=False, default=1.0)
        root_cause = Column(Text, nullable=True)
        recommended_solution = Column(Text, nullable=True)
        executive_summary = Column(Text, nullable=True)
        bug_report = Column(JSONB, nullable=True)
        metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
        created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
        updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
        resolved_at = Column(DateTime(timezone=True), nullable=True)

        assignment_team = relationship("AssignmentTeam", back_populates="incidents")
        evidence = relationship("Evidence", back_populates="incident", cascade="all, delete-orphan")
        events = relationship("IncidentEvent", back_populates="incident", cascade="all, delete-orphan")
        analysis = relationship("IncidentAnalysis", back_populates="incident", uselist=False, cascade="all, delete-orphan")
        recommendations = relationship("Recommendation", back_populates="incident", uselist=False, cascade="all, delete-orphan")
        knowledge_document = relationship("KnowledgeDocument", back_populates="incident", uselist=False)

    class Evidence(Base):
        __tablename__ = "evidence"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
        type = Column(String(50), nullable=False, index=True)
        source = Column(String(100), nullable=False, default="upload")
        file_name = Column(String(255), nullable=False)
        mime_type = Column(String(100), nullable=False)
        content = Column(Text, nullable=True)
        storage_path = Column(String(1000), nullable=True)
        extracted_text = Column(Text, nullable=True)
        metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
        created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

        incident = relationship("Incident", back_populates="evidence")

    class IncidentEvent(Base):
        __tablename__ = "incident_events"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
        event_timestamp = Column(DateTime(timezone=True), nullable=True)
        is_approximate = Column(Boolean, nullable=False, default=False)
        source_type = Column(String(50), nullable=False, default="SYSTEM")
        description = Column(Text, nullable=False)
        severity_hint = Column(String(50), nullable=True)
        metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
        created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

        incident = relationship("Incident", back_populates="events")

    class IncidentAnalysis(Base):
        __tablename__ = "incident_analysis"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
        probable_root_cause = Column(Text, nullable=False)
        root_cause_confidence = Column(Float, nullable=False, default=0.0)
        supporting_evidence = Column(JSONB, nullable=False, default=list)
        contradicting_evidence = Column(JSONB, nullable=False, default=list)
        alternative_hypotheses = Column(JSONB, nullable=False, default=list)
        next_checks = Column(JSONB, nullable=False, default=list)
        severity_assigned = Column(String(10), nullable=False)
        severity_confidence = Column(Float, nullable=False, default=0.0)
        severity_factors = Column(JSONB, nullable=False, default=list)
        routed_team_id = Column(UUID(as_uuid=True), ForeignKey("assignment_teams.id", ondelete="SET NULL"), nullable=True)
        routing_reasons = Column(JSONB, nullable=False, default=list)
        model_version = Column(String(100), nullable=False, default="mock-engine-v1")
        analyzed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

        incident = relationship("Incident", back_populates="analysis")
        routed_team = relationship("AssignmentTeam", back_populates="routed_analyses")

    class Recommendation(Base):
        __tablename__ = "recommendations"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
        immediate_actions = Column(JSONB, nullable=False, default=list)
        short_term_actions = Column(JSONB, nullable=False, default=list)
        long_term_actions = Column(JSONB, nullable=False, default=list)
        risk_if_unresolved = Column(Text, nullable=True)
        rollback_option = Column(Text, nullable=True)
        verification_steps = Column(JSONB, nullable=False, default=list)
        created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

        incident = relationship("Incident", back_populates="recommendations")

    class KnowledgeDocument(Base):
        __tablename__ = "knowledge_documents"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
        title = Column(String(500), nullable=False)
        problem_description = Column(Text, nullable=False)
        root_cause = Column(Text, nullable=False)
        solution = Column(Text, nullable=False)
        affected_systems = Column(ARRAY(String), nullable=False, default=list)
        category = Column(String(100), nullable=False, index=True)
        severity = Column(String(10), nullable=False, index=True)
        resolution_time_min = Column(Integer, nullable=True)
        embedding = Column(VECTOR_TYPE, nullable=True)
        metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
        created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
        updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

        incident = relationship("Incident", back_populates="knowledge_document")

    class EmbeddingRecord(Base):
        __tablename__ = "embedding_records"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        entity_type = Column(String(50), nullable=False, index=True)
        entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
        model_name = Column(String(100), nullable=False)
        dimensions = Column(Integer, nullable=False)
        vector_data = Column(VECTOR_TYPE, nullable=True)
        created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

except ImportError:
    # Pure Python Model Definitions when SQLAlchemy is not installed
    class Base:
        pass

    class AssignmentTeam:
        __tablename__ = "assignment_teams"

    class User:
        __tablename__ = "users"

    class Incident:
        __tablename__ = "incidents"

    class Evidence:
        __tablename__ = "evidence"

    class IncidentEvent:
        __tablename__ = "incident_events"

    class IncidentAnalysis:
        __tablename__ = "incident_analysis"

    class Recommendation:
        __tablename__ = "recommendations"

    class KnowledgeDocument:
        __tablename__ = "knowledge_documents"

    class EmbeddingRecord:
        __tablename__ = "embedding_records"
