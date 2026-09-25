import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from incident_normalizer import infer_column_mapping, normalize_incident_row

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("IncidentCleaner")

def clean_and_normalize_incidents(
    input_file: str,
    output_file: Optional[str] = None,
    is_synthetic: bool = False,
    deduplicate: bool = True
) -> List[Dict[str, Any]]:
    """
    Cleans, deduplicates, normalizes timestamps, categories, severities,
    and maps source rows into canonical IncidentIQ JSON records.
    Never alters the raw dataset in-place.
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    ext = os.path.splitext(input_file)[1].lower()
    logger.info(f"Loading raw incident dataset: {input_file}")

    if ext == ".csv":
        df = pd.read_csv(input_file, low_memory=False)
    elif ext in [".json", ".jsonl"]:
        df = pd.read_json(input_file, lines=(ext == ".jsonl"))
    elif ext == ".parquet":
        df = pd.read_parquet(input_file)
    else:
        df = pd.read_csv(input_file, low_memory=False)

    initial_count = len(df)
    logger.info(f"Loaded {initial_count} raw records.")

    # Deduplicate if requested
    if deduplicate:
        df = df.drop_duplicates()
        dedup_count = len(df)
        logger.info(f"Deduplication removed {initial_count - dedup_count} identical records. {dedup_count} remaining.")

    columns = list(df.columns)
    mapping = infer_column_mapping(columns)
    logger.info(f"Applied inferred mapping: {mapping}")

    cleaned_records: List[Dict[str, Any]] = []
    
    # Track unique IDs to avoid primary key collisions
    seen_ids = set()

    for idx, row in df.iterrows():
        try:
            record = normalize_incident_row(row, mapping, is_synthetic=is_synthetic)
            inc_id = record["id"]
            if inc_id in seen_ids:
                # Add suffix to preserve uniqueness
                inc_id = f"{inc_id}-{idx}"
                record["id"] = inc_id
            seen_ids.add(inc_id)
            cleaned_records.append(record)
        except Exception as e:
            logger.warning(f"Error parsing row {idx}: {e}")

    logger.info(f"Successfully cleaned and standardized {len(cleaned_records)} incidents.")

    # Output file handling
    if output_file is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_file = os.path.join(base_dir, "data", "processed", "incidents_cleaned.json")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, indent=2, ensure_ascii=False)

    logger.info(f"Cleaned incident dataset written to: {output_file}")
    return cleaned_records

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_input = os.path.join(base_dir, "data", "raw", "it_incidents.csv")
    sample_input = os.path.join(base_dir, "data", "samples", "sample_incidents.csv")
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else (default_input if os.path.exists(default_input) else sample_input)
    output_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join(base_dir, "data", "processed", "incidents_cleaned.json")

    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)

    clean_and_normalize_incidents(input_file=input_file, output_file=output_file)

if __name__ == "__main__":
    main()
