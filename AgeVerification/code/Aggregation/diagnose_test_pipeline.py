# Author: Hannah Lybbert
# Created: 02/24/2026
# Purpose: Diagnostics for the machine-level panel pipeline — test or full cluster run

"""
Diagnose Machine Panel Pipeline
Validates and summarises the outputs of scripts 3–5.
Works for both the two-month test dataset and the full 36-month cluster output.

Usage:
  python code/Aggregation/diagnose_test_pipeline.py             # real / cluster data
  python code/Aggregation/diagnose_test_pipeline.py --test      # two-month test data
  python code/Aggregation/diagnose_test_pipeline.py --project-root /abs/path

Sections:
  1. Machine roster          — machines, weeks, boundary weeks
  2. Temporal coverage       — active machines per week, entry/exit
  3. Machine tenure          — weeks in panel distribution, short-tenure flag
  4. Monthly files           — completeness per category × month (script 4)
  5. Final panel (per cat)   — shape, NULL/zero/positive, duplicates,
                               duration diagnostics, usage rate over time,
                               NULL-vs-zero rule (vectorized)
  6. Cross-category consistency — person_count and gender identical across files
  7. Boundary-week check     — durations summed correctly (sampled)

All output is written to stdout (captured by SBATCH to logs/aggregation_*.out).

NOTE: total_duration units are SECONDS throughout.
"""

import argparse
import os
import sys
from glob import glob
from datetime import datetime

import numpy as np
import pandas as pd

# ══════════════════════════════════════════════════════════════════════════════
# ARGS
# ══════════════════════════════════════════════════════════════════════════════
parser = argparse.ArgumentParser(description="Diagnose machine panel pipeline outputs.")
parser.add_argument("--test", action="store_true",
                    help="Use machine_panel_test/ instead of machine_panel/")
parser.add_argument("--project-root", default=None,
                    help="Absolute path to project root. Default: two levels up from this script.")
args = parser.parse_args()
TEST_MODE = args.test

try:
    _here = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _here = os.getcwd()

project_root = (
    os.path.abspath(args.project_root) if args.project_root
    else os.path.abspath(os.path.join(_here, "..", ".."))
)

# ══════════════════════════════════════════════════════════════════════════════
# THRESHOLDS  (total_duration is in SECONDS)
# ══════════════════════════════════════════════════════════════════════════════
IMPLAUSIBLE_HOURS  = 168   # > 168 h/week is physically impossible (1 week = 168 h)
HIGH_USAGE_HOURS   = 50    # suspicious — may indicate "left computer open"
SHORT_TENURE_WEEKS = 3     # machines observed in fewer weeks than this are flagged

IMPLAUSIBLE_SECS = IMPLAUSIBLE_HOURS * 3600   # 604,800 s
HIGH_USAGE_SECS  = HIGH_USAGE_HOURS  * 3600   # 180,000 s

# ══════════════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════════════
PANEL_DIR   = os.path.join(project_root, "data", "Aggregation",
                           "machine_panel_test" if TEST_MODE else "machine_panel")
MONTHLY_DIR = os.path.join(PANEL_DIR, "monthly")

# ══════════════════════════════════════════════════════════════════════════════
# TEE — write to stdout AND a log file simultaneously
# ══════════════════════════════════════════════════════════════════════════════
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
PASS = "[PASS]"; WARN = "[WARN]"; FAIL = "[FAIL]"

def chk(ok, msg, warn=False):
    print(f"    {PASS if ok else (WARN if warn else FAIL)} {msg}")

def hdr(title):
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")

def dur_row(s, label=""):
    """Quantile display for a duration Series (converts seconds → hours)."""
    s = s.dropna()
    if len(s) == 0:
        print(f"    {label:35s}  (no positive data)")
        return
    q = s.quantile([.25, .50, .75, .90, .99]) / 3600
    print(f"    {label:35s}  "
          f"p25={q[.25]:.2f}h  p50={q[.50]:.2f}h  "
          f"p75={q[.75]:.2f}h  p90={q[.90]:.2f}h  "
          f"p99={q[.99]:.2f}h  max={s.max()/3600:.2f}h")

