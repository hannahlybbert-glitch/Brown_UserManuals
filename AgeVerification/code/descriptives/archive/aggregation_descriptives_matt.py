# Author: Matt Brown, assisted by Claude
# Created: 02/16/2026
# Purpose: 2022 baseline summary statistics — mean weekly minutes per machine by state

"""
2022 Baseline Descriptive Statistics

Computes pre-period (2022) summary statistics for XXX site usage:
- Mean weekly minutes per machine by state (XXX and all sites)
- Mean XXX share of total duration
- Time series and bar chart visualizations

Usage: python code/descriptives/aggregation_descriptives_matt.py

Inputs:
- data/Aggregation/final_aggregated.csv
- raw/statelaws/statelaws_dates.csv

Outputs (to output/descriptives/Aggregation/matt/):
- baseline_2022_means.csv
- timeseries_xxx_min_per_machine_2022.png
- barchart_xxx_min_per_machine_2022.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')

# Import house plotting style
import sys
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", ".."))
sys.path.insert(0, os.path.join(project_root, "code"))
from plot_style import apply_plot_style, UCHICAGO_MAROON, COLOR_PALETTE

apply_plot_style()

# ============================================================================
# SETUP
# ============================================================================

data_file = os.path.join(project_root, "data", "Aggregation", "final_aggregated.csv")
laws_file = os.path.join(project_root, "raw", "statelaws", "statelaws_dates.csv")
output_dir = os.path.join(project_root, "output", "descriptives", "Aggregation", "matt")
os.makedirs(output_dir, exist_ok=True)

XXX_CATEGORIES = [
    'PORNHUB.COM', 'XVIDEOS.COM', 'XHAMSTER.COM', 'XNXX.COM',
    'CHATURBATE.COM', 'other_XXX_sites'
]

# ============================================================================
# LOAD DATA
# ============================================================================

print("Loading data...")
df_full = pd.read_csv(data_file)
df_full['week_start_date'] = pd.to_datetime(df_full['week_start_date'])

# Exclude non-states
df_full = df_full[~df_full['state'].isin(['XX', 'ZZ', 'DC'])].copy()
print(f"  Full: {len(df_full):,} rows | {df_full['state'].nunique()} states | "
      f"{df_full['week_start_date'].min().date()} to {df_full['week_start_date'].max().date()}")

# 2022 subset for baseline descriptives
df = df_full[df_full['week_start_date'].dt.year == 2022].copy()
print(f"  2022: {len(df):,} rows")

# Load state laws for treatment indicator
laws = pd.read_csv(laws_file)
laws['day_effective'] = pd.to_datetime(laws['day_effective'], format='%d%b%Y', errors='coerce')
treated_states = laws.loc[laws['day_passed'].notna(), 'state'].tolist()

# ============================================================================
# COLLAPSE TO STATE-WEEK LEVEL
# ============================================================================

print("Computing state-week aggregates...")

# Get machine count (constant within state-week, take first)
machines = (df.groupby(['state', 'week_start_date'])['all_machine_count']
            .first().reset_index())

# Total XXX duration per state-week
xxx_dur = (df[df['coarse_category'].isin(XXX_CATEGORIES)]
           .groupby(['state', 'week_start_date'])['total_duration_seconds']
           .sum().reset_index()
           .rename(columns={'total_duration_seconds': 'xxx_duration'}))

# Total all duration per state-week
all_dur = (df.groupby(['state', 'week_start_date'])['total_duration_seconds']
           .sum().reset_index()
           .rename(columns={'total_duration_seconds': 'all_duration'}))

# Merge
sw = machines.merge(xxx_dur, on=['state', 'week_start_date']) \
             .merge(all_dur, on=['state', 'week_start_date'])

# Drop state-weeks with zero machines (a few small states)
sw = sw[sw['all_machine_count'] > 0].copy()

# Compute per-machine minutes and XXX share per state-week (for time series)
sw['min_per_machine_xxx'] = sw['xxx_duration'] / 60 / sw['all_machine_count']
sw['xxx_share'] = sw['xxx_duration'] / sw['all_duration']
sw['treated'] = sw['state'].isin(treated_states).astype(int)

# ============================================================================
# OUTPUT 1: SUMMARY TABLE (pooled ratios to avoid small-sample bias)
# ============================================================================

print("Writing summary table...")

state_means = (sw.groupby('state')
               .agg(
                   tot_xxx=('xxx_duration', 'sum'),
                   tot_all=('all_duration', 'sum'),
                   tot_machines=('all_machine_count', 'sum'),
                   treated=('treated', 'first')
               )
               .reset_index())
state_means['mean_weekly_min_per_machine_xxx'] = state_means['tot_xxx'] / 60 / state_means['tot_machines']
state_means['mean_weekly_min_per_machine_all'] = state_means['tot_all'] / 60 / state_means['tot_machines']
state_means['mean_xxx_share'] = state_means['tot_xxx'] / state_means['tot_all']
state_means = (state_means.drop(columns=['tot_xxx', 'tot_all', 'tot_machines'])
               .sort_values('mean_weekly_min_per_machine_xxx', ascending=False))

state_means.to_csv(os.path.join(output_dir, 'baseline_2022_means.csv'), index=False)

# Print summary
print(f"\n  Overall mean XXX min/machine: "
      f"{state_means['mean_weekly_min_per_machine_xxx'].mean():.2f}")
print(f"  Overall mean XXX share: "
      f"{state_means['mean_xxx_share'].mean():.1%}")
print(f"  Treated states: {state_means['treated'].sum()}")
print(f"  Control states: {(state_means['treated'] == 0).sum()}")

# ============================================================================
# OUTPUT 2: TIME SERIES — TREATED VS CONTROL
# ============================================================================

print("Creating time series plot...")

ts = (sw.groupby(['week_start_date', 'treated'])['min_per_machine_xxx']
      .mean().reset_index())

fig, ax = plt.subplots(figsize=(10, 6))
for treated_val, label, color in [(1, 'Treated', UCHICAGO_MAROON),
                                   (0, 'Control', COLOR_PALETTE[2])]:
    subset = ts[ts['treated'] == treated_val]
    ax.plot(subset['week_start_date'], subset['min_per_machine_xxx'],
            label=label, color=color)

ax.set_xlabel('Week')
ax.set_ylabel('Mean Weekly Minutes per Machine (XXX)')
ax.set_title('XXX Site Usage by Treatment Status, 2022')
ax.legend()
fig.autofmt_xdate()
fig.savefig(os.path.join(output_dir, 'timeseries_xxx_min_per_machine_2022.png'))
plt.close(fig)

# ============================================================================
# OUTPUT 3: BAR CHART — STATES SORTED BY XXX MIN/MACHINE
# ============================================================================

print("Creating bar chart...")

plot_df = state_means.sort_values('mean_weekly_min_per_machine_xxx')
colors = [UCHICAGO_MAROON if t == 1 else COLOR_PALETTE[2]
          for t in plot_df['treated']]

fig, ax = plt.subplots(figsize=(12, 8))
ax.barh(plot_df['state'], plot_df['mean_weekly_min_per_machine_xxx'], color=colors)
ax.set_xlabel('Mean Weekly Minutes per Machine (XXX)')
ax.set_title('2022 Baseline: XXX Minutes per Machine by State')

# Legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=UCHICAGO_MAROON, label='Treated'),
                   Patch(facecolor=COLOR_PALETTE[2], label='Control')]
ax.legend(handles=legend_elements, loc='lower right')

fig.savefig(os.path.join(output_dir, 'barchart_xxx_min_per_machine_2022.png'))
plt.close(fig)

# ============================================================================
# OUTPUT 4: NATIONAL TIME SERIES — TOTAL XXX + BY SUBCATEGORY
# ============================================================================

print("Creating national subcategory time series...")

# National weekly: aggregate across all states per week
# Use pooled approach: sum duration / sum machines per week
nat_machines = df.groupby('week_start_date')['all_machine_count'].first()  # need per state
nat_machines = (df.groupby(['state', 'week_start_date'])['all_machine_count']
                .first().reset_index()
                .groupby('week_start_date')['all_machine_count'].sum())

# By category per week
cat_dur = (df.groupby(['week_start_date', 'coarse_category'])['total_duration_seconds']
           .sum().reset_index())
cat_dur = cat_dur.merge(nat_machines.reset_index(), on='week_start_date')
cat_dur['min_per_machine'] = cat_dur['total_duration_seconds'] / 60 / cat_dur['all_machine_count']

# Plot 1: Total XXX vs all_other_sites
fig, ax1 = plt.subplots(figsize=(10, 6))

# Total XXX per week
xxx_nat = (cat_dur[cat_dur['coarse_category'].isin(XXX_CATEGORIES)]
           .groupby('week_start_date')['min_per_machine'].sum().reset_index())
other_nat = cat_dur[cat_dur['coarse_category'] == 'all_other_sites']

ax1.plot(xxx_nat['week_start_date'], xxx_nat['min_per_machine'],
         label='All XXX', color=UCHICAGO_MAROON, linewidth=2)
ax1.set_xlabel('Week')
ax1.set_ylabel('XXX Minutes per Machine', color=UCHICAGO_MAROON)
ax1.tick_params(axis='y', labelcolor=UCHICAGO_MAROON)

ax2 = ax1.twinx()
ax2.plot(other_nat['week_start_date'], other_nat['min_per_machine'],
         label='All Other Sites', color=COLOR_PALETTE[2], linewidth=2)
ax2.set_ylabel('Other Sites Minutes per Machine', color=COLOR_PALETTE[2])
ax2.tick_params(axis='y', labelcolor=COLOR_PALETTE[2])
ax2.spines['right'].set_visible(True)

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

ax1.set_title('National Weekly Usage: XXX vs Other Sites, 2022')
fig.autofmt_xdate()
fig.savefig(os.path.join(output_dir, 'timeseries_national_xxx_vs_other_2022.png'))
plt.close(fig)

# Plot 2: XXX subcategories
fig, ax = plt.subplots(figsize=(10, 6))

TOP5 = [c for c in XXX_CATEGORIES if c != 'other_XXX_sites']

# All top 5 combined
top5_nat = (cat_dur[cat_dur['coarse_category'].isin(TOP5)]
            .groupby('week_start_date')['min_per_machine'].sum().reset_index())
ax.plot(top5_nat['week_start_date'], top5_nat['min_per_machine'],
        label='All Top 5', color='#999999', linewidth=2, linestyle='--')

for i, cat in enumerate(sorted(XXX_CATEGORIES)):
    subset = cat_dur[cat_dur['coarse_category'] == cat]
    label = cat.replace('.COM', '').replace('_', ' ').title()
    ax.plot(subset['week_start_date'], subset['min_per_machine'],
            label=label, color=COLOR_PALETTE[i % len(COLOR_PALETTE)])

ax.set_ylim(bottom=0)
ax.set_xlabel('Week')
ax.set_ylabel('Minutes per Machine (National)')
ax.set_title('National Weekly Usage by XXX Subcategory, 2022')
ax.legend(loc='upper right')
fig.autofmt_xdate()
fig.savefig(os.path.join(output_dir, 'timeseries_national_subcategories_2022.png'))
plt.close(fig)

# ============================================================================
# OUTPUT 5: PER-STATE EVENT STUDIES (full sample period)
# ============================================================================

print("Creating per-state event study plots...")

# Build state-week series for full sample
control_states = [s for s in df_full['state'].unique() if s not in treated_states]

# Get machine counts per state-week (full sample)
machines_full = (df_full.groupby(['state', 'week_start_date'])['all_machine_count']
                 .first().reset_index())

# All XXX min/machine per state-week (full sample)
xxx_dur_full = (df_full[df_full['coarse_category'].isin(XXX_CATEGORIES)]
                .groupby(['state', 'week_start_date'])['total_duration_seconds']
                .sum().reset_index()
                .rename(columns={'total_duration_seconds': 'xxx_duration'}))
sw_full = machines_full.merge(xxx_dur_full, on=['state', 'week_start_date'])
sw_full = sw_full[sw_full['all_machine_count'] > 0].copy()
sw_full['min_per_machine_xxx'] = sw_full['xxx_duration'] / 60 / sw_full['all_machine_count']

# Pornhub min/machine per state-week (full sample)
ph_dur_full = (df_full[df_full['coarse_category'] == 'PORNHUB.COM']
               .groupby(['state', 'week_start_date'])[['total_duration_seconds', 'all_machine_count']]
               .first().reset_index())
ph_dur_full = ph_dur_full[ph_dur_full['all_machine_count'] > 0].copy()
ph_dur_full['min_per_machine_ph'] = ph_dur_full['total_duration_seconds'] / 60 / ph_dur_full['all_machine_count']

# Control averages by week
ctrl_xxx = (sw_full[sw_full['state'].isin(control_states)]
            .groupby('week_start_date')['min_per_machine_xxx'].mean()
            .reset_index().rename(columns={'min_per_machine_xxx': 'ctrl_xxx'}))
ctrl_ph = (ph_dur_full[ph_dur_full['state'].isin(control_states)]
           .groupby('week_start_date')['min_per_machine_ph'].mean()
           .reset_index().rename(columns={'min_per_machine_ph': 'ctrl_ph'}))

# Only plot treated states with effective date before data ends
data_end = df_full['week_start_date'].max()
laws_to_plot = (laws[laws['day_effective'].notna() & (laws['day_effective'] <= data_end)]
                .sort_values('day_effective'))

for _, row in laws_to_plot.iterrows():
    st = row['state']
    eff_date = row['day_effective']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Left panel: Pornhub
    st_ph = ph_dur_full[ph_dur_full['state'] == st]
    ax1.plot(st_ph['week_start_date'], st_ph['min_per_machine_ph'],
             color=UCHICAGO_MAROON, label=st, linewidth=1.5)
    ax1.plot(ctrl_ph['week_start_date'], ctrl_ph['ctrl_ph'],
             color=COLOR_PALETTE[2], label='Control avg', linewidth=1.5)
    ax1.axvline(eff_date, color='black', linestyle='--', linewidth=1.5,
                label='Law effective')
    ax1.set_xlabel('Week')
    ax1.set_ylabel('Minutes per Machine')
    ax1.set_title('Pornhub')
    ax1.legend(loc='upper right', fontsize=10)

    # Right panel: All XXX
    st_xxx = sw_full[sw_full['state'] == st]
    ax2.plot(st_xxx['week_start_date'], st_xxx['min_per_machine_xxx'],
             color=UCHICAGO_MAROON, label=st, linewidth=1.5)
    ax2.plot(ctrl_xxx['week_start_date'], ctrl_xxx['ctrl_xxx'],
             color=COLOR_PALETTE[2], label='Control avg', linewidth=1.5)
    ax2.axvline(eff_date, color='black', linestyle='--', linewidth=1.5,
                label='Law effective')
    ax2.set_xlabel('Week')
    ax2.set_ylabel('Minutes per Machine')
    ax2.set_title('All XXX')
    ax2.legend(loc='upper right', fontsize=10)

    fig.suptitle(f'{st} — Law Effective {eff_date.strftime("%b %d, %Y")}',
                 fontsize=16, fontweight='bold')
    fig.autofmt_xdate()
    fig.savefig(os.path.join(output_dir, f'event_study_{st}.png'))
    plt.close(fig)
    print(f"  {st} ({eff_date.date()})")

# ============================================================================
# OUTPUT 6: STACKED EVENT STUDY (Cengiz et al. style)
# ============================================================================
#
# Approach (following Cengiz, Dube, Lindner & Zipperer 2019):
# For each treated state ("cohort"), we define event time τ as the number of
# weeks since that state's law effective date. We then recenter both the
# treated state's series AND the control states' series to the same event
# time. This produces one (treated, control) pair of observations at each τ
# for each cohort. We then average across cohorts at each τ.
#
# This avoids the problem of assigning a fake treatment date to control states.
# Each control state appears multiple times (once per cohort), always aligned
# to the real calendar dates, just recentered. The composition of cohorts
# contributing to each τ may vary (unbalanced stacking) — early adopters
# contribute more post-period data, late adopters contribute more pre-period.
#
# We drop Texas because Pornhub geo-blocked the entire state, making its
# event qualitatively different from the other age-verification laws.

print("Creating stacked event study (Cengiz et al.)...")

DROP_STATES = ['TX']
stacked_cohorts = laws_to_plot[~laws_to_plot['state'].isin(DROP_STATES)]

stacked_rows = []
for _, row in stacked_cohorts.iterrows():
    st = row['state']
    eff_date = row['day_effective']

    # Treated state series
    st_xxx = sw_full[sw_full['state'] == st][['week_start_date', 'min_per_machine_xxx']].copy()
    st_xxx['event_week'] = ((st_xxx['week_start_date'] - eff_date).dt.days / 7).round().astype(int)
    st_xxx = st_xxx.rename(columns={'min_per_machine_xxx': 'treated_xxx'})

    st_ph = ph_dur_full[ph_dur_full['state'] == st][['week_start_date', 'min_per_machine_ph']].copy()
    st_ph['event_week'] = ((st_ph['week_start_date'] - eff_date).dt.days / 7).round().astype(int)
    st_ph = st_ph.rename(columns={'min_per_machine_ph': 'treated_ph'})

    # Control average over the same calendar dates, recentered
    ctrl_xxx_c = ctrl_xxx.copy()
    ctrl_xxx_c['event_week'] = ((ctrl_xxx_c['week_start_date'] - eff_date).dt.days / 7).round().astype(int)

    ctrl_ph_c = ctrl_ph.copy()
    ctrl_ph_c['event_week'] = ((ctrl_ph_c['week_start_date'] - eff_date).dt.days / 7).round().astype(int)

    # Merge treated + control for this cohort
    cohort = (st_xxx[['event_week', 'treated_xxx']]
              .merge(st_ph[['event_week', 'treated_ph']], on='event_week', how='outer')
              .merge(ctrl_xxx_c[['event_week', 'ctrl_xxx']], on='event_week', how='outer')
              .merge(ctrl_ph_c[['event_week', 'ctrl_ph']], on='event_week', how='outer'))
    cohort['cohort'] = st
    stacked_rows.append(cohort)

stacked = pd.concat(stacked_rows, ignore_index=True)

# Average across cohorts at each event week
stacked_avg = stacked.groupby('event_week').agg(
    treated_xxx=('treated_xxx', 'mean'),
    ctrl_xxx=('ctrl_xxx', 'mean'),
    treated_ph=('treated_ph', 'mean'),
    ctrl_ph=('ctrl_ph', 'mean'),
    n_cohorts=('cohort', 'nunique')
).reset_index()

# Balanced window: keep [-16, +8] so all 14 cohorts contribute at every τ
EVENT_PRE = -16
EVENT_POST = 8
stacked_avg = stacked_avg[(stacked_avg['event_week'] >= EVENT_PRE) &
                          (stacked_avg['event_week'] <= EVENT_POST)].copy()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

# Common y-axis range across both panels
all_vals = pd.concat([stacked_avg[['treated_ph', 'ctrl_ph', 'treated_xxx', 'ctrl_xxx']].stack()])
y_max = all_vals.max() * 1.05

# Left panel: Pornhub
ax1.plot(stacked_avg['event_week'], stacked_avg['treated_ph'],
         color=UCHICAGO_MAROON, label='Treated', linewidth=2)
ax1.plot(stacked_avg['event_week'], stacked_avg['ctrl_ph'],
         color=COLOR_PALETTE[2], label='Control', linewidth=2)
ax1.axvline(0, color='black', linestyle='--', linewidth=1.5)
ax1.set_xlabel('Weeks Since Law Effective')
ax1.set_ylabel('Minutes per Machine')
ax1.set_title('Pornhub')
ax1.set_ylim(0, y_max)
ax1.legend()

# Right panel: All XXX
ax2.plot(stacked_avg['event_week'], stacked_avg['treated_xxx'],
         color=UCHICAGO_MAROON, label='Treated', linewidth=2)
ax2.plot(stacked_avg['event_week'], stacked_avg['ctrl_xxx'],
         color=COLOR_PALETTE[2], label='Control', linewidth=2)
ax2.axvline(0, color='black', linestyle='--', linewidth=1.5)
ax2.set_xlabel('Weeks Since Law Effective')
ax2.set_ylabel('Minutes per Machine')
ax2.set_title('All XXX')
ax2.set_ylim(0, y_max)
ax2.legend()

n_cohorts = len(stacked_cohorts)
fig.suptitle(f'Stacked Event Study — {n_cohorts} Treated States (excl. TX) vs Control',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_stacked.png'))
plt.close(fig)

print(f"  {n_cohorts} cohorts stacked | event window: "
      f"[{stacked_avg['event_week'].min()}, {stacked_avg['event_week'].max()}]")

# ============================================================================
# OUTPUT 7: STACKED EVENT STUDY — BY SUBCATEGORY
# ============================================================================

print("Creating stacked event study by subcategory...")

# Build per-category min/machine for each state-week (full sample)
cat_sw_full = (df_full.groupby(['state', 'week_start_date', 'coarse_category'])
               [['total_duration_seconds', 'all_machine_count']].first().reset_index())
cat_sw_full = cat_sw_full[cat_sw_full['all_machine_count'] > 0].copy()
cat_sw_full['min_per_machine'] = cat_sw_full['total_duration_seconds'] / 60 / cat_sw_full['all_machine_count']

# Also build "All XXX except Pornhub"
xxx_no_ph = [c for c in XXX_CATEGORIES if c != 'PORNHUB.COM']
xxx_no_ph_sw = (df_full[df_full['coarse_category'].isin(xxx_no_ph)]
                .groupby(['state', 'week_start_date'])
                .agg(total_duration_seconds=('total_duration_seconds', 'sum'),
                     all_machine_count=('all_machine_count', 'first'))
                .reset_index())
xxx_no_ph_sw = xxx_no_ph_sw[xxx_no_ph_sw['all_machine_count'] > 0].copy()
xxx_no_ph_sw['min_per_machine'] = xxx_no_ph_sw['total_duration_seconds'] / 60 / xxx_no_ph_sw['all_machine_count']
xxx_no_ph_sw['coarse_category'] = 'All XXX excl. Pornhub'

# Combine
cat_sw_all = pd.concat([cat_sw_full, xxx_no_ph_sw], ignore_index=True)

# Panels to plot
PANELS = ['PORNHUB.COM', 'XHAMSTER.COM', 'XVIDEOS.COM', 'XNXX.COM',
          'CHATURBATE.COM', 'other_XXX_sites', 'All XXX excl. Pornhub', 'all_other_sites']
PANEL_LABELS = {
    'PORNHUB.COM': 'Pornhub', 'XHAMSTER.COM': 'XHamster', 'XVIDEOS.COM': 'XVideos',
    'XNXX.COM': 'XNXX', 'CHATURBATE.COM': 'Chaturbate', 'other_XXX_sites': 'Other XXX Sites',
    'All XXX excl. Pornhub': 'All XXX excl. Pornhub', 'all_other_sites': 'All Other Sites'
}

# Stack cohorts for each category
cat_stacked = {}
for cat in PANELS:
    cat_data = cat_sw_all[cat_sw_all['coarse_category'] == cat]

    # Control average by week for this category
    ctrl_cat = (cat_data[cat_data['state'].isin(control_states)]
                .groupby('week_start_date')['min_per_machine'].mean()
                .reset_index().rename(columns={'min_per_machine': 'ctrl'}))

    rows = []
    for _, row in stacked_cohorts.iterrows():
        st, eff_date = row['state'], row['day_effective']

        st_data = cat_data[cat_data['state'] == st][['week_start_date', 'min_per_machine']].copy()
        st_data['event_week'] = ((st_data['week_start_date'] - eff_date).dt.days / 7).round().astype(int)
        st_data = st_data.rename(columns={'min_per_machine': 'treated'})

        ctrl_c = ctrl_cat.copy()
        ctrl_c['event_week'] = ((ctrl_c['week_start_date'] - eff_date).dt.days / 7).round().astype(int)

        cohort = (st_data[['event_week', 'treated']]
                  .merge(ctrl_c[['event_week', 'ctrl']], on='event_week', how='outer'))
        rows.append(cohort)

    cat_stack = pd.concat(rows, ignore_index=True)
    cat_stack = (cat_stack.groupby('event_week').agg(treated=('treated', 'mean'), ctrl=('ctrl', 'mean'))
                 .reset_index())
    cat_stack = cat_stack[(cat_stack['event_week'] >= EVENT_PRE) &
                          (cat_stack['event_week'] <= EVENT_POST)]
    cat_stacked[cat] = cat_stack

fig, axes = plt.subplots(2, 4, figsize=(24, 10))
for ax, cat in zip(axes.flat, PANELS):
    s = cat_stacked[cat]
    ax.plot(s['event_week'], s['treated'], color=UCHICAGO_MAROON, label='Treated', linewidth=2)
    ax.plot(s['event_week'], s['ctrl'], color=COLOR_PALETTE[2], label='Control', linewidth=2)
    ax.axvline(0, color='black', linestyle='--', linewidth=1.5)
    ax.set_title(PANEL_LABELS[cat])
    ax.set_xlabel('Weeks Since Law Effective')
    ax.set_ylabel('Minutes per Machine')
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=8)

fig.suptitle(f'Stacked Event Study by Category — {n_cohorts} Treated States (excl. TX) vs Control',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_stacked_by_category.png'))
plt.close(fig)
print("  Saved event_study_stacked_by_category.png")

# ============================================================================
# OUTPUT 8: STACKED EVENT STUDY — SHARE OF MACHINE HOURS
# ============================================================================

print("Creating stacked event study (share of machine hours)...")

# Build share variables per state-week (full sample)
# Total duration across all categories per state-week
all_dur_full = (df_full.groupby(['state', 'week_start_date'])['total_duration_seconds']
                .sum().reset_index()
                .rename(columns={'total_duration_seconds': 'total_duration'}))

# Pornhub share
ph_share_sw = (ph_dur_full[['state', 'week_start_date', 'total_duration_seconds']]
               .merge(all_dur_full, on=['state', 'week_start_date']))
ph_share_sw['share_ph'] = ph_share_sw['total_duration_seconds'] / ph_share_sw['total_duration']

# All XXX share
xxx_dur_full2 = (df_full[df_full['coarse_category'].isin(XXX_CATEGORIES)]
                 .groupby(['state', 'week_start_date'])['total_duration_seconds']
                 .sum().reset_index()
                 .rename(columns={'total_duration_seconds': 'xxx_duration'}))
xxx_share_sw = xxx_dur_full2.merge(all_dur_full, on=['state', 'week_start_date'])
xxx_share_sw['share_xxx'] = xxx_share_sw['xxx_duration'] / xxx_share_sw['total_duration']

# Control averages
ctrl_share_ph = (ph_share_sw[ph_share_sw['state'].isin(control_states)]
                 .groupby('week_start_date')['share_ph'].mean()
                 .reset_index().rename(columns={'share_ph': 'ctrl_ph'}))
ctrl_share_xxx = (xxx_share_sw[xxx_share_sw['state'].isin(control_states)]
                  .groupby('week_start_date')['share_xxx'].mean()
                  .reset_index().rename(columns={'share_xxx': 'ctrl_xxx'}))

# Stack cohorts
share_rows = []
for _, row in stacked_cohorts.iterrows():
    st, eff_date = row['state'], row['day_effective']

    st_ph_s = ph_share_sw[ph_share_sw['state'] == st][['week_start_date', 'share_ph']].copy()
    st_ph_s['event_week'] = ((st_ph_s['week_start_date'] - eff_date).dt.days / 7).round().astype(int)
    st_ph_s = st_ph_s.rename(columns={'share_ph': 'treated_ph'})

    st_xxx_s = xxx_share_sw[xxx_share_sw['state'] == st][['week_start_date', 'share_xxx']].copy()
    st_xxx_s['event_week'] = ((st_xxx_s['week_start_date'] - eff_date).dt.days / 7).round().astype(int)
    st_xxx_s = st_xxx_s.rename(columns={'share_xxx': 'treated_xxx'})

    ctrl_ph_c = ctrl_share_ph.copy()
    ctrl_ph_c['event_week'] = ((ctrl_ph_c['week_start_date'] - eff_date).dt.days / 7).round().astype(int)

    ctrl_xxx_c = ctrl_share_xxx.copy()
    ctrl_xxx_c['event_week'] = ((ctrl_xxx_c['week_start_date'] - eff_date).dt.days / 7).round().astype(int)

    cohort = (st_ph_s[['event_week', 'treated_ph']]
              .merge(st_xxx_s[['event_week', 'treated_xxx']], on='event_week', how='outer')
              .merge(ctrl_ph_c[['event_week', 'ctrl_ph']], on='event_week', how='outer')
              .merge(ctrl_xxx_c[['event_week', 'ctrl_xxx']], on='event_week', how='outer'))
    share_rows.append(cohort)

share_stacked = pd.concat(share_rows, ignore_index=True)
share_avg = (share_stacked.groupby('event_week')
             .agg(treated_ph=('treated_ph', 'mean'), ctrl_ph=('ctrl_ph', 'mean'),
                  treated_xxx=('treated_xxx', 'mean'), ctrl_xxx=('ctrl_xxx', 'mean'))
             .reset_index())
share_avg = share_avg[(share_avg['event_week'] >= EVENT_PRE) &
                      (share_avg['event_week'] <= EVENT_POST)]

# Shared y-axis
share_vals = pd.concat([share_avg[['treated_ph', 'ctrl_ph', 'treated_xxx', 'ctrl_xxx']].stack()])
y_max_share = share_vals.max() * 1.05

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

ax1.plot(share_avg['event_week'], share_avg['treated_ph'] * 100,
         color=UCHICAGO_MAROON, label='Treated', linewidth=2)
ax1.plot(share_avg['event_week'], share_avg['ctrl_ph'] * 100,
         color=COLOR_PALETTE[2], label='Control', linewidth=2)
ax1.axvline(0, color='black', linestyle='--', linewidth=1.5)
ax1.set_xlabel('Weeks Since Law Effective')
ax1.set_ylabel('Share of Total Machine Hours (%)')
ax1.set_title('Pornhub')
ax1.set_ylim(0, y_max_share * 100)
ax1.legend()

ax2.plot(share_avg['event_week'], share_avg['treated_xxx'] * 100,
         color=UCHICAGO_MAROON, label='Treated', linewidth=2)
ax2.plot(share_avg['event_week'], share_avg['ctrl_xxx'] * 100,
         color=COLOR_PALETTE[2], label='Control', linewidth=2)
ax2.axvline(0, color='black', linestyle='--', linewidth=1.5)
ax2.set_xlabel('Weeks Since Law Effective')
ax2.set_ylabel('Share of Total Machine Hours (%)')
ax2.set_title('All XXX')
ax2.set_ylim(0, y_max_share * 100)
ax2.legend()

fig.suptitle(f'Stacked Event Study (Share of Hours) — {n_cohorts} Treated States (excl. TX) vs Control',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_stacked_share.png'))
plt.close(fig)
print("  Saved event_study_stacked_share.png")

# ============================================================================
# OUTPUT 9: TEXAS — BY SUBCATEGORY (calendar time)
# ============================================================================

print("Creating Texas by-subcategory plot...")

tx_eff = laws.loc[laws['state'] == 'TX', 'day_effective'].iloc[0]

fig, axes = plt.subplots(2, 4, figsize=(24, 10))
for ax, cat in zip(axes.flat, PANELS):
    cat_data = cat_sw_all[cat_sw_all['coarse_category'] == cat]
    tx_data = cat_data[cat_data['state'] == 'TX']
    ctrl_data = (cat_data[cat_data['state'].isin(control_states)]
                 .groupby('week_start_date')['min_per_machine'].mean().reset_index())

    ax.plot(tx_data['week_start_date'], tx_data['min_per_machine'],
            color=UCHICAGO_MAROON, label='TX', linewidth=1.5)
    ax.plot(ctrl_data['week_start_date'], ctrl_data['min_per_machine'],
            color=COLOR_PALETTE[2], label='Control avg', linewidth=1.5)
    ax.axvline(tx_eff, color='black', linestyle='--', linewidth=1.5)
    ax.set_title(PANEL_LABELS[cat])
    ax.set_xlabel('Week')
    ax.set_ylabel('Minutes per Machine')
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=8)

fig.suptitle(f'Texas — Law Effective {tx_eff.strftime("%b %d, %Y")} — by Category',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.autofmt_xdate()
fig.savefig(os.path.join(output_dir, 'event_study_TX_by_category.png'))
plt.close(fig)
print("  Saved event_study_TX_by_category.png")

# ============================================================================
# OUTPUT 10: TWFE EVENT STUDY REGRESSIONS
# ============================================================================
#
# Standard TWFE event study:
#   y_{st} = α_s + α_t + Σ_{τ≠-1} β_τ * 1[event_time_{st} = τ] + ε_{st}
#
# - State FE (α_s) and week FE (α_t) absorb level differences and common trends
# - Event-time dummies only "turn on" for treated states; controls have no
#   event time and so are absorbed by the time FE
# - τ = -1 is the omitted reference period
# - β_τ measures the treatment effect at event time τ relative to τ = -1
# - We drop TX (geo-block) and restrict to [-16, +8] for a balanced window

print("Running TWFE event study regressions...")

import statsmodels.formula.api as smf

# Build panel: all states × all weeks, with event time for treated states
# Use full sample, drop TX
panel_states = [s for s in df_full['state'].unique() if s != 'TX']

def run_twfe_event_study(y_data, y_col, panel_states, laws, event_pre, event_post,
                         biweekly=False, weight_col=None, cluster=True):
    """Run TWFE event study and return coefficients + CIs.

    Args:
        y_data: DataFrame with columns [state, week_start_date, <y_col>]
        y_col: name of the outcome column
        panel_states: list of states to include
        laws: laws DataFrame with day_effective
        event_pre, event_post: event window bounds (in period units)
        biweekly: if True, aggregate to two-week periods before running
        weight_col: if provided, use WLS with this column as weights
        cluster: if True, cluster SEs by state; if False, use HC1 robust SEs
    """
    panel = y_data[y_data['state'].isin(panel_states)].copy()

    # Merge treatment timing
    panel = panel.merge(laws[['state', 'day_effective']], on='state', how='left')

    # Compute event time in weeks
    panel['event_time_weeks'] = np.where(
        panel['day_effective'].notna(),
        ((panel['week_start_date'] - panel['day_effective']).dt.days / 7).round().astype(float),
        np.nan
    )

    if biweekly:
        # Assign each week to a two-week period (floored to even weeks from sample start)
        sample_start = panel['week_start_date'].min()
        panel['period_idx'] = ((panel['week_start_date'] - sample_start).dt.days // 14).astype(int)
        panel['period_id'] = panel['period_idx'].astype(str)

        # Aggregate to state × two-week period
        agg_dict = {y_col: 'mean', 'week_start_date': 'first',
                    'day_effective': 'first', 'event_time_weeks': 'mean'}
        if weight_col:
            agg_dict[weight_col] = 'mean'
        panel = panel.groupby(['state', 'period_idx']).agg(agg_dict).reset_index()
        panel['period_id'] = panel['period_idx'].astype(str)

        # Convert event time from weeks to biweekly periods
        panel['event_time'] = np.where(
            panel['event_time_weeks'].notna(),
            (panel['event_time_weeks'] / 2).round().astype(float),
            np.nan
        )
        time_fe = 'C(period_id)'
    else:
        panel['event_time'] = panel['event_time_weeks']
        panel['week_id'] = panel['week_start_date'].astype(str)
        time_fe = 'C(week_id)'

    # Create event-time dummies within window, omitting τ = -1
    event_times = [t for t in range(event_pre, event_post + 1) if t != -1]
    for t in event_times:
        col = f'tau_{t}' if t >= 0 else f'tau_neg{abs(t)}'
        panel[col] = (panel['event_time'] == t).astype(int)

    # States outside the window but treated: bin at endpoints
    panel.loc[panel['event_time'] < event_pre, f'tau_neg{abs(event_pre)}'] = 1
    panel.loc[panel['event_time'] > event_post, f'tau_{event_post}'] = 1

    # Build formula
    tau_cols = []
    for t in event_times:
        col = f'tau_{t}' if t >= 0 else f'tau_neg{abs(t)}'
        tau_cols.append(col)

    formula = f'{y_col} ~ C(state) + {time_fe} + ' + ' + '.join(tau_cols)

    # Run OLS (or WLS if weights provided)
    if cluster:
        cov_args = dict(cov_type='cluster', cov_kwds={'groups': panel['state']})
    else:
        cov_args = dict(cov_type='HC1')

    if weight_col:
        model = smf.wls(formula, data=panel, weights=panel[weight_col]).fit(**cov_args)
    else:
        model = smf.ols(formula, data=panel).fit(**cov_args)

    # Extract coefficients
    results = []
    for t in event_times:
        col = f'tau_{t}' if t >= 0 else f'tau_neg{abs(t)}'
        coef = model.params[col]
        ci_lo, ci_hi = model.conf_int().loc[col]
        results.append({'event_time': t, 'coef': coef, 'ci_lo': ci_lo, 'ci_hi': ci_hi})

    # Add the omitted period (τ = -1, coef = 0)
    results.append({'event_time': -1, 'coef': 0, 'ci_lo': 0, 'ci_hi': 0})

    return pd.DataFrame(results).sort_values('event_time')

def plot_twfe(ax, res, title, ylabel='Coefficient (min/machine)', period_label='Weeks'):
    """Plot TWFE event study coefficients with 95% CI."""
    ax.fill_between(res['event_time'], res['ci_lo'], res['ci_hi'],
                     color=UCHICAGO_MAROON, alpha=0.2)
    ax.plot(res['event_time'], res['coef'], color=UCHICAGO_MAROON,
            linewidth=2, marker='o', markersize=4)
    ax.axvline(0, color='black', linestyle='--', linewidth=1)
    ax.axhline(0, color='gray', linewidth=0.8, alpha=0.5)
    ax.set_xlabel(f'{period_label} Since Law Effective')
    ax.set_ylabel(ylabel)
    ax.set_title(title)

# --- Helper: build panel data for different DVs ---
# Include all_machine_count for precision weighting

ph_data = ph_dur_full[['state', 'week_start_date', 'min_per_machine_ph', 'all_machine_count']].copy()
xxx_data = sw_full[['state', 'week_start_date', 'min_per_machine_xxx', 'all_machine_count']].copy()

# Share of minutes: Pornhub and All XXX as share of total duration
all_dur_full = (df_full.groupby(['state', 'week_start_date'])['total_duration_seconds']
                .sum().reset_index().rename(columns={'total_duration_seconds': 'total_dur'}))

ph_share_data = (ph_dur_full[['state', 'week_start_date', 'total_duration_seconds', 'all_machine_count']]
                 .merge(all_dur_full, on=['state', 'week_start_date']))
ph_share_data['share_ph'] = ph_share_data['total_duration_seconds'] / ph_share_data['total_dur'] * 100
ph_share_data = ph_share_data[['state', 'week_start_date', 'share_ph', 'all_machine_count']]

xxx_dur_merge = (df_full[df_full['coarse_category'].isin(XXX_CATEGORIES)]
                 .groupby(['state', 'week_start_date'])['total_duration_seconds']
                 .sum().reset_index().rename(columns={'total_duration_seconds': 'xxx_dur'}))
xxx_share_data = xxx_dur_merge.merge(all_dur_full, on=['state', 'week_start_date'])
xxx_share_data = xxx_share_data.merge(
    machines_full[['state', 'week_start_date', 'all_machine_count']],
    on=['state', 'week_start_date'])
xxx_share_data['share_xxx'] = xxx_share_data['xxx_dur'] / xxx_share_data['total_dur'] * 100
xxx_share_data = xxx_share_data[['state', 'week_start_date', 'share_xxx', 'all_machine_count']]

# Log minutes
log_ph_data = ph_data.copy()
log_ph_data['log_min_ph'] = np.log(log_ph_data['min_per_machine_ph'] + 0.01)
log_ph_data = log_ph_data[['state', 'week_start_date', 'log_min_ph', 'all_machine_count']]

log_xxx_data = xxx_data.copy()
log_xxx_data['log_min_xxx'] = np.log(log_xxx_data['min_per_machine_xxx'] + 0.01)
log_xxx_data = log_xxx_data[['state', 'week_start_date', 'log_min_xxx', 'all_machine_count']]

# ============================================================
# TWFE A: Minutes per machine (weekly) — original
# ============================================================

print("  TWFE (min/machine, weekly)...")
res_ph = run_twfe_event_study(ph_data, 'min_per_machine_ph', panel_states, laws,
                               EVENT_PRE, EVENT_POST)
res_xxx = run_twfe_event_study(xxx_data, 'min_per_machine_xxx', panel_states, laws,
                                EVENT_PRE, EVENT_POST)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe(ax1, res_ph, 'Pornhub')
plot_twfe(ax2, res_xxx, 'All XXX')
fig.suptitle(f'TWFE Event Study (min/machine) — 14 States (excl. TX), [{EVENT_PRE}, +{EVENT_POST}] weeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe.png'))
plt.close(fig)
print("    Saved event_study_twfe.png")

# ============================================================
# TWFE B: Share of minutes (weekly)
# ============================================================

print("  TWFE (share of minutes, weekly)...")
res_ph_s = run_twfe_event_study(ph_share_data, 'share_ph', panel_states, laws,
                                 EVENT_PRE, EVENT_POST)
res_xxx_s = run_twfe_event_study(xxx_share_data, 'share_xxx', panel_states, laws,
                                  EVENT_PRE, EVENT_POST)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe(ax1, res_ph_s, 'Pornhub', ylabel='Coefficient (pp share)')
plot_twfe(ax2, res_xxx_s, 'All XXX', ylabel='Coefficient (pp share)')
fig.suptitle(f'TWFE Event Study (share of minutes, pp) — 14 States (excl. TX), [{EVENT_PRE}, +{EVENT_POST}] weeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_share.png'))
plt.close(fig)
print("    Saved event_study_twfe_share.png")

# ============================================================
# TWFE C: Log minutes (weekly)
# ============================================================

print("  TWFE (log minutes, weekly)...")
res_ph_l = run_twfe_event_study(log_ph_data, 'log_min_ph', panel_states, laws,
                                 EVENT_PRE, EVENT_POST)
res_xxx_l = run_twfe_event_study(log_xxx_data, 'log_min_xxx', panel_states, laws,
                                  EVENT_PRE, EVENT_POST)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe(ax1, res_ph_l, 'Pornhub', ylabel='Coefficient (log min)')
plot_twfe(ax2, res_xxx_l, 'All XXX', ylabel='Coefficient (log min)')
fig.suptitle(f'TWFE Event Study (log minutes) — 14 States (excl. TX), [{EVENT_PRE}, +{EVENT_POST}] weeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_log.png'))
plt.close(fig)
print("    Saved event_study_twfe_log.png")

# ============================================================
# TWFE D: Biweekly — min/machine, share, log
# ============================================================
# Collapse weeks to two-week periods to increase power.
# Event window becomes [-8, +4] in biweekly units (= [-16, +8] weeks).

BIWEEK_PRE = EVENT_PRE // 2   # -8
BIWEEK_POST = EVENT_POST // 2  # 4

print("  TWFE (biweekly, min/machine)...")
res_ph_bw = run_twfe_event_study(ph_data, 'min_per_machine_ph', panel_states, laws,
                                  BIWEEK_PRE, BIWEEK_POST, biweekly=True)
res_xxx_bw = run_twfe_event_study(xxx_data, 'min_per_machine_xxx', panel_states, laws,
                                   BIWEEK_PRE, BIWEEK_POST, biweekly=True)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe(ax1, res_ph_bw, 'Pornhub', period_label='Biweeks')
plot_twfe(ax2, res_xxx_bw, 'All XXX', period_label='Biweeks')
fig.suptitle(f'TWFE Event Study (biweekly, min/machine) — 14 States (excl. TX), [{BIWEEK_PRE}, +{BIWEEK_POST}] biweeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_biweekly.png'))
plt.close(fig)
print("    Saved event_study_twfe_biweekly.png")

print("  TWFE (biweekly, share)...")
res_ph_s_bw = run_twfe_event_study(ph_share_data, 'share_ph', panel_states, laws,
                                    BIWEEK_PRE, BIWEEK_POST, biweekly=True)
res_xxx_s_bw = run_twfe_event_study(xxx_share_data, 'share_xxx', panel_states, laws,
                                     BIWEEK_PRE, BIWEEK_POST, biweekly=True)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe(ax1, res_ph_s_bw, 'Pornhub', ylabel='Coefficient (pp share)', period_label='Biweeks')
plot_twfe(ax2, res_xxx_s_bw, 'All XXX', ylabel='Coefficient (pp share)', period_label='Biweeks')
fig.suptitle(f'TWFE Event Study (biweekly, share pp) — 14 States (excl. TX), [{BIWEEK_PRE}, +{BIWEEK_POST}] biweeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_biweekly_share.png'))
plt.close(fig)
print("    Saved event_study_twfe_biweekly_share.png")

print("  TWFE (biweekly, log)...")
res_ph_l_bw = run_twfe_event_study(log_ph_data, 'log_min_ph', panel_states, laws,
                                    BIWEEK_PRE, BIWEEK_POST, biweekly=True)
res_xxx_l_bw = run_twfe_event_study(log_xxx_data, 'log_min_xxx', panel_states, laws,
                                     BIWEEK_PRE, BIWEEK_POST, biweekly=True)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe(ax1, res_ph_l_bw, 'Pornhub', ylabel='Coefficient (log min)', period_label='Biweeks')
plot_twfe(ax2, res_xxx_l_bw, 'All XXX', ylabel='Coefficient (log min)', period_label='Biweeks')
fig.suptitle(f'TWFE Event Study (biweekly, log min) — 14 States (excl. TX), [{BIWEEK_PRE}, +{BIWEEK_POST}] biweeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_biweekly_log.png'))
plt.close(fig)
print("    Saved event_study_twfe_biweekly_log.png")

# ============================================================
# TWFE E: By category (weekly, min/machine) — 8 panels
# ============================================================

print("  TWFE by category (weekly)...")
fig, axes = plt.subplots(2, 4, figsize=(24, 10))

for ax, cat in zip(axes.flat, PANELS):
    cat_data = cat_sw_all[cat_sw_all['coarse_category'] == cat][
        ['state', 'week_start_date', 'min_per_machine']].copy()
    label = PANEL_LABELS[cat]
    print(f"    {label}...")
    res = run_twfe_event_study(cat_data, 'min_per_machine', panel_states, laws,
                                EVENT_PRE, EVENT_POST)
    plot_twfe(ax, res, label)

fig.suptitle(f'TWFE Event Study by Category — 14 Treated States (excl. TX), [{EVENT_PRE}, +{EVENT_POST}] weeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_by_category.png'))
plt.close(fig)
print("    Saved event_study_twfe_by_category.png")

# ============================================================
# TWFE F: By category (biweekly, min/machine) — 8 panels
# ============================================================

print("  TWFE by category (biweekly)...")
fig, axes = plt.subplots(2, 4, figsize=(24, 10))

for ax, cat in zip(axes.flat, PANELS):
    cat_data = cat_sw_all[cat_sw_all['coarse_category'] == cat][
        ['state', 'week_start_date', 'min_per_machine']].copy()
    label = PANEL_LABELS[cat]
    print(f"    {label}...")
    res = run_twfe_event_study(cat_data, 'min_per_machine', panel_states, laws,
                                BIWEEK_PRE, BIWEEK_POST, biweekly=True)
    plot_twfe(ax, res, label, period_label='Biweeks')

fig.suptitle(f'TWFE Event Study by Category (biweekly) — 14 States (excl. TX), [{BIWEEK_PRE}, +{BIWEEK_POST}] biweeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_by_category_biweekly.png'))
plt.close(fig)
print("    Saved event_study_twfe_by_category_biweekly.png")

# ============================================================================
# TWFE G–I: PRECISION-WEIGHTED (WLS by machine count)
# ============================================================================
# Small states (WY, SD, AK) have very few machines, making their per-machine
# rates noisy. Weighting by all_machine_count gives more precise state-weeks
# more influence, tightening CIs.

W = 'all_machine_count'

# G: Weighted, biweekly, min/machine — Pornhub + All XXX
print("  TWFE weighted (biweekly, min/machine)...")
res_ph_w = run_twfe_event_study(ph_data, 'min_per_machine_ph', panel_states, laws,
                                 BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W)
res_xxx_w = run_twfe_event_study(xxx_data, 'min_per_machine_xxx', panel_states, laws,
                                  BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe(ax1, res_ph_w, 'Pornhub', period_label='Biweeks')
plot_twfe(ax2, res_xxx_w, 'All XXX', period_label='Biweeks')
fig.suptitle(f'TWFE Event Study (weighted, biweekly, min/machine) — 14 States (excl. TX)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_weighted_biweekly.png'))
plt.close(fig)
print("    Saved event_study_twfe_weighted_biweekly.png")

# H: Weighted, biweekly, share
print("  TWFE weighted (biweekly, share)...")
res_ph_sw = run_twfe_event_study(ph_share_data, 'share_ph', panel_states, laws,
                                  BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W)
res_xxx_sw = run_twfe_event_study(xxx_share_data, 'share_xxx', panel_states, laws,
                                   BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe(ax1, res_ph_sw, 'Pornhub', ylabel='Coefficient (pp share)', period_label='Biweeks')
plot_twfe(ax2, res_xxx_sw, 'All XXX', ylabel='Coefficient (pp share)', period_label='Biweeks')
fig.suptitle(f'TWFE Event Study (weighted, biweekly, share pp) — 14 States (excl. TX)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_weighted_biweekly_share.png'))
plt.close(fig)
print("    Saved event_study_twfe_weighted_biweekly_share.png")

# I: Weighted, biweekly, log
print("  TWFE weighted (biweekly, log)...")
res_ph_lw = run_twfe_event_study(log_ph_data, 'log_min_ph', panel_states, laws,
                                  BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W)
res_xxx_lw = run_twfe_event_study(log_xxx_data, 'log_min_xxx', panel_states, laws,
                                   BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe(ax1, res_ph_lw, 'Pornhub', ylabel='Coefficient (log min)', period_label='Biweeks')
plot_twfe(ax2, res_xxx_lw, 'All XXX', ylabel='Coefficient (log min)', period_label='Biweeks')
fig.suptitle(f'TWFE Event Study (weighted, biweekly, log min) — 14 States (excl. TX)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_weighted_biweekly_log.png'))
plt.close(fig)
print("    Saved event_study_twfe_weighted_biweekly_log.png")

# J: Weighted, biweekly, by category — 8 panels
print("  TWFE weighted by category (biweekly)...")
fig, axes = plt.subplots(2, 4, figsize=(24, 10))

for ax, cat in zip(axes.flat, PANELS):
    cat_data = cat_sw_all[cat_sw_all['coarse_category'] == cat][
        ['state', 'week_start_date', 'min_per_machine', 'all_machine_count']].copy()
    label = PANEL_LABELS[cat]
    print(f"    {label}...")
    res = run_twfe_event_study(cat_data, 'min_per_machine', panel_states, laws,
                                BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W)
    plot_twfe(ax, res, label, period_label='Biweeks')

fig.suptitle(f'TWFE Event Study by Category (weighted, biweekly) — 14 States (excl. TX)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_weighted_by_category_biweekly.png'))
plt.close(fig)
print("    Saved event_study_twfe_weighted_by_category_biweekly.png")

# ============================================================================
# TWFE K: COMPARISON — UNWEIGHTED vs WEIGHTED (biweekly)
# ============================================================================
# Overlay both on same axes to see the precision gain from weighting.

print("  Creating unweighted vs weighted comparison plots...")

def plot_twfe_compare(ax, res_uw, res_w, title, ylabel='Coefficient (min/machine)'):
    """Overlay unweighted (gray) and weighted (maroon) TWFE on same axes."""
    # Unweighted in gray
    ax.fill_between(res_uw['event_time'], res_uw['ci_lo'], res_uw['ci_hi'],
                     color='gray', alpha=0.15)
    ax.plot(res_uw['event_time'], res_uw['coef'], color='gray',
            linewidth=1.5, marker='o', markersize=3, label='Unweighted')
    # Weighted in maroon
    ax.fill_between(res_w['event_time'], res_w['ci_lo'], res_w['ci_hi'],
                     color=UCHICAGO_MAROON, alpha=0.2)
    ax.plot(res_w['event_time'], res_w['coef'], color=UCHICAGO_MAROON,
            linewidth=2, marker='o', markersize=4, label='Weighted')
    ax.axvline(0, color='black', linestyle='--', linewidth=1)
    ax.axhline(0, color='gray', linewidth=0.8, alpha=0.5)
    ax.set_xlabel('Biweeks Since Law Effective')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=10)

# Min/machine comparison
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe_compare(ax1, res_ph_bw, res_ph_w, 'Pornhub')
plot_twfe_compare(ax2, res_xxx_bw, res_xxx_w, 'All XXX')
fig.suptitle('TWFE: Unweighted vs Machine-Weighted (biweekly, min/machine)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_compare_biweekly.png'))
plt.close(fig)
print("    Saved event_study_twfe_compare_biweekly.png")

# Share comparison
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe_compare(ax1, res_ph_s_bw, res_ph_sw, 'Pornhub', ylabel='Coefficient (pp share)')
plot_twfe_compare(ax2, res_xxx_s_bw, res_xxx_sw, 'All XXX', ylabel='Coefficient (pp share)')
fig.suptitle('TWFE: Unweighted vs Machine-Weighted (biweekly, share pp)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_compare_biweekly_share.png'))
plt.close(fig)
print("    Saved event_study_twfe_compare_biweekly_share.png")

# Log comparison
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe_compare(ax1, res_ph_l_bw, res_ph_lw, 'Pornhub', ylabel='Coefficient (log min)')
plot_twfe_compare(ax2, res_xxx_l_bw, res_xxx_lw, 'All XXX', ylabel='Coefficient (log min)')
fig.suptitle('TWFE: Unweighted vs Machine-Weighted (biweekly, log min)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_compare_biweekly_log.png'))
plt.close(fig)
print("    Saved event_study_twfe_compare_biweekly_log.png")

# ============================================================================
# TWFE L: CLUSTERED vs UNCLUSTERED comparison (weighted, biweekly)
# ============================================================================

print("  Creating clustered vs unclustered comparison...")

res_ph_nc = run_twfe_event_study(ph_data, 'min_per_machine_ph', panel_states, laws,
                                  BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W,
                                  cluster=False)
res_xxx_nc = run_twfe_event_study(xxx_data, 'min_per_machine_xxx', panel_states, laws,
                                   BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W,
                                   cluster=False)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe_compare(ax1, res_ph_w, res_ph_nc, 'Pornhub')
plot_twfe_compare(ax2, res_xxx_w, res_xxx_nc, 'All XXX')
# Relabel legend
for ax in [ax1, ax2]:
    ax.legend(['Clustered', '_', 'Robust (HC1)', '_'], fontsize=10)
fig.suptitle('TWFE: Clustered vs Robust SEs (weighted, biweekly, min/machine)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_clustered_vs_robust.png'))
plt.close(fig)
print("    Saved event_study_twfe_clustered_vs_robust.png")

# Also do share
res_ph_s_nc = run_twfe_event_study(ph_share_data, 'share_ph', panel_states, laws,
                                    BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W,
                                    cluster=False)
res_xxx_s_nc = run_twfe_event_study(xxx_share_data, 'share_xxx', panel_states, laws,
                                     BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W,
                                     cluster=False)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe_compare(ax1, res_ph_sw, res_ph_s_nc, 'Pornhub', ylabel='Coefficient (pp share)')
plot_twfe_compare(ax2, res_xxx_sw, res_xxx_s_nc, 'All XXX', ylabel='Coefficient (pp share)')
for ax in [ax1, ax2]:
    ax.legend(['Clustered', '_', 'Robust (HC1)', '_'], fontsize=10)
fig.suptitle('TWFE: Clustered vs Robust SEs (weighted, biweekly, share pp)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_clustered_vs_robust_share.png'))
plt.close(fig)
print("    Saved event_study_twfe_clustered_vs_robust_share.png")

# ============================================================================
# TWFE M: VISITOR SHARE (site_person_count / all_person_count)
# ============================================================================
#
# Extensive margin outcome: fraction of panel users who visited the site.
# Bounded [0, 100 pp], no zero-inflation, not sensitive to outlier sessions.
# Pornhub share is exact (single category); all-XXX share sums person counts
# across XXX categories (negligible double-counting: <0.01% of state-weeks).

print("Building visitor share panel data...")

ph_visitor_data = (df_full[df_full['coarse_category'] == 'PORNHUB.COM']
                   [['state', 'week_start_date', 'site_person_count',
                     'all_person_count', 'all_machine_count']].copy())
ph_visitor_data = ph_visitor_data[ph_visitor_data['all_person_count'] > 0].copy()
ph_visitor_data['visitor_share_ph'] = (ph_visitor_data['site_person_count'] /
                                        ph_visitor_data['all_person_count'] * 100)

xxx_person_sum = (df_full[df_full['coarse_category'].isin(XXX_CATEGORIES)]
                  .groupby(['state', 'week_start_date'])
                  .agg(xxx_person_count=('site_person_count', 'sum'),
                       all_person_count=('all_person_count', 'first'),
                       all_machine_count=('all_machine_count', 'first'))
                  .reset_index())
xxx_person_sum = xxx_person_sum[xxx_person_sum['all_person_count'] > 0].copy()
xxx_person_sum['visitor_share_xxx'] = (xxx_person_sum['xxx_person_count'] /
                                        xxx_person_sum['all_person_count'] * 100)

print("  TWFE M (visitor share, weekly)...")
res_ph_vs = run_twfe_event_study(ph_visitor_data, 'visitor_share_ph', panel_states, laws,
                                  EVENT_PRE, EVENT_POST)
res_xxx_vs = run_twfe_event_study(xxx_person_sum, 'visitor_share_xxx', panel_states, laws,
                                   EVENT_PRE, EVENT_POST)
res_ph_vs_w = run_twfe_event_study(ph_visitor_data, 'visitor_share_ph', panel_states, laws,
                                    EVENT_PRE, EVENT_POST, weight_col=W)
res_xxx_vs_w = run_twfe_event_study(xxx_person_sum, 'visitor_share_xxx', panel_states, laws,
                                     EVENT_PRE, EVENT_POST, weight_col=W)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe_compare(ax1, res_ph_vs, res_ph_vs_w, 'Pornhub', ylabel='pp of panel users visiting')
plot_twfe_compare(ax2, res_xxx_vs, res_xxx_vs_w, 'All XXX', ylabel='pp of panel users visiting')
fig.suptitle(f'TWFE Event Study (visitor share): Unweighted vs Weighted — 14 States (excl. TX), [{EVENT_PRE}, +{EVENT_POST}] weeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_visitor_share.png'))
plt.close(fig)
print("    Saved event_study_twfe_visitor_share.png")

# Report average CI widths
for label, res_uw, res_w in [('PH weekly', res_ph_vs, res_ph_vs_w),
                               ('XXX weekly', res_xxx_vs, res_xxx_vs_w)]:
    uw_width = (res_uw['ci_hi'] - res_uw['ci_lo']).mean()
    w_width  = (res_w['ci_hi']  - res_w['ci_lo']).mean()
    print(f"    {label}: avg CI width  unweighted={uw_width:.3f}pp  weighted={w_width:.3f}pp  "
          f"reduction={100*(uw_width-w_width)/uw_width:.1f}%")

print("  TWFE M (visitor share, biweekly)...")
res_ph_vs_bw = run_twfe_event_study(ph_visitor_data, 'visitor_share_ph', panel_states, laws,
                                     BIWEEK_PRE, BIWEEK_POST, biweekly=True)
res_xxx_vs_bw = run_twfe_event_study(xxx_person_sum, 'visitor_share_xxx', panel_states, laws,
                                      BIWEEK_PRE, BIWEEK_POST, biweekly=True)
res_ph_vs_bw_w = run_twfe_event_study(ph_visitor_data, 'visitor_share_ph', panel_states, laws,
                                       BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W)
res_xxx_vs_bw_w = run_twfe_event_study(xxx_person_sum, 'visitor_share_xxx', panel_states, laws,
                                        BIWEEK_PRE, BIWEEK_POST, biweekly=True, weight_col=W)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
plot_twfe_compare(ax1, res_ph_vs_bw, res_ph_vs_bw_w, 'Pornhub',
                  ylabel='pp of panel users visiting')
plot_twfe_compare(ax2, res_xxx_vs_bw, res_xxx_vs_bw_w, 'All XXX',
                  ylabel='pp of panel users visiting')
# fix legend labels (plot_twfe_compare hardcodes "Unweighted"/"Weighted")
for ax in [ax1, ax2]:
    ax.set_xlabel('Biweeks Since Law Effective')
fig.suptitle(f'TWFE Event Study (visitor share, biweekly): Unweighted vs Weighted — 14 States (excl. TX)',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_visitor_share_biweekly.png'))
plt.close(fig)
print("    Saved event_study_twfe_visitor_share_biweekly.png")

for label, res_uw, res_w in [('PH biweekly', res_ph_vs_bw, res_ph_vs_bw_w),
                               ('XXX biweekly', res_xxx_vs_bw, res_xxx_vs_bw_w)]:
    uw_width = (res_uw['ci_hi'] - res_uw['ci_lo']).mean()
    w_width  = (res_w['ci_hi']  - res_w['ci_lo']).mean()
    print(f"    {label}: avg CI width  unweighted={uw_width:.3f}pp  weighted={w_width:.3f}pp  "
          f"reduction={100*(uw_width-w_width)/uw_width:.1f}%")

# ============================================================================
# TWFE N: VISITOR SHARE BY CATEGORY (weekly, 8 panels)
# ============================================================================

print("  TWFE N (visitor share by category, weekly)...")

# Build per-category visitor share data
cat_visitor_sw = (df_full.groupby(['state', 'week_start_date', 'coarse_category'])
                  [['site_person_count', 'all_person_count', 'all_machine_count']]
                  .first().reset_index())
cat_visitor_sw = cat_visitor_sw[cat_visitor_sw['all_person_count'] > 0].copy()
cat_visitor_sw['visitor_share'] = (cat_visitor_sw['site_person_count'] /
                                    cat_visitor_sw['all_person_count'] * 100)

# Also add "All XXX excl. Pornhub" visitor share
xxx_no_ph_visitor = (df_full[df_full['coarse_category'].isin(
                         [c for c in XXX_CATEGORIES if c != 'PORNHUB.COM'])]
                     .groupby(['state', 'week_start_date'])
                     .agg(xxx_person_count=('site_person_count', 'sum'),
                          all_person_count=('all_person_count', 'first'),
                          all_machine_count=('all_machine_count', 'first'))
                     .reset_index())
xxx_no_ph_visitor = xxx_no_ph_visitor[xxx_no_ph_visitor['all_person_count'] > 0].copy()
xxx_no_ph_visitor['visitor_share'] = (xxx_no_ph_visitor['xxx_person_count'] /
                                       xxx_no_ph_visitor['all_person_count'] * 100)
xxx_no_ph_visitor['coarse_category'] = 'All XXX excl. Pornhub'

cat_visitor_all = pd.concat([cat_visitor_sw, xxx_no_ph_visitor], ignore_index=True)

fig, axes = plt.subplots(2, 4, figsize=(24, 10))

for ax, cat in zip(axes.flat, PANELS):
    cat_d = cat_visitor_all[cat_visitor_all['coarse_category'] == cat][
        ['state', 'week_start_date', 'visitor_share', 'all_machine_count']].copy()
    label = PANEL_LABELS[cat]
    print(f"    {label}...")
    res = run_twfe_event_study(cat_d, 'visitor_share', panel_states, laws,
                                EVENT_PRE, EVENT_POST, weight_col=W)
    plot_twfe(ax, res, label, ylabel='pp of panel users visiting')

fig.suptitle(f'TWFE Event Study (visitor share by category, weighted) — 14 States (excl. TX), [{EVENT_PRE}, +{EVENT_POST}] weeks',
             fontsize=16, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(output_dir, 'event_study_twfe_visitor_share_by_category.png'))
plt.close(fig)
print("    Saved event_study_twfe_visitor_share_by_category.png")

print(f"\nDone. Outputs saved to {output_dir}")
