"""
Analyze Full Demographic Panel: 36 Months (Jan 2022 - Dec 2024)

This script analyzes the complete demographic panel across all 36 months to understand:
- Pairwise retention between any two months
- Panel stability and attrition patterns over time
- Panel size trends
- Data for event study design

Key Output: 36x36 retention matrix showing count of machines present in both
"past month" (row) and "future month" (column).

Usage:
    python3 code/ProcessComscore/data_structure_validation/analyze_full_panel.py

Outputs:
    - output/ProcessComscore/data_structure_validation/retention_matrix_36m.csv
    - output/ProcessComscore/data_structure_validation/monthly_panel_composition.csv
    - data/ProcessComscore/data_structure_validation/retention_statistics_36m.csv
    - output/ProcessComscore/data_structure_validation/retention_heatmap_36m.png
    - output/ProcessComscore/data_structure_validation/retention_curves_36m.png
    - output/ProcessComscore/data_structure_validation/panel_churn_36m.png
    - output/ProcessComscore/data_structure_validation/panel_size_trend_36m.png
    - data/ProcessComscore/data_structure_validation/full_panel_analysis_36m.txt
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from datetime import datetime
import sys

# Add parent directory to path to import plot_style
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from plot_style import apply_plot_style, UCHICAGO_MAROON, COLOR_PALETTE

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Column names for demographic files
DEMOGRAPHIC_COLUMNS = [
    'machine_id',
    'country',
    'metro_area',
    'DMA_code',
    'device_type',
    'age_range',
    'HHI',
    'children',
    'household_size',
    'month_id'
]


def generate_month_list():
    """Generate list of month IDs from Jan 2022 to Dec 2024."""
    months = pd.date_range('2022-01', '2024-12', freq='MS')
    month_ids = [d.strftime('%Y%m') for d in months]
    return month_ids


def load_all_demographic_files(raw_dir):
    """
    Load all 36 demographic files and extract machine_id sets.

    Memory-efficient: loads files sequentially and keeps only machine_id sets.

    Args:
        raw_dir: Path to directory containing demographic files

    Returns:
        Dict mapping month_id to set of machine_ids
    """
    logger.info("Loading all demographic files...")

    month_ids = generate_month_list()
    machine_sets = {}

    for i, month_id in enumerate(month_ids, 1):
        file_path = raw_dir / f'US_comscore_machine_demos_{month_id}.txt.gz'

        if not file_path.exists():
            logger.warning(f"  [{i}/36] File not found: {file_path.name}")
            continue

        logger.info(f"  [{i}/36] Loading {month_id}...")

        try:
            # Load file
            df = pd.read_csv(
                file_path,
                sep='\t',
                compression='gzip',
                header=None,
                names=DEMOGRAPHIC_COLUMNS,
                dtype={'machine_id': str},
                low_memory=False,
                usecols=['machine_id']  # Only load machine_id column
            )

            # Extract unique machine_ids as set
            machine_set = set(df['machine_id'].dropna())
            machine_sets[month_id] = machine_set

            logger.info(f"      Found {len(machine_set):,} unique machines")

        except Exception as e:
            logger.error(f"  Error loading {month_id}: {e}")
            continue

    logger.info(f"\nSuccessfully loaded {len(machine_sets)} months")
    return machine_sets


def compute_retention_matrix(machine_sets):
    """
    Compute 36x36 retention matrix.

    Matrix[i,j] = count of machines present in both month i and month j
    - Diagonal: panel size for that month
    - Upper triangle: retention counts (future months)
    - Lower triangle: zeros (not meaningful)

    Args:
        machine_sets: Dict mapping month_id to set of machine_ids

    Returns:
        Tuple of (matrix as numpy array, sorted month_ids list)
    """
    logger.info("\nComputing 36x36 retention matrix...")

    month_ids = sorted(machine_sets.keys())
    n = len(month_ids)

    # Initialize matrix
    matrix = np.zeros((n, n), dtype=np.uint32)

    # Compute pairwise intersections
    for i, month_i in enumerate(month_ids):
        for j, month_j in enumerate(month_ids):
            if i <= j:  # Diagonal and upper triangle only
                intersection_count = len(machine_sets[month_i] & machine_sets[month_j])
                matrix[i, j] = intersection_count

    logger.info(f"  Computed {n}x{n} retention matrix")
    logger.info(f"  Diagonal (panel sizes): {matrix.diagonal().min():,} to {matrix.diagonal().max():,}")

    return matrix, month_ids


def save_retention_matrix(matrix, month_ids, output_path):
    """Save retention matrix as CSV with proper row/column headers."""
    logger.info(f"\nSaving retention matrix to {output_path}...")

    df = pd.DataFrame(matrix, index=month_ids, columns=month_ids)
    df.to_csv(output_path)

    logger.info(f"  Saved {df.shape[0]}x{df.shape[1]} matrix")


def compute_retention_statistics(machine_sets, matrix, month_ids):
    """
    Compute retention statistics and panel composition.

    Returns:
        Tuple of (monthly_composition_df, retention_stats_df)
    """
    logger.info("\nComputing retention statistics...")

    # Monthly panel composition
    composition_data = []
    for i, month_id in enumerate(month_ids):
        panel_size = len(machine_sets[month_id])

        # Month-to-month change
        if i > 0:
            prev_month_id = month_ids[i-1]
            prev_machines = machine_sets[prev_month_id]
            curr_machines = machine_sets[month_id]

            retained = len(prev_machines & curr_machines)
            lost = len(prev_machines - curr_machines)
            new = len(curr_machines - prev_machines)
            retention_rate = retained / len(prev_machines) if len(prev_machines) > 0 else 0
        else:
            retained = panel_size
            lost = 0
            new = 0
            retention_rate = 1.0

        composition_data.append({
            'month': month_id,
            'panel_size': panel_size,
            'retained_from_previous': retained,
            'lost_from_previous': lost,
            'new_machines': new,
            'retention_rate': retention_rate
        })

    composition_df = pd.DataFrame(composition_data)

    # Retention decay statistics (from first month)
    first_month_machines = machine_sets[month_ids[0]]
    first_month_size = len(first_month_machines)

    decay_data = []
    for i, month_id in enumerate(month_ids):
        months_elapsed = i
        retained_count = matrix[0, i]  # From first month to this month
        retention_rate = retained_count / first_month_size

        decay_data.append({
            'months_elapsed': months_elapsed,
            'target_month': month_id,
            'machines_retained_from_202201': retained_count,
            'retention_rate_from_202201': retention_rate
        })

    decay_df = pd.DataFrame(decay_data)

    logger.info(f"  Month-to-month retention: {composition_df['retention_rate'].mean():.1%} average")
    logger.info(f"  First-to-last retention: {decay_df.iloc[-1]['retention_rate_from_202201']:.1%}")

    return composition_df, decay_df


def plot_retention_heatmap(matrix, month_ids, output_path):
    """Create heatmap visualization of retention matrix."""
    logger.info(f"\nCreating retention heatmap...")

    apply_plot_style()

    # Mask lower triangle (except diagonal)
    mask = np.tril(np.ones_like(matrix, dtype=bool), k=-1)

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 12))

    # Create colormap (white to maroon)
    from matplotlib.colors import LinearSegmentedColormap
    colors = ['#FFFFFF', UCHICAGO_MAROON]
    n_bins = 100
    cmap = LinearSegmentedColormap.from_list('maroon', colors, N=n_bins)

    # Plot heatmap
    sns.heatmap(
        matrix,
        mask=mask,
        cmap=cmap,
        annot=False,
        fmt='d',
        square=True,
        linewidths=0.5,
        cbar_kws={'label': 'Machine Count'},
        xticklabels=month_ids,
        yticklabels=month_ids,
        ax=ax
    )

    ax.set_xlabel('Future Month')
    ax.set_ylabel('Past Month')
    ax.set_title('Panel Retention Matrix: Machine Overlap Between Months', fontweight='bold')

    # Rotate labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    plt.setp(ax.get_yticklabels(), rotation=0)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved heatmap to {output_path}")


def plot_retention_curves(machine_sets, matrix, month_ids, output_path):
    """Plot retention decay curves for all starting months."""
    logger.info(f"\nCreating retention curves for all starting months...")

    apply_plot_style()

    fig, ax = plt.subplots(figsize=(14, 8))

    # Compute retention curve for each starting month
    for i, start_month in enumerate(month_ids):
        start_size = len(machine_sets[start_month])
        retention_rates = []
        months_forward = []

        for j in range(i, len(month_ids)):
            months_elapsed = j - i
            retained_count = matrix[i, j]
            retention_rate = (retained_count / start_size * 100) if start_size > 0 else 0

            retention_rates.append(retention_rate)
            months_forward.append(months_elapsed)

        # Plot with varying transparency - older starting months more transparent
        alpha = 0.2 + (i / len(month_ids)) * 0.6  # Range from 0.2 to 0.8

        # Highlight first, middle, and last starting months
        if i == 0:
            ax.plot(months_forward, retention_rates, color=UCHICAGO_MAROON,
                   linewidth=3, alpha=1.0, label=f'{start_month} (first)', zorder=10)
        elif i == len(month_ids) - 1:
            ax.plot(months_forward, retention_rates, color=COLOR_PALETTE[1],
                   linewidth=2.5, alpha=1.0, label=f'{start_month} (last)', zorder=9)
        elif i == len(month_ids) // 2:
            ax.plot(months_forward, retention_rates, color=COLOR_PALETTE[2],
                   linewidth=2.5, alpha=1.0, label=f'{start_month} (mid)', zorder=8)
        else:
            ax.plot(months_forward, retention_rates, color='gray',
                   linewidth=1, alpha=alpha, zorder=1)

    ax.set_xlabel('Months Elapsed from Starting Month')
    ax.set_ylabel('Retention Rate (%)')
    ax.set_title('Panel Retention Decay: All Starting Months', fontweight='bold')
    ax.legend()
    ax.set_ylim(0, 105)
    ax.set_xlim(0, 35)

    # Add reference lines
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.3, linewidth=1)
    ax.axhline(y=25, color='gray', linestyle='--', alpha=0.3, linewidth=1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved retention curves to {output_path}")


def plot_panel_trend(composition_df, output_path):
    """Plot panel size trend over time."""
    logger.info(f"\nCreating panel size trend plot...")

    apply_plot_style()

    fig, ax = plt.subplots(figsize=(12, 7))

    # Convert month to datetime for better x-axis formatting
    composition_df['date'] = pd.to_datetime(composition_df['month'], format='%Y%m')

    # Plot panel size
    ax.plot(
        composition_df['date'],
        composition_df['panel_size'] / 1000,  # Convert to thousands
        color=UCHICAGO_MAROON,
        linewidth=3,
        marker='o',
        markersize=5
    )

    ax.set_xlabel('Month')
    ax.set_ylabel('Panel Size (thousands)')
    ax.set_title('Demographic Panel Size Over Time', fontweight='bold')

    # Format x-axis
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    # Add annotations for first and last
    first_size = composition_df.iloc[0]['panel_size']
    last_size = composition_df.iloc[-1]['panel_size']
    first_date = composition_df.iloc[0]['date']
    last_date = composition_df.iloc[-1]['date']

    ax.annotate(f'{first_size:,}',
                xy=(first_date, first_size/1000),
                xytext=(10, 10),
                textcoords='offset points',
                fontsize=10)
    ax.annotate(f'{last_size:,}',
                xy=(last_date, last_size/1000),
                xytext=(10, -20),
                textcoords='offset points',
                fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved panel trend to {output_path}")


def plot_panel_churn(composition_df, output_path):
    """Plot panel churn: new machines added, machines lost, and net change."""
    logger.info(f"\nCreating panel churn plot...")

    apply_plot_style()

    fig, ax = plt.subplots(figsize=(14, 8))

    # Convert month to datetime for better x-axis formatting
    composition_df['date'] = pd.to_datetime(composition_df['month'], format='%Y%m')

    # Skip first month (no previous month to compare to)
    plot_df = composition_df.iloc[1:].copy()

    # Plot lost machines as negative
    ax.bar(
        plot_df['date'],
        -plot_df['lost_from_previous'] / 1000,  # Negative for losses
        color=COLOR_PALETTE[4],  # Dark gray
        alpha=0.7,
        label='Machines Lost',
        width=20
    )

    # Plot new machines as positive
    ax.bar(
        plot_df['date'],
        plot_df['new_machines'] / 1000,
        color=COLOR_PALETTE[1],  # Burnt orange
        alpha=0.7,
        label='New Machines',
        width=20
    )

    # Plot net change as prominent line
    net_change = plot_df['new_machines'] - plot_df['lost_from_previous']
    ax.plot(
        plot_df['date'],
        net_change / 1000,
        color=UCHICAGO_MAROON,
        linewidth=4,
        marker='o',
        markersize=6,
        label='Net Change',
        zorder=10
    )

    # Add zero line
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)

    ax.set_xlabel('Month')
    ax.set_ylabel('Change in Panel Size (thousands)')
    ax.set_title('Panel Churn: Monthly Additions, Losses, and Net Change', fontweight='bold')

    # Format x-axis
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    ax.legend(loc='best')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved panel churn plot to {output_path}")


def generate_summary_report(composition_df, decay_df, matrix, month_ids, output_path):
    """Generate comprehensive text report."""
    logger.info(f"\nGenerating summary report...")

    with open(output_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("FULL PANEL ANALYSIS: 36 MONTHS (JAN 2022 - DEC 2024)\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        # Overall panel statistics
        f.write("1. OVERALL PANEL STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Analysis Period: {month_ids[0]} to {month_ids[-1]}\n")
        f.write(f"Total Months: {len(month_ids)}\n\n")

        first_size = composition_df.iloc[0]['panel_size']
        last_size = composition_df.iloc[-1]['panel_size']
        change = last_size - first_size
        pct_change = (change / first_size) * 100

        f.write(f"Starting Panel Size (Jan 2022): {first_size:,}\n")
        f.write(f"Ending Panel Size (Dec 2024): {last_size:,}\n")
        f.write(f"Net Change: {change:,} ({pct_change:+.1f}%)\n\n")

        # Panel retention from first month
        f.write("2. RETENTION FROM JAN 2022\n")
        f.write("-" * 80 + "\n")
        for i in [0, 5, 11, 17, 23, 29, 35]:  # 0, 6, 12, 18, 24, 30, 36 months
            if i < len(decay_df):
                row = decay_df.iloc[i]
                f.write(f"After {row['months_elapsed']:2d} months ({row['target_month']}): ")
                f.write(f"{row['machines_retained_from_202201']:,} machines ")
                f.write(f"({row['retention_rate_from_202201']:.1%})\n")
        f.write("\n")

        # Month-to-month statistics
        f.write("3. MONTH-TO-MONTH STABILITY\n")
        f.write("-" * 80 + "\n")
        avg_retention = composition_df['retention_rate'].mean()
        min_retention = composition_df['retention_rate'].min()
        max_retention = composition_df['retention_rate'].max()

        f.write(f"Average month-to-month retention: {avg_retention:.1%}\n")
        f.write(f"Range: {min_retention:.1%} to {max_retention:.1%}\n\n")

        # Periods with lowest retention
        lowest_retention = composition_df.nsmallest(5, 'retention_rate')[['month', 'retention_rate']]
        f.write("Months with lowest retention from previous month:\n")
        for _, row in lowest_retention.iterrows():
            f.write(f"  {row['month']}: {row['retention_rate']:.1%}\n")
        f.write("\n")

        # Panel churn summary
        f.write("4. PANEL CHURN SUMMARY\n")
        f.write("-" * 80 + "\n")
        total_lost = composition_df['lost_from_previous'].sum()
        total_new = composition_df['new_machines'].sum()
        f.write(f"Total machines lost over 36 months: {total_lost:,}\n")
        f.write(f"Total new machines added over 36 months: {total_new:,}\n")
        f.write(f"Net churn: {total_new - total_lost:,}\n\n")

        # Retention matrix statistics
        f.write("5. RETENTION MATRIX STATISTICS\n")
        f.write("-" * 80 + "\n")
        # Get upper triangle values (excluding diagonal)
        upper_triangle = matrix[np.triu_indices_from(matrix, k=1)]
        f.write(f"Total pairwise comparisons: {len(upper_triangle):,}\n")
        f.write(f"Average retention count: {upper_triangle.mean():,.0f}\n")
        f.write(f"Median retention count: {np.median(upper_triangle):,.0f}\n")
        f.write(f"Min retention count: {upper_triangle.min():,}\n")
        f.write(f"Max retention count: {upper_triangle.max():,}\n\n")

        # Implications for event study
        f.write("6. IMPLICATIONS FOR EVENT STUDY DESIGN\n")
        f.write("-" * 80 + "\n")
        f.write(f"- Panel exhibits substantial attrition ({100-decay_df.iloc[-1]['retention_rate_from_202201']*100:.1f}% over 36 months)\n")
        f.write(f"- Month-to-month stability is moderate ({avg_retention:.1%} average)\n")
        f.write(f"- Retention matrix available for sample selection decisions\n")
        f.write(f"- Consider balanced vs. unbalanced panel trade-offs\n")

        f.write("=" * 80 + "\n")

    logger.info(f"  Saved report to {output_path}")


def main():
    """Main execution function."""

    # Define paths
    base_dir = Path('/Users/mattbrownecon/Documents/Research/AgeVerification')
    raw_dir = base_dir / 'raw' / 'desktop_demographics'
    data_dir = base_dir / 'data' / 'ProcessComscore' / 'data_structure_validation'
    output_dir = base_dir / 'output' / 'ProcessComscore' / 'data_structure_validation'

    # Create output directories
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("FULL 36-MONTH DEMOGRAPHIC PANEL ANALYSIS")
    logger.info("=" * 80)

    # Step 1: Load all files and extract machine_id sets
    machine_sets = load_all_demographic_files(raw_dir)

    if len(machine_sets) == 0:
        logger.error("No demographic files loaded. Exiting.")
        return

    # Step 2: Compute retention matrix
    matrix, month_ids = compute_retention_matrix(machine_sets)

    # Step 3: Save retention matrix (to output/)
    save_retention_matrix(
        matrix,
        month_ids,
        output_dir / 'retention_matrix_36m.csv'
    )

    # Step 4: Compute statistics
    composition_df, decay_df = compute_retention_statistics(machine_sets, matrix, month_ids)

    # Save statistics
    composition_df.to_csv(output_dir / 'monthly_panel_composition.csv', index=False)
    decay_df.to_csv(data_dir / 'retention_statistics_36m.csv', index=False)

    # Step 5: Create visualizations
    plot_retention_heatmap(
        matrix,
        month_ids,
        output_dir / 'retention_heatmap_36m.png'
    )

    plot_retention_curves(
        machine_sets,
        matrix,
        month_ids,
        output_dir / 'retention_curves_36m.png'
    )

    plot_panel_churn(
        composition_df,
        output_dir / 'panel_churn_36m.png'
    )

    plot_panel_trend(
        composition_df,
        output_dir / 'panel_size_trend_36m.png'
    )

    # Step 6: Generate report
    generate_summary_report(
        composition_df,
        decay_df,
        matrix,
        month_ids,
        data_dir / 'full_panel_analysis_36m.txt'
    )

    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"\nOutputs saved to:")
    logger.info(f"  Data: {data_dir}/")
    logger.info(f"  Plots: {output_dir}/")


if __name__ == "__main__":
    main()
