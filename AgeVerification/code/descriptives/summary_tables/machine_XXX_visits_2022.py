#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 04/21/2026
# Purpose: Table -- share of machines visiting XXX sites in 2022 (pre-treatment year), for full sample, never-treated, and ever-treated groups (analysis_sample == 1, desktop + mobile combined).
'''
2022 definition: weeks 1-52 (Jan 1 -- Dec 30, 2022). Week 53 starts Dec 31 and
spans into 2023 so it is excluded.

A machine "visits" a category in 2022 if it has any total_duration > 0 in that
category during weeks 1-52. "All XXX" is the union across all 6 XXX categories.

Denominators are machines with analysis_sample == 1 AND in_panel == 1 at least
once during weeks 1-52, within each treatment group.

Input files
  data/Aggregation/machine_activity/machine_week_activity.parquet

Output files (in output/descriptives/summary_tables/)
  machine_XXX_visits_2022.tex / .md

Usage: python code/descriptives/summary_tables/machine_XXX_visits_2022.py
'''

import os
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

ACTIVITY_FILE = os.path.join(BASE, "data", "Aggregation", "machine_activity",
                             "machine_week_activity.parquet")
OUTPUT_DIR    = os.path.join(BASE, "output", "descriptives", "summary_tables")
os.makedirs(OUTPUT_DIR, exist_ok=True)

WEEKS_2022 = (1, 52)  # inclusive

# Column names in activity file → display labels
ROW_COLS = ["pornhub", "xvideos", "xnxx", "any_xxx"]
ROW_LABELS = {
    "pornhub": "Visited Pornhub",
    "xvideos": "Visited XVideos",
    "xnxx":    "Visited XNXX",
    "any_xxx": "Visited any XXX site",
}


# ── Load activity file and collapse to machine-level 2022 visit flags ─────────
print("Loading machine_week_activity.parquet...")
lo, hi = WEEKS_2022
activity = pd.read_parquet(
    ACTIVITY_FILE,
    columns=["machine_id", "week", "in_panel", "ever_treated", "analysis_sample", "pornhub", "xvideos", "xnxx", "any_xxx"]
)
activity["machine_id"] = activity["machine_id"].astype(str)
print(f"  {activity['machine_id'].nunique():,} machines in activity file")

# Restrict to analysis_sample == 1 machines, then weeks 1-52 AND in_panel == 1.
analysis_machines = set(
    activity.loc[activity["analysis_sample"] == 1, "machine_id"].unique()
)
activity_2022 = activity[
    activity["machine_id"].isin(analysis_machines)
    & (activity["week"] >= lo) & (activity["week"] <= hi) & (activity["in_panel"] == 1)
]
machines_2022 = (
    activity_2022
    .groupby("machine_id", as_index=False)
    .agg(ever_treated=("ever_treated", "first"),
         pornhub=("pornhub",  "max"),
         xvideos=("xvideos",  "max"),
         xnxx=("xnxx",        "max"),
         any_xxx=("any_xxx",  "max"))
)
print(f"  Machines in analysis sample and panel in 2022 (weeks {lo}-{hi}): {len(machines_2022):,}")

# activity_2023 = activity[(activity["week"] >= 53) & (activity["week"] <= 104)]
# machines_2023 = (
#     activity_2023
#     .groupby("machine_id", as_index=False)
#     .agg(ever_treated=("ever_treated", "first"),
#          pornhub=("pornhub",  "max"),
#          xvideos=("xvideos",  "max"),
#          xnxx=("xnxx",        "max"),
#          any_xxx=("any_xxx",  "max"))
# )
# print(f"  Machines observed in 2023 (weeks 53-104): {len(machines_2023):,}")


print(f"  Ever-treated:  {(machines_2022['ever_treated'] == 1).sum():,}")
print(f"  Never-treated: {(machines_2022['ever_treated'] == 0).sum():,}")

full          = machines_2022
never_treated = machines_2022[machines_2022["ever_treated"] == 0]
ever_treated  = machines_2022[machines_2022["ever_treated"] == 1]

GROUPS = {
    "Full Sample":   full,
    "Never-Treated": never_treated,
    "Ever-Treated":  ever_treated,
}
GROUP_NAMES = list(GROUPS.keys())

print(f"\n  Observed in 2022 by group:")
for name, df in GROUPS.items():
    print(f"    {name}: {len(df):,}")

for col in ROW_COLS:
    n = (machines_2022[col] == 1).sum()
    print(f"  Visited {col} in 2022: {n:,}")


# ── Compute shares ─────────────────────────────────────────────────────────────
def visit_share(group_df, col):
    n = len(group_df)
    return 100 * (group_df[col] == 1).sum() / n if n > 0 else 0.0


# ── Console output ─────────────────────────────────────────────────────────────
COL_W = 16
print("\n" + "=" * 65)
print("  XXX VISITS IN 2022 (share of machines observed in 2022)")
print("=" * 65)
print(f"  {'':28}" + "".join(f"{n:>{COL_W}}" for n in GROUP_NAMES))

for col in ROW_COLS:
    label = ROW_LABELS[col]
    line = f"  {label:<28}"
    for df in GROUPS.values():
        line += f"{visit_share(df, col):>{COL_W - 1}.1f}%"
    print(line)

print(f"\n  {'N observed in 2022':<28}" +
      "".join(f"{len(df):>{COL_W},}" for df in GROUPS.values()))


# ── Export helpers ─────────────────────────────────────────────────────────────
def build_table_rows():
    rows = []
    for col in ROW_COLS:
        pcts = [visit_share(GROUPS[g], col) for g in GROUP_NAMES]
        rows.append((ROW_LABELS[col], pcts))
    ns = [len(GROUPS[g]) for g in GROUP_NAMES]
    return rows, ns


def export_tex(path):
    rows, ns = build_table_rows()
    col_spec = "l" + "r" * len(GROUP_NAMES)
    lines = [
        r"\begin{table}[h!]",
        r"\centering",
        r"\caption{Machine Visits to XXX Sites in 2022 (Pre-Treatment Year)}",
        r"\label{tab:xxx_visits_2022}",
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        " & " + " & ".join(GROUP_NAMES) + r" \\",
        " & " + " & ".join(f"(N = {n:,})" for n in ns) + r" \\",
        r"\midrule",
    ]
    for label, pcts in rows:
        lines.append(label + " & " + " & ".join(f"{p:.1f}\\%" for p in pcts) + r" \\")
    lines += [
        r"\midrule",
        "N observed in 2022 & " + " & ".join(f"{n:,}" for n in ns) + r" \\",
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
    n_row  = "| **N observed in 2022** |" + "|".join(f" {n:,} " for n in ns) + "|"
    lines  = [
        "## XXX Site Visits in 2022 (Pre-Treatment Year)\n",
        "*Share of machines observed in 2022 that visited each site at least once.*\n",
        header, sep,
    ]
    for label, pcts in rows:
        lines.append("| " + label + " |" + "|".join(f" {p:.1f}% " for p in pcts) + "|")
    lines.append(n_row)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {path}")


# ── Run exports ────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  SAVING OUTPUT FILES")
print("=" * 65)
export_tex(os.path.join(OUTPUT_DIR, "machine_XXX_visits_2022.tex"))
export_md( os.path.join(OUTPUT_DIR, "machine_XXX_visits_2022.md"))

print("\n" + "=" * 65)
print("  COMPLETE")
print("=" * 65)
