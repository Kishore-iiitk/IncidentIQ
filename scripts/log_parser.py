import os
import re
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LogParser")

# Standard LogHub / System Log Regex Patterns
LOG_PATTERNS = {
    # HDFS: "081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block..."
    "HDFS": re.compile(
        r"^(?P<date>\d{6})\s+(?P<time>\d{6})\s+(?P<pid>\d+)\s+(?P<level>INFO|WARN|ERROR|FATAL|DEBUG)\s+(?P<component>[^:]+):\s+(?P<message>.*)$"
    ),
    # OpenStack: "2026-03-24 10:14:02.124 1024 INFO nova.osapi_compute [req-...] message"
    "OPENSTACK": re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(?P<pid>\d+)\s+(?P<level>INFO|WARNING|WARN|ERROR|CRITICAL|DEBUG)\s+(?P<component>\S+)(?:\s+\[(?P<request_id>[^\]]+)\])?\s+(?P<message>.*)$"
    ),
    # BGL: "- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.675872 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction cache parity error..."
    "BGL": re.compile(
        r"^(?P<alert_tag>[-+])\s+(?P<epoch>\d+)\s+(?P<date>\S+)\s+(?P<node>\S+)\s+(?P<timestamp>\d{4}-\d{2}-\d{2}-\d{2}\.\d{2}\.\d{2}\.\d+)\s+(?P<location>\S+)\s+(?P<subsystem>\S+)\s+(?P<category>\S+)\s+(?P<level>INFO|WARN|WARNING|ERROR|FATAL|SEVERE|DEBUG)\s+(?P<message>.*)$"
    ),
    # Apache: "[Sun Mar 22 06:28:45 2026] [error] [client 192.168.1.108:54322] Script timed out..."
    "APACHE": re.compile(
        r"^\[(?P<timestamp>[^\]]+)\]\s+\[(?P<level>[^\]]+)\](?:\s+\[client\s+(?P<client>[^\]]+)\])?\s+(?P<message>.*)$"
    ),
    # Generic Syslog / Standard Timestamp Log: "2026-03-24T10:00:00Z [ERROR] component: message"
    "GENERIC": re.compile(
        r"^(?:\[?(?P<timestamp>\d{4}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\]?\s+)?(?:\[?(?P<level>INFO|WARN|WARNING|ERROR|CRITICAL|FATAL|DEBUG|NOTICE|EMERG)\]?:?\s+)?(?:(?P<component>[A-Za-z0-9_.-]+(?:\([^)]+\))?):?\s+)?(?P<message>.+)$",
        re.IGNORECASE
    )
}

SEVERITY_LEVEL_MAP = {
    "FATAL": "CRITICAL",
    "CRIT": "CRITICAL",
    "CRITICAL": "CRITICAL",
    "EMERG": "CRITICAL",
    "ERROR": "ERROR",
    "ERR": "ERROR",
    "SEVERE": "ERROR",
    "WARN": "WARNING",
    "WARNING": "WARNING",
    "NOTICE": "INFO",
    "INFO": "INFO",
    "DEBUG": "DEBUG"
}

def normalize_log_level(level: Optional[str]) -> str:
    """Normalizes raw log level to standard set: DEBUG, INFO, WARNING, ERROR, CRITICAL."""
    if not level:
        return "INFO"
    clean = level.strip().upper()
    return SEVERITY_LEVEL_MAP.get(clean, "INFO")

def parse_hdfs_timestamp(date_str: str, time_str: str) -> Optional[str]:
    """Parse HDFS timestamp e.g. '081109' '203518' -> ISO-8601 UTC."""
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%y%m%d %H%M%S").replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

def parse_bgl_timestamp(ts_str: str) -> Optional[str]:
    """Parse BGL timestamp e.g. '2005-06-03-15.42.50.675872' -> ISO-8601 UTC."""
    try:
        # Format: YYYY-MM-DD-HH.MM.SS.microseconds
        dt = datetime.strptime(ts_str, "%Y-%m-%d-%H.%M.%S.%f").replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

