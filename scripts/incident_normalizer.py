import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("IncidentNormalizer")

# Canonical severity mapping
SEVERITY_MAPPINGS = {
    "1": "P1", "p1": "P1", "critical": "P1", "high": "P2", "2": "P2", "p2": "P2",
    "medium": "P3", "moderate": "P3", "3": "P3", "p3": "P3", "low": "P4", "minor": "P4", "4": "P4", "p4": "P4"
}

# Canonical category mapping
CATEGORY_MAPPINGS = {
    "db": "Database", "database": "Database", "sql": "Database", "postgres": "Database",
    "network": "Network", "net": "Network", "connectivity": "Network", "dns": "Network",
    "security": "Security", "sec": "Security", "auth": "Security", "breach": "Security",
    "devops": "DevOps", "infra": "Infrastructure", "infrastructure": "Infrastructure",
    "k8s": "DevOps", "kubernetes": "DevOps", "cloud": "Cloud",
    "backend": "Backend", "api": "Backend", "service": "Backend", "server": "Backend",
    "frontend": "Frontend", "ui": "Frontend", "client": "Frontend", "web": "Frontend",
    "support": "Support", "general": "Support", "hardware": "Infrastructure"
}

# Canonical team mapping
TEAM_MAPPINGS = {
    "db": "Database", "database": "Database",
    "network": "Network", "net": "Network",
    "sec": "Security", "security": "Security",
    "devops": "DevOps", "sre": "DevOps", "infra": "Infrastructure", "infrastructure": "Infrastructure",
    "backend": "Backend", "core": "Backend",
    "frontend": "Frontend", "ui": "Frontend",
    "support": "Support", "it support": "Support", "helpdesk": "Support", "cloud": "Cloud"
}

def parse_iso_timestamp(val: Any) -> Optional[str]:
    """Parse various timestamp representations into ISO-8601 UTC string."""
    if val is None or pd.isna(val) or str(val).strip() == "":
        return None
    try:
        dt = pd.to_datetime(val, utc=True)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        # Fallback manual parsing if needed
        return None

def normalize_severity(val: Any) -> str:
    """Normalize severity into canonical P1, P2, P3, P4. Default to P3 if unknown."""
    if val is None or pd.isna(val):
        return "P3"
    s = str(val).strip().lower()
    if s in SEVERITY_MAPPINGS:
        return SEVERITY_MAPPINGS[s]
    # Check prefixes or substring indicators
    if s.startswith("1") or "crit" in s:
        return "P1"
    if s.startswith("2") or "high" in s:
        return "P2"
    if s.startswith("3") or "med" in s or "mod" in s:
        return "P3"
    if s.startswith("4") or "low" in s or "minor" in s:
        return "P4"
    return "P3"

def normalize_category(val: Any) -> str:
    """Normalize category into canonical taxonomy."""
    if val is None or pd.isna(val):
        return "Support"
    s = str(val).strip().lower()
    for k, v in CATEGORY_MAPPINGS.items():
        if k in s:
            return v
    return "Support"

def normalize_team(val: Any, category: str = "Support") -> str:
    """Normalize assignment team."""
    if val is not None and not pd.isna(val) and str(val).strip() != "":
        s = str(val).strip().lower()
        for k, v in TEAM_MAPPINGS.items():
            if k in s:
                return v
    # Fallback to category-based team assignment
    category_to_team = {
        "Database": "Database",
        "Network": "Network",
        "Security": "Security",
        "DevOps": "DevOps",
        "Infrastructure": "Infrastructure",
        "Backend": "Backend",
        "Frontend": "Frontend",
        "Cloud": "Cloud",
        "Support": "Support"
    }
    return category_to_team.get(category, "Support")

def infer_column_mapping(columns: List[str]) -> Dict[str, str]:
    """
    Programmatically infer which column maps to which standard field.
    Handles varied schema names without hardcoding rigid expectations.
    """
    col_lower = {c.lower().strip().replace(" ", "_").replace("-", "_"): c for c in columns}
    
    mapping: Dict[str, str] = {}
    
    def find_match(candidates: List[str]) -> Optional[str]:
        # Exact candidate match
        for cand in candidates:
            if cand in col_lower:
                return col_lower[cand]
        # Substring search in column name
        for cand in candidates:
            for k, orig in col_lower.items():
                if cand in k:
                    return orig
        return None

    # Title / Summary / Short Description
    title_match = find_match(["short_description", "short_desc", "summary", "subject", "headline", "title"])
    if title_match:
        mapping["title"] = title_match

    # Full Description / Details / Symptoms
    desc_match = find_match(["detailed_notes", "description", "details", "notes", "symptoms", "body"])
    if desc_match and desc_match != mapping.get("title"):
        mapping["description"] = desc_match
    elif "title" in mapping and "description" not in mapping:
        mapping["description"] = mapping["title"]
    elif "description" in mapping and "title" not in mapping:
        mapping["title"] = mapping["description"]

    # ID
    id_match = find_match(["ticket_id", "incident_id", "number", "id", "ticket_number", "key"])
    if id_match:
        mapping["id"] = id_match

    # Severity / Priority / Urgency / Impact
    sev_match = find_match(["severity", "impact_level", "priority", "urgency", "impact"])
    if sev_match:
        mapping["severity"] = sev_match

    # Category / Type / Subcategory
    cat_match = find_match(["category_name", "category", "subcategory", "type", "classification"])
    if cat_match:
        mapping["category"] = cat_match

    # Affected Systems / Configuration Item / CI / Service
    sys_match = find_match(["cmdb_ci", "configuration_item", "service", "affected_system", "system", "component", "application"])
    if sys_match:
        mapping["affected_systems"] = sys_match

    # Assignment Team / Group / Assignee
    team_match = find_match(["assigned_group", "assignment_group", "assigned_to", "team", "group", "owner_group"])
    if team_match:
        mapping["assignment_team"] = team_match

    # Status / State
    status_match = find_match(["state", "incident_state", "status", "stage"])
    if status_match:
        mapping["status"] = status_match

    # Timestamps
    created_match = find_match(["opened_at", "report_date", "created_at", "open_time", "creation_date", "timestamp"])
    if created_match:
        mapping["created_at"] = created_match

    resolved_match = find_match(["close_date", "closed_at", "resolved_at", "close_time", "resolution_date", "end_time"])
    if resolved_match:
        mapping["resolved_at"] = resolved_match

    updated_match = find_match(["sys_updated_at", "updated_at", "modified_date", "last_modified"])
    if updated_match:
        mapping["updated_at"] = updated_match

    # Root Cause / Close Notes / Resolution
    rc_match = find_match(["resolution_summary", "close_notes", "resolution_notes", "root_cause", "solution", "cause"])
    if rc_match:
        mapping["root_cause"] = rc_match

    return mapping

