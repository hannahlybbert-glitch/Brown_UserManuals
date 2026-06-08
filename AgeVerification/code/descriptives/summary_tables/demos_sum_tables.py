#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 04/21/2026
# Purpose: Table 1 -- machine-level demographic shares for full sample, never-treated, and ever-treated groups (desktop + mobile combined).

'''
Treatment definitions
  ever-treated : machine is in a state with a law AND is observed in the panel
                 at or after the week the law takes effect
  never-treated: all others -- untreated-state machines, or treated-state
                 machines that dropped out of the panel before the law took effect

Sample definition
  machine_week_activity.parquet is the authoritative machine universe. The sample
  is restricted to machines with analysis_sample == 1 (i.e., machines observed in
  the panel during at least one week of their relevant [-16, +8] event-study
  window). Demographics are pulled from the full_*_demos files via inner join.

Input files
  data/Aggregation/machine_activity/machine_week_activity.parquet           (machine universe + ever_treated)
  data/ProcessComscore/full_demographics/full_machine_person_demos.parquet  (desktop demographics)
  data/ProcessComscore/full_demographics/full_mobile_demos.parquet          (mobile demographics)

Output files (in output/descriptives/summary_tables/)
  sample_counts.tex / .md       -- sample composition (Table 1)
  demographics_summary_table.tex / .md -- demographic shares (Table 2)

Usage: python code/descriptives/summary_tables/demog_sum_tables.py
'''

import os
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

DESKTOP_DEMOS = os.path.join(BASE, "data", "ProcessComscore", "full_demographics",
                             "full_machine_person_demos.parquet")
MOBILE_DEMOS  = os.path.join(BASE, "data", "ProcessComscore", "full_demographics",
                             "full_mobile_demos.parquet")
ACTIVITY_FILE = os.path.join(BASE, "data", "Aggregation", "machine_activity",
                             "machine_week_activity.parquet")
OUTPUT_DIR    = os.path.join(BASE, "output", "descriptives", "summary_tables")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Load machine universe from activity file ──────────────────────────────────
print("Loading machine universe from machine_week_activity.parquet...")
activity = pd.read_parquet(ACTIVITY_FILE, columns=["machine_id", "ever_treated", "analysis_sample"])
activity["machine_id"] = activity["machine_id"].astype(str)
machine_universe = (
    activity.drop_duplicates("machine_id")
    [["machine_id", "ever_treated", "analysis_sample"]]
    .copy()
)
machine_universe = machine_universe[machine_universe["analysis_sample"] == 1].drop(columns="analysis_sample")
n_ever = (machine_universe["ever_treated"] == 1).sum()
print(f"  {len(machine_universe):,} machines with analysis_sample == 1")
print(f"  Ever-treated: {n_ever:,}  Never-treated: {len(machine_universe) - n_ever:,}")


# ── Load demographics and inner-join onto machine universe ────────────────────
print("\nLoading desktop demographics...")
desktop_raw = pd.read_parquet(
    DESKTOP_DEMOS,
    columns=["machine_id", "state", "hoh_age", "hh_income", "children_present", "hh_size"]
)
desktop_raw["machine_id"] = desktop_raw["machine_id"].astype(str)
print(f"  {len(desktop_raw):,} desktop machines in demo file")

print("Loading mobile demographics...")
mobile_raw = pd.read_parquet(
    MOBILE_DEMOS,
    columns=["machine_id", "state", "age", "hh_income", "hh_size", "children_present"]
)
mobile_raw["machine_id"] = mobile_raw["machine_id"].astype(str)
print(f"  {len(mobile_raw):,} mobile machines in demo file")

# Inner join: restrict to machines present in the activity panel
desktop = machine_universe.merge(desktop_raw, on="machine_id", how="inner")
mobile  = machine_universe.merge(mobile_raw,  on="machine_id", how="inner")
print(f"\n  Desktop machines matched to panel: {len(desktop):,}")
print(f"  Mobile machines matched to panel:  {len(mobile):,}")

# Count unique treated states in the analysis sample
all_states = (
    pd.concat([desktop[["machine_id", "state"]], mobile[["machine_id", "state"]]])
    .drop_duplicates("machine_id")
)
n_treated_states = (
    all_states[all_states["machine_id"].isin(machine_universe[machine_universe["ever_treated"] == 1]["machine_id"])]
    ["state"].nunique()
)
print(f"  Unique states (ever_treated == 1): {n_treated_states}")


# ── Standardize demographics ───────────────────────────────────────────────────
AGE_LABELS    = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
INCOME_LABELS = ["< $25k", "$25k-$39k", "$40k-$59k", "$60k-$74k", "$75k-$99k", "$100k+"]
HHSIZE_LABELS = ["1", "2", "3", "4", "5+"]

DESKTOP_INCOME_MAP = {
    "Less than 25k": "< $25k",   "25k-39k":   "$25k-$39k",
    "40k-59k":  "$40k-$59k",     "60k-74k":   "$60k-$74k",
    "75k-99k":  "$75k-$99k",     "100k-149k": "$100k+",
    "150k-199k":"$100k+",        "200k+":     "$100k+",
}
MOBILE_INCOME_MAP = {
    "Less than 25000": "< $25k",    "25000 - 39999": "$25k-$39k",
    "40000 - 59999":   "$40k-$59k", "60000 - 74999": "$60k-$74k",
    "75000 - 99999":   "$75k-$99k", "100000 or more": "$100k+",
}


