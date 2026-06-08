#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 04/24/2026
# Purpose: Descriptive breakdown of the machine_week_activity.parquet sample.
#          Prints to console only — no output files written.
#
# Usage: python code/descriptives/summary_tables/active_machines.py

import os
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ACTIVITY_FILE = os.path.join(BASE, "data", "Aggregation", "machine_activity",
                             "machine_week_activity.parquet")

WEEKS_2022 = (1, 52)

SEP  = "=" * 65
SEP2 = "-" * 65

# ── Load ───────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  LOADING DATA")
print(SEP)
print(f"  File: {ACTIVITY_FILE}")

activity = pd.read_parquet(ACTIVITY_FILE)
activity["machine_id"] = activity["machine_id"].astype(str)
print(f"  Rows:     {len(activity):,}")
print(f"  Columns:  {list(activity.columns)}")

# ── Collapse to machine level ──────────────────────────────────────────────────
lo, hi = WEEKS_2022
act_2022 = activity[activity["week"].between(lo, hi)]

machines = (
    activity
    .groupby("machine_id", as_index=False)
    .agg(
        state            = ("state",           "first"),
        ever_treated     = ("ever_treated",     "first"),
        analysis_sample  = ("analysis_sample",  "first"),
        n_weeks_in_panel = ("in_panel",         "sum"),
        ever_ph          = ("pornhub",          "max"),
        ever_xvideos     = ("xvideos",          "max"),
        ever_xnxx        = ("xnxx",             "max"),
        ever_any_xxx     = ("any_xxx",          "max"),
    )
)

# In-panel weeks during 2022 specifically
in_panel_2022 = (
    act_2022[act_2022["in_panel"] == 1]
    .groupby("machine_id")
    .agg(n_weeks_in_panel_2022=("in_panel", "sum"))
    .reset_index()
)
in_panel_2022["in_panel_2022"] = 1

machines = machines.merge(
    in_panel_2022[["machine_id", "in_panel_2022", "n_weeks_in_panel_2022"]],
    on="machine_id", how="left"
)
machines["in_panel_2022"]         = machines["in_panel_2022"].fillna(0).astype(int)
machines["n_weeks_in_panel_2022"] = machines["n_weeks_in_panel_2022"].fillna(0).astype(int)

# XXX activity in 2022 only
xxx_2022 = (
    act_2022[act_2022["in_panel"] == 1]
    .groupby("machine_id", as_index=False)
    .agg(ph_2022=("pornhub", "max"), any_xxx_2022=("any_xxx", "max"))
)
machines = machines.merge(xxx_2022, on="machine_id", how="left")
machines["ph_2022"]      = machines["ph_2022"].fillna(0).astype(int)
machines["any_xxx_2022"] = machines["any_xxx_2022"].fillna(0).astype(int)

# Convenience subsets
analysis = machines[machines["analysis_sample"] == 1]
ever_tr  = analysis[analysis["ever_treated"] == 1]
never_tr = analysis[analysis["ever_treated"] == 0]

def pct(n, d):
    return f"{100 * n / d:.1f}%" if d > 0 else "—"


# ── Section 1: Overall sample ─────────────────────────────────────────────────
print(f"\n{SEP}")
print("  1. OVERALL SAMPLE")
print(SEP)
print(f"  Total machines in file:                    {len(machines):>10,}")
n_invalid = machines["state"].isin({"XX", "ZZ", "US"}).sum()
print(f"  Machines with invalid state (XX/ZZ/US):    {n_invalid:>10,}  (excluded during build)")
print(f"  Unique states represented:                 {machines['state'].nunique():>10,}")


# ── Section 2: Panel coverage ─────────────────────────────────────────────────
print(f"\n{SEP}")
print("  2. PANEL COVERAGE (all machines, all years)")
print(SEP)
wk = machines["n_weeks_in_panel"]
print(f"  Total machine-week rows:                   {len(activity):>10,}")
print(f"  In-panel machine-weeks:                    {int(activity['in_panel'].sum()):>10,}")
print(f"  Avg weeks in panel per machine:            {wk.mean():>10.1f}")
print(f"  Median:                                    {wk.median():>10.1f}")
print(f"  p25 / p75:                       {wk.quantile(0.25):>10.1f} / {wk.quantile(0.75):.1f}")
print(f"  Min / Max:                       {wk.min():>10,} / {wk.max():,}")


