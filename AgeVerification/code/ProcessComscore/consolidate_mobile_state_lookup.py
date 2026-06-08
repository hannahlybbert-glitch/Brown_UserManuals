# Author: Emily Davis, assisted by Claude
# Created: 2026-03-11
# Purpose: Combine per-month mobile_to_state_lookup.parquet files into a single
#          machine → state lookup for the analysis pipeline.
#
# Input:  data/ProcessComscore/intermediate/*/mobile_to_state_lookup.parquet
# Output: data/Aggregation/mobile_to_state_lookup.parquet
#         Columns: machine_id, state, majority_share
#
# Deduplication: a machine appearing in multiple months keeps the assignment
# with the highest majority_share (most confident state assignment).
#
# Usage (run from project root):
#   python3 code/ProcessComscore/consolidate_mobile_state_lookup.py

import glob
import os
import pandas as pd

INTERMEDIATE_DIR = "data/ProcessComscore/intermediate"
OUTPUT_PATH = "data/Aggregation/mobile_to_state_lookup.parquet"

# ── Find all per-month lookup files ──────────────────────────────────────────
pattern = os.path.join(INTERMEDIATE_DIR, "*", "mobile_to_state_lookup.parquet")
files = sorted(glob.glob(pattern))

if not files:
    print(f"ERROR: No mobile_to_state_lookup.parquet files found under {INTERMEDIATE_DIR}/")
    raise SystemExit(1)

print(f"Found {len(files)} monthly lookup files:")
for f in files:
    print(f"  {f}")

# ── Load and concatenate ──────────────────────────────────────────────────────
print(f"\nLoading {len(files)} files...")
frames = []
for f in files:
    df = pd.read_parquet(f, columns=["machine_id", "state", "majority_share"])
    df["machine_id"] = df["machine_id"].astype(str)
    frames.append(df)

combined = pd.concat(frames, ignore_index=True)
print(f"  Total rows (before dedup): {len(combined):,}")
print(f"  Unique machine_ids:        {combined['machine_id'].nunique():,}")

# ── Deduplicate: keep the row with the highest majority_share per machine ─────
# Sort so highest majority_share is first, then drop_duplicates keeps first.
combined_sorted = combined.sort_values("majority_share", ascending=False)
lookup = combined_sorted.drop_duplicates(subset="machine_id", keep="first").reset_index(drop=True)

print(f"  Rows after dedup:          {len(lookup):,}")

# ── State distribution ────────────────────────────────────────────────────────
valid   = ((lookup["state"] != "XX") & (lookup["state"] != "ZZ")).sum()
unknown = (lookup["state"] == "ZZ").sum()
no_demo = (lookup["state"] == "XX").sum()
print(f"\nState assignment breakdown:")
print(f"  Valid state:              {valid:,} ({valid/len(lookup)*100:.1f}%)")
print(f"  Unknown region (ZZ):      {unknown:,} ({unknown/len(lookup)*100:.1f}%)")
print(f"  No demographics (XX):     {no_demo:,} ({no_demo/len(lookup)*100:.1f}%)")

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
lookup.to_parquet(OUTPUT_PATH, index=False, engine="pyarrow")
print(f"\nSaved: {OUTPUT_PATH}  ({os.path.getsize(OUTPUT_PATH)/1e6:.1f} MB)")