def prep_desktop(df):
    df = df.copy()
    df["age_bracket"] = df["hoh_age"].replace({"65 and Over": "65+", "Unknown": np.nan})
    income_clean = (df["hh_income"]
                    .str.replace("HHI US: ", "", regex=False)
                    .str.replace(".999k", "k", regex=False))
    df["income_bracket"] = income_clean.map(DESKTOP_INCOME_MAP)
    df["hh_size_clean"] = (df["hh_size"]
                           .str.replace("HH Size:", "", regex=False).str.strip()
                           .replace({"5 or More": "5+", "Unknown": np.nan}))
    df["children_clean"] = (df["children_present"]
                            .str.replace("Children:", "", regex=False).str.strip())
    return df


def prep_mobile(df):
    df = df.copy()
    df["age_bracket"] = pd.cut(
        df["age"], bins=[17, 24, 34, 44, 54, 64, 150], labels=AGE_LABELS
    ).astype("object")
    income_clean = (df["hh_income"]
                    .str.replace("HHI USD:", "", regex=False).str.strip()
                    .str.replace(",", "", regex=False).str.replace("  ", " ", regex=False))
    df["income_bracket"] = income_clean.map(MOBILE_INCOME_MAP)
    df["hh_size_clean"] = (df["hh_size"]
                           .str.replace("HH Size:", "", regex=False).str.strip()
                           .replace({"5 or More": "5+", "Unknown": np.nan}))
    df["children_clean"] = (df["children_present"]
                            .str.replace("Children:", "", regex=False).str.strip())
    return df


desktop = prep_desktop(desktop)
mobile  = prep_mobile(mobile)

for dev, df in [("Desktop", desktop), ("Mobile", mobile)]:
    unmapped = df[df["hh_income"].notna() & df["income_bracket"].isna()]["hh_income"].unique()
    if len(unmapped):
        print(f"\nWARNING -- {dev} income values with no mapping: {unmapped}")


# ── Combine & build sample groups ─────────────────────────────────────────────
desktop["device"] = "desktop"
mobile["device"]  = "mobile"

KEEP = ["machine_id", "device", "ever_treated",
        "age_bracket", "income_bracket", "hh_size_clean", "children_clean"]

combined = pd.concat([desktop[KEEP], mobile[KEEP]], ignore_index=True)

GROUPS = {
    "Full Sample":   combined,
    "Never-Treated": combined[combined["ever_treated"] == 0],
    "Ever-Treated":  combined[combined["ever_treated"] == 1],
}

GROUP_NAMES = list(GROUPS.keys())


# ── Console preview ────────────────────────────────────────────────────────────
COL_W = 16

print("\n" + "=" * 65)
print("  SAMPLE COUNTS")
print("=" * 65)
hdr = f"  {'':28}" + "".join(f"{n:>{COL_W}}" for n in GROUP_NAMES)
print(hdr)

count_rows = [
    ("Total machines",  lambda g: len(GROUPS[g])),
    ("  Desktop",       lambda g: (GROUPS[g]["device"] == "desktop").sum()),
    ("  Mobile",        lambda g: (GROUPS[g]["device"] == "mobile").sum()),
]
for label, fn in count_rows:
    line = f"  {label:<28}" + "".join(f"{fn(g):>{COL_W},}" for g in GROUP_NAMES)
    print(line)

print("\n" + "=" * 65)
print("  DEMOGRAPHIC SHARES (% of machines in panel)")
print("=" * 65)


def console_share_rows(title, var, cats):
    print(f"\n  {title}")
    print(f"  {'':28}" + "".join(f"{n:>{COL_W}}" for n in GROUP_NAMES))
    for cat in cats:
        line = f"    {str(cat):<26}"
        for df in GROUPS.values():
            sub = df[var].dropna()
            pct = 100 * (sub == cat).sum() / len(sub) if len(sub) else 0
            line += f"{pct:>{COL_W - 1}.1f}%"
        print(line)


console_share_rows("AGE",              "age_bracket",    AGE_LABELS)
console_share_rows("HOUSEHOLD INCOME", "income_bracket", INCOME_LABELS)

print(f"\n  CHILDREN PRESENT IN HH")
print(f"  {'':28}" + "".join(f"{n:>{COL_W}}" for n in GROUP_NAMES))
line = f"    {'Yes':<26}"
for df in GROUPS.values():
    sub = df["children_clean"].dropna()
    pct = 100 * (sub == "Yes").sum() / len(sub) if len(sub) else 0
    line += f"{pct:>{COL_W - 1}.1f}%"
print(line)

console_share_rows("HOUSEHOLD SIZE", "hh_size_clean", HHSIZE_LABELS)

print(f"\n  {'N':<28}" +
      "".join(f"{len(df):>{COL_W},}" for df in GROUPS.values()))