def parse_apache_timestamp(ts_str: str) -> Optional[str]:
    """Parse Apache timestamp e.g. 'Sun Mar 22 06:28:45 2026' -> ISO-8601 UTC."""
    try:
        # Strip weekday if present
        parts = ts_str.split()
        if len(parts) >= 4 and len(parts[0]) == 3:
            # "Sun Mar 22 06:28:45 2026"
            dt = datetime.strptime(ts_str, "%a %b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    try:
        # Fallback to dateutil/pandas if needed
        import pandas as pd
        return pd.to_datetime(ts_str, utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

def parse_openstack_timestamp(ts_str: str) -> Optional[str]:
    """Parse OpenStack timestamp e.g. '2026-03-24 10:14:02.124' -> ISO-8601 UTC."""
    try:
        import pandas as pd
        return pd.to_datetime(ts_str, utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

def parse_log_line(line: str, format_hint: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Parses a single log line into a normalized log-event dictionary.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # Check format_hint first if provided
    detected_format = None
    match = None

    if format_hint and format_hint.upper() in LOG_PATTERNS:
        pattern = LOG_PATTERNS[format_hint.upper()]
        m = pattern.match(line)
        if m:
            detected_format = format_hint.upper()
            match = m

    # Autodetect format if not matched
    if not match:
        for fmt, pattern in LOG_PATTERNS.items():
            if fmt == "GENERIC":
                continue
            m = pattern.match(line)
            if m:
                detected_format = fmt
                match = m
                break

    # Fallback to GENERIC
    if not match:
        m = LOG_PATTERNS["GENERIC"].match(line)
        if m:
            detected_format = "GENERIC"
            match = m
        else:
            return {
                "id": str(uuid.uuid4()),
                "timestamp": None,
                "is_approximate": True,
                "level": "INFO",
                "source_format": "RAW",
                "component": "unknown",
                "message": line,
                "is_anomaly": False
            }

    data = match.groupdict()
    timestamp = None
    level = normalize_log_level(data.get("level"))
    component = data.get("component") or "system"
    message = data.get("message") or line

    if detected_format == "HDFS":
        timestamp = parse_hdfs_timestamp(data.get("date", ""), data.get("time", ""))
    elif detected_format == "OPENSTACK":
        timestamp = parse_openstack_timestamp(data.get("timestamp", ""))
        component = data.get("component", "openstack")
    elif detected_format == "BGL":
        timestamp = parse_bgl_timestamp(data.get("timestamp", ""))
        component = f"{data.get('subsystem', 'RAS')}:{data.get('location', 'node')}"
    elif detected_format == "APACHE":
        timestamp = parse_apache_timestamp(data.get("timestamp", ""))
        component = "apache-httpd"
    elif detected_format == "GENERIC":
        raw_ts = data.get("timestamp")
        if raw_ts:
            try:
                import pandas as pd
                timestamp = pd.to_datetime(raw_ts, utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                timestamp = None

    # Check anomaly indicators
    is_anomaly = level in ["ERROR", "CRITICAL"] or any(
        kw in message.lower() for kw in ["exception", "timeout", "exhausted", "oomkilled", "fatal", "fail", "corrupt"]
    )

    return {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "is_approximate": (timestamp is None),
        "level": level,
        "source_format": detected_format,
        "component": component.strip(),
        "message": message.strip(),
        "is_anomaly": is_anomaly,
        "metadata": {k: v for k, v in data.items() if k not in ["message", "level", "timestamp"] and v is not None}
    }

def detect_log_source_format(sample_lines: List[str]) -> str:
    """Detects the primary log source format (HDFS, OPENSTACK, BGL, APACHE, GENERIC) from log samples."""
    scores = {"HDFS": 0, "OPENSTACK": 0, "BGL": 0, "APACHE": 0, "GENERIC": 0}
    for line in sample_lines:
        line = line.strip()
        if not line:
            continue
        for fmt, pat in LOG_PATTERNS.items():
            if pat.match(line):
                scores[fmt] += 1
                break
    best_fmt = max(scores, key=scores.get)
    return best_fmt if scores[best_fmt] > 0 else "GENERIC"
