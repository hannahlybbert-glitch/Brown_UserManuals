"""
Audit the unique values held by each demographic variable in the two files
that prepare_combined.R reads directly:

  Desktop: data/ProcessComscore/full_demographics/full_machine_person_demos.parquet
  Mobile:  data/ProcessComscore/mobile_characteristics.csv

Purpose: catch label inconsistencies (e.g. "65 and Over" vs "65+",
"HH Size:1" vs "HH Size: 1") between device types or unexpected values
that would silently fall through to NA in the analysis case_when blocks.

Usage (run from project root):
    python code/ProcessComscore/data_structure_validation/scan_demo_values.py

Outputs:
    data/ProcessComscore/data_structure_validation/demo_value_audit.txt
    data/ProcessComscore/data_structure_validation/demo_value_audit.json
"""

import json
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# PATHS  (exactly the files opened by prepare_combined.R)
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DESKTOP_FILE = (PROJECT_ROOT / "data" / "ProcessComscore" /
                "full_demographics" / "full_machine_person_demos.parquet")
MOBILE_FILE  = PROJECT_ROOT / "data" / "ProcessComscore" / "mobile_characteristics.csv"

OUTPUT_DIR  = PROJECT_ROOT / "data" / "ProcessComscore" / "data_structure_validation"
OUTPUT_TXT  = OUTPUT_DIR / "demo_value_audit.txt"
OUTPUT_JSON = OUTPUT_DIR / "demo_value_audit.json"

# ---------------------------------------------------------------------------
# VARIABLES TO AUDIT
# Matches the col_select in prepare_combined.R for each device type.
# ---------------------------------------------------------------------------

# Desktop: hoh_age / hh_income / children_present / hh_size come through
# unchanged from machine demographics; gender comes from person demographics.
DESKTOP_VARS = ["hoh_age", "hh_income", "children_present", "hh_size", "gender"]

# Mobile: age is numeric (recoded to hoh_age bins in prepare_combined.R).
# All other vars are categorical strings passed through as-is.
MOBILE_VARS  = ["age", "gender", "hh_income", "hh_size", "children_present"]

# Variables where a full value listing is not useful (too many values or numeric).
# For "age" we show range + non-numeric stragglers instead.
HIGH_CARDINALITY = {"age"}


# ---------------------------------------------------------------------------
# CORE AUDIT
# ---------------------------------------------------------------------------

def audit_dataframe(df: pd.DataFrame, vars_to_check: list[str]) -> dict:
    """
    Return {var: {"values": sorted list, "n_null": int, "n_total": int}}
    for each variable in vars_to_check that exists in df.
    """
    result = {}
    for var in vars_to_check:
        if var not in df.columns:
            result[var] = {"error": "column not found"}
            continue

        col     = df[var]
        n_total = len(col)
        n_null  = int(col.isna().sum())

        if var in HIGH_CARDINALITY:
            # Numeric variable — report range and flag any non-numeric values
            numeric = pd.to_numeric(col, errors="coerce")
            non_numeric = sorted(
                col.dropna().astype(str)
                   .loc[numeric.isna() & col.notna()]
                   .unique()
                   .tolist()
            )
            result[var] = {
                "n_total":      n_total,
                "n_null":       n_null,
                "min":          float(numeric.min()) if numeric.notna().any() else None,
                "max":          float(numeric.max()) if numeric.notna().any() else None,
                "non_numeric":  non_numeric,
            }
        else:
            # Categorical — collect every unique string value
            unique_vals = sorted(
                col.dropna().astype(str).str.strip().str.strip('"').unique().tolist()
            )
            result[var] = {
                "n_total":  n_total,
                "n_null":   n_null,
                "n_unique": len(unique_vals),
                "values":   unique_vals,
            }
    return result


# ---------------------------------------------------------------------------
# REPORT RENDERING
# ---------------------------------------------------------------------------

def render_report(desktop: dict, mobile: dict) -> str:
    lines = []

    def section(label: str, data: dict, file_path: Path):
        lines.append("=" * 78)
        lines.append(f"  {label.upper()}")
        lines.append(f"  Source: {file_path.relative_to(PROJECT_ROOT)}")
        lines.append("=" * 78)

        for var, info in data.items():
            if "error" in info:
                lines.append(f"\n  [{var}]  *** {info['error']} ***")
                continue

            n_total = info["n_total"]
            n_null  = info["n_null"]

            if var in HIGH_CARDINALITY:
                lines.append(
                    f"\n  [{var}]  (numeric)  "
                    f"n={n_total:,}  null={n_null:,}  "
                    f"range=[{info['min']}, {info['max']}]"
                )
                if info["non_numeric"]:
                    lines.append(f"    *** NON-NUMERIC VALUES FOUND: {info['non_numeric']}")
                if n_null > 0:
                    lines.append(f"    *** {n_null:,} null / missing values")
            else:
                lines.append(
                    f"\n  [{var}]  {info['n_unique']} unique value(s)  "
                    f"n={n_total:,}  null={n_null:,}"
                )
                if n_null > 0:
                    lines.append(f"    *** {n_null:,} null / missing values")
                for val in info["values"]:
                    lines.append(f'    {repr(val)}')

    section("Desktop", desktop, DESKTOP_FILE)
    lines.append("")
    section("Mobile",  mobile,  MOBILE_FILE)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Desktop ---
    if not DESKTOP_FILE.exists():
        raise FileNotFoundError(
            f"Desktop demographics not found: {DESKTOP_FILE}\n"
            "Run create_full_demographics.py then merge_full_demographics.py first."
        )
    print(f"Loading desktop demographics: {DESKTOP_FILE.name} ...")
    desk_df = pd.read_parquet(DESKTOP_FILE, columns=DESKTOP_VARS)
    print(f"  {len(desk_df):,} rows")
    desktop = audit_dataframe(desk_df, DESKTOP_VARS)
    del desk_df

    # --- Mobile ---
    if not MOBILE_FILE.exists():
        raise FileNotFoundError(
            f"Mobile demographics not found: {MOBILE_FILE}\n"
            "Run create_mobile_characteristics.py first."
        )
    print(f"Loading mobile demographics:  {MOBILE_FILE.name} ...")
    mob_df = pd.read_csv(MOBILE_FILE, usecols=MOBILE_VARS, dtype=str, low_memory=False)
    print(f"  {len(mob_df):,} rows")
    mobile = audit_dataframe(mob_df, MOBILE_VARS)
    del mob_df

    # --- Report ---
    report = render_report(desktop, mobile)
    print("\n" + report)

    OUTPUT_TXT.write_text(report, encoding="utf-8")
    print(f"\nWrote: {OUTPUT_TXT}")

    OUTPUT_JSON.write_text(json.dumps({"desktop": desktop, "mobile": mobile}, indent=2),
                           encoding="utf-8")
    print(f"Wrote: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
