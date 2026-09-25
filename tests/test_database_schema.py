import os
import sys
import unittest
import asyncio

backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db.migrations.runner import SchemaValidator
from app.db.session import db_manager
from app.models.entities import (
    AssignmentTeam,
    User,
    Incident,
    Evidence,
    IncidentEvent,
    IncidentAnalysis,
    Recommendation,
    KnowledgeDocument,
    EmbeddingRecord
)

class TestDatabaseSchemaAndMigrations(unittest.TestCase):

    def setUp(self):
        self.migration_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "backend", "app", "db", "migrations", "001_initial_schema.sql"
        )

    def test_migration_file_exists(self):
        self.assertTrue(os.path.exists(self.migration_file))

    def test_schema_validator_identifies_all_required_tables(self):
        report = SchemaValidator.validate_migration(self.migration_file)
        self.assertTrue(report["is_valid"])
        self.assertEqual(len(report["missing_tables"]), 0)

        expected = [
            "assignment_teams", "users", "incidents", "evidence",
            "incident_events", "incident_analysis", "recommendations",
            "knowledge_documents", "embedding_records"
        ]
        for tbl in expected:
            self.assertIn(tbl, report["tables_found"])

    def test_vector_extension_and_hnsw_index(self):
        report = SchemaValidator.validate_migration(self.migration_file)
        self.assertTrue(report["has_vector_extension"])
        self.assertTrue(report["has_hnsw_index"])
        self.assertIn("vector", report["extensions_found"])
        self.assertIn("idx_knowledge_docs_embedding_hnsw", report["indexes_found"])

    def test_orm_models_definitions(self):
        # Verify table name bindings
        self.assertEqual(AssignmentTeam.__tablename__, "assignment_teams")
        self.assertEqual(User.__tablename__, "users")
        self.assertEqual(Incident.__tablename__, "incidents")
        self.assertEqual(Evidence.__tablename__, "evidence")
        self.assertEqual(IncidentEvent.__tablename__, "incident_events")
        self.assertEqual(IncidentAnalysis.__tablename__, "incident_analysis")
        self.assertEqual(Recommendation.__tablename__, "recommendations")
        self.assertEqual(KnowledgeDocument.__tablename__, "knowledge_documents")
        self.assertEqual(EmbeddingRecord.__tablename__, "embedding_records")

    def test_database_manager_health(self):
        health = asyncio.run(db_manager.check_health())
        self.assertTrue(health["configured"])
        self.assertEqual(health["dialect"], "postgresql")
        self.assertTrue(health["vector_enabled"])

if __name__ == "__main__":
    unittest.main()