def num_row(s, label=""):
    """Quantile display for a general numeric Series."""
    s = s.dropna()
    if len(s) == 0:
        print(f"    {label:35s}  (no data)")
        return
    q = s.quantile([.25, .50, .75, .90, .99])
    print(f"    {label:35s}  "
          f"p25={q[.25]:.1f}  p50={q[.50]:.1f}  "
          f"p75={q[.75]:.1f}  p90={q[.90]:.1f}  "
          f"p99={q[.99]:.1f}  max={s.max():.1f}")

# ══════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print(f"DIAGNOSE MACHINE PANEL PIPELINE{' [TEST MODE]' if TEST_MODE else ''}")
print(f"  Project root : {project_root}")
print(f"  Panel dir    : {PANEL_DIR}")
print(f"  Run time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: MACHINE ROSTER
# ══════════════════════════════════════════════════════════════════════════════
hdr("SECTION 1: MACHINE ROSTER")

# --- 1a. machine_demographics ---
demo_path = os.path.join(project_root, "data", "ProcessComscore",
                         "full_demographics", "machine_demographics.parquet")
if not os.path.exists(demo_path):
    print(f"  ERROR: {demo_path} not found. Run create_full_demographics.py first.")
    sys.exit(1)
demo = pd.read_parquet(demo_path)
demo_ids = set(demo["machine_id"])

print(f"\n  [1a] machine_demographics.parquet")
print(f"    Total unique machines : {len(demo):>10,}")
print(f"\n    have_demos distribution:")
for v, n in demo["have_demos"].value_counts().sort_index().items():
    label = "with Comscore machine demos" if v == 1 else "session-only (no machine demos)"
    print(f"      {v}: {n:>8,}  ({n/len(demo)*100:.1f}%)  {label}")
chk(len(demo) > 0, f"machine_demographics has {len(demo):,} machines")

# Restrict to have_demos==1 — matches script 5's panel scope
demo    = demo[demo["have_demos"] == 1]
demo_ids = set(demo["machine_id"])
print(f"    Panel scope (have_demos==1):  {len(demo):>10,}")

# --- 1b. machine_week_presence ---
presence_path = os.path.join(PANEL_DIR, "machine_week_presence.parquet")
if not os.path.exists(presence_path):
    print(f"  ERROR: {presence_path} not found. Run script 3 first.")
    sys.exit(1)
presence = pd.read_parquet(presence_path)
presence_ids = set(presence["machine_id"])

print(f"\n  [1b] machine_week_presence.parquet")
print(f"    Rows (machine × week) : {len(presence):>10,}")
print(f"    Unique machines       : {presence['machine_id'].nunique():>10,}")
print(f"    Unique weeks          : {presence['week_of_sample'].nunique():>10,}")
print(f"    Week range            : {presence['week_of_sample'].min()} – "
      f"{presence['week_of_sample'].max()}")

chk(demo_ids == presence_ids,
    f"machine_ids consistent across demographics and presence"
    + (f"  [extra in presence: {len(presence_ids - demo_ids)}, "
       f"missing from presence: {len(demo_ids - presence_ids)}]"
       if demo_ids != presence_ids else ""))

# --- 1c. boundary_weeks ---
bw_path = os.path.join(PANEL_DIR, "boundary_weeks.csv")
if not os.path.exists(bw_path):
    print(f"\n  [1c] WARN: boundary_weeks.csv not found.")
    boundary_weeks = []
else:
    bw_df          = pd.read_csv(bw_path)
    boundary_weeks = sorted(bw_df["week_of_sample"].tolist())
    print(f"\n  [1c] boundary_weeks.csv")
    print(f"    Count : {len(boundary_weeks)}")
    print(f"    Weeks : {boundary_weeks}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: TEMPORAL COVERAGE
# ══════════════════════════════════════════════════════════════════════════════
hdr("SECTION 2: TEMPORAL COVERAGE")
print("  Active machines per week = machines with at least one session that week.\n")

active_per_week = (
    presence.groupby("week_of_sample")["machine_id"]
    .nunique()
    .sort_index()
    .rename("active_machines")
)
all_weeks  = active_per_week.index.tolist()
n_weeks    = len(all_weeks)
med_active = active_per_week.median()

print(f"  Weeks in panel data : {n_weeks}")
print(f"  Active machines/wk  : "
      f"min={active_per_week.min():,}  "
      f"median={med_active:,.0f}  "
      f"max={active_per_week.max():,}")

low_thresh = med_active * 0.75
low_weeks  = active_per_week[active_per_week < low_thresh]
chk(len(low_weeks) == 0,
    f"no weeks with active machines < 75% of median  ({low_thresh:.0f})", warn=True)
if len(low_weeks) > 0:
    print(f"\n    Weeks below {low_thresh:.0f} machines (potential data gaps):")
    for w, n in low_weeks.items():
        print(f"      Week {w:>4}: {n:,} active machines")

# Entry / exit table
first_week = presence.groupby("machine_id")["week_of_sample"].min()
last_week  = presence.groupby("machine_id")["week_of_sample"].max()
entries    = first_week.value_counts().sort_index()
exits      = last_week.value_counts().sort_index()

print(f"\n  Entry / exit per week:")
print(f"    {'Week':>6}  {'Entries':>8}  {'Exits':>8}  {'Net':>6}")
disp = all_weeks if n_weeks <= 20 else all_weeks[:10] + [None] + all_weeks[-10:]
for w in disp:
    if w is None:
        print(f"    {'...':>6}  {'...':>8}  {'...':>8}  {'...':>6}")
        continue
    e_in  = entries.get(w, 0)
    e_out = exits.get(w, 0)
    print(f"    {w:>6}  {e_in:>8,}  {e_out:>8,}  {e_in - e_out:>+6,}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: MACHINE TENURE
# ══════════════════════════════════════════════════════════════════════════════
hdr("SECTION 3: MACHINE TENURE")
print(f"  Machines naturally join and leave throughout the sample — attrition is expected.")
print(f"  We flag machines observed in fewer than {SHORT_TENURE_WEEKS} weeks as potentially suspect.\n")

tenure = presence.groupby("machine_id")["week_of_sample"].agg(
    first_week="min",
    last_week="max",
    weeks_observed="count",
)
tenure["week_span"] = tenure["last_week"] - tenure["first_week"] + 1

print(f"  weeks_observed (distinct weeks with data):")
num_row(tenure["weeks_observed"], "weeks_observed")
print(f"  week_span (last − first + 1, including any gaps):")
num_row(tenure["week_span"], "week_span")

n_full   = (tenure["weeks_observed"] == n_weeks).sum()
n_short  = (tenure["weeks_observed"] < SHORT_TENURE_WEEKS).sum()
n_single = (tenure["weeks_observed"] == 1).sum()
n_gt8    = (tenure["weeks_observed"] > 8).sum()
n_gt26   = (tenure["weeks_observed"] > 26).sum()
n_gt52   = (tenure["weeks_observed"] > 52).sum()

print(f"\n  In panel all {n_weeks} weeks : {n_full:>8,}  ({n_full/len(tenure)*100:.1f}%)")
print(f"  < {SHORT_TENURE_WEEKS} weeks observed    : {n_short:>8,}  ({n_short/len(tenure)*100:.1f}%)")
print(f"  Exactly 1 week observed  : {n_single:>8,}  ({n_single/len(tenure)*100:.1f}%)")
print(f"  > 8  weeks observed      : {n_gt8:>8,}  ({n_gt8/len(tenure)*100:.1f}%)")
print(f"  > 26 weeks observed      : {n_gt26:>8,}  ({n_gt26/len(tenure)*100:.1f}%)")
print(f"  > 52 weeks observed      : {n_gt52:>8,}  ({n_gt52/len(tenure)*100:.1f}%)")

chk(n_single == 0,
    f"no machines observed in exactly 1 week  ({n_single} found)", warn=True)
chk(n_short / len(tenure) < 0.05,
    f"< 5% of machines have < {SHORT_TENURE_WEEKS} weeks  "
    f"(found {n_short/len(tenure)*100:.1f}%)", warn=True)

if 0 < n_short <= 200:
    sample = tenure[tenure["weeks_observed"] < SHORT_TENURE_WEEKS].head(10)
    print(f"\n  Sample machines with < {SHORT_TENURE_WEEKS} weeks (first 10):")
    print(f"    {'machine_id':>12}  {'first_week':>10}  {'last_week':>9}  {'wks_obs':>7}")
    for mid, row in sample.iterrows():
        print(f"    {mid:>12}  {row['first_week']:>10}  "
              f"{row['last_week']:>9}  {row['weeks_observed']:>7}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: MONTHLY FILES COMPLETENESS
# ══════════════════════════════════════════════════════════════════════════════
hdr("SECTION 4: MONTHLY FILES COMPLETENESS  (script 4 output)")
print("  Expected: one parquet file per category × month in monthly/\n")

categories = []
if not os.path.isdir(MONTHLY_DIR):
    print(f"  ERROR: {MONTHLY_DIR} not found. Run script 4 first.")
else:
    categories = sorted(os.listdir(MONTHLY_DIR))
    print(f"  Categories found: {len(categories)}\n")

    # Use pyarrow metadata for fast row counts (avoids loading data)
    try:
        import pyarrow.parquet as pq
        def _nrows(f): return pq.read_metadata(f).num_rows
    except ImportError:
        def _nrows(f): return len(pd.read_parquet(f, columns=["machine_id"]))

    for cat in categories:
        files = sorted(glob(os.path.join(MONTHLY_DIR, cat, f"machine_month_*_{cat}.parquet")))
        months = [os.path.basename(f).split("_")[2] for f in files]
        empty  = [os.path.basename(f) for f in files if _nrows(f) == 0]
        span   = f"{months[0]} – {months[-1]}" if months else "n/a"
        print(f"  {cat}:")
        print(f"    Files: {len(files):>3}  |  months: {span}  |  empty: {len(empty)}")
        if empty:
            for ef in empty:
                print(f"      (empty) {ef}")
        chk(len(files) > 0, f"{cat}: ≥ 1 monthly file found")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: FINAL PANEL FILES  (one category at a time)
# ══════════════════════════════════════════════════════════════════════════════
hdr("SECTION 5: FINAL PANEL FILES  (script 5 output — loaded one category at a time)")
print("  NULL = not in panel that week  |  0 = in panel, no usage  |  >0 = has usage\n")

panel_files = sorted(glob(os.path.join(PANEL_DIR, "machine_aggregated_*.parquet")))
chk(len(panel_files) > 0, f"{len(panel_files)} panel file(s) found")

expected_machines = len(demo)
expected_weeks    = n_weeks
expected_rows     = expected_machines * expected_weeks

print(f"\n  Expected grid per file: {expected_machines:,} machines × {expected_weeks} weeks "
      f"= {expected_rows:,} rows")
print(f"\n  File sizes:")
for pf in panel_files:
    size_kb = os.path.getsize(pf) / 1024
    print(f"    {os.path.basename(pf):52s}  {size_kb:>8.1f} KB")

# Build presence MultiIndex once — used for vectorized NULL/zero check per category
presence_midx = pd.MultiIndex.from_frame(presence[["machine_id", "week_of_sample"]])

# Collect machine_ids and weeks per category for Section 6 consistency check
cat_meta = {}

for pf in panel_files:
    cat   = os.path.basename(pf).replace("machine_aggregated_", "").replace(".parquet", "")
    panel = pd.read_parquet(pf)

    n_null     = panel["total_duration"].isna().sum()
    n_zero     = (panel["total_duration"] == 0).sum()
    n_positive = (panel["total_duration"] > 0).sum()

    print(f"\n  {'─' * 76}")
    print(f"  CATEGORY: {cat}")
    print(f"  {'─' * 76}")
    print(f"    Rows     : {len(panel):>10,}  (expected {expected_rows:,})")
    print(f"    NULL     : {n_null:>10,}  ({n_null/len(panel)*100:.1f}%)  not in panel")
    print(f"    Zero     : {n_zero:>10,}  ({n_zero/len(panel)*100:.1f}%)  in panel, no usage")
    print(f"    Positive : {n_positive:>10,}  ({n_positive/len(panel)*100:.1f}%)  has usage")

    chk(len(panel) == expected_rows,
        f"row count {len(panel):,} == expected {expected_rows:,}")
    chk(set(panel["machine_id"].unique()) == demo_ids,
        "machine_ids match machine_demographics")

    # Duplicate (machine, week) rows
    n_dupes = panel.duplicated(subset=["machine_id", "week_of_sample"]).sum()
    chk(n_dupes == 0, f"no duplicate (machine_id, week_of_sample) rows  ({n_dupes} found)")

    # ── Duration diagnostics ─────────────────────────────────────────────────
    positive_dur = panel.loc[panel["total_duration"] > 0, "total_duration"]
    n_implaus    = (positive_dur > IMPLAUSIBLE_SECS).sum()
    n_high       = ((positive_dur > HIGH_USAGE_SECS) &
                    (positive_dur <= IMPLAUSIBLE_SECS)).sum()

    print(f"\n    Duration diagnostics  (positive rows: {len(positive_dur):,})")
    print(f"    Thresholds — implausible: >{IMPLAUSIBLE_HOURS}h ({IMPLAUSIBLE_SECS:,}s)  "
          f"| high usage: >{HIGH_USAGE_HOURS}h ({HIGH_USAGE_SECS:,}s)")

    chk(n_implaus == 0,
        f"implausible rows (>{IMPLAUSIBLE_HOURS}h in one week): {n_implaus}")
    chk(n_high == 0,
        f"high-usage rows (>{HIGH_USAGE_HOURS}h – {IMPLAUSIBLE_HOURS}h): {n_high}  "
        f"({n_high / max(len(positive_dur), 1) * 100:.1f}% of positive rows)",
        warn=True)

    if n_implaus > 0:
        samp = (panel[panel["total_duration"] > IMPLAUSIBLE_SECS]
                [["machine_id", "week_of_sample", "total_duration"]]
                .assign(hours=lambda d: (d["total_duration"] / 3600).round(1))
                .head(5))
        print(f"      Sample implausible rows:")
        print("      " + samp.to_string(index=False).replace("\n", "\n      "))

    if n_high > 0:
        samp = (panel[(panel["total_duration"] > HIGH_USAGE_SECS) &
                      (panel["total_duration"] <= IMPLAUSIBLE_SECS)]
                [["machine_id", "week_of_sample", "total_duration"]]
                .assign(hours=lambda d: (d["total_duration"] / 3600).round(1))
                .head(5))
        print(f"      Sample high-usage rows:")
        print("      " + samp.to_string(index=False).replace("\n", "\n      "))

    print(f"\n    Distribution of positive total_duration:")
    dur_row(positive_dur, cat)

    # ── Usage rate over time ─────────────────────────────────────────────────
    pos_per_week = (
        panel[panel["total_duration"] > 0]
        .groupby("week_of_sample")["machine_id"].nunique()
        .reindex(all_weeks, fill_value=0)
    )
    usage_rate  = (pos_per_week / active_per_week).fillna(0)
    med_rate    = usage_rate.median()
    low_rate_wk = usage_rate[usage_rate < med_rate * 0.5]

    print(f"\n    Usage rate over time (fraction of in-panel machines with positive duration):")
    print(f"      median={med_rate:.3f}  "
          f"min={usage_rate.min():.3f}  "
          f"max={usage_rate.max():.3f}")
    chk(len(low_rate_wk) == 0,
        f"no weeks with usage rate < 50% of median  ({med_rate*0.5:.3f})", warn=True)
    if 0 < len(low_rate_wk) <= 10:
        for w, r in low_rate_wk.items():
            print(f"      Week {w:>4}: usage rate = {r:.3f}")
    elif len(low_rate_wk) > 10:
        print(f"      {len(low_rate_wk)} flagged weeks (showing first 5):")
        for w, r in low_rate_wk.head(5).items():
            print(f"      Week {w:>4}: usage rate = {r:.3f}")

    # ── NULL-vs-zero rule (vectorized) ────────────────────────────────────────
    panel_midx = pd.MultiIndex.from_frame(panel[["machine_id", "week_of_sample"]])
    in_panel   = panel_midx.isin(presence_midx)
    null_mask  = panel["total_duration"].isna().values

    v1 = (null_mask  &  in_panel).sum()   # NULL but machine WAS in panel → should be 0
    v2 = (~null_mask & ~in_panel).sum()   # non-NULL but machine was NOT in panel → should be NULL
    chk(v1 == 0 and v2 == 0,
        f"NULL/zero rule holds  "
        f"[NULL-but-in-panel: {v1}, non-NULL-but-absent: {v2}]"
        if v1 + v2 > 0 else "NULL/zero rule holds")

    # Stash machine_ids and weeks for Section 6 consistency check
    cat_meta[cat] = {
        "machine_ids": set(panel["machine_id"].unique()),
        "weeks":       set(panel["week_of_sample"].unique()),
    }

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: CROSS-CATEGORY CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════════
hdr("SECTION 6: CROSS-CATEGORY CONSISTENCY")
print("  All 7 panel files should have identical machine_ids and week sets.\n")

if len(cat_meta) > 1:
    cats_list = list(cat_meta.keys())
    ref_cat   = cats_list[0]
    ref_ids   = cat_meta[ref_cat]["machine_ids"]
    ref_weeks = cat_meta[ref_cat]["weeks"]

    for cat in cats_list[1:]:
        ids     = cat_meta[cat]["machine_ids"]
        weeks   = cat_meta[cat]["weeks"]
        id_ok   = ids == ref_ids
        week_ok = weeks == ref_weeks
        chk(id_ok and week_ok,
            f"{ref_cat} vs {cat}: "
            + ("machine_ids match" if id_ok
               else f"machine_id mismatch ({len(ids ^ ref_ids):,} differ)")
            + ",  "
            + ("weeks match" if week_ok
               else f"week mismatch ({len(weeks ^ ref_weeks)} differ)"))

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7: BOUNDARY-WEEK DURATION CHECK
# ══════════════════════════════════════════════════════════════════════════════
hdr("SECTION 7: BOUNDARY-WEEK DURATION CHECK")
print("  Verify boundary-week durations in the final panel equal the sum of the two")
print("  partial monthly files. Sampled to keep runtime manageable.\n")

MAX_BW_SAMPLE = 5
sampled_bws   = boundary_weeks[:MAX_BW_SAMPLE]

if len(boundary_weeks) == 0:
    print("  No boundary weeks identified — skipping.")
elif not os.path.isdir(MONTHLY_DIR) or len(categories) == 0:
    print("  Monthly directory or category list not available — skipping.")
else:
    print(f"  Checking {len(sampled_bws)} of {len(boundary_weeks)} boundary "
          f"week(s): {sampled_bws}\n")

    for cat in categories:
        cat_monthly_files = sorted(
            glob(os.path.join(MONTHLY_DIR, cat, f"machine_month_*_{cat}.parquet"))
        )
        panel_path = os.path.join(PANEL_DIR, f"machine_aggregated_{cat}.parquet")
        if not os.path.exists(panel_path):
            continue

        issues = 0
        for bw in sampled_bws:
            # Collect partial durations for this boundary week from each monthly file
            partials = []
            for f in cat_monthly_files:
                chunk = pd.read_parquet(
                    f, filters=[("week_of_sample", "==", bw)]
                )
                if len(chunk) > 0:
                    partials.append(chunk[["machine_id", "total_duration"]])

            if not partials:
                continue

            expected = (
                pd.concat(partials, ignore_index=True)
                .groupby("machine_id")["total_duration"].sum()
            )

            # Read only the relevant week from the final panel (filter pushdown)
            actual = (
                pd.read_parquet(panel_path, filters=[("week_of_sample", "==", bw)])
                .dropna(subset=["total_duration"])
                .set_index("machine_id")["total_duration"]
            )

            for m, exp_val in expected.items():
                if m not in demo_ids:   # skip machines excluded from panel (have_demos==0)
                    continue
                act_val = actual.get(m, np.nan)
                if pd.isna(act_val) or not np.isclose(exp_val, act_val, rtol=1e-6):
                    issues += 1

        chk(issues == 0,
            f"{cat}: boundary-week durations correctly summed"
            + (f"  [{issues} mismatch(es)]" if issues else ""))

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
hdr("SUMMARY")
print(f"""
  Mode             : {'TEST' if TEST_MODE else 'FULL RUN'}
  Panel dir        : {PANEL_DIR}

  Machines         : {len(demo):,}
  Weeks            : {n_weeks}
  Categories       : {len(panel_files)}
  Rows per file    : {expected_rows:,}

  Boundary weeks   : {len(boundary_weeks)}  → {boundary_weeks}

  Machine tenure:
    < {SHORT_TENURE_WEEKS} weeks observed   : {n_short:,}  ({n_short/len(tenure)*100:.1f}%)
    Exactly 1 week   : {n_single:,}  ({n_single/len(tenure)*100:.1f}%)
    All {n_weeks} weeks    : {n_full:,}  ({n_full/len(tenure)*100:.1f}%)

  Duration thresholds:
    Implausible (>{IMPLAUSIBLE_HOURS}h) : {IMPLAUSIBLE_SECS:,} s
    High usage  (>{HIGH_USAGE_HOURS}h)  : {HIGH_USAGE_SECS:,} s

""")

hdr("COMPLETE")

