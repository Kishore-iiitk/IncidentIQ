"""
Unit and API integration tests for Incident Management endpoints and services.
Validates schemas, status codes, state transitions, filtering, and pagination.
"""

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.incident import (
    IncidentCategory,
    IncidentCreate,
    IncidentSeverity,
    IncidentStatus,
    IncidentUpdate,
)
from backend.app.services.incident.incident_service import IncidentRepository, IncidentService, _repository


@pytest.fixture(autouse=True)
def clean_repository():
    """Ensure a clean in-memory repository for each test."""
    _repository.clear()
    yield
    _repository.clear()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoints."""

    def test_health_check(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "IncidentIQ"

    def test_api_health_check(self, client: TestClient):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestIncidentAPI:
    """API endpoint tests for /api/incidents."""

    def test_create_incident_success(self, client: TestClient):
        payload = {
            "title": "Payment Gateway 504 Timeouts",
            "description": "Nginx upstream timed out during checkout transactions.",
            "severity": "P1",
            "priority": "P1",
            "category": "API Service",
            "affected_systems": ["payment-service", "nginx-gateway"],
            "assignment_team": "Backend",
            "source": "monitoring",
            "metadata": {"cluster": "prod-us-east-1"},
        }
        response = client.post("/api/incidents", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["status"] == "Open"
        assert data["severity"] == "P1"
        assert data["confidence"] == 1.0
        assert data["affected_systems"] == ["payment-service", "nginx-gateway"]
        assert "id" in data
        assert "created_at" in data
        assert data["resolved_at"] is None

    def test_create_incident_validation_failure(self, client: TestClient):
        # Blank title
        payload = {
            "title": "   ",
            "description": "Valid description for testing",
        }
        response = client.post("/api/incidents", json=payload)
        assert response.status_code == 422

        # Invalid severity
        payload2 = {
            "title": "Valid Title",
            "description": "Valid description for testing",
            "severity": "P99_INVALID",
        }
        response2 = client.post("/api/incidents", json=payload2)
        assert response2.status_code == 422

    def test_get_incident_by_id(self, client: TestClient):
        # Create an incident first
        payload = {
            "title": "Postgres High CPU",
            "description": "Database query lock saturation detected.",
            "severity": "P2",
            "category": "Database",
        }
        create_resp = client.post("/api/incidents", json=payload)
        incident_id = create_resp.json()["id"]

        # Fetch by ID
        get_resp = client.get(f"/api/incidents/{incident_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == incident_id
        assert get_resp.json()["title"] == "Postgres High CPU"

    def test_get_incident_not_found(self, client: TestClient):
        random_id = str(uuid4())
        response = client.get(f"/api/incidents/{random_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_patch_incident_fields(self, client: TestClient):
        # Create
        create_resp = client.post(
            "/api/incidents",
            json={"title": "Redis Outage", "description": "Cache cluster node unreachable."},
        )
        incident_id = create_resp.json()["id"]

        # Update assignment and severity
        patch_payload = {
            "assignment_team": "DevOps",
            "severity": "P1",
            "status": "Investigating",
        }
        patch_resp = client.patch(f"/api/incidents/{incident_id}", json=patch_payload)
        assert patch_resp.status_code == 200
        updated = patch_resp.json()
        assert updated["assignment_team"] == "DevOps"
        assert updated["severity"] == "P1"
        assert updated["status"] == "Investigating"

    def test_incident_resolution_lifecycle(self, client: TestClient):
        # Create
        create_resp = client.post(
            "/api/incidents",
            json={"title": "DNS Flapping", "description": "CoreDNS pods restarting."},
        )
        incident_id = create_resp.json()["id"]
        assert create_resp.json()["resolved_at"] is None

        # Resolve
        resolve_resp = client.patch(
            f"/api/incidents/{incident_id}",
            json={"status": "Resolved", "root_cause": "ConfigMap syntax error"},
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["resolved_at"] is not None
        assert resolve_resp.json()["root_cause"] == "ConfigMap syntax error"

        # Reopen
        reopen_resp = client.patch(
            f"/api/incidents/{incident_id}",
            json={"status": "Open"},
        )
        assert reopen_resp.status_code == 200
        assert reopen_resp.json()["resolved_at"] is None

    def test_list_incidents_filtering_and_pagination(self, client: TestClient):
        # Seed 3 incidents
        client.post(
            "/api/incidents",
            json={"title": "Incident Alpha", "description": "Database issue", "severity": "P1", "category": "Database", "assignment_team": "Database"},
        )
        client.post(
            "/api/incidents",
            json={"title": "Incident Beta", "description": "Network latency", "severity": "P2", "category": "Network", "assignment_team": "Network"},
        )
        client.post(
            "/api/incidents",
            json={"title": "Incident Gamma", "description": "API Gateway error", "severity": "P1", "category": "API Service", "assignment_team": "Backend"},
        )

        # List all
        resp_all = client.get("/api/incidents")
        assert resp_all.status_code == 200
        assert resp_all.json()["total"] == 3
        assert len(resp_all.json()["items"]) == 3

        # Filter by severity=P1
        resp_p1 = client.get("/api/incidents?severity=P1")
        assert resp_p1.status_code == 200
        assert resp_p1.json()["total"] == 2

        # Filter by category=Network
        resp_net = client.get("/api/incidents?category=Network")
        assert resp_net.status_code == 200
        assert resp_net.json()["total"] == 1
        assert resp_net.json()["items"][0]["title"] == "Incident Beta"

        # Search query
        resp_search = client.get("/api/incidents?search=Gateway")
        assert resp_search.status_code == 200
        assert resp_search.json()["total"] == 1
        assert resp_search.json()["items"][0]["title"] == "Incident Gamma"

        # Pagination: page_size=2
        resp_page1 = client.get("/api/incidents?page=1&page_size=2")
        assert resp_page1.status_code == 200
        assert len(resp_page1.json()["items"]) == 2
        assert resp_page1.json()["total_pages"] == 2


class TestIncidentServiceUnit:
    """Direct unit tests for the IncidentService class."""

    def test_service_crud(self):
        repo = IncidentRepository()
        service = IncidentService(repo=repo)

        # Create
        created = service.create_incident(
            IncidentCreate(
                title="Service Unit Test",
                description="Testing service logic directly",
                severity=IncidentSeverity.P2,
                category=IncidentCategory.STORAGE,
            )
        )
        assert created.title == "Service Unit Test"
        assert created.status == IncidentStatus.OPEN

        # Retrieve
        fetched = service.get_incident(created.id)
        assert fetched is not None
        assert fetched.id == created.id

        # Update
        updated = service.update_incident(
            created.id,
            IncidentUpdate(title="Updated Title", status=IncidentStatus.INVESTIGATING),
        )
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.status == IncidentStatus.INVESTIGATING
