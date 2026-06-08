# Author: Hannah Lybbert
# Created: 2026-03-31
# Purpose: Build merged session parquet files for PORNHUB.COM, XNXX.COM, and
#          XVIDEOS.COM from the full set of mobile merged session files.

"""
Loops through every merged_mobile_sessions_{YYYYMM}.parquet file one at a time,
filters to the three target sites, appends new columns, and writes each
site's sessions incrementally to its own output parquet file using
PyArrow's ParquetWriter (avoids loading all months into memory at once).

New columns added:
  date     — calendar date of session (datetime64), derived from time_id
              using base date 1999-12-31 (i.e. date = 1999-12-31 + time_id days)
  treated  — 1 if session's state ever has an age-verification law in the sample
              period, 0 otherwise
  post     — 1 if session date >= state's day_effective (on or after treatment),
              0 if session date < day_effective,
              NaN if state is never treated (treated == 0)

Treatment dates come from raw/statelaws/statelaws_dates.csv using day_effective.
States with an empty day_effective are classified as never-treated (treated == 0).

Inputs:
  data/ProcessComscore/merged_session_files/merged_mobile_sessions_{YYYYMM}.parquet
  raw/statelaws/statelaws_dates.csv

Outputs:
  data/ProcessComscore/merged_cat_session_files/mobile_pornhub_sessions.parquet
  data/ProcessComscore/merged_cat_session_files/mobile_xnxx_sessions.parquet
  data/ProcessComscore/merged_cat_session_files/mobile_xvideos_sessions.parquet

Usage:
  python code/ProcessComscore/create_mobile_category_sessions_files.py
  (run from project root on the cluster)
"""

import glob
import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ==============================================================================
# PATHS AND CONSTANTS
# ==============================================================================
project_root = os.getcwd()

sessions_dir = os.path.join(project_root, "data", "ProcessComscore", "merged_session_files")
laws_path    = os.path.join(project_root, "raw", "statelaws", "statelaws_dates.csv")
output_dir   = os.path.join(project_root, "data", "ProcessComscore", "merged_cat_session_files")
os.makedirs(output_dir, exist_ok=True)

# Target sites: display name (as stored in top_web_name) -> output file stem
SITES = {
    "PORNHUB.COM": "mobile_pornhub_sessions",
    "XNXX.COM":    "mobile_xnxx_sessions",
    "XVIDEOS.COM": "mobile_xvideos_sessions",
}

# time_id base: verified against time_lookup (time_id=8037 -> 2022-01-01)
TIME_ID_BASE = pd.Timestamp("1999-12-31")

# ==============================================================================
# LOAD TREATMENT DATES
# ==============================================================================
print("=" * 70)
print("LOADING TREATMENT DATES")
print("=" * 70)

laws = pd.read_csv(laws_path)

treated_mask          = laws["day_effective"].notna() & (laws["day_effective"].str.strip() != "")
laws_treated          = laws[treated_mask].copy()
laws_treated["treat_date"] = pd.to_datetime(
    laws_treated["day_effective"].str.strip(), format="%d%b%Y"
)

treat_dates    = dict(zip(laws_treated["state"], laws_treated["treat_date"]))
treated_states = set(treat_dates.keys())

print(f"  Treated states ({len(treated_states)}): {sorted(treated_states)}")
for st, dt in sorted(treat_dates.items(), key=lambda x: x[1]):
    print(f"    {st}: {dt.date()}")

# ==============================================================================
# HELPER: ADD NEW COLUMNS TO A FILTERED DATAFRAME
# ==============================================================================
def add_columns(df):
    # date: calendar date from time_id
    df = df.copy()
    df["date"] = TIME_ID_BASE + pd.to_timedelta(df["time_id"], unit="D")

    # treated: 1 if state ever has a law, 0 otherwise
    df["treated"] = df["state"].isin(treated_states).astype(np.int8)

    # post: 1/0 for treated states, NaN for never-treated
    treat_date_col = df["state"].map(treat_dates)            # NaT for untreated
    is_treated     = df["treated"] == 1

    df["post"] = np.where(
        ~is_treated,
        np.nan,
        np.where(df["date"] >= treat_date_col, 1.0, 0.0),
    )

    return df

# ==============================================================================
# MAIN LOOP: ONE MONTHLY FILE AT A TIME
# ==============================================================================
session_files = sorted(
    glob.glob(os.path.join(sessions_dir, "merged_mobile_sessions_??????.parquet"))
)
print(f"\nFound {len(session_files)} monthly mobile session files")
print(f"Processing sites: {list(SITES.keys())}\n")

# One ParquetWriter per site, opened lazily on first non-empty chunk.
# schemas dict stores the reference schema so later months can be cast to match
# (ref_pattern_id dtype varies across monthly files: int64 vs uint64).
writers    = {}
schemas    = {}
row_counts = {stem: 0 for stem in SITES.values()}

for fpath in session_files:
    yyyymm = os.path.basename(fpath).replace("merged_mobile_sessions_", "").replace(".parquet", "")
    print(f"[{yyyymm}] Loading...", end=" ", flush=True)

    # Use pyarrow row filter to load only rows matching our target sites,
    # avoiding reading the full monthly file into memory before filtering.
    target_names = list(SITES.keys())
    table_full = pq.read_table(
        fpath,
        filters=[("top_web_name", "in", target_names)],
    )
    df = table_full.to_pandas()
    del table_full
    df["_web_upper"] = df["top_web_name"].str.upper()

    site_counts = []
    for site_name, stem in SITES.items():
        sub = df[df["_web_upper"] == site_name].drop(columns=["_web_upper"])

        if len(sub) == 0:
            site_counts.append(f"{site_name}=0")
            continue

        sub = add_columns(sub)
        table = pa.Table.from_pandas(sub, preserve_index=False)

        out_path = os.path.join(output_dir, f"{stem}.parquet")
        if stem not in writers:
            writers[stem] = pq.ParquetWriter(out_path, table.schema)
            schemas[stem]  = table.schema
        else:
            table = table.cast(schemas[stem])

        writers[stem].write_table(table)
        row_counts[stem] += len(sub)
        site_counts.append(f"{site_name}={len(sub):,}")

    print("  ".join(site_counts))

# Close all writers
for stem, writer in writers.items():
    writer.close()

# ==============================================================================
# SUMMARY
# ==============================================================================
print("\n" + "=" * 70)
print("OUTPUT SUMMARY")
print("=" * 70)
for site_name, stem in SITES.items():
    out_path = os.path.join(output_dir, f"{stem}.parquet")
    print(f"  {site_name:15s}  {row_counts[stem]:>12,} rows  ->  {out_path}")

print("\nCOMPLETE")