def normalize_incident_row(row: pd.Series, mapping: Dict[str, str], is_synthetic: bool = False) -> Dict[str, Any]:
    """
    Transforms a single source row into a canonical IncidentIQ incident record.
    """
    raw_id = str(row[mapping["id"]]).strip() if "id" in mapping and not pd.isna(row.get(mapping["id"])) else str(uuid.uuid4())
    
    title = str(row[mapping["title"]]).strip() if "title" in mapping and not pd.isna(row.get(mapping["title"])) else "Untitled Incident"
    if title == "" or title.lower() == "nan":
        title = "Untitled Incident"

    description = str(row[mapping["description"]]).strip() if "description" in mapping and not pd.isna(row.get(mapping["description"])) else title
    if description == "" or description.lower() == "nan":
        description = title

    raw_severity = row.get(mapping.get("severity")) if "severity" in mapping else None
    severity = normalize_severity(raw_severity)

    raw_category = row.get(mapping.get("category")) if "category" in mapping else None
    category = normalize_category(raw_category)

    raw_team = row.get(mapping.get("assignment_team")) if "assignment_team" in mapping else None
    assignment_team = normalize_team(raw_team, category)

    # Status
    raw_status = str(row.get(mapping.get("status"), "Open")).strip().capitalize() if "status" in mapping else "Open"
    if raw_status.lower() in ["closed", "resolved", "complete", "finished"]:
        status = "Resolved"
    else:
        status = "Open"

    # Affected Systems
    affected_systems: List[str] = []
    if "affected_systems" in mapping and not pd.isna(row.get(mapping["affected_systems"])):
        sys_val = str(row.get(mapping["affected_systems"])).strip()
        if sys_val and sys_val.lower() != "nan":
            # Split if comma-separated
            affected_systems = [s.strip() for s in sys_val.replace(";", ",").split(",") if s.strip()]
    if not affected_systems:
        affected_systems = [f"{category.lower()}-service"]

    # Timestamps
    created_at = parse_iso_timestamp(row.get(mapping.get("created_at"))) if "created_at" in mapping else None
    if not created_at:
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    resolved_at = parse_iso_timestamp(row.get(mapping.get("resolved_at"))) if "resolved_at" in mapping else None
    updated_at = parse_iso_timestamp(row.get(mapping.get("updated_at"))) if "updated_at" in mapping else created_at

    root_cause = str(row.get(mapping.get("root_cause"))).strip() if "root_cause" in mapping and not pd.isna(row.get(mapping["root_cause"])) else None
    if root_cause and root_cause.lower() == "nan":
        root_cause = None

    # Construct clean standardized incident
    record: Dict[str, Any] = {
        "id": raw_id,
        "title": title,
        "description": description,
        "status": status,
        "severity": severity,
        "priority": severity,
        "category": category,
        "affected_systems": affected_systems,
        "assignment_team": assignment_team,
        "source": "kaggle_it_incident" if not is_synthetic else "synthetic_multimodal",
        "created_at": created_at,
        "updated_at": updated_at or created_at,
        "resolved_at": resolved_at,
        "confidence": 0.85 if is_synthetic else 0.75,
        "root_cause": root_cause,
        "recommended_solution": f"Remediate {category} component following standard runbook." if not root_cause else f"Applied fix: {root_cause}",
        "executive_summary": f"Incident {raw_id} affecting {', '.join(affected_systems)} classified as {severity} ({category}).",
        "bug_report": None,
        "timeline": [
            {
                "timestamp": created_at,
                "event": "Incident opened and assigned to " + assignment_team,
                "is_approximate": False
            }
        ],
        "metadata": {
            "is_synthetic": is_synthetic,
            "raw_fields": {k: str(v) for k, v in row.items() if not pd.isna(v)}
        }
    }

    if resolved_at:
        record["timeline"].append({
            "timestamp": resolved_at,
            "event": "Incident resolved.",
            "is_approximate": False
        })

    return record
