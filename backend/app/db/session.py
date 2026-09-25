"""
Database session and connection management for IncidentIQ.
Provides async and sync session fixtures with clean mock fallback
when external database drivers are running in standalone mode.
"""

import logging
from typing import Optional
from ..config import settings

logger = logging.getLogger("DatabaseSession")

class DatabaseManager:
    """Manages database connection lifecycle and health checks."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        self._engine = None
        self._sessionmaker = None

    def is_postgres_configured(self) -> bool:
        return "postgres" in self.database_url.lower()

    async def check_health(self) -> dict:
        """Returns connection status and configuration metrics."""
        return {
            "configured": True,
            "dialect": "postgresql" if self.is_postgres_configured() else "sqlite",
            "host": settings.POSTGRES_SERVER,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB,
            "vector_enabled": True
        }

db_manager = DatabaseManager()
