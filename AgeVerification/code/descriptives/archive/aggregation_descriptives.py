# Author: Hannah Lybbert, assisted by Claude
# Created: 02/16/2026
# Last updated: 02/16/2026
# Purpose: Descriptive statistics and preliminary figures for aggregated XXX site usage data

"""
Descriptive Statistics for Aggregated Data
Analyzes time spent on XXX sites (top 5 + other) across states and time, comparing
states that passed age verification laws vs. control states.

Usage: python code/descriptives/aggregation_descriptives.py

Inputs:
- data/Aggregation/aggregated_file/final_aggregated.csv
- raw/statelaws/statelaws_dates.csv

Outputs:
- output/descriptives/Aggregation/*.png (figures)
- output/descriptives/Aggregation/*.csv (summary tables)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

# Import house plotting style
import sys
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", ".."))
sys.path.insert(0, os.path.join(project_root, "code"))
from plot_style import apply_plot_style, UCHICAGO_MAROON, COLOR_PALETTE

# Apply house style
apply_plot_style()

# ============================================================================
# SETUP PATHS
# ============================================================================

# Build paths from project root
data_file = os.path.join(project_root, "data", "Aggregation", "aggregated_file", "final_aggregated.csv")
laws_file = os.path.join(project_root, "raw", "statelaws", "statelaws_dates.csv")
output_dir = os.path.join(project_root, "output", "descriptives", "Aggregation")
os.makedirs(output_dir, exist_ok=True)

print("="*80)
print("DESCRIPTIVE STATISTICS - AGGREGATED DATA")
print("="*80)
print(f"\nProject root: {project_root}")
print(f"Output directory: {output_dir}")

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_aggregated_data():
    """Load the main aggregated data file and exclude XX, ZZ, DC, US."""
    print("\n[1/3] Loading aggregated data...")
    df = pd.read_csv(data_file)

    # Exclude non-state entries (XX, ZZ, DC, US)
    # DC and US are critical to exclude as US is aggregate data that would contaminate control group
    excluded_states = ['XX', 'ZZ', 'DC', 'US']
    df = df[~df['state'].isin(excluded_states)].copy()

    # Convert week_start_date to datetime
    df['week_start_date'] = pd.to_datetime(df['week_start_date'])

    print(f"  Loaded {len(df):,} rows (excluding XX, ZZ, DC, US)")
    print(f"  States: {df['state'].nunique()}")
    print(f"  Weeks: {df['week_of_sample'].min()} to {df['week_of_sample'].max()}")
    print(f"  Date range: {df['week_start_date'].min().date()} to {df['week_start_date'].max().date()}")
    print(f"  Categories: {df['coarse_category'].nunique()}")
    return df

def load_state_laws():
    """Load state age verification laws data and exclude DC and US."""
    print("\n[2/3] Loading state laws data...")
    laws = pd.read_csv(laws_file)

    # CRITICAL: Exclude DC and US (not proper states, US is aggregate data)
    excluded_pseudo_states = ['DC', 'US']
    laws = laws[~laws['state'].isin(excluded_pseudo_states)].copy()

    # Convert date columns to datetime
    laws['day_passed'] = pd.to_datetime(laws['day_passed'], format='%d%b%Y', errors='coerce')
    laws['day_effective'] = pd.to_datetime(laws['day_effective'], format='%d%b%Y', errors='coerce')

    # Create treatment indicator (any state with non-null effective date)
    laws['treated'] = laws['day_effective'].notna().astype(int)

    print(f"  Loaded {len(laws)} states (excluded DC, US)")
    print(f"  Treated states: {laws['treated'].sum()}")
    print(f"  Control states: {(1 - laws['treated']).sum()}")

    return laws

def create_additional_date_variables(df):
    """Add additional date variables for analysis.

    week_start_date is loaded directly from the aggregation output (precise dates from time_lookup).
    This function just adds derived date variables for convenience.
    """
    print("\n[3/3] Creating additional date variables...")

    # week_start_date is already loaded from the CSV (precise dates from aggregation)
    # Just add week_end_date and other derived variables
    df['week_end_date'] = df['week_start_date'] + pd.to_timedelta(6, unit='D')

    # Create year-month for aggregation
    df['year'] = df['week_start_date'].dt.year
    df['month'] = df['week_start_date'].dt.month
    df['year_month'] = df['week_start_date'].dt.to_period('M')

    # Validation
    print(f"  Date range: {df['week_start_date'].min().date()} to {df['week_end_date'].max().date()}")
    print(f"  Total weeks: {df['week_of_sample'].nunique()}")

    # Ensure no data extends beyond 2024
    if df['week_start_date'].max().year > 2024:
        print(f"  WARNING: Data extends into {df['week_start_date'].max().year}!")
        print(f"  Last week start: {df['week_start_date'].max().date()}")
    else:
        print(f"  [OK] All data within 2022-2024 as expected")

    return df

# ============================================================================
# TREATMENT VARIABLE FUNCTIONS
# ============================================================================

def create_treatment_variables(df, laws):
    """Create treatment indicators for when laws were passed and effective."""
    print("\n" + "="*80)
    print("CREATING TREATMENT VARIABLES")
    print("="*80)

    # DIAGNOSTIC: Check which states are in data vs laws file
    states_in_data = set(df['state'].unique())
    states_in_laws = set(laws['state'].unique())

    missing_from_data = states_in_laws - states_in_data
    missing_from_laws = states_in_data - states_in_laws

    if missing_from_data:
        print(f"\n[WARNING] States in laws file but MISSING from aggregated data:")
        print(f"     {sorted(missing_from_data)}")
        print(f"     Count: {len(missing_from_data)}")
        print(f"     Note: NH and NJ are expected to be missing (Comscore markets below threshold)")
    if missing_from_laws:
        print(f"\n[WARNING] States in aggregated data but MISSING from laws file:")
        print(f"     {sorted(missing_from_laws)}")
        print(f"     Count: {len(missing_from_laws)}")

    print(f"\nState counts:")
    print(f"  States in aggregated data: {len(states_in_data)}")
    print(f"  States in laws file (excl. DC, US): {len(states_in_laws)}")
    print(f"  Expected: 50 states")

    # Merge laws data with main dataset
    df = df.merge(laws[['state', 'day_passed', 'day_effective', 'treated']],
                  on='state', how='left')

    # Create treatment indicators
    # post_passed: indicator for periods after law was passed
    df['post_passed'] = ((df['week_start_date'] >= df['day_passed']) &
                         df['day_passed'].notna()).astype(int)

    # post_effective: indicator for periods after law became effective (main treatment)
    df['post_effective'] = ((df['week_start_date'] >= df['day_effective']) &
                            df['day_effective'].notna()).astype(int)

    # Create event time relative to law effective date (for event studies)
    df['weeks_to_effective'] = ((df['week_start_date'] - df['day_effective']).dt.days / 7).round().astype('Int64')

    # Treated indicator (ever-treated)
    df['treated'] = df['treated'].fillna(0).astype(int)

    print(f"\nTreatment variable summary:")
    print(f"  Ever-treated states: {df[df['treated']==1]['state'].nunique()}")
    print(f"  Never-treated states: {df[df['treated']==0]['state'].nunique()}")
    print(f"  State-weeks with law effective: {df['post_effective'].sum():,}")

    # List treated and non-treated states
    treated_states = sorted(df[df['treated']==1]['state'].unique())
    control_states = sorted(df[df['treated']==0]['state'].unique())
    print(f"\n  Treated states ({len(treated_states)}): {', '.join(treated_states)}")
    print(f"\n  Control states ({len(control_states)}): {', '.join(control_states)}")

    # Show timing of treatments
    treatment_timing = df[df['treated']==1].groupby('state').agg({
        'day_passed': 'first',
        'day_effective': 'first'
    }).sort_values('day_effective')

    print(f"\nTreatment timing by state:")
    print(treatment_timing.to_string())

    return df

# ============================================================================
# DESCRIPTIVE STATISTICS FUNCTIONS
# ============================================================================

def data_coverage_summary(df):
    """Generate data coverage and sample statistics."""
    print("\n" + "="*80)
    print("DATA COVERAGE & SAMPLE STATISTICS")
    print("="*80)

    stats = {
        'total_observations': len(df),
        'n_states': df['state'].nunique(),
        'n_weeks': df['week_of_sample'].nunique(),
        'n_categories': df['coarse_category'].nunique(),
        'date_start': df['week_start_date'].min().date(),
        'date_end': df['week_end_date'].max().date(),
        'avg_machines_per_state_week': df['all_machine_count'].mean(),
        'avg_persons_per_state_week': df['all_person_count'].mean()
    }

    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Check for missing data patterns
    print("\n[Missing Data Patterns]")
    missing_by_col = df.isnull().sum()
    print(missing_by_col[missing_by_col > 0])

    # Investigate missing log hours
    if df['log_hrs_per_machine'].isnull().sum() > 0:
        print(f"\n[Investigating missing log hours]")
        missing_logs = df[df['log_hrs_per_machine'].isnull()]
        print(f"  Total missing: {len(missing_logs):,} / {len(df):,} ({len(missing_logs)/len(df)*100:.2f}%)")
        print(f"\n  Missing by state:")
        print(missing_logs['state'].value_counts().head(10))
        print(f"\n  Missing by category:")
        print(missing_logs['coarse_category'].value_counts())
        print(f"\n  Sample of rows with missing logs:")
        print(missing_logs[['state', 'week_start_date', 'coarse_category',
                            'total_duration_seconds', 'site_machine_count']].head(10))

    # States with most missing weeks
    weeks_by_state = df.groupby('state')['week_of_sample'].nunique()
    max_weeks = weeks_by_state.max()
    missing_weeks = max_weeks - weeks_by_state

    print(f"\n[States with missing weeks]")
    print(f"  Max weeks observed: {max_weeks}")
    if (missing_weeks > 0).any():
        print("\n  States missing weeks:")
        print(missing_weeks[missing_weeks > 0].sort_values(ascending=False))
    else:
        print("  No states missing weeks - complete panel!")

    # Save summary
    summary_df = pd.DataFrame([stats])
    summary_file = os.path.join(output_dir, "data_coverage_summary.csv")
    summary_df.to_csv(summary_file, index=False)
    print(f"\n  Saved to: {summary_file}")

    return stats

def balance_table(df):
    """Compare treated vs control states on pre-treatment characteristics.

    For never-treated states: uses all data before the earliest treatment date
    For ever-treated states: uses only data before their own treatment date
    """
    print("\n" + "="*80)
    print("BALANCE TABLE - PRE-TREATMENT CHARACTERISTICS")
    print("="*80)

    # Define pre-treatment period differently for treated vs control states
    # For never-treated states: use all data before earliest treatment
    first_treatment = df[df['post_effective']==1]['week_start_date'].min()

    # For ever-treated states: use only data before their own treatment (post_effective==0)
    # For never-treated states: use all data before first treatment date
    pre_treatment = df[
        ((df['treated'] == 1) & (df['post_effective'] == 0)) |  # Treated states: pre-treatment only
        ((df['treated'] == 0) & (df['week_start_date'] < first_treatment))  # Control states: before earliest treatment
    ].copy()

    print(f"\nPre-treatment period:")
    print(f"  - Never-treated states: {pre_treatment[pre_treatment['treated']==0]['week_start_date'].min().date()} to {first_treatment.date()}")
    print(f"  - Ever-treated states: varies by state (before own treatment date)")
    print(f"  Total observations: {len(pre_treatment):,}")
    print(f"  Treated state obs: {len(pre_treatment[pre_treatment['treated']==1]):,}")
    print(f"  Control state obs: {len(pre_treatment[pre_treatment['treated']==0]):,}")

    # Calculate means by treatment group and category
    balance = pre_treatment.groupby(['treated', 'coarse_category']).agg({
        'all_machine_count': 'mean',
        'all_person_count': 'mean',
        'site_machine_count': 'mean',
        'site_person_count': 'mean',
        'total_duration_seconds': 'mean',
        'log_hrs_per_machine': 'mean',
        'log_hrs_per_person': 'mean'
    }).reset_index()

    # Pivot to wide format for comparison
    balance_wide = balance.pivot(index='coarse_category',
                                  columns='treated',
                                  values=['all_machine_count', 'all_person_count',
                                         'log_hrs_per_machine', 'log_hrs_per_person'])

    # Calculate differences
    for metric in ['all_machine_count', 'all_person_count', 'log_hrs_per_machine', 'log_hrs_per_person']:
        if (metric, 0) in balance_wide.columns and (metric, 1) in balance_wide.columns:
            balance_wide[(metric, 'difference')] = balance_wide[(metric, 1)] - balance_wide[(metric, 0)]

    # Clean column names
    balance_wide.columns = ['_'.join([str(c) for c in col]).strip('_') for col in balance_wide.columns]
    balance_wide = balance_wide.reset_index()

    print("\nBalance table:")
    print(balance_wide.to_string())

    # Save balance table
    balance_file = os.path.join(output_dir, "balance_table_pretreatment.csv")
    balance_wide.to_csv(balance_file, index=False)
    print(f"\n  Saved to: {balance_file}")

    return balance_wide

def baseline_usage_statistics(df):
    """Calculate baseline usage statistics for pre-treatment period.

    For never-treated states: uses all data before the earliest treatment date
    For ever-treated states: uses only data before their own treatment date
    """
    print("\n" + "="*80)
    print("BASELINE USAGE STATISTICS (PRE-TREATMENT)")
    print("="*80)

    # Define pre-treatment period (same logic as balance_table)
    first_treatment = df[df['post_effective']==1]['week_start_date'].min()

    pre_treatment = df[
        ((df['treated'] == 1) & (df['post_effective'] == 0)) |  # Treated states: pre-treatment only
        ((df['treated'] == 0) & (df['week_start_date'] < first_treatment))  # Control states: before earliest treatment
    ].copy()

    # 1. Average hours per machine/person by category
    print("\n[Average log hours per machine/person by category]")
    avg_by_category = pre_treatment.groupby('coarse_category').agg({
        'log_hrs_per_machine': 'mean',
        'log_hrs_per_person': 'mean',
        'total_duration_seconds': 'sum'
    }).round(3)
    print(avg_by_category)

    # 2. Distribution across states
    print("\n[Average usage by state (top 10)]")
    avg_by_state = pre_treatment[pre_treatment['coarse_category']!='all_other_sites'].groupby('state').agg({
        'log_hrs_per_machine': 'mean',
        'total_duration_seconds': 'sum'
    }).sort_values('log_hrs_per_machine', ascending=False).head(10).round(3)
    print(avg_by_state)

    # 3. Correlation between top 5 sites
    print("\n[Correlation between top 5 sites (log hours per machine)]")
    top5_data = pre_treatment[~pre_treatment['coarse_category'].isin(['other_XXX_sites', 'all_other_sites'])]
    top5_pivot = top5_data.pivot_table(
        index=['state', 'week_of_sample'],
        columns='coarse_category',
        values='log_hrs_per_machine'
    )
    correlation = top5_pivot.corr().round(3)
    print(correlation)

    # 4. Share of XXX traffic from top 5 vs other
    print("\n[Share of XXX traffic: Top 5 vs Other XXX sites]")
    xxx_only = pre_treatment[pre_treatment['coarse_category']!='all_other_sites'].copy()
    xxx_only['is_top5'] = ~xxx_only['coarse_category'].isin(['other_XXX_sites', 'all_other_sites'])

    total_xxx_duration = xxx_only['total_duration_seconds'].sum()
    top5_duration = xxx_only[xxx_only['is_top5']]['total_duration_seconds'].sum()
    other_duration = xxx_only[~xxx_only['is_top5']]['total_duration_seconds'].sum()

    print(f"  Top 5 share: {(top5_duration/total_xxx_duration)*100:.2f}%")
    print(f"  Other XXX share: {(other_duration/total_xxx_duration)*100:.2f}%")

    # Save statistics
    stats_file = os.path.join(output_dir, "baseline_usage_statistics.csv")
    avg_by_category.to_csv(stats_file)

    corr_file = os.path.join(output_dir, "baseline_top5_correlation.csv")
    correlation.to_csv(corr_file)

    print(f"\n  Saved baseline statistics to: {output_dir}")

    return avg_by_category, correlation

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def plot_treatment_timeline(df):
    """Visualize timeline of law enactments - shows when laws became effective."""
    print("\n[Plotting treatment timeline...]")

    # Get unique treatment dates by state
    treatments = df[df['treated']==1].groupby('state').agg({
        'day_passed': 'first',
        'day_effective': 'first'
    }).sort_values('day_effective').reset_index()

    fig, ax = plt.subplots(figsize=(12, 8))

    # Plot markers at law effective dates
    y_pos = range(len(treatments))

    # Draw horizontal lines from sample start to law effective date
    sample_start = pd.to_datetime('2022-01-01')
    for i, row in treatments.iterrows():
        # Line from sample start to law effective (pre-treatment)
        ax.plot([sample_start, row['day_effective']],
               [i, i], color='gray', linewidth=3, alpha=0.3)
        # Marker at law effective date
        ax.scatter(row['day_effective'], i, color=UCHICAGO_MAROON,
                  s=100, zorder=3, marker='D')

    # Format
    ax.set_yticks(y_pos)
    ax.set_yticklabels(treatments['state'])
    ax.set_xlabel('Date')
    ax.set_title('Age Verification Laws: When Laws Became Effective by State',
                fontsize=16, fontweight='bold')

    # Add legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='gray', linewidth=3, alpha=0.3, label='Pre-treatment period'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor=UCHICAGO_MAROON,
              markersize=8, label='Law becomes effective')
    ]
    ax.legend(handles=legend_elements, loc='lower right')

    ax.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()

    output_file = os.path.join(output_dir, "treatment_timeline.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved to: {output_file}")

def plot_time_trends_by_category(df):
    """Plot overall time trends in XXX site usage by category (all states averaged)."""
    print("\n[Plotting time trends by category (all states)...]")

    # Exclude 'all_other_sites' for XXX-focused analysis
    # NOTE: "XXX site usage" = Top 5 + other_XXX_sites
    xxx_df = df[df['coarse_category'] != 'all_other_sites'].copy()

    # Aggregate by week and category (across all states)
    weekly_trends = xxx_df.groupby(['week_start_date', 'coarse_category']).agg({
        'log_hrs_per_machine': 'mean'
    }).reset_index()

    # Separate top 5 from other_XXX_sites
    top5 = weekly_trends[weekly_trends['coarse_category'] != 'other_XXX_sites']
    other_xxx = weekly_trends[weekly_trends['coarse_category'] == 'other_XXX_sites']

    # Create two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: Top 5 individual sites
    for i, category in enumerate(top5['coarse_category'].unique()):
        data = top5[top5['coarse_category'] == category]
        ax1.plot(data['week_start_date'], data['log_hrs_per_machine'],
                label=category, linewidth=2, color=COLOR_PALETTE[i])

    ax1.set_ylabel('Log Hours per Machine')
    ax1.set_title('Time Trends: Top 5 XXX Sites (All States Average)',
                 fontsize=14, fontweight='bold')
    ax1.legend(loc='best', ncol=2)
    ax1.grid(True, alpha=0.3)

    # Plot 2: All other XXX sites
    ax2.plot(other_xxx['week_start_date'], other_xxx['log_hrs_per_machine'],
            linewidth=2, color=UCHICAGO_MAROON, label='Other XXX Sites')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Log Hours per Machine')
    ax2.set_title('Time Trends: Other XXX Sites Pooled (All States Average)',
                 fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    output_file = os.path.join(output_dir, "time_trends_by_category.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved to: {output_file}")

def plot_xxx_share_of_browsing(df):
    """Plot share of total browsing time spent on XXX sites over time (all states average).
    Note: XXX sites = Top 5 + other_XXX_sites."""
    print("\n[Plotting XXX share of total browsing time (all states average)...]")

    # Calculate total duration by week for XXX vs all sites
    weekly_duration = df.groupby(['week_start_date', 'state']).apply(
        lambda x: pd.Series({
            'xxx_duration': x[x['coarse_category'] != 'all_other_sites']['total_duration_seconds'].sum(),
            'total_duration': x['total_duration_seconds'].sum()
        })
    ).reset_index()

    # Calculate share
    weekly_duration['xxx_share'] = (weekly_duration['xxx_duration'] / weekly_duration['total_duration']) * 100

    # Aggregate across states
    avg_share = weekly_duration.groupby('week_start_date')['xxx_share'].mean().reset_index()

    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(avg_share['week_start_date'], avg_share['xxx_share'],
           linewidth=2, color=UCHICAGO_MAROON)

    ax.set_xlabel('Date')
    ax.set_ylabel('XXX Share of Total Browsing Time (%)')
    ax.set_title('Share of Total Browsing Time Spent on XXX Sites Over Time (All States Average)',
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Add horizontal line at mean
    mean_share = avg_share['xxx_share'].mean()
    ax.axhline(mean_share, color='gray', linestyle='--', alpha=0.5,
              label=f'Mean: {mean_share:.2f}%')

    # Add note
    ax.text(0.02, 0.98, 'XXX sites = Top 5 + other_XXX_sites',
           transform=ax.transAxes, fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    ax.legend()

    plt.tight_layout()

    output_file = os.path.join(output_dir, "xxx_share_of_browsing.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved to: {output_file}")

    print(f"\n  Average XXX share: {mean_share:.2f}%")
    print(f"  Min: {avg_share['xxx_share'].min():.2f}%")
    print(f"  Max: {avg_share['xxx_share'].max():.2f}%")

def plot_state_heterogeneity(df):
    """Plot distribution of usage across states (pre-treatment period only).

    For never-treated states: uses all data before the earliest treatment date
    For ever-treated states: uses only data before their own treatment date
    """
    print("\n[Plotting state heterogeneity...]")

    # Pre-treatment period only (same logic as balance_table)
    first_treatment = df[df['post_effective']==1]['week_start_date'].min()

    pre_df = df[
        ((df['treated'] == 1) & (df['post_effective'] == 0)) |  # Treated states: pre-treatment only
        ((df['treated'] == 0) & (df['week_start_date'] < first_treatment))  # Control states: before earliest treatment
    ].copy()

    # Focus on XXX sites
    xxx_df = pre_df[pre_df['coarse_category'] != 'all_other_sites']

    # Average log hours by state
    state_avg = xxx_df.groupby('state').agg({
        'log_hrs_per_machine': 'mean',
        'treated': 'first'
    }).sort_values('log_hrs_per_machine', ascending=False).reset_index()

    # Plot
    fig, ax = plt.subplots(figsize=(14, 8))

    colors = [UCHICAGO_MAROON if t == 1 else COLOR_PALETTE[2] for t in state_avg['treated']]
    bars = ax.bar(range(len(state_avg)), state_avg['log_hrs_per_machine'], color=colors, alpha=0.7)

    ax.set_xticks(range(len(state_avg)))
    ax.set_xticklabels(state_avg['state'], rotation=90)
    ax.set_ylabel('Average Log Hours per Machine (XXX Sites)')
    ax.set_title('Pre-Treatment XXX Site Usage by State', fontsize=14, fontweight='bold')

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=UCHICAGO_MAROON, alpha=0.7, label='Treated States'),
                      Patch(facecolor=COLOR_PALETTE[2], alpha=0.7, label='Control States')]
    ax.legend(handles=legend_elements, loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    output_file = os.path.join(output_dir, "state_heterogeneity.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved to: {output_file}")

    # Print top 5 states
    print(f"\n[Top 5 states by XXX usage (pre-treatment)]")
    print(state_avg.head(5)[['state', 'log_hrs_per_machine', 'treated']])

def plot_event_study(df):
    """Event study plot: treated vs control states (±52 weeks)."""
    print("\n[Plotting event study (treated vs control)...]")

    # Focus on XXX sites only
    xxx_df = df[df['coarse_category'] != 'all_other_sites'].copy()

    # TREATED STATES: Keep only weeks within +/- 52 weeks of treatment
    treated_df = xxx_df[(xxx_df['treated'] == 1) &
                        (xxx_df['weeks_to_effective'] >= -52) &
                        (xxx_df['weeks_to_effective'] <= 52)]

    treated_means = treated_df.groupby('weeks_to_effective').agg({
        'log_hrs_per_machine': 'mean'
    }).reset_index()

    # CONTROL STATES: Select random 104 consecutive weeks
    control_df = xxx_df[xxx_df['treated'] == 0].copy()
    control_weeks = sorted(control_df['week_of_sample'].unique())

    # Pick a random starting week (same seed as parallel trends for consistency)
    np.random.seed(42)
    max_start = len(control_weeks) - 104
    start_idx = np.random.randint(0, max_start + 1)
    selected_weeks = control_weeks[start_idx:start_idx + 104]

    control_subset = control_df[control_df['week_of_sample'].isin(selected_weeks)].copy()

    # Create event time for control (centered at midpoint)
    min_week = control_subset['week_of_sample'].min()
    control_subset['weeks_relative'] = control_subset['week_of_sample'] - min_week - 52

    control_means = control_subset.groupby('weeks_relative').agg({
        'log_hrs_per_machine': 'mean'
    }).reset_index()

    # Plot
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot treated states
    ax.plot(treated_means['weeks_to_effective'], treated_means['log_hrs_per_machine'],
           linewidth=2.5, color=UCHICAGO_MAROON, marker='o', markersize=3,
           label='Treated States', alpha=0.8)

    # Plot control states
    ax.plot(control_means['weeks_relative'], control_means['log_hrs_per_machine'],
           linewidth=2.5, color=COLOR_PALETTE[2], marker='o', markersize=3,
           label='Control States', alpha=0.8)

    # Add vertical line at treatment
    ax.axvline(0, color='black', linestyle='--', linewidth=2,
              label='Law Effective Date (Treated)')

    ax.set_xlabel('Weeks Relative to Law Effective Date')
    ax.set_ylabel('Log Hours per Machine (XXX Sites)')
    ax.set_title('Event Study: XXX Site Usage (±52 weeks, Treated vs Control)',
                fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    output_file = os.path.join(output_dir, "event_study.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved to: {output_file}")

def plot_la_specific(df):
    """Plot Louisiana-specific trends for all 6 XXX categories (top 5 + other_XXX_sites)."""
    print("\n[Plotting Louisiana-specific trends...]")

    # Filter to Louisiana only and XXX sites only
    la_df = df[(df['state'] == 'LA') &
               (df['coarse_category'] != 'all_other_sites')].copy()

    # Get LA's law effective date
    la_law_date = la_df['day_effective'].iloc[0]

    # Aggregate by week and category
    la_trends = la_df.groupby(['week_start_date', 'coarse_category']).agg({
        'log_hrs_per_machine': 'mean'
    }).reset_index()

    # Separate top 5 from other_XXX_sites
    top5_categories = [cat for cat in la_trends['coarse_category'].unique()
                      if cat != 'other_XXX_sites']

    # Plot
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot top 5 sites
    for i, category in enumerate(sorted(top5_categories)):
        data = la_trends[la_trends['coarse_category'] == category]
        ax.plot(data['week_start_date'], data['log_hrs_per_machine'],
               label=category, linewidth=2, color=COLOR_PALETTE[i], alpha=0.8)

    # Plot other_XXX_sites
    other_data = la_trends[la_trends['coarse_category'] == 'other_XXX_sites']
    ax.plot(other_data['week_start_date'], other_data['log_hrs_per_machine'],
           label='other_XXX_sites', linewidth=2.5, color='black',
           linestyle='--', alpha=0.7)

    # Add vertical line at law enactment
    if pd.notna(la_law_date):
        ax.axvline(la_law_date, color='red', linestyle=':', linewidth=3,
                  label=f'Law Enacted\n({la_law_date.strftime("%b %d, %Y")})',
                  alpha=0.7)

    ax.set_xlabel('Date')
    ax.set_ylabel('Log Hours per Machine')
    ax.set_title('Louisiana: XXX Site Usage Over Time (All Categories)',
                fontsize=14, fontweight='bold')
    ax.legend(loc='best', ncol=2)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    output_file = os.path.join(output_dir, "louisiana_specific_trends.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved to: {output_file}")
    print(f"  LA law effective date: {la_law_date.strftime('%b %d, %Y') if pd.notna(la_law_date) else 'N/A'}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""

    # Load data
    df = load_aggregated_data()
    laws = load_state_laws()

    # Create date and treatment variables
    df = create_additional_date_variables(df)
    df = create_treatment_variables(df, laws)

    # Generate descriptive statistics
    print("\n" + "="*80)
    print("GENERATING DESCRIPTIVE STATISTICS")
    print("="*80)

    data_coverage_summary(df)
    balance_table(df)
    baseline_usage_statistics(df)

    # Generate visualizations
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)

    plot_treatment_timeline(df)
    plot_time_trends_by_category(df)
    plot_xxx_share_of_browsing(df)
    plot_state_heterogeneity(df)
    plot_event_study(df)  # Event study with markers (±52 weeks, treated vs control)
    plot_la_specific(df)  # NEW: Louisiana-specific trends

    print("\n" + "="*80)
    print("COMPLETE - ALL OUTPUTS SAVED")
    print("="*80)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    for file in sorted(os.listdir(output_dir)):
        print(f"  - {file}")

if __name__ == "__main__":
    main()
