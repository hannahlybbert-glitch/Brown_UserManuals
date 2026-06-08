#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 04/24/2026
# Purpose: Summary table reporting machine-level average weekly minute activity on XXX sites in 2022

'''
End product:
    3 columns (full sample, never-treated, ever-treated)
    5 rows
        Weekly minutes on PH (winsorized, weekly minutes spent on PH among all maching in the analysis sample that we observe in 2022)
        Weekly minutes on XVideos
        Weekly minutes on XNXX
        Weekly minutes on any XXX
        N (total machines from analysis sample observed in 2022, never-treated observed in 2022, ever-treated observed in 2022)

Notes:
    - Denominators are machines with analysis_sample == 1 AND in_panel == 1 at least
        once during weeks 1-52, within each treatment group
    - This data has already been winsorized at the 95th percentile so no more winsorization needed here.
        We just need to take the mean of the weekly minutes across all machines in the analysis sample
        observed in 2022, within each treatment group.
    - Averaging method: for each machine, compute avg_weekly_min =
        sum(duration over in-panel weeks) / count(in-panel weeks) / 60.
        Grand mean = mean of per-machine averages (equal machine weight).
    - "any XXX" is the sum of all 6 category durations per (machine, week),
        computed fresh from the parquet files.

Input files:
    "data/Aggregation/desktop_mobile_machine_panel/machine_aggregated_{all the XXX categories}.parquet"
        PORNHUB.COM, XNXX.COM, XVIDEOS.COM, XHAMSTER.COM, CHATURBATE.COM, other_XXX_sites
    "data/Aggregation/machine_activity/machine_week_activity.parquet"

Output files (output/descriptives/summary_tables/machine_xxx_weekly_mins_2022.tex / .md)

Usage: python code/descriptives/summary_tables/machine_XXX_weekly_mins_2022.py
'''

import os
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

ACTIVITY_FILE = os.path.join(BASE, "data", "Aggregation", "machine_activity",
                             "machine_week_activity.parquet")
PANEL_DIR     = os.path.join(BASE, "data", "Aggregation", "desktop_mobile_machine_panel")
OUTPUT_DIR    = os.path.join(BASE, "output", "descriptives", "summary_tables")
os.makedirs(OUTPUT_DIR, exist_ok=True)

WEEKS_2022 = (1, 52)  # inclusive

XXX_CATS = [
    "PORNHUB.COM",
    "XNXX.COM",
    "XVIDEOS.COM",
    "XHAMSTER.COM",
    "CHATURBATE.COM",
    "other_XXX_sites",
]

ROW_CATS = ["PORNHUB.COM", "XVIDEOS.COM", "XNXX.COM", "any_xxx"]
ROW_LABELS = {
    "PORNHUB.COM": "Weekly minutes on PornHub",
    "XVIDEOS.COM": "Weekly minutes on XVideos",
    "XNXX.COM":    "Weekly minutes on XNXX",
    "any_xxx":     "Weekly minutes on any XXX site",
}

# ── Step 1: Identify qualifying machines ───────────────────────────────────────
print("Loading machine_week_activity.parquet...")
lo, hi = WEEKS_2022
activity = pd.read_parquet(
    ACTIVITY_FILE,
    columns=["machine_id", "week", "in_panel", "ever_treated", "analysis_sample"]
)
activity["machine_id"] = activity["machine_id"].astype(str)
print(f"  {activity['machine_id'].nunique():,} total machines in activity file")

# Restrict to analysis_sample == 1, weeks 1-52
analysis_machines = set(activity.loc[activity["analysis_sample"] == 1, "machine_id"].unique())
activity_2022 = activity[
    activity["machine_id"].isin(analysis_machines)
    & activity["week"].between(lo, hi)
]

# Qualifying machines: in_panel == 1 at least once in weeks 1-52
qual_in_panel = activity_2022.groupby("machine_id")["in_panel"].max()
qualifying_ids = set(qual_in_panel[qual_in_panel == 1].index)

# Machine-level metadata (ever_treated is constant per machine)
machine_meta = (
    activity_2022[activity_2022["machine_id"].isin(qualifying_ids)]
    .groupby("machine_id", as_index=False)
    .agg(ever_treated=("ever_treated", "first"))
)
print(f"  Qualifying machines (analysis_sample==1, in_panel in 2022): {len(machine_meta):,}")
print(f"  Ever-treated:  {(machine_meta['ever_treated'] == 1).sum():,}")
print(f"  Never-treated: {(machine_meta['ever_treated'] == 0).sum():,}")

# In-panel (machine, week) observations for qualifying machines in 2022
in_panel_obs = activity_2022[
    activity_2022["machine_id"].isin(qualifying_ids)
    & (activity_2022["in_panel"] == 1)
][["machine_id", "week"]].copy()
print(f"  Total qualifying in-panel machine-week obs: {len(in_panel_obs):,}")

