import os
import json
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from generate_synthetic_data import SYNTHETIC_SCENARIOS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DatabaseSeeder")

def prepare_seed_payload(
    processed_incidents_path: Optional[str] = None,
    synthetic_incidents_path: Optional[str] = None,
    output_seed_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Combines cleaned public/sample incident data with synthetic multimodal data
    into a standardized, validated seed fixture payload ready for database ingestion.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if processed_incidents_path is None:
        processed_incidents_path = os.path.join(base_dir, "data", "processed", "incidents_cleaned.json")
        
    if synthetic_incidents_path is None:
        synthetic_incidents_path = os.path.join(base_dir, "data", "synthetic", "synthetic_incidents.json")

    if output_seed_path is None:
        output_seed_path = os.path.join(base_dir, "data", "processed", "seed_incidents.json")

    incidents: List[Dict[str, Any]] = []

    # 1. Load cleaned real/sample incidents if available
    if os.path.exists(processed_incidents_path):
        with open(processed_incidents_path, "r", encoding="utf-8") as f:
            real_data = json.load(f)
            incidents.extend(real_data)
            logger.info(f"Loaded {len(real_data)} incidents from {processed_incidents_path}")
    else:
        logger.warning(f"No processed incidents found at {processed_incidents_path}")

    # 2. Load synthetic incidents if available, else use embedded scenarios
    if os.path.exists(synthetic_incidents_path):
        with open(synthetic_incidents_path, "r", encoding="utf-8") as f:
            synth_data = json.load(f)
            incidents.extend(synth_data)
            logger.info(f"Loaded {len(synth_data)} synthetic incidents from {synthetic_incidents_path}")
    else:
        incidents.extend(SYNTHETIC_SCENARIOS)
        logger.info(f"Appended {len(SYNTHETIC_SCENARIOS)} default synthetic scenarios.")

    # Canonical teams definition
    assignment_teams = [
        {"name": "Database", "lead_email": "db-leads@incidentiq.internal", "slack_channel": "#oncall-database"},
        {"name": "Backend", "lead_email": "backend-leads@incidentiq.internal", "slack_channel": "#oncall-backend"},
        {"name": "Frontend", "lead_email": "frontend-leads@incidentiq.internal", "slack_channel": "#oncall-frontend"},
        {"name": "DevOps", "lead_email": "devops-leads@incidentiq.internal", "slack_channel": "#oncall-devops"},
        {"name": "Infrastructure", "lead_email": "infra-leads@incidentiq.internal", "slack_channel": "#oncall-infra"},
        {"name": "Network", "lead_email": "network-leads@incidentiq.internal", "slack_channel": "#oncall-network"},
        {"name": "Security", "lead_email": "secops-leads@incidentiq.internal", "slack_channel": "#oncall-security"},
        {"name": "Cloud", "lead_email": "cloud-leads@incidentiq.internal", "slack_channel": "#oncall-cloud"},
        {"name": "Support", "lead_email": "support-leads@incidentiq.internal", "slack_channel": "#tier2-support"}
    ]

    seed_payload = {
        "metadata": {
            "total_incidents": len(incidents),
            "generated_at": pd.Timestamp.utcnow().isoformat(),
            "teams_count": len(assignment_teams)
        },
        "assignment_teams": assignment_teams,
        "incidents": incidents
    }

    os.makedirs(os.path.dirname(output_seed_path), exist_ok=True)
    with open(output_seed_path, "w", encoding="utf-8") as f:
        json.dump(seed_payload, f, indent=2, ensure_ascii=False)

    logger.info(f"Seed payload successfully written to {output_seed_path} ({len(incidents)} total incidents).")
    return seed_payload

if __name__ == "__main__":
    prepare_seed_payload()
