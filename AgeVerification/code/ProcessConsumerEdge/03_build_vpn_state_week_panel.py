"""
Build a brand × state × week panel for all VPN brands, 2022-2024.

Input:  raw/dewey-downloads/daily-spend-breakout-by-brand-and-state/
Output: data/ConsumerEdge/vpn_state_week_2022_2024.csv

Aggregation: sum daily SPEND_AMOUNT and TRANS_COUNT to ISO week
(year_week defined as the Monday of the ISO week, so weeks are
unambiguous across year boundaries).
"""

import glob
import os
import pandas as pd

SRC_DIR = "raw/dewey-downloads/daily-spend-breakout-by-brand-and-state"
OUT_PATH = "data/ConsumerEdge/vpn_state_week_2022_2024.csv"

VPN_BRAND_IDS = {
    18937,  # NORDVPN
    23012,  # EXPRESS VPN
    21761,  # PROTONVPN
    20485,  # PUREVPN
    17728,  # STRONG VPN
    21746,  # CYBERGHOST VPN
    21941,  # VYPRVPN (few/no obs but keep in filter)
}

# All daily files in 2022-2024
files = sorted(
    f for f in glob.glob(os.path.join(SRC_DIR, "20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]--data_*.csv.gz"))
    if os.path.basename(f)[:4] in {"2022", "2023", "2024"}
)
print(f"Files to read: {len(files)}")

chunks = []
bad_files = []
for i, f in enumerate(files):
    try:
        df = pd.read_csv(f, usecols=["BRAND_ID", "BRAND_NAME", "SPEND_AMOUNT", "STATE_ABBR", "TRANS_COUNT", "TRANS_DATE"])
        df = df[df["BRAND_ID"].isin(VPN_BRAND_IDS)]
        if not df.empty:
            chunks.append(df)
    except Exception as e:
        bad_files.append((os.path.basename(f), str(e)))
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(files)} files read...")

if bad_files:
    print(f"\nSkipped {len(bad_files)} unreadable files:")
    for name, err in bad_files:
        print(f"  {name}: {err}")

print(f"Files with VPN rows: {len(chunks)}")
df = pd.concat(chunks, ignore_index=True)
print(f"Total daily rows: {len(df):,}")

# Parse date and compute ISO week start (Monday)
df["TRANS_DATE"] = pd.to_datetime(df["TRANS_DATE"])
df["week_start"] = df["TRANS_DATE"] - pd.to_timedelta(df["TRANS_DATE"].dt.dayofweek, unit="D")

# Aggregate to brand × state × week
panel = (
    df.groupby(["BRAND_ID", "BRAND_NAME", "STATE_ABBR", "week_start"])
    .agg(spend=("SPEND_AMOUNT", "sum"), trans=("TRANS_COUNT", "sum"), days_observed=("TRANS_DATE", "nunique"))
    .reset_index()
    .sort_values(["BRAND_NAME", "STATE_ABBR", "week_start"])
)

print(f"\nPanel shape: {panel.shape}")
print(f"Brands: {panel['BRAND_NAME'].unique().tolist()}")
print(f"Date range: {panel['week_start'].min().date()} – {panel['week_start'].max().date()}")
print(f"Weeks: {panel['week_start'].nunique()}")

# Sanity check: weeks with < 7 days observed (partial weeks at year boundaries or data gaps)
partial = panel[panel["days_observed"] < 7]
print(f"Brand×state×week cells with <7 days observed: {len(partial):,} ({100*len(partial)/len(panel):.1f}%)")

# Scale up partial weeks: multiply by 7/days_observed (MAR assumption)
panel["spend"] = panel["spend"] * (7 / panel["days_observed"])
panel["trans"] = panel["trans"] * (7 / panel["days_observed"])

panel.to_csv(OUT_PATH, index=False)
print(f"\nSaved to {OUT_PATH}")
