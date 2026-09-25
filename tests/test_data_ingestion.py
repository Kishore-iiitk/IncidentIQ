import os
import sys
import unittest
import tempfile
import json
import pandas as pd

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from incident_normalizer import (
    infer_column_mapping,
    normalize_severity,
    normalize_category,
    normalize_team,
    parse_iso_timestamp,
    normalize_incident_row
)
from inspect_dataset import inspect_dataset
from clean_incidents import clean_and_normalize_incidents
from generate_synthetic_data import generate_synthetic_incidents, SYNTHETIC_SCENARIOS
from seed_database import prepare_seed_payload

class TestIncidentDatasetIngestion(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_csv_path = os.path.join(self.temp_dir.name, "test_incidents.csv")
        
        # Create small test CSV with irregular column headers
        test_df = pd.DataFrame([
            {
                "Ticket_ID": "INC-TEST-001",
                "Short_Desc": "Redis cluster timeout",
                "Detailed_Notes": "Redis master node not responding on port 6379",
                "Category_Name": "Database / Caching",
                "Impact_Level": "Critical",
                "Assigned_Group": "db-admins",
                "State": "Closed",
                "Report_Date": "2026-03-24 10:00:00",
                "Close_Date": "2026-03-24 10:45:00",
                "Resolution_Summary": "Failed over to slave node"
            },
            {
                "Ticket_ID": "INC-TEST-002",
                "Short_Desc": "Network switch packet drop",
                "Detailed_Notes": "High error counter on interface eth0",
                "Category_Name": "Network Infrastructure",
                "Impact_Level": "2 - High",
                "Assigned_Group": "net-ops",
                "State": "In Progress",
                "Report_Date": "2026-03-24 11:00:00",
                "Close_Date": "",
                "Resolution_Summary": ""
            }
        ])
        test_df.to_csv(self.sample_csv_path, index=False)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_schema_inference_handles_unseen_headers(self):
        columns = ["Ticket_ID", "Short_Desc", "Detailed_Notes", "Category_Name", "Impact_Level", "Assigned_Group", "State", "Report_Date"]
        mapping = infer_column_mapping(columns)
        
        self.assertEqual(mapping.get("id"), "Ticket_ID")
        self.assertEqual(mapping.get("title"), "Short_Desc")
        self.assertEqual(mapping.get("description"), "Detailed_Notes")
        self.assertEqual(mapping.get("category"), "Category_Name")
        self.assertEqual(mapping.get("severity"), "Impact_Level")
        self.assertEqual(mapping.get("assignment_team"), "Assigned_Group")
        self.assertEqual(mapping.get("status"), "State")
        self.assertEqual(mapping.get("created_at"), "Report_Date")

    def test_normalization_rules(self):
        self.assertEqual(normalize_severity("critical"), "P1")
        self.assertEqual(normalize_severity("1 - High"), "P1")
        self.assertEqual(normalize_severity("medium"), "P3")
        self.assertEqual(normalize_severity("minor"), "P4")
        self.assertEqual(normalize_severity("unknown_val"), "P3")

        self.assertEqual(normalize_category("Database / Caching"), "Database")
        self.assertEqual(normalize_category("Network Infrastructure"), "Network")
        self.assertEqual(normalize_category("k8s pod errors"), "DevOps")
        self.assertEqual(normalize_category("unrecognized"), "Support")

        self.assertEqual(normalize_team("db-admins", "Database"), "Database")
        self.assertEqual(normalize_team("net-ops", "Network"), "Network")
        self.assertEqual(normalize_team(None, "Security"), "Security")

        self.assertEqual(parse_iso_timestamp("2026-03-24 10:00:00"), "2026-03-24T10:00:00Z")
        self.assertIsNone(parse_iso_timestamp(""))

    def test_dataset_inspection_profiles_accurately(self):
        report = inspect_dataset(self.sample_csv_path)
        self.assertEqual(report["total_records"], 2)
        self.assertEqual(report["total_columns"], 10)
        self.assertEqual(report["duplicate_rows"], 0)
        self.assertIn("Ticket_ID", report["columns"])
        self.assertEqual(report["inferred_mapping"]["id"], "Ticket_ID")

    def test_clean_incidents_pipeline_output(self):
        out_json = os.path.join(self.temp_dir.name, "cleaned.json")
        records = clean_and_normalize_incidents(self.sample_csv_path, output_file=out_json)
        
        self.assertEqual(len(records), 2)
        r1 = records[0]
        self.assertEqual(r1["id"], "INC-TEST-001")
        self.assertEqual(r1["severity"], "P1")
        self.assertEqual(r1["category"], "Database")
        self.assertEqual(r1["status"], "Resolved")
        self.assertEqual(r1["created_at"], "2026-03-24T10:00:00Z")
        self.assertEqual(r1["resolved_at"], "2026-03-24T10:45:00Z")
        self.assertEqual(r1["root_cause"], "Failed over to slave node")

        # Verify output file content
        self.assertTrue(os.path.exists(out_json))
        with open(out_json, "r") as f:
            data = json.load(f)
            self.assertEqual(len(data), 2)

    def test_synthetic_scenarios_validation(self):
        out_synth = os.path.join(self.temp_dir.name, "synthetic.json")
        scenarios = generate_synthetic_incidents(output_file=out_synth)
        self.assertEqual(len(scenarios), 10)
        
        for sc in scenarios:
            self.assertTrue(sc["metadata"]["is_synthetic"])
            self.assertIn(sc["severity"], ["P1", "P2", "P3", "P4"])
            self.assertIn("timeline", sc)
            self.assertIn("executive_summary", sc)
            self.assertIn("recommended_solution", sc)
            self.assertIn("root_cause", sc)

    def test_seed_database_payload_assembly(self):
        out_seed = os.path.join(self.temp_dir.name, "seed.json")
        out_cleaned = os.path.join(self.temp_dir.name, "cleaned.json")
        clean_and_normalize_incidents(self.sample_csv_path, output_file=out_cleaned)
        
        payload = prepare_seed_payload(
            processed_incidents_path=out_cleaned,
            output_seed_path=out_seed
        )
        self.assertIn("assignment_teams", payload)
        self.assertIn("incidents", payload)
        self.assertGreaterEqual(len(payload["incidents"]), 2)
        self.assertEqual(len(payload["assignment_teams"]), 9)

if __name__ == "__main__":
    unittest.main()
