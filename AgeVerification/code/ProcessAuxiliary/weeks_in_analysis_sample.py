#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 04/22/2026
# Purpose: Build a week-level indicator for which weeks fall inside any treated
#          state's [-16, +8] event-study analysis window.
'''
Mirrors the window definition in code/analysis/_source/config.R:
  T_MIN = -16, T_MAX = 8  (25-week window centered just before treatment)

For each state with a valid day_effective date, the analysis window is
  [law_week + T_MIN, law_week + T_MAX]
where law_week = (day_effective - 2022-01-01).days // 7 + 1.

in_analysis_window = 1 if the week falls inside ANY state's window, else 0.

Input:  raw/statelaws/statelaws_dates.csv
Output: data/ProcessAuxiliary/weeks_in_analysis_sample.csv
  Columns: week (1–156), in_analysis_window (0/1)

Usage: python code/ProcessAuxiliary/weeks_in_analysis_sample.py
'''

import os
import pandas as pd

BASE      = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LAWS_FILE = os.path.join(BASE, "raw", "statelaws", "statelaws_dates.csv")
OUT_DIR   = os.path.join(BASE, "data", "ProcessAuxiliary")
OUT_FILE  = os.path.join(OUT_DIR, "weeks_in_analysis_sample.csv")
os.makedirs(OUT_DIR, exist_ok=True)

BASE_DATE = pd.Timestamp("2022-01-01")
N_WEEKS   = 156
T_MIN     = -16
T_MAX     =   8


def date_to_week(d: pd.Timestamp) -> int:
    return int((d - BASE_DATE).days // 7) + 1


# ── Load and filter state laws ────────────────────────────────────────────────
laws = pd.read_csv(LAWS_FILE)
laws = laws[laws["day_effective"].notna()][["state", "day_effective"]].copy()
laws["day_effective"] = pd.to_datetime(laws["day_effective"], format="%d%b%Y")
laws["law_week"] = laws["day_effective"].apply(date_to_week)

print(f"States with a valid day_effective: {len(laws)}")
for _, row in laws.iterrows():
    w = row["law_week"]
    print(f"  {row['state']:2s}  law_week={w:3d}  window=[{w+T_MIN}, {w+T_MAX}]")

# ── Mark covered weeks ────────────────────────────────────────────────────────
covered = set()
for law_week in laws["law_week"]:
    lo = max(1,       law_week + T_MIN)
    hi = min(N_WEEKS, law_week + T_MAX)
    covered.update(range(lo, hi + 1))

# ── Build output ──────────────────────────────────────────────────────────────
out = pd.DataFrame({"week": range(1, N_WEEKS + 1)})
out["in_analysis_window"] = out["week"].isin(covered).astype(int)

n_covered = out["in_analysis_window"].sum()
print(f"\nWeeks covered by at least one state's analysis window: {n_covered} of {N_WEEKS}")
print(f"First covered week: {out.loc[out['in_analysis_window']==1, 'week'].min()}")
print(f"Last  covered week: {out.loc[out['in_analysis_window']==1, 'week'].max()}")

out.to_csv(OUT_FILE, index=False)
print(f"\nSaved: {OUT_FILE}")
