import os
import re
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MigrationRunner")

class SchemaValidator:
    """
    Validates SQL migration files, parses table definitions, foreign keys,
    indices, and vector extensions, and validates database readiness.
    """

    @staticmethod
    def load_migration_sql(file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Migration script not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def extract_created_tables(sql_content: str) -> List[str]:
        pattern = re.compile(r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
        return pattern.findall(sql_content)

    @staticmethod
    def extract_created_indexes(sql_content: str) -> List[str]:
        pattern = re.compile(r"CREATE\s+INDEX(?:\s+IF\s+NOT\s+EXISTS)?\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
        return pattern.findall(sql_content)

    @staticmethod
    def extract_extensions(sql_content: str) -> List[str]:
        pattern = re.compile(r'CREATE\s+EXTENSION(?:\s+IF\s+NOT\s+EXISTS)?\s+["\']?([a-zA-Z0-9_-]+)["\']?', re.IGNORECASE)
        return pattern.findall(sql_content)

    @classmethod
    def validate_migration(cls, file_path: str) -> Dict[str, Any]:
        sql = cls.load_migration_sql(file_path)
        tables = cls.extract_created_tables(sql)
        indexes = cls.extract_created_indexes(sql)
        extensions = cls.extract_extensions(sql)

        expected_tables = {
            "assignment_teams", "users", "incidents", "evidence",
            "incident_events", "incident_analysis", "recommendations",
            "knowledge_documents", "embedding_records"
        }

        missing_tables = expected_tables - set(tables)
        has_vector_ext = "vector" in extensions
        has_hnsw_index = "idx_knowledge_docs_embedding_hnsw" in indexes

        is_valid = (len(missing_tables) == 0) and has_vector_ext and has_hnsw_index

        result = {
            "file": file_path,
            "is_valid": is_valid,
            "tables_found": tables,
            "missing_tables": list(missing_tables),
            "indexes_found": indexes,
            "extensions_found": extensions,
            "has_vector_extension": has_vector_ext,
            "has_hnsw_index": has_hnsw_index
        }
        logger.info(f"Migration validation for {file_path}: Valid={is_valid}, Tables={len(tables)}, Indexes={len(indexes)}")
        return result
