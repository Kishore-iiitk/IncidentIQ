"""
Structured logging configuration for IncidentIQ.
Provides standardized formatting and audit trails for operations.
"""

import logging
import sys

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configures structured console logging for the IncidentIQ platform."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    logger = logging.getLogger("incidentiq")
    logger.setLevel(numeric_level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

logger = setup_logging()
