#!/usr/bin/env python3
# Author: Hannah Lybbert
# Created: 04/21/2026
'''
Purpose: Build a machine-week level activity panel combining all category parquet
files from desktop_mobile_machine_panel/ into a single output file.

Output columns
  machine_id           -- machine identifier
  week                 -- week_of_sample (1 = Jan 1 2022, 156 = Dec 2024)
  in_panel             -- 1 if machine was observed in Comscore that week (from machine_week_presence), 0 otherwise
  active               -- 1 if in_panel and total_duration > 0 in ANY category; 0 if in_panel and no usage; NaN if not in panel
  ever_treated         -- 1 if machine is from a state in phshutdown_dates.csv AND was
                          observed in_panel==1 at or after the PornHub shutdown date for
                          that state (machine-level, constant across weeks for a given machine)
  week_from_treatment  -- integer offset from state's law week (0 = law week, -1 = week before, etc.)
                          NaN for machines in never-treated states (machine-week level)
  analysis_sample      -- 1 if machine was ever in_panel during the relevant analysis window:
                            treated machines: any week in [law_week + T_MIN, law_week + T_MAX]
                            control machines: any in_analysis_window week (from weeks_in_analysis_sample.csv)
                          machine-level (constant across weeks for a given machine)
  pornhub              -- 1 if total_duration > 0 on Pornhub that week
  xvideos              -- 1 if total_duration > 0 on XVideos that week
  xnxx                 -- 1 if total_duration > 0 on XNXX that week
  any_xxx              -- 1 if total_duration > 0 on any of the 6 XXX categories that week
                          (Pornhub, XVideos, XNXX, Chaturbate, XHamster, other_XXX_sites)
  state                -- 2-letter US state code from demographics (machine-level, constant across weeks)
                          XX/ZZ/US machines are excluded entirely; never-treated machines have a valid
                          non-treated state

ever_treated, analysis_sample, state are machine-level (constant across weeks for a given machine).
week_from_treatment and all binary indicators are machine-week level.

Input files
  data/ProcessComscore/full_demographics/full_machine_person_demos.parquet  (desktop)
  data/ProcessComscore/full_demographics/full_mobile_demos.parquet          (mobile)
  raw/statelaws/phshutdown_dates.csv                                        (PornHub shutdown dates)
  data/Aggregation/machine_panel/machine_week_presence.parquet              (desktop presence)
  data/Aggregation/mobile_machine_panel/machine_week_presence.parquet       (mobile presence)
  data/Aggregation/desktop_mobile_machine_panel/machine_aggregated_*.parquet
  data/ProcessAuxiliary/weeks_in_analysis_sample.csv                        (analysis window weeks)

Output files
  data/Aggregation/machine_activity/machine_week_activity.parquet

Usage: python code/Aggregation/7_machine_week_activity.py
'''

import os
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DESKTOP_DEMOS = os.path.join(BASE, "data", "ProcessComscore", "full_demographics",
                             "full_machine_person_demos.parquet")
MOBILE_DEMOS  = os.path.join(BASE, "data", "ProcessComscore", "full_demographics",
                             "full_mobile_demos.parquet")
STATE_LAWS    = os.path.join(BASE, "raw", "statelaws", "phshutdown_dates.csv")
DESKTOP_PRES  = os.path.join(BASE, "data", "Aggregation", "machine_panel",
                             "machine_week_presence.parquet")
MOBILE_PRES   = os.path.join(BASE, "data", "Aggregation", "mobile_machine_panel",
                             "machine_week_presence.parquet")
PANEL_DIR          = os.path.join(BASE, "data", "Aggregation", "desktop_mobile_machine_panel")
ANALYSIS_WEEKS_FILE = os.path.join(BASE, "data", "ProcessAuxiliary", "weeks_in_analysis_sample.csv")
OUTPUT_DIR    = os.path.join(BASE, "data", "Aggregation", "machine_activity")
OUTPUT_FILE   = os.path.join(OUTPUT_DIR, "machine_week_activity.parquet")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_DATE = pd.Timestamp("2022-01-01")
T_MIN = -16  # event-study window start (mirrors config.R)
T_MAX =   8  # event-study window end

