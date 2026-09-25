"""
Incident Service layer for IncidentIQ.
Encapsulates all domain logic, state transitions, validation, and storage operations.
Maintains strict separation between database entities and API schemas.
"""

from datetime import datetime, timezone
import math
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from ...core.logging import logger
from ...schemas.incident import (
    IncidentCategory,
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentSeverity,
    IncidentStatus,
    IncidentUpdate,
)


class IncidentRepository:
    """
    In-memory / persistence repository abstraction for Incidents.
    Ensures IncidentIQ runs seamlessly out of the box in standalone mode,
    while maintaining full compatibility with the PostgreSQL relational schema.
    """

    def __init__(self) -> None:
        self._storage: Dict[UUID, dict] = {}

    def get(self, incident_id: UUID) -> Optional[dict]:
        return self._storage.get(incident_id)

    def save(self, record: dict) -> dict:
        self._storage[record["id"]] = record
        return record

    def list_all(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        team: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        results = list(self._storage.values())

        if status:
            results = [r for r in results if r.get("status") == status]
        if severity:
            results = [r for r in results if r.get("severity") == severity]
        if category:
            results = [r for r in results if r.get("category") == category]
        if team:
            results = [
                r for r in results
                if (r.get("assignment_team") or "").lower() == team.lower()
            ]
        if search:
            q = search.lower()
            results = [
                r for r in results
                if q in r.get("title", "").lower() or q in r.get("description", "").lower()
            ]

        # Sort descending by created_at
        results.sort(key=lambda x: x.get("created_at"), reverse=True)
        return results

    def count(self) -> int:
        return len(self._storage)

    def clear(self) -> None:
        self._storage.clear()


# Shared repository singleton instance
_repository = IncidentRepository()


class IncidentService:
    """Domain service handling incident operations and lifecycle."""

    def __init__(self, repo: Optional[IncidentRepository] = None) -> None:
        self.repo = repo or _repository

    def create_incident(self, data: IncidentCreate) -> IncidentResponse:
        """Creates and persists a new incident record."""
        now = datetime.now(timezone.utc)
        incident_id = uuid4()

        record = {
            "id": incident_id,
            "title": data.title,
            "description": data.description,
            "status": IncidentStatus.OPEN.value,
            "severity": data.severity.value,
            "priority": data.priority.value,
            "category": data.category.value,
            "affected_systems": list(data.affected_systems),
            "assignment_team": data.assignment_team,
            "source": data.source,
            "confidence": 1.0,
            "root_cause": None,
            "recommended_solution": None,
            "executive_summary": None,
            "bug_report": None,
            "metadata": dict(data.metadata),
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
        }

        self.repo.save(record)
        logger.info(f"Created incident {incident_id}: '{data.title}' [Severity: {data.severity.value}]")
        return IncidentResponse(**record)

    def get_incident(self, incident_id: UUID) -> Optional[IncidentResponse]:
        """Retrieves a single incident by its unique ID."""
        record = self.repo.get(incident_id)
        if not record:
            return None
        return IncidentResponse(**record)

    def update_incident(self, incident_id: UUID, update_data: IncidentUpdate) -> Optional[IncidentResponse]:
        """Applies partial updates to an existing incident."""
        record = self.repo.get(incident_id)
        if not record:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        now = datetime.now(timezone.utc)

        for key, value in update_dict.items():
            if value is not None:
                # Unpack enum values if necessary
                if hasattr(value, "value"):
                    record[key] = value.value
                else:
                    record[key] = value

        # Handle automatic resolution timestamp transitions
        if "status" in update_dict:
            new_status = record["status"]
            if new_status in (IncidentStatus.RESOLVED.value, IncidentStatus.CLOSED.value):
                if not record.get("resolved_at"):
                    record["resolved_at"] = now
            elif new_status in (IncidentStatus.OPEN.value, IncidentStatus.INVESTIGATING.value, IncidentStatus.IN_PROGRESS.value):
                record["resolved_at"] = None

        record["updated_at"] = now
        self.repo.save(record)
        logger.info(f"Updated incident {incident_id}: updated fields={list(update_dict.keys())}")
        return IncidentResponse(**record)

    def list_incidents(
        self,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None,
        category: Optional[IncidentCategory] = None,
        team: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> IncidentListResponse:
        """Retrieves a paginated list of incidents matching filters."""
        status_val = status.value if status else None
        severity_val = severity.value if severity else None
        category_val = category.value if category else None

        records = self.repo.list_all(
            status=status_val,
            severity=severity_val,
            category=category_val,
            team=team,
            search=search,
        )

        total = len(records)
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_records = records[start_idx:end_idx]

        items = [IncidentResponse(**r) for r in paginated_records]

        return IncidentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
