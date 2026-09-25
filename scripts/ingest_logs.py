import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from log_parser import parse_log_line, detect_log_source_format

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LogIngester")

def ingest_log_file(
    file_path: str,
    output_path: Optional[str] = None,
    format_hint: Optional[str] = None,
    max_lines: Optional[int] = None
) -> Dict[str, Any]:
    """
    Ingests an operational log file, parses log events into normalized structures,
    detects anomalies, and structures the event stream chronologically.
    Never misrepresents raw log events as incident tickets.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Log file not found: {file_path}")

    logger.info(f"Ingesting log stream from: {file_path}")
    
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = [line for line in f if line.strip()]

    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]

    total_lines = len(lines)
    logger.info(f"Read {total_lines} raw log lines.")

    # Detect format if not explicitly provided
    detected_format = format_hint or detect_log_source_format(lines[:20])
    logger.info(f"Applying log format parser: {detected_format}")

    parsed_events: List[Dict[str, Any]] = []
    level_counts: Dict[str, int] = {}
    anomalies_count = 0

    for idx, line in enumerate(lines):
        event = parse_log_line(line, format_hint=detected_format)
        if event:
            event["line_number"] = idx + 1
            parsed_events.append(event)
            lvl = event["level"]
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
            if event["is_anomaly"]:
                anomalies_count += 1

    # Chronological sort for events with timestamps
    timestamped_events = [e for e in parsed_events if e["timestamp"] is not None]
    untimestamped_events = [e for e in parsed_events if e["timestamp"] is None]
    timestamped_events.sort(key=lambda x: x["timestamp"])
    sorted_events = timestamped_events + untimestamped_events

    summary = {
        "source_file": file_path,
        "detected_format": detected_format,
        "total_lines": total_lines,
        "parsed_events_count": len(parsed_events),
        "level_breakdown": level_counts,
        "anomalies_detected": anomalies_count,
        "time_range": {
            "start": timestamped_events[0]["timestamp"] if timestamped_events else None,
            "end": timestamped_events[-1]["timestamp"] if timestamped_events else None
        }
    }

    payload = {
        "summary": summary,
        "events": sorted_events
    }

    if output_path is None:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(base_dir, "data", "processed", f"{base_name}_events.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info(f"Log stream ingestion complete. {len(parsed_events)} events written to {output_path} (Anomalies: {anomalies_count})")
    return payload

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samples_dir = os.path.join(base_dir, "data", "samples", "loghub")
    
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        out_file = sys.argv[2] if len(sys.argv) > 2 else None
        ingest_log_file(target_file, output_path=out_file)
    else:
        # Ingest all sample logs if present
        if os.path.exists(samples_dir):
            for fname in os.listdir(samples_dir):
                if fname.endswith(".log") or fname.endswith(".txt"):
                    fpath = os.path.join(samples_dir, fname)
                    ingest_log_file(fpath)
        else:
            logger.info("Usage: python scripts/ingest_logs.py <path_to_logfile> [optional_output_json]")

if __name__ == "__main__":
    main()