# ── Step 2: Load category parquets and merge onto in-panel observations ─────────
print("\nLoading machine_aggregated parquet files...")
panel = in_panel_obs.copy()
for cat in XXX_CATS:
    path = os.path.join(PANEL_DIR, f"machine_aggregated_{cat}.parquet")
    df = pd.read_parquet(path, columns=["machine_id", "week_of_sample", "total_duration"])
    df["machine_id"] = df["machine_id"].astype(str)
    df = (
        df[df["machine_id"].isin(qualifying_ids) & df["week_of_sample"].between(lo, hi)]
        .rename(columns={"week_of_sample": "week", "total_duration": cat})
    )
    panel = panel.merge(df, on=["machine_id", "week"], how="left")
    # In-panel week with no row in category file → 0 usage in that category
    panel[cat] = panel[cat].fillna(0)
    print(f"  Merged {cat}")

panel["any_xxx"] = panel[XXX_CATS].sum(axis=1)

# ── Step 3: Per-machine average weekly minutes (Option A: equal machine weight) ─
# avg_wk_min = sum(duration in in-panel weeks) / count(in-panel weeks) / 60
agg_spec = {"week": "count"}
for col in XXX_CATS + ["any_xxx"]:
    agg_spec[col] = "sum"

machine_totals = panel.groupby("machine_id").agg(agg_spec).reset_index()
machine_totals = machine_totals.rename(columns={"week": "n_weeks"})

for col in XXX_CATS + ["any_xxx"]:
    machine_totals[col + "_avg_wk_min"] = machine_totals[col] / machine_totals["n_weeks"] / 60

machine_totals = machine_totals.merge(machine_meta, on="machine_id")

# ── Step 4: Group statistics ───────────────────────────────────────────────────
full          = machine_totals
never_treated = machine_totals[machine_totals["ever_treated"] == 0]
ever_treated  = machine_totals[machine_totals["ever_treated"] == 1]

GROUPS = {
    "Full Sample":   full,
    "Never-Treated": never_treated,
    "Ever-Treated":  ever_treated,
}
GROUP_NAMES = list(GROUPS.keys())

# ── Console output ─────────────────────────────────────────────────────────────
COL_W = 16
print("\n" + "=" * 65)
print("  AVG WEEKLY XXX MINUTES IN 2022 (PER MACHINE)")
print("=" * 65)
print(f"  {'':30}" + "".join(f"{n:>{COL_W}}" for n in GROUP_NAMES))

for cat in ROW_CATS:
    avg_col = cat + "_avg_wk_min"
    label = ROW_LABELS[cat]
    line = f"  {label:<30}"
    for df in GROUPS.values():
        line += f"{df[avg_col].mean():>{COL_W}.2f}"
    print(line)

print(f"\n  {'N':30}" + "".join(f"{len(df):>{COL_W},}" for df in GROUPS.values()))


# ── Export helpers ─────────────────────────────────────────────────────────────
def build_table_rows():
    rows = []
    for cat in ROW_CATS:
        avg_col = cat + "_avg_wk_min"
        vals = [GROUPS[g][avg_col].mean() for g in GROUP_NAMES]
        rows.append((ROW_LABELS[cat], vals))
    ns = [len(GROUPS[g]) for g in GROUP_NAMES]
    return rows, ns


def export_tex(path):
    rows, ns = build_table_rows()
    col_spec = "l" + "r" * len(GROUP_NAMES)
    lines = [
        r"\begin{table}[h!]",
        r"\centering",
        r"\caption{Average Weekly Minutes on XXX Sites in 2022 (Pre-Treatment Year)}",
        r"\label{tab:xxx_weekly_mins_2022}",
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        " & " + " & ".join(GROUP_NAMES) + r" \\",
        " & " + " & ".join(f"(N = {n:,})" for n in ns) + r" \\",
        r"\midrule",
    ]
    for label, vals in rows:
        lines.append(label + " & " + " & ".join(f"{v:.2f}" for v in vals) + r" \\")
    lines += [
        r"\midrule",
        "N & " + " & ".join(f"{n:,}" for n in ns) + r" \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {path}")


def export_md(path):
    rows, ns = build_table_rows()
    header = "| |" + "|".join(f" {n} " for n in GROUP_NAMES) + "|"
    sep    = "|---|" + "|".join(" ---: " for _ in GROUP_NAMES) + "|"
    n_row  = "| **N** |" + "|".join(f" {n:,} " for n in ns) + "|"
    lines  = [
        "## Average Weekly XXX Minutes in 2022 (Pre-Treatment Year)\n",
        "*Average weekly minutes per machine, computed over in-panel weeks only, "
        "among machines with analysis_sample == 1 observed in 2022.*\n",
        header, sep,
    ]
    for label, vals in rows:
        lines.append("| " + label + " |" + "|".join(f" {v:.2f} " for v in vals) + "|")
    lines.append(n_row)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {path}")


# ── Run exports ────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  SAVING OUTPUT FILES")
print("=" * 65)
export_tex(os.path.join(OUTPUT_DIR, "machine_xxx_weekly_mins_2022.tex"))
export_md( os.path.join(OUTPUT_DIR, "machine_xxx_weekly_mins_2022.md"))

print("\n" + "=" * 65)
print("  COMPLETE")
print("=" * 65)
