"""
IncidentIQ Incident Pydantic Schemas.
Separates API contracts and data validation from database persistence models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


class IncidentSeverity(str, Enum):
    P1 = "P1"  # Critical
    P2 = "P2"  # High
    P3 = "P3"  # Medium
    P4 = "P4"  # Low


class IncidentPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentStatus(str, Enum):
    OPEN = "Open"
    INVESTIGATING = "Investigating"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class IncidentCategory(str, Enum):
    DATABASE = "Database"
    API_SERVICE = "API Service"
    NETWORK = "Network"
    INFRASTRUCTURE = "Infrastructure"
    SECURITY = "Security"
    AUTHENTICATION = "Authentication"
    STORAGE = "Storage"
    DEVOPS = "DevOps"
    FRONTEND = "Frontend"
    SUPPORT = "Support"
    OTHER = "Other"


class IncidentBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=500, description="Short summary of the incident")
    description: str = Field(..., min_length=5, description="Detailed incident description and symptoms")
    severity: IncidentSeverity = Field(default=IncidentSeverity.P3, description="Incident severity level")
    priority: IncidentPriority = Field(default=IncidentPriority.P3, description="Operational priority")
    category: IncidentCategory = Field(default=IncidentCategory.SUPPORT, description="Primary technical domain")
    affected_systems: List[str] = Field(default_factory=list, description="List of impacted hosts/services")
    assignment_team: Optional[str] = Field(default=None, max_length=100, description="Assigned engineering team")
    source: str = Field(default="manual", max_length=100, description="Incident ingestion source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary incident metadata")

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Incident title cannot be blank or whitespace only")
        return stripped

    @field_validator("description")
    @classmethod
    def validate_description_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Incident description cannot be blank or whitespace only")
        return stripped


class IncidentCreate(IncidentBase):
    """Schema for creating a new incident."""
    pass


class IncidentUpdate(BaseModel):
    """Schema for partial update of an existing incident."""
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = Field(None, min_length=5)
    status: Optional[IncidentStatus] = None
    severity: Optional[IncidentSeverity] = None
    priority: Optional[IncidentPriority] = None
    category: Optional[IncidentCategory] = None
    affected_systems: Optional[List[str]] = None
    assignment_team: Optional[str] = None
    root_cause: Optional[str] = None
    recommended_solution: Optional[str] = None
    executive_summary: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("title")
    @classmethod
    def validate_title_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Incident title cannot be blank")
            return stripped
        return v


class IncidentResponse(IncidentBase):
    """Schema returned to API clients representing an Incident."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique incident identifier")
    status: IncidentStatus = Field(default=IncidentStatus.OPEN, description="Current incident lifecycle status")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in current diagnosis")
    root_cause: Optional[str] = Field(default=None, description="Identified or hypothesized root cause")
    recommended_solution: Optional[str] = Field(default=None, description="Proposed remediation steps")
    executive_summary: Optional[str] = Field(default=None, description="High-level business summary")
    bug_report: Optional[Dict[str, Any]] = Field(default=None, description="Structured bug report if generated")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    resolved_at: Optional[datetime] = Field(default=None, description="Resolution timestamp")


class IncidentListResponse(BaseModel):
    """Paginated response containing multiple incidents."""
    items: List[IncidentResponse]
    total: int = Field(..., description="Total count matching filter criteria")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
