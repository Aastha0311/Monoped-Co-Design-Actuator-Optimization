import argparse
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd


def normalize_header_key(key):
    return key.strip().lower().replace(" ", "_")


def build_column_map(columns):
    mapping = {}
    for col in columns:
        key = normalize_header_key(col)
        if key not in mapping:
            mapping[key] = col
    return mapping


def find_cost_column(columns):
    normalized = [(col, normalize_header_key(col)) for col in columns]
    for col, key in normalized:
        if key == "cost":
            return col
    for col, key in normalized:
        if key.endswith("_cost"):
            return col
    for col, key in normalized:
        if "cost" in key:
            return col
    return None


def extract_min_cost_row(csv_path):
    df = pd.read_csv(csv_path)
    cost_col = find_cost_column(df.columns)
    if cost_col is None:
        raise ValueError(f"Missing Cost column in {csv_path}")

    costs = pd.to_numeric(df[cost_col], errors="coerce")
    min_cost = costs.min()
    if pd.isna(min_cost):
        raise ValueError(f"All Cost values are NaN in {csv_path}")

    min_mask = np.isclose(costs, min_cost, atol=1e-16, rtol=1e-16)
    min_rows = df[min_mask]

    if len(min_rows) > 5:
        print(f"Warning: {os.path.basename(csv_path)} has {len(min_rows)} rows with min cost.")

    selected_row = min_rows.iloc[0].to_dict()

    return float(min_cost), selected_row, df


def default_match_columns(best_map, all_map):
    common = set(best_map.keys()) & set(all_map.keys())
    filtered = [
        key
        for key in sorted(common)
        if "cost" not in key and key not in {"best_index"}
    ]
    return filtered


def match_all_row(all_df, all_map, best_row, best_map, match_cols, tol):
    if not match_cols:
        raise ValueError("No matching columns available between best and all files.")

    mask = pd.Series(True, index=all_df.index)
    for key in match_cols:
        all_col = all_map[key]
        best_col = best_map[key]
        best_val = best_row[best_col]
        all_series = all_df[all_col]

        best_num = pd.to_numeric(pd.Series([best_val]), errors="coerce").iloc[0]
        all_num = pd.to_numeric(all_series, errors="coerce")

        if not pd.isna(best_num) and all_num.notna().any():
            mask &= np.isclose(all_num, best_num, atol=tol, rtol=tol)
        else:
            mask &= all_series.astype(str) == str(best_val)

    matches = all_df[mask]
    if matches.empty:
        raise ValueError("No matching row found in all file for best-file minimum.")

    if len(matches) > 1:
        print(f"Warning: {len(matches)} matching rows in all file; using the first.")

    return matches.iloc[0].to_dict()


def compare_all_and_best(all_csv, best_csv=None, output_path=None, match_cols=None, tol=1e-9):
    if not os.path.isfile(all_csv):
        raise FileNotFoundError(f"All file not found: {all_csv}")
    min_all, row_all, all_df = extract_min_cost_row(all_csv)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "all_file": os.path.abspath(all_csv),
        "all_min_cost": min_all,
        "all_min_row": row_all,
    }

    if best_csv:
        if not os.path.isfile(best_csv):
            raise FileNotFoundError(f"Best file not found: {best_csv}")

        min_best, row_best, best_df = extract_min_cost_row(best_csv)

        all_map = build_column_map(all_df.columns)
        best_map = build_column_map(best_df.columns)

        if match_cols is None:
            match_cols = default_match_columns(best_map, all_map)
        else:
            match_cols = [normalize_header_key(c) for c in match_cols]

        best_cost_col = find_cost_column(best_df.columns)
        best_costs = pd.to_numeric(best_df[best_cost_col], errors="coerce")
        best_min_mask = np.isclose(best_costs, min_best, atol=1e-16, rtol=1e-16)
        best_min_rows = best_df[best_min_mask]
        best_min_row = best_min_rows.iloc[0]

        matched_all_row = match_all_row(
            all_df,
            all_map,
            best_min_row,
            best_map,
            match_cols,
            tol,
        )
        if np.isclose(min_all, min_best, atol=1e-16, rtol=1e-16):
            winner = "tie"
            overall_min = min_all
        elif min_all < min_best:
            winner = "all"
            overall_min = min_all
        else:
            winner = "best"
            overall_min = min_best

        payload.update(
            {
                "best_file": os.path.abspath(best_csv),
                "match_columns": match_cols,
                "match_tolerance": tol,
                "best_min_cost": min_best,
                "overall_min_cost": overall_min,
                "winner": winner,
                "best_min_row": row_best,
                "all_row_for_best_min": matched_all_row,
            }
        )

    if output_path:
        with open(output_path, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"Saved comparison to {output_path}")
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare min-cost rows between an all CSV and a best CSV."
    )
    parser.add_argument("--all-file", required=True, help="Path to the all CSV file")
    parser.add_argument("--best-file", default=None, help="Path to the best CSV file")
    parser.add_argument(
        "--match-cols",
        default=None,
        help="Comma-separated list of columns to match between files",
    )
    parser.add_argument(
        "--tol",
        type=float,
        default=1e-9,
        help="Tolerance for numeric matching",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output JSON path (prints to stdout if omitted)",
    )
    args = parser.parse_args()

    match_cols = None
    if args.match_cols:
        match_cols = [c.strip() for c in args.match_cols.split(",") if c.strip()]

    compare_all_and_best(
        args.all_file,
        best_csv=args.best_file,
        output_path=args.output,
        match_cols=match_cols,
        tol=args.tol,
    )