# ── Export helpers ─────────────────────────────────────────────────────────────
def _pct(df, var, cat):
    sub = df[var].dropna()
    return 100 * (sub == cat).sum() / len(sub) if len(sub) else 0


# ── TABLE 1: Sample counts ─────────────────────────────────────────────────────
def build_counts_rows():
    return [
        ("Total machines", 0, [len(GROUPS[g])                              for g in GROUP_NAMES]),
        ("Desktop",        1, [(GROUPS[g]["device"] == "desktop").sum()    for g in GROUP_NAMES]),
        ("Mobile",         1, [(GROUPS[g]["device"] == "mobile").sum()     for g in GROUP_NAMES]),
    ]


def export_counts_tex(path):
    rows = build_counts_rows()
    col_spec = "l" + "r" * len(GROUP_NAMES)
    lines = [
        r"\begin{table}[h!]",
        r"\centering",
        r"\caption{Sample Composition}",
        r"\label{tab:sample_counts}",
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        " & " + " & ".join(GROUP_NAMES) + r" \\",
        r"\midrule",
    ]
    for label, indent, vals in rows:
        prefix = r"\quad " * indent
        lines.append(prefix + label + " & " + " & ".join(f"{v:,}" for v in vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {path}")


def export_counts_md(path):
    rows = build_counts_rows()
    indent_md = ["", "&nbsp;&nbsp;&nbsp;&nbsp;", "&nbsp;" * 8]
    header = "| |" + "|".join(f" {n} " for n in GROUP_NAMES) + "|"
    sep    = "|---|" + "|".join("---:" for _ in GROUP_NAMES) + "|"
    lines  = ["## Table 1: Sample Composition\n", header, sep]
    for label, indent, vals in rows:
        prefix = indent_md[min(indent, 2)]
        lines.append("| " + prefix + label + " |" + "|".join(f" {v:,} " for v in vals) + "|")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {path}")


# ── TABLE 2: Demographic shares ────────────────────────────────────────────────
DEMO_SECTIONS = [
    ("Age",               "age_bracket",    AGE_LABELS),
    ("Household Income",  "income_bracket", INCOME_LABELS),
    ("Children Present",  "children_clean", ["Yes"]),
    ("Household Size",    "hh_size_clean",  HHSIZE_LABELS),
]


def build_demo_rows():
    rows = []
    for section, var, cats in DEMO_SECTIONS:
        rows.append(("section", section, None))
        for cat in cats:
            pcts = [_pct(GROUPS[g], var, cat) for g in GROUP_NAMES]
            rows.append(("data", cat, pcts))
    return rows


def export_demo_tex(path):
    rows = build_demo_rows()
    ns   = [len(GROUPS[g]) for g in GROUP_NAMES]
    col_spec = "l" + "r" * len(GROUP_NAMES)
    lines = [
        r"\begin{table}[h!]",
        r"\centering",
        r"\caption{Demographic Characteristics}",
        r"\label{tab:demographics}",
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        " & " + " & ".join(GROUP_NAMES) + r" \\",
        " & " + " & ".join(f"(N = {n:,})" for n in ns) + r" \\",
        r"\midrule",
    ]
    for kind, label, pcts in rows:
        if kind == "section":
            lines.append(
                rf"\multicolumn{{{len(GROUP_NAMES) + 1}}}{{l}}{{\textit{{{label}}}}} \\"
            )
        else:
            lines.append(
                r"\quad " + label + " & " + " & ".join(f"{p:.1f}\\%" for p in pcts) + r" \\"
            )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {path}")


def export_demo_md(path):
    rows = build_demo_rows()
    ns   = [len(GROUPS[g]) for g in GROUP_NAMES]
    header = "| |" + "|".join(f" {n} " for n in GROUP_NAMES) + "|"
    sep    = "|---|" + "|".join(" ---: " for _ in GROUP_NAMES) + "|"
    n_row  = "| **N** |" + "|".join(f" {n:,} " for n in ns) + "|"
    lines  = [
        "## Table 2: Demographic Characteristics\n",
        "*Sample: machines in the activity panel. All figures are % of column N.*\n",
        header, sep, n_row,
    ]
    for kind, label, pcts in rows:
        if kind == "section":
            lines.append("| **" + label + "** |" + "|".join(" " for _ in GROUP_NAMES) + "|")
        else:
            lines.append(
                "| &nbsp;&nbsp;&nbsp;&nbsp;" + label + " |" +
                "|".join(f" {p:.1f}% " for p in pcts) + "|"
            )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {path}")


# ── Run exports ────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  SAVING OUTPUT FILES")
print("=" * 65)
export_counts_tex(os.path.join(OUTPUT_DIR, "sample_counts.tex"))
export_counts_md( os.path.join(OUTPUT_DIR, "sample_counts.md"))
export_demo_tex(  os.path.join(OUTPUT_DIR, "demographics_summary_table.tex"))
export_demo_md(   os.path.join(OUTPUT_DIR, "demographics_summary_table.md"))

print("\n" + "=" * 65)
print("  COMPLETE")
print("=" * 65)