# ── Section 3: Analysis sample ────────────────────────────────────────────────
print(f"\n{SEP}")
print("  3. ANALYSIS SAMPLE (analysis_sample == 1)")
print(SEP)
print(f"  Total:                                     {len(analysis):>10,}")
print(f"    ever_treated == 1:                       {len(ever_tr):>10,}  ({pct(len(ever_tr), len(analysis))})")
print(f"    ever_treated == 0:                       {len(never_tr):>10,}  ({pct(len(never_tr), len(analysis))})")

# Machines in treated states that did NOT make the analysis sample
# (ever_treated==0 but state is in a treated state — i.e. left panel before shutdown)
treated_state_all = machines[machines["state"].isin(
    ever_tr["state"].unique()
)]
not_in_sample = treated_state_all[treated_state_all["analysis_sample"] == 0]
print(f"\n  Machines in treated states but analysis_sample == 0:")
print(f"  (likely left the panel before their state's shutdown)")
print(f"    {len(not_in_sample):>10,}")


# ── Section 4: Pre-treatment year 2022 (weeks 1–52) ───────────────────────────
print(f"\n{SEP}")
print("  4. PRE-TREATMENT YEAR 2022 (weeks 1-52, in_panel >= 1)")
print(SEP)
print(f"  {'Group':<35} {'Total machines':>16} {'In panel 2022':>15} {'Avg 2022 wks':>14}")
print(f"  {SEP2}")
rows = [
    ("All machines",          machines),
    ("  ever_treated == 1",   machines[machines["ever_treated"] == 1]),
    ("  ever_treated == 0",   machines[machines["ever_treated"] == 0]),
    ("Analysis sample",       analysis),
    ("  ever_treated == 1",   ever_tr),
    ("  ever_treated == 0",   never_tr),
]
for label, sub in rows:
    n_tot   = len(sub)
    n_2022  = sub["in_panel_2022"].sum()
    in_2022 = sub[sub["in_panel_2022"] == 1]["n_weeks_in_panel_2022"]
    avg_str = f"{in_2022.mean():.1f}" if len(in_2022) > 0 else "—"
    print(f"  {label:<35} {n_tot:>16,} {n_2022:>15,} {avg_str:>14}")


# ── Section 5: XXX engagement ─────────────────────────────────────────────────
print(f"\n{SEP}")
print("  5. XXX ENGAGEMENT (analysis_sample == 1, share of machines)")
print(SEP)
print(f"  {'Metric':<40} {'Full sample':>12} {'Ever-treated':>14} {'Never-treated':>15}")
print(f"  {SEP2}")
n_a, n_e, n_n = len(analysis), len(ever_tr), len(never_tr)
eng_rows = [
    ("Ever visited PornHub (any week)",    "ever_ph"),
    ("Ever visited XVideos (any week)",    "ever_xvideos"),
    ("Ever visited XNXX (any week)",       "ever_xnxx"),
    ("Ever visited any XXX (any week)",    "ever_any_xxx"),
    ("Visited PornHub in 2022",            "ph_2022"),
    ("Visited any XXX in 2022",            "any_xxx_2022"),
]
for label, col in eng_rows:
    fa = analysis[col].sum()
    fe = ever_tr[col].sum()
    fn = never_tr[col].sum()
    print(f"  {label:<40} {pct(fa, n_a):>12} {pct(fe, n_e):>14} {pct(fn, n_n):>15}")


# ── Section 6: State breakdown ────────────────────────────────────────────────
print(f"\n{SEP}")
print("  6. STATE BREAKDOWN (analysis_sample == 1)")
print(SEP)
by_state = (
    analysis
    .groupby("state")
    .agg(n_machines=("machine_id", "count"), ever_treated=("ever_treated", "first"))
    .reset_index()
    .sort_values("n_machines", ascending=False)
)
by_state["group"] = by_state["ever_treated"].map({1: "treated", 0: "control"})
print(f"  {'State':<8} {'N machines':>12} {'Group':>10}")
print(f"  {SEP2}")
for _, row in by_state.iterrows():
    print(f"  {row['state']:<8} {row['n_machines']:>12,} {row['group']:>10}")
print(f"  {SEP2}")
print(f"  {'TOTAL':<8} {len(analysis):>12,}")

print(f"\n{SEP}")
print("  COMPLETE")
print(SEP + "\n")
