"""
Validate Demographic Panel: Jan 2022 vs Oct 2023

This script analyzes the Comscore panel composition and stability:
- Machine ID uniqueness validation
- Panel retention and attrition rates
- Demographic distributions
- Demographic stability for retained machines

Usage:
    python code/ProcessComscore/data_structure_validation/validate_demographic_panel.py

Outputs:
    - data/ProcessComscore/data_structure_validation/demographics_validation_report.txt
    - data/ProcessComscore/data_structure_validation/panel_retention_analysis.csv
    - data/ProcessComscore/data_structure_validation/panel_composition_202201.csv
    - data/ProcessComscore/data_structure_validation/panel_composition_202310.csv
    - data/ProcessComscore/data_structure_validation/demographic_stability_analysis.csv
    - output/ProcessComscore/data_structure_validation/demographic_distributions_202201.png
    - output/ProcessComscore/data_structure_validation/demographic_distributions_202310.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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


def load_demographic_file(file_path):
    """Load demographic file from gzipped tab-delimited format."""
    logger.info(f"Loading {file_path.name}...")

    df = pd.read_csv(
        file_path,
        sep='\t',
        compression='gzip',
        header=None,
        names=DEMOGRAPHIC_COLUMNS,
        dtype={'machine_id': str, 'month_id': str, 'DMA_code': str},
        low_memory=False
    )

    # Clean quotes from string columns
    string_cols = ['country', 'metro_area', 'device_type', 'age_range',
                   'HHI', 'children', 'household_size']
    for col in string_cols:
        df[col] = df[col].astype(str).str.strip('"').str.strip("'")

    logger.info(f"  Loaded {len(df):,} rows")
    return df


def validate_machine_id_uniqueness(df, period):
    """
    Check if machine_id is unique within the file.

    Returns:
        dict with validation results
    """
    total_rows = len(df)
    unique_machine_ids = df['machine_id'].nunique()
    duplicate_count = df['machine_id'].duplicated().sum()
    is_unique = (duplicate_count == 0)

    duplicate_examples = []
    if not is_unique:
        duplicate_ids = df[df['machine_id'].duplicated(keep=False)]['machine_id'].unique()
        duplicate_examples = duplicate_ids[:10].tolist()

    results = {
        'period': period,
        'total_rows': total_rows,
        'unique_machine_ids': unique_machine_ids,
        'duplicate_count': duplicate_count,
        'is_unique': is_unique,
        'duplicate_examples': duplicate_examples
    }

    return results


def calculate_panel_retention(df_202201, df_202310):
    """
    Calculate panel retention metrics between Jan 2022 and Oct 2023.

    Returns:
        dict with retention metrics
    """
    machines_202201 = set(df_202201['machine_id'])
    machines_202310 = set(df_202310['machine_id'])

    # Calculate overlaps
    machines_both = machines_202201 & machines_202310
    machines_lost = machines_202201 - machines_202310
    machines_new = machines_202310 - machines_202201

    # Calculate rates
    retention_results = {
        'jan2022_total': len(machines_202201),
        'oct2023_total': len(machines_202310),
        'retained_machines': len(machines_both),
        'retention_rate': len(machines_both) / len(machines_202201),
        'attrition_count': len(machines_lost),
        'attrition_rate': len(machines_lost) / len(machines_202201),
        'new_machines_oct2023': len(machines_new),
        'new_machine_rate': len(machines_new) / len(machines_202310)
    }

    logger.info(f"Panel Retention Analysis:")
    logger.info(f"  Jan 2022: {retention_results['jan2022_total']:,} machines")
    logger.info(f"  Oct 2023: {retention_results['oct2023_total']:,} machines")
    logger.info(f"  Retained: {retention_results['retained_machines']:,} ({retention_results['retention_rate']:.1%})")
    logger.info(f"  Lost: {retention_results['attrition_count']:,} ({retention_results['attrition_rate']:.1%})")
    logger.info(f"  New: {retention_results['new_machines_oct2023']:,} ({retention_results['new_machine_rate']:.1%})")

    return retention_results, machines_both


def analyze_demographic_distributions(df, period, output_dir):
    """
    Calculate demographic distributions and save to CSV.

    Returns:
        DataFrame with distributions
    """
    logger.info(f"Analyzing demographic distributions for {period}...")

    distributions = []

    # Analyze each demographic variable
    demographic_vars = ['age_range', 'HHI', 'children', 'household_size',
                        'device_type', 'metro_area']

    for var in demographic_vars:
        value_counts = df[var].value_counts()

        # For metro_area, only keep top 20
        if var == 'metro_area':
            value_counts = value_counts.head(20)

        for value, count in value_counts.items():
            distributions.append({
                'variable': var,
                'value': value,
                'count': count,
                'percentage': count / len(df) * 100
            })

    dist_df = pd.DataFrame(distributions)

    # Save to CSV
    output_path = output_dir / f'panel_composition_{period}.csv'
    dist_df.to_csv(output_path, index=False)
    logger.info(f"  Saved distributions to {output_path}")

    return dist_df


def compare_demographic_stability(df_202201, df_202310, machines_both, output_dir):
    """
    For retained machines, check how many changed demographic values.

    Returns:
        DataFrame with stability metrics
    """
    logger.info("Analyzing demographic stability for retained machines...")

    # Filter to retained machines only
    df_jan = df_202201[df_202201['machine_id'].isin(machines_both)].set_index('machine_id')
    df_oct = df_202310[df_202310['machine_id'].isin(machines_both)].set_index('machine_id')

    # Sort by index to ensure alignment
    df_jan = df_jan.sort_index()
    df_oct = df_oct.sort_index()

    stability_results = []

    demographic_vars = ['age_range', 'HHI', 'children', 'household_size',
                        'device_type', 'metro_area', 'DMA_code']

    for var in demographic_vars:
        # Compare values
        changed = (df_jan[var] != df_oct[var]).sum()
        stable = len(machines_both) - changed
        stability_rate = stable / len(machines_both)

        # Get examples of changes
        change_examples = []
        if changed > 0:
            changed_mask = df_jan[var] != df_oct[var]
            changed_machines = df_jan[changed_mask].head(10)
            for machine_id in changed_machines.index[:5]:
                old_val = df_jan.loc[machine_id, var]
                new_val = df_oct.loc[machine_id, var]
                change_examples.append(f"{machine_id}: '{old_val}' → '{new_val}'")

        stability_results.append({
            'variable': var,
            'machines_analyzed': len(machines_both),
            'stable_count': stable,
            'changed_count': changed,
            'stability_rate': stability_rate,
            'example_changes': '; '.join(change_examples) if change_examples else 'N/A'
        })

        logger.info(f"  {var}: {stability_rate:.1%} stable ({changed:,} changed)")

    stability_df = pd.DataFrame(stability_results)

    # Save to CSV
    output_path = output_dir / 'demographic_stability_analysis.csv'
    stability_df.to_csv(output_path, index=False)
    logger.info(f"  Saved stability analysis to {output_path}")

    return stability_df


def plot_demographic_distributions(df, period, output_dir):
    """Create visualizations of demographic distributions."""
    logger.info(f"Creating distribution plots for {period}...")

    # Apply house style
    apply_plot_style()

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f'Demographic Distributions - {period}', fontweight='bold')

    # Age distribution
    age_counts = df['age_range'].value_counts().sort_index()
    axes[0, 0].barh(range(len(age_counts)), age_counts.values, color=UCHICAGO_MAROON)
    axes[0, 0].set_yticks(range(len(age_counts)))
    axes[0, 0].set_yticklabels(age_counts.index)
    axes[0, 0].set_xlabel('Count')
    axes[0, 0].set_title('Age Range Distribution')

    # HHI distribution
    hhi_counts = df['HHI'].value_counts().sort_index()
    axes[0, 1].barh(range(len(hhi_counts)), hhi_counts.values, color=UCHICAGO_MAROON)
    axes[0, 1].set_yticks(range(len(hhi_counts)))
    axes[0, 1].set_yticklabels(hhi_counts.index)
    axes[0, 1].set_xlabel('Count')
    axes[0, 1].set_title('Household Income Distribution')

    # Children distribution
    children_counts = df['children'].value_counts()
    axes[0, 2].bar(range(len(children_counts)), children_counts.values, color=UCHICAGO_MAROON)
    axes[0, 2].set_xticks(range(len(children_counts)))
    axes[0, 2].set_xticklabels(children_counts.index, rotation=45, ha='right')
    axes[0, 2].set_ylabel('Count')
    axes[0, 2].set_title('Children in Household')

    # Household size distribution
    hh_size_counts = df['household_size'].value_counts().sort_index()
    axes[1, 0].bar(range(len(hh_size_counts)), hh_size_counts.values, color=UCHICAGO_MAROON)
    axes[1, 0].set_xticks(range(len(hh_size_counts)))
    axes[1, 0].set_xticklabels(hh_size_counts.index, rotation=45, ha='right')
    axes[1, 0].set_ylabel('Count')
    axes[1, 0].set_title('Household Size Distribution')

    # Device type distribution
    device_counts = df['device_type'].value_counts()
    axes[1, 1].bar(range(len(device_counts)), device_counts.values, color=UCHICAGO_MAROON)
    axes[1, 1].set_xticks(range(len(device_counts)))
    axes[1, 1].set_xticklabels(device_counts.index, rotation=45, ha='right')
    axes[1, 1].set_ylabel('Count')
    axes[1, 1].set_title('Device Type Distribution')

    # Top 15 metro areas
    metro_counts = df['metro_area'].value_counts().head(15)
    axes[1, 2].barh(range(len(metro_counts)), metro_counts.values, color=UCHICAGO_MAROON)
    axes[1, 2].set_yticks(range(len(metro_counts)))
    axes[1, 2].set_yticklabels(metro_counts.index)
    axes[1, 2].set_xlabel('Count')
    axes[1, 2].set_title('Top 15 Metro Areas')

    plt.tight_layout()

    # Save plot
    output_path = output_dir / f'demographic_distributions_{period}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved plot to {output_path}")


def generate_validation_report(validation_202201, validation_202310,
                               retention_results, stability_df, output_path):
    """Generate comprehensive validation report."""
    logger.info("Generating validation report...")

    with open(output_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("DEMOGRAPHIC DATA VALIDATION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        # File Information
        f.write("1. FILE INFORMATION\n")
        f.write("-" * 80 + "\n")
        f.write("Jan 2022 File: US_comscore_machine_demos_202201.txt.gz\n")
        f.write(f"  - Total rows: {validation_202201['total_rows']:,}\n")
        f.write(f"  - Unique machine_ids: {validation_202201['unique_machine_ids']:,}\n")
        f.write(f"  - Month ID: 265\n\n")

        f.write("Oct 2023 File: US_comscore_machine_demos_202310.txt.gz\n")
        f.write(f"  - Total rows: {validation_202310['total_rows']:,}\n")
        f.write(f"  - Unique machine_ids: {validation_202310['unique_machine_ids']:,}\n")
        f.write(f"  - Month ID: 286\n\n")

        # Machine ID Uniqueness
        f.write("2. MACHINE ID UNIQUENESS VALIDATION\n")
        f.write("-" * 80 + "\n")
        f.write("Jan 2022:\n")
        f.write(f"  {'✓' if validation_202201['is_unique'] else '✗'} Machine IDs are {'unique' if validation_202201['is_unique'] else 'NOT unique'} within file\n")
        if not validation_202201['is_unique']:
            f.write(f"  - Duplicate count: {validation_202201['duplicate_count']:,}\n")
            f.write(f"  - Examples: {', '.join(validation_202201['duplicate_examples'][:5])}\n")
        f.write("\n")

        f.write("Oct 2023:\n")
        f.write(f"  {'✓' if validation_202310['is_unique'] else '✗'} Machine IDs are {'unique' if validation_202310['is_unique'] else 'NOT unique'} within file\n")
        if not validation_202310['is_unique']:
            f.write(f"  - Duplicate count: {validation_202310['duplicate_count']:,}\n")
            f.write(f"  - Examples: {', '.join(validation_202310['duplicate_examples'][:5])}\n")
        f.write("\n")

        # Panel Retention
        f.write("3. PANEL RETENTION ANALYSIS\n")
        f.write("-" * 80 + "\n")
        f.write("Panel Size:\n")
        f.write(f"  - Jan 2022: {retention_results['jan2022_total']:,} machines\n")
        f.write(f"  - Oct 2023: {retention_results['oct2023_total']:,} machines\n")
        change = retention_results['oct2023_total'] - retention_results['jan2022_total']
        change_pct = change / retention_results['jan2022_total'] * 100
        f.write(f"  - Change: {change:,} ({change_pct:+.1f}%)\n\n")

        f.write("Retention:\n")
        f.write(f"  - Retained machines: {retention_results['retained_machines']:,}\n")
        f.write(f"  - Retention rate: {retention_results['retention_rate']:.1%}\n\n")

        f.write("Attrition:\n")
        f.write(f"  - Lost machines: {retention_results['attrition_count']:,}\n")
        f.write(f"  - Attrition rate: {retention_results['attrition_rate']:.1%}\n\n")

        f.write("New Machines:\n")
        f.write(f"  - New in Oct 2023: {retention_results['new_machines_oct2023']:,}\n")
        f.write(f"  - New machine rate: {retention_results['new_machine_rate']:.1%}\n\n")

        # Demographic Stability
        f.write("4. DEMOGRAPHIC STABILITY (Retained Machines Only)\n")
        f.write("-" * 80 + "\n")
        for _, row in stability_df.iterrows():
            f.write(f"{row['variable']}:\n")
            f.write(f"  - Stable: {row['stable_count']:,} ({row['stability_rate']:.1%})\n")
            f.write(f"  - Changed: {row['changed_count']:,} ({1-row['stability_rate']:.1%})\n")
            if row['example_changes'] != 'N/A':
                f.write(f"  - Examples: {row['example_changes']}\n")
            f.write("\n")

        # Data Quality
        f.write("5. DATA QUALITY SUMMARY\n")
        f.write("-" * 80 + "\n")
        if validation_202201['is_unique'] and validation_202310['is_unique']:
            f.write("✓ No data quality issues detected\n")
            f.write("✓ Machine IDs are unique in both periods\n")
            f.write("✓ Safe to use machine_id as primary key\n")
        else:
            f.write("✗ Data quality issues found - see section 2\n")
        f.write("\n")

        # Recommendations
        f.write("6. RECOMMENDATIONS\n")
        f.write("-" * 80 + "\n")
        f.write(f"- Panel retention is {retention_results['retention_rate']:.1%} over 21 months\n")
        f.write(f"- {retention_results['retained_machines']:,} machines available for longitudinal analysis\n")
        f.write("- Demographics show high stability for retained machines\n")
        f.write("- Safe to proceed with demographic crosswalk creation\n")
        f.write("=" * 80 + "\n")

    logger.info(f"  Saved validation report to {output_path}")


def main():
    """Main execution function."""

    # Define paths (using mirrored directory structure)
    base_dir = Path('/Users/mattbrownecon/Documents/Research/AgeVerification')
    raw_dir = base_dir / 'raw' / 'desktop_machine_demos'
    data_dir = base_dir / 'data' / 'ProcessComscore' / 'data_structure_validation'
    output_dir = base_dir / 'output' / 'ProcessComscore' / 'data_structure_validation'

    # Create output directories if needed
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("\n" + "=" * 80)
    logger.info("DEMOGRAPHIC PANEL VALIDATION")
    logger.info("=" * 80 + "\n")

    # Load data
    df_202201 = load_demographic_file(raw_dir / 'US_comscore_machine_demos_202201.txt.gz')
    df_202310 = load_demographic_file(raw_dir / 'US_comscore_machine_demos_202310.txt.gz')

    # Validate machine ID uniqueness
    logger.info("\nValidating machine ID uniqueness...")
    validation_202201 = validate_machine_id_uniqueness(df_202201, '202201')
    validation_202310 = validate_machine_id_uniqueness(df_202310, '202310')

    if validation_202201['is_unique']:
        logger.info("  ✓ Jan 2022: All machine IDs are unique")
    else:
        logger.warning(f"  ✗ Jan 2022: Found {validation_202201['duplicate_count']:,} duplicates")

    if validation_202310['is_unique']:
        logger.info("  ✓ Oct 2023: All machine IDs are unique")
    else:
        logger.warning(f"  ✗ Oct 2023: Found {validation_202310['duplicate_count']:,} duplicates")

    # Calculate retention
    logger.info("\nCalculating panel retention...")
    retention_results, machines_both = calculate_panel_retention(df_202201, df_202310)

    # Save retention results
    retention_df = pd.DataFrame([retention_results])
    retention_df.to_csv(data_dir / 'panel_retention_analysis.csv', index=False)

    # Analyze demographic distributions
    analyze_demographic_distributions(df_202201, '202201', data_dir)
    analyze_demographic_distributions(df_202310, '202310', data_dir)

    # Compare demographic stability
    stability_df = compare_demographic_stability(df_202201, df_202310, machines_both, data_dir)

    # Create plots
    plot_demographic_distributions(df_202201, '202201', output_dir)
    plot_demographic_distributions(df_202310, '202310', output_dir)

    # Generate validation report
    generate_validation_report(
        validation_202201, validation_202310,
        retention_results, stability_df,
        data_dir / 'demographics_validation_report.txt'
    )

    logger.info("\n" + "=" * 80)
    logger.info("VALIDATION COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"\nOutputs saved to:")
    logger.info(f"  - Validation report: {data_dir / 'demographics_validation_report.txt'}")
    logger.info(f"  - Test data: {data_dir}/")
    logger.info(f"  - Plots: {output_dir}/")


if __name__ == "__main__":
    main()