# Categories that contribute to any_xxx
XXX_CATS = {
    "PORNHUB.COM",
    "XVIDEOS.COM",
    "XNXX.COM",
    "CHATURBATE.COM",
    "XHAMSTER.COM",
    "other_XXX_sites",
}

# Categories that get their own explicit output column
NAMED_COLS = {
    "PORNHUB.COM":  "pornhub",
    "XVIDEOS.COM":  "xvideos",
    "XNXX.COM":     "xnxx",
}


def date_to_week(d: pd.Timestamp) -> int:
    return int((d - BASE_DATE).days // 7) + 1


# ── Build ever_treated lookup (machine-level) ─────────────────────────────────
print("Building ever_treated lookup...")

laws = pd.read_csv(STATE_LAWS)
laws = laws[laws["date_PH_shutdown"].notna()][["state", "date_PH_shutdown"]].copy()
laws["law_week"] = pd.to_datetime(laws["date_PH_shutdown"], format="%Y-%m-%d").apply(date_to_week)
state_law_week = laws.set_index("state")["law_week"].to_dict()
treated_states = set(state_law_week.keys())
print(f"  Treated states ({len(treated_states)}): {sorted(treated_states)}")

desktop_states = pd.read_parquet(DESKTOP_DEMOS, columns=["machine_id", "state"])
mobile_states  = pd.read_parquet(MOBILE_DEMOS,  columns=["machine_id", "state"])
desktop_states["machine_id"] = desktop_states["machine_id"].astype(str)
mobile_states["machine_id"]  = mobile_states["machine_id"].astype(str)
INVALID_STATES = {"XX", "ZZ", "US"}

all_states_raw = (
    pd.concat([desktop_states, mobile_states], ignore_index=True)
    .drop_duplicates("machine_id")
)
print(f"  {len(all_states_raw):,} machines with state info")

invalid_machine_ids = set(
    all_states_raw.loc[all_states_raw["state"].isin(INVALID_STATES), "machine_id"]
)
if invalid_machine_ids:
    print(f"  Dropping {len(invalid_machine_ids):,} machines with invalid state "
          f"(XX/ZZ/US) -- excluded from sample entirely")

all_states = all_states_raw[~all_states_raw["state"].isin(INVALID_STATES)].copy()
print(f"  {len(all_states):,} machines with valid state retained")

d_pres = pd.read_parquet(DESKTOP_PRES)
m_pres = pd.read_parquet(MOBILE_PRES)
d_pres["machine_id"] = d_pres["machine_id"].astype(str)
m_pres["machine_id"] = m_pres["machine_id"].astype(str)

# Build combined presence index for in_panel flag (used later)
combined_pres = pd.concat(
    [d_pres[["machine_id", "week_of_sample"]],
     m_pres[["machine_id", "week_of_sample"]]],
    ignore_index=True,
).drop_duplicates()
presence_index = pd.MultiIndex.from_arrays(
    [combined_pres["machine_id"], combined_pres["week_of_sample"]],
    names=["machine_id", "week_of_sample"],
)
print(f"  {len(combined_pres):,} machine-week pairs in presence index")

all_max = (
    pd.concat([
        d_pres.groupby("machine_id")["week_of_sample"].max(),
        m_pres.groupby("machine_id")["week_of_sample"].max(),
    ])
    .groupby(level=0).max()
    .rename("max_week")
    .reset_index()
)

machines = all_states.merge(all_max, on="machine_id", how="left")
machines["law_week"] = machines["state"].map(state_law_week)
machines["ever_treated"] = (
    machines["state"].isin(treated_states)
    & machines["max_week"].notna()
    & machines["law_week"].notna()
    & (machines["max_week"] >= machines["law_week"])
).astype(np.int8)

ever_treated_lookup = machines[["machine_id", "ever_treated"]].copy()
print(f"  Ever-treated machines:  {(machines['ever_treated'] == 1).sum():,}")
print(f"  Never-treated machines: {(machines['ever_treated'] == 0).sum():,}")
et_states = sorted(machines.loc[machines['ever_treated'] == 1, 'state'].unique())
print(f"  Ever-treated states ({len(et_states)}): {et_states}")


# ── Read all panel files and build activity indicators ────────────────────────
panel_files = sorted(
    f for f in os.listdir(PANEL_DIR) if f.startswith("machine_aggregated_") and f.endswith(".parquet")
)
print(f"\nFound {len(panel_files)} panel files in {PANEL_DIR}:")
for f in panel_files:
    print(f"  {f}")

# Extract category name from filename (strips "machine_aggregated_" prefix and ".parquet" suffix)
def get_category(filename):
    return filename.replace("machine_aggregated_", "").replace(".parquet", "")

# Read each file, compute binary activity flag, and merge incrementally.
# base holds the growing (machine_id, week_of_sample) universe with binary columns.
base = None

for filename in panel_files:
    cat = get_category(filename)
    fpath = os.path.join(PANEL_DIR, filename)
    print(f"\n  Reading {filename}...")

    df = pd.read_parquet(fpath, columns=["machine_id", "week_of_sample", "total_duration"])
    df["machine_id"] = df["machine_id"].astype(str)
    print(f"    {len(df):,} rows")

    active_flag = (df["total_duration"] > 0).astype(np.int8)

    # Determine which columns to add for this file
    cols_to_add = {}

    # Named individual column (pornhub / xvideos / xnxx)
    if cat in NAMED_COLS:
        cols_to_add[NAMED_COLS[cat]] = active_flag

    # Contributes to any_xxx
    if cat in XXX_CATS:
        cols_to_add["_xxx_" + cat] = active_flag

    # Always contributes to active
    cols_to_add["_active_" + cat] = active_flag

    df = df[["machine_id", "week_of_sample"]].copy()
    for col, vals in cols_to_add.items():
        df[col] = vals.values

    if base is None:
        base = df
    else:
        base = base.merge(df, on=["machine_id", "week_of_sample"], how="outer")
        # Fill NaN from outer join with 0 (machine not in panel for that category = no activity)
        fill_cols = [c for c in df.columns if c not in ("machine_id", "week_of_sample")]
        base[fill_cols] = base[fill_cols].fillna(0).astype(np.int8)

    print(f"    base shape: {base.shape}")

# Fill any remaining NaN from earlier outer joins
activity_cols = [c for c in base.columns if c not in ("machine_id", "week_of_sample")]
base[activity_cols] = base[activity_cols].fillna(0).astype(np.int8)


# ── Compute derived columns ────────────────────────────────────────────────────
print("\nComputing derived columns...")

active_src_cols = [c for c in base.columns if c.startswith("_active_")]
xxx_src_cols    = [c for c in base.columns if c.startswith("_xxx_")]

base["active"]  = base[active_src_cols].max(axis=1).astype(np.int8)
base["any_xxx"] = base[xxx_src_cols].max(axis=1).astype(np.int8)

# Drop intermediate columns
base = base.drop(columns=active_src_cols + xxx_src_cols)

# Ensure named columns exist even if those files were absent (fill with 0)
for col in ("pornhub", "xvideos", "xnxx"):
    if col not in base.columns:
        print(f"  WARNING: {col} column missing (file not found) -- filling with 0")
        base[col] = np.int8(0)


# ── Add in_panel flag ─────────────────────────────────────────────────────────
print("Computing in_panel flag from machine_week_presence...")
base_index = pd.MultiIndex.from_arrays(
    [base["machine_id"], base["week_of_sample"]]
)
base["in_panel"] = base_index.isin(presence_index).astype(np.int8)
print(f"  In-panel machine-weeks:     {base['in_panel'].sum():,}")
print(f"  Out-of-panel machine-weeks: {(base['in_panel'] == 0).sum():,}")

# active is only meaningful when the machine is in the panel
base["active"] = base["active"].where(base["in_panel"] == 1).astype(float)


# ── Join ever_treated ──────────────────────────────────────────────────────────
print("Joining ever_treated lookup...")
base = base.merge(ever_treated_lookup, on="machine_id", how="left")
base["ever_treated"] = base["ever_treated"].fillna(0).astype(np.int8)

# Drop machines with invalid states (XX/ZZ/US) entirely from the sample
n_before = base["machine_id"].nunique()
base = base[~base["machine_id"].isin(invalid_machine_ids)]
n_dropped = n_before - base["machine_id"].nunique()
if n_dropped:
    print(f"  Dropped {n_dropped:,} machines with invalid state (XX/ZZ/US) from base")


# ── week_from_treatment and analysis_sample ───────────────────────────────────
print("Computing week_from_treatment and analysis_sample...")

analysis_weeks = pd.read_csv(ANALYSIS_WEEKS_FILE)
analysis_window_set = set(
    analysis_weeks.loc[analysis_weeks["in_analysis_window"] == 1, "week"]
)

# Temporarily join state and law_week onto base
base = base.merge(all_states[["machine_id", "state"]], on="machine_id", how="left")
base["law_week"] = base["state"].map(state_law_week)

# week_from_treatment: integer offset from state law week; NaN for never-treated
base["week_from_treatment"] = (base["week_of_sample"] - base["law_week"]).astype(float)

# _in_window: True for rows falling in the relevant analysis period
#   treated machines  → own state's [-16, +8] window
#   control machines  → any in_analysis_window week
treated_mask = base["law_week"].notna()
base["_in_window"] = False
base.loc[treated_mask,  "_in_window"] = (
    (base.loc[treated_mask, "week_from_treatment"] >= T_MIN) &
    (base.loc[treated_mask, "week_from_treatment"] <= T_MAX)
)
base.loc[~treated_mask, "_in_window"] = (
    base.loc[~treated_mask, "week_of_sample"].isin(analysis_window_set)
)

# analysis_sample: machine-level — 1 if ever in_panel during the relevant window
machine_in_sample = (
    base["_in_window"] & (base["in_panel"] == 1)
).groupby(base["machine_id"]).max().astype(np.int8).rename("analysis_sample")
base = base.merge(machine_in_sample, on="machine_id", how="left")
base["analysis_sample"] = base["analysis_sample"].fillna(0).astype(np.int8)

base = base.drop(columns=["law_week", "_in_window"])

n_machines_in_sample = base.drop_duplicates("machine_id")["analysis_sample"].sum()
print(f"  Machines in analysis sample: {n_machines_in_sample:,}")


# ── Finalise ───────────────────────────────────────────────────────────────────
base = base.rename(columns={"week_of_sample": "week"})
base = base[["machine_id", "week", "in_panel", "active", "ever_treated",
             "week_from_treatment", "analysis_sample", "state",
             "pornhub", "xvideos", "xnxx", "any_xxx"]]

print(f"\nFinal output shape: {base.shape}")
print(f"  Machines:                   {base['machine_id'].nunique():,}")
print(f"  Weeks:                      {base['week'].nunique():,} (range {base['week'].min()}--{base['week'].max()})")
print(f"  In-panel machine-weeks:     {(base['in_panel'] == 1).sum():,}")
print(f"  Ever-treated machine-weeks: {(base['ever_treated'] == 1).sum():,}")
print(f"  In analysis sample:         {n_machines_in_sample:,} machines")
print(f"  Active machine-weeks:       {(base['active'] == 1).sum():,}")
print(f"  Pornhub visits:             {(base['pornhub'] == 1).sum():,}")
print(f"  XVideos visits:             {(base['xvideos'] == 1).sum():,}")
print(f"  XNXX visits:                {(base['xnxx'] == 1).sum():,}")
print(f"  Any XXX visits:             {(base['any_xxx'] == 1).sum():,}")

# Ever-treated state breakdown (unique machines, analysis_sample == 1)
et_machines = base.drop_duplicates("machine_id")
et_machines = et_machines[et_machines["ever_treated"] == 1]
et_by_state = (
    et_machines.groupby("state", as_index=False)
    .size()
    .rename(columns={"size": "n_machines"})
    .sort_values("state")
)
print(f"\nEver-treated machines by state (unique machines, all analysis_sample):")
print(f"  {'State':<10} {'N Machines':>12}")
print(f"  {'-'*10} {'-'*12}")
for _, row in et_by_state.iterrows():
    print(f"  {row['state']:<10} {row['n_machines']:>12,}")
print(f"  {'-'*10} {'-'*12}")
print(f"  {'Total':<10} {len(et_machines):>12,}")
print(f"  Unique ever-treated states: {et_machines['state'].nunique()}")


# ── Write output ──────────────────────────────────────────────────────────────
print(f"\nWriting output to {OUTPUT_FILE}...")
base.to_parquet(OUTPUT_FILE, index=False)
print("Done.")
