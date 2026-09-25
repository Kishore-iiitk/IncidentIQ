import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from incident_normalizer import infer_column_mapping

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DatasetInspector")

def inspect_dataset(file_path: str) -> Dict[str, Any]:
    """
    Inspects a dataset file (CSV, JSON, Parquet) without permanent modification.
    Reports shape, columns, inferred types, missing counts, null percentages, duplicate count,
    and inferred column mapping to canonical IncidentIQ fields.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    logger.info(f"Inspecting file: {file_path} (Format: {ext})")

    if ext == ".csv":
        df = pd.read_csv(file_path, low_memory=False)
    elif ext in [".json", ".jsonl"]:
        df = pd.read_json(file_path, lines=(ext == ".jsonl"))
    elif ext == ".parquet":
        df = pd.read_parquet(file_path)
    else:
        # Fallback attempting CSV
        df = pd.read_csv(file_path, low_memory=False)

    num_rows, num_cols = df.shape
    columns = list(df.columns)
    
    col_profiles: Dict[str, Dict[str, Any]] = {}
    for col in columns:
        null_count = int(df[col].isna().sum())
        null_pct = round((null_count / num_rows) * 100, 2) if num_rows > 0 else 0.0
        unique_count = int(df[col].nunique(dropna=True))
        
        # Sample values
        sample_vals = [str(x) for x in df[col].dropna().head(3).tolist()]
        
        col_profiles[col] = {
            "dtype": str(df[col].dtype),
            "null_count": null_count,
            "null_percentage": null_pct,
            "unique_values": unique_count,
            "sample_values": sample_vals
        }

    duplicate_rows = int(df.duplicated().sum())
    inferred_mapping = infer_column_mapping(columns)

    report = {
        "file_path": file_path,
        "format": ext,
        "total_records": num_rows,
        "total_columns": num_cols,
        "duplicate_rows": duplicate_rows,
        "columns": col_profiles,
        "inferred_mapping": inferred_mapping
    }

    logger.info(f"Inspection complete. Records: {num_rows}, Columns: {num_cols}, Duplicates: {duplicate_rows}")
    logger.info(f"Inferred column mappings: {inferred_mapping}")
    return report

def main():
    if len(sys.argv) < 2:
        # Check standard default raw path
        default_raw = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "it_incidents.csv")
        sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "samples", "sample_incidents.csv")
        target_path = default_raw if os.path.exists(default_raw) else sample_path
    else:
        target_path = sys.argv[1]

    if not os.path.exists(target_path):
        logger.error(f"Target file does not exist: {target_path}")
        logger.info("Usage: python scripts/inspect_dataset.py <path_to_dataset_file>")
        sys.exit(1)

    report = inspect_dataset(target_path)
    print("\n" + "="*50)
    print("DATASET INSPECTION REPORT")
    print("="*50)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
