import json
import os
from datetime import datetime

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
REPO_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
RESULTS_DIR = os.path.join(REPO_DIR, "results")
DYNAMIC_DIR = os.path.join(RESULTS_DIR, "dynamic_vel_limits")
OUTPUT_DIR = os.path.join(RESULTS_DIR, "Opt_design_control_parameters", "dynamic_vel_limits")

CASE_DIRS = {
    "A": "Case_A_ll",
    "B": "Case_B_act",
    "C": "Case_C_Full_co_design",
    "BASELINE": "baseline",
}


def normalize_coeff(value):
    if value <= 1:
        return float(value)
    digits = len(str(int(round(value))))
    if digits >= 4:
        return float(value) / 10000.0
    if digits == 3:
        return float(value) / 1000.0
    if digits == 2:
        return float(value) / 100.0
    return float(value) / 10.0


def parse_coeffs_from_filename(filename):
    stem = os.path.basename(filename)
    parts = stem.split("_")
    # Expected pattern: all_<label>_<c1>_<c2>_<timestamp>_<seed>.csv
    # Coeffs are the two numeric parts immediately after the '20' token.
    for i in range(len(parts) - 2):
        if parts[i] == "20" and parts[i + 1].isdigit() and parts[i + 2].isdigit():
            c1 = float(parts[i + 1])
            c2 = float(parts[i + 2])
            return normalize_coeff(c1), normalize_coeff(c2)
    return None, None


def load_or_init_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"generated_at": None, "case": None, "entries": []}


def normalize_header_key(key):
    return key.strip().lower().replace(" ", "_")


def extract_min_cost_rows(case_key):
    case_key = case_key.strip().upper()
    if case_key not in CASE_DIRS:
        raise ValueError(f"Unknown case '{case_key}'. Use A, B, C, or baseline.")

    case_dir = os.path.join(DYNAMIC_DIR, CASE_DIRS[case_key])
    if not os.path.isdir(case_dir):
        raise FileNotFoundError(f"Case directory not found: {case_dir}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{case_key.lower()}.json")
    payload = load_or_init_json(output_path)
    payload["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload["case"] = case_key

    all_files = [
        os.path.join(case_dir, f)
        for f in os.listdir(case_dir)
        if f.startswith("all_") and f.endswith(".csv")
    ]
    all_files.sort()

    entries = []

    for csv_path in all_files:
        df = pd.read_csv(csv_path)
        if "Cost" not in df.columns:
            raise ValueError(f"Missing Cost column in {csv_path}")

        costs = pd.to_numeric(df["Cost"], errors="coerce")
        min_cost = costs.min()
        if pd.isna(min_cost):
            raise ValueError(f"All Cost values are NaN in {csv_path}")

        min_mask = np.isclose(costs, min_cost, atol=1e-16, rtol=1e-16)
        min_rows = df[min_mask]

        if len(min_rows) > 5:
            print(f"Warning: {os.path.basename(csv_path)} has {len(min_rows)} rows with min cost.")

        selected_row = min_rows.iloc[0].to_dict()
        normalized_row = {
            normalize_header_key(k): v for k, v in selected_row.items()
        }
        coeff1, coeff2 = parse_coeffs_from_filename(csv_path)

        entry = {
            "coeff1": coeff1,
            "coeff2": coeff2,
            "source_file": os.path.basename(csv_path),
            "min_cost": float(min_cost),
            **normalized_row,
        }
        entries.append(entry)

    payload["entries"] = entries

    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Saved {len(entries)} entries to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract min-cost entries per coeff CSV.")
    parser.add_argument("case", help="Case: A, B, C, or baseline")
    args = parser.parse_args()

    extract_min_cost_rows(args.case)