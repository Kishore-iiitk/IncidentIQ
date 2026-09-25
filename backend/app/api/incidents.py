"""
Incident Management API Endpoints.
Provides RESTful CRUD operations conforming to OpenAPI 3.1 specifications.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas.incident import (
    IncidentCategory,
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentSeverity,
    IncidentStatus,
    IncidentUpdate,
)
from ..services.incident.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


def get_incident_service() -> IncidentService:
    """Dependency provider for IncidentService."""
    return IncidentService()


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new incident",
    description="Registers a new operational incident and initializes triage workflow.",
)
async def create_incident(
    payload: IncidentCreate,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    try:
        return service.create_incident(payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create incident: {str(e)}",
        )


@router.get(
    "",
    response_model=IncidentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List incidents with filtering and pagination",
    description="Retrieves a list of incidents filtered by status, severity, category, or assignment team.",
)
async def list_incidents(
    status_filter: Optional[IncidentStatus] = Query(None, alias="status", description="Filter by status"),
    severity: Optional[IncidentSeverity] = Query(None, description="Filter by severity level"),
    category: Optional[IncidentCategory] = Query(None, description="Filter by domain category"),
    team: Optional[str] = Query(None, description="Filter by assignment team"),
    search: Optional[str] = Query(None, description="Search term in title or description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size limit"),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    return service.list_incidents(
        status=status_filter,
        severity=severity,
        category=category,
        team=team,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get incident by ID",
    description="Retrieves comprehensive details for a specific incident record.",
)
async def get_incident(
    incident_id: UUID,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    incident = service.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return incident


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update an incident",
    description="Modifies fields on an existing incident such as status, severity, team, or notes.",
)
async def update_incident(
    incident_id: UUID,
    payload: IncidentUpdate,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    updated = service.update_incident(incident_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return updated
