"""
Analyze Person Demographics Data

This script analyzes person-level demographic files to understand:
- Relationship between person_id and machine_id (1:1, many:1, 1:many, or both?)
- Machine coverage: % of machines with person-level data
- Primary person concept for multi-person machines
- Summary statistics of person demographics
- Panel composition and size over time

Usage:
    python3 code/ProcessComscore/data_structure_validation/analyze_person_demos.py

Outputs:
    - output/ProcessComscore/data_structure_validation/person_machine_relationship.csv
    - output/ProcessComscore/data_structure_validation/machine_person_coverage.csv
    - output/ProcessComscore/data_structure_validation/person_summary_statistics.csv
    - output/ProcessComscore/data_structure_validation/person_demographics_summary.png
    - output/ProcessComscore/data_structure_validation/machine_coverage_trend.png
    - output/ProcessComscore/data_structure_validation/persons_per_machine_distribution.png
    - data/ProcessComscore/data_structure_validation/person_analysis_report.txt
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

# Column names for person demographic files
PERSON_COLUMNS = [
    'person_id',
    'machine_id',
    'gender',
    'age',
    'children',
    'HHI_USD',
    'HH_Size',
    'ethnicity',
    'race',
    'device_type',
    'country',
    'metro',
    'DMA',
    'month_id'
]


def generate_month_list():
    """Generate list of month IDs from Jan 2022 to Dec 2024."""
    months = pd.date_range('2022-01', '2024-12', freq='MS')
    month_ids = [d.strftime('%Y%m') for d in months]
    return month_ids


def load_person_file(file_path):
    """Load a single person demographic file."""
    df = pd.read_csv(
        file_path,
        sep='\t',
        compression='gzip',
        header=None,
        names=PERSON_COLUMNS,
        dtype={'person_id': str, 'machine_id': str, 'month_id': str, 'DMA': str},
        low_memory=False
    )

    # Clean quotes from string columns
    string_cols = ['gender', 'children', 'HHI_USD', 'HH_Size', 'ethnicity',
                   'race', 'device_type', 'country', 'metro']
    for col in string_cols:
        df[col] = df[col].astype(str).str.strip('"').str.strip("'")

    return df


def analyze_person_machine_relationship(raw_dir):
    """
    Analyze relationship between person_id and machine_id across all months.

    Returns:
        DataFrame with relationship statistics per month
    """
    logger.info("\nAnalyzing person-machine relationships...")

    month_ids = generate_month_list()
    relationship_stats = []

    for i, month_id in enumerate(month_ids, 1):
        file_path = raw_dir / f'US_comscore_person_demos_{month_id}.txt.gz'

        if not file_path.exists():
            logger.warning(f"  [{i}/36] File not found: {file_path.name}")
            continue

        logger.info(f"  [{i}/36] Analyzing {month_id}...")

        df = load_person_file(file_path)

        # Calculate statistics
        total_persons = len(df)
        unique_persons = df['person_id'].nunique()
        unique_machines = df['machine_id'].nunique()

        # Check for duplicates
        person_duplicates = df['person_id'].duplicated().sum()
        machine_duplicates = df['machine_id'].duplicated().sum()

        # Understand relationships
        persons_per_machine = df.groupby('machine_id')['person_id'].nunique()
        machines_per_person = df.groupby('person_id')['machine_id'].nunique()

        relationship_stats.append({
            'month': month_id,
            'total_rows': total_persons,
            'unique_persons': unique_persons,
            'unique_machines': unique_machines,
            'person_duplicates': person_duplicates,
            'machine_duplicates': machine_duplicates,
            'avg_persons_per_machine': persons_per_machine.mean(),
            'max_persons_per_machine': persons_per_machine.max(),
            'machines_with_multiple_persons': (persons_per_machine > 1).sum(),
            'avg_machines_per_person': machines_per_person.mean(),
            'max_machines_per_person': machines_per_person.max(),
            'persons_with_multiple_machines': (machines_per_person > 1).sum()
        })

        logger.info(f"      {total_persons:,} rows, {unique_persons:,} persons, {unique_machines:,} machines")

    relationship_df = pd.DataFrame(relationship_stats)

    logger.info("\nRelationship Summary:")
    logger.info(f"  Avg persons per machine: {relationship_df['avg_persons_per_machine'].mean():.2f}")
    logger.info(f"  Avg machines per person: {relationship_df['avg_machines_per_person'].mean():.2f}")

    return relationship_df


def calculate_machine_coverage(raw_dir):
    """
    Calculate what share of machines have person-level data.

    Compares machine panel (from machine demos) vs person panel (from person demos).

    Returns:
        DataFrame with coverage statistics per month
    """
    logger.info("\nCalculating machine coverage (machines with person data)...")

    month_ids = generate_month_list()
    coverage_stats = []

    # Column names for machine files
    MACHINE_COLUMNS = [
        'machine_id', 'country', 'metro_area', 'DMA_code', 'device_type',
        'age_range', 'HHI', 'children', 'household_size', 'month_id'
    ]

    for i, month_id in enumerate(month_ids, 1):
        machine_file = raw_dir / f'US_comscore_machine_demos_{month_id}.txt.gz'
        person_file = raw_dir / f'US_comscore_person_demos_{month_id}.txt.gz'

        if not machine_file.exists() or not person_file.exists():
            logger.warning(f"  [{i}/36] Missing file for {month_id}")
            continue

        logger.info(f"  [{i}/36] Analyzing coverage for {month_id}...")

        # Load machine IDs from machine file
        df_machine = pd.read_csv(
            machine_file,
            sep='\t',
            compression='gzip',
            header=None,
            names=MACHINE_COLUMNS,
            dtype={'machine_id': str},
            usecols=['machine_id'],
            low_memory=False
        )
        machines_total = set(df_machine['machine_id'].dropna())

        # Load machine IDs from person file
        df_person = pd.read_csv(
            person_file,
            sep='\t',
            compression='gzip',
            header=None,
            names=PERSON_COLUMNS,
            dtype={'machine_id': str},
            usecols=['machine_id'],
            low_memory=False
        )
        machines_with_persons = set(df_person['machine_id'].dropna())

        # Calculate coverage
        machines_without_persons = machines_total - machines_with_persons
        coverage_rate = len(machines_with_persons) / len(machines_total) if len(machines_total) > 0 else 0

        coverage_stats.append({
            'month': month_id,
            'total_machines': len(machines_total),
            'machines_with_persons': len(machines_with_persons),
            'machines_without_persons': len(machines_without_persons),
            'coverage_rate': coverage_rate
        })

        logger.info(f"      {len(machines_with_persons):,}/{len(machines_total):,} machines have person data ({coverage_rate:.1%})")

    coverage_df = pd.DataFrame(coverage_stats)

    logger.info("\nCoverage Summary:")
    logger.info(f"  Avg coverage: {coverage_df['coverage_rate'].mean():.1%}")
    logger.info(f"  Range: {coverage_df['coverage_rate'].min():.1%} to {coverage_df['coverage_rate'].max():.1%}")

    return coverage_df


def investigate_primary_person(raw_dir, sample_month='202201'):
    """
    Investigate if there's a 'primary person' concept for machines with multiple persons.

    Args:
        raw_dir: Path to raw data directory
        sample_month: Month to analyze (default: 202201)

    Returns:
        Dict with findings about primary person
    """
    logger.info(f"\nInvestigating primary person concept (using {sample_month})...")

    file_path = raw_dir / f'US_comscore_person_demos_{sample_month}.txt.gz'
    df = load_person_file(file_path)

    # Find machines with multiple persons
    persons_per_machine = df.groupby('machine_id')['person_id'].count()
    multi_person_machines = persons_per_machine[persons_per_machine > 1].index

    logger.info(f"  Found {len(multi_person_machines):,} machines with multiple persons")

    if len(multi_person_machines) == 0:
        return {'has_primary_person': False, 'method': 'N/A - no multi-person machines'}

    # Analyze a sample of multi-person machines
    sample_machines = multi_person_machines[:100]  # Sample first 100
    findings = []

    for machine_id in sample_machines:
        machine_persons = df[df['machine_id'] == machine_id].copy()

        # Check ordering patterns
        findings.append({
            'machine_id': machine_id,
            'num_persons': len(machine_persons),
            'person_ids': machine_persons['person_id'].tolist(),
            'ages': machine_persons['age'].tolist(),
            'genders': machine_persons['gender'].tolist(),
            # Check if sorted by age (descending - oldest first)
            'sorted_by_age_desc': machine_persons['age'].tolist() == sorted(machine_persons['age'].tolist(), reverse=True),
            # Check if sorted by person_id
            'sorted_by_person_id': machine_persons['person_id'].tolist() == sorted(machine_persons['person_id'].tolist())
        })

    findings_df = pd.DataFrame(findings)

    # Analyze patterns
    pct_sorted_by_age = findings_df['sorted_by_age_desc'].mean() * 100
    pct_sorted_by_person_id = findings_df['sorted_by_person_id'].mean() * 100

    logger.info(f"  Analysis of {len(findings_df)} multi-person machines:")
    logger.info(f"    - {pct_sorted_by_age:.1f}% sorted by age (descending)")
    logger.info(f"    - {pct_sorted_by_person_id:.1f}% sorted by person_id")

    # Determine if there's a primary person pattern
    if pct_sorted_by_age > 80:
        primary_method = "First person (oldest)"
        has_primary = True
    elif pct_sorted_by_person_id > 80:
        primary_method = "First person (by person_id)"
        has_primary = True
    else:
        primary_method = "No consistent ordering - recommend first person as default"
        has_primary = False

    logger.info(f"  Recommendation: {primary_method}")

    return {
        'has_primary_person': has_primary,
        'method': primary_method,
        'pct_sorted_by_age': pct_sorted_by_age,
        'pct_sorted_by_person_id': pct_sorted_by_person_id,
        'sample_size': len(findings_df)
    }


def compute_summary_statistics(raw_dir):
    """
    Compute summary statistics across all person demographic files.

    Returns:
        DataFrame with summary statistics
    """
    logger.info("\nComputing summary statistics...")

    # Load a sample month to analyze distributions
    sample_month = '202201'
    file_path = raw_dir / f'US_comscore_person_demos_{sample_month}.txt.gz'

    logger.info(f"  Loading {sample_month} for detailed statistics...")
    df = load_person_file(file_path)

    summary_stats = []

    # Age statistics
    age_stats = df['age'].describe()
    summary_stats.append({
        'variable': 'age',
        'type': 'numeric',
        'count': age_stats['count'],
        'mean': age_stats['mean'],
        'std': age_stats['std'],
        'min': age_stats['min'],
        'p25': age_stats['25%'],
        'median': age_stats['50%'],
        'p75': age_stats['75%'],
        'max': age_stats['max'],
        'unique_values': df['age'].nunique()
    })

    # Categorical variable distributions
    categorical_vars = ['gender', 'children', 'ethnicity', 'race', 'HH_Size']

    for var in categorical_vars:
        value_counts = df[var].value_counts()
        top_category = value_counts.index[0] if len(value_counts) > 0 else None
        top_count = value_counts.iloc[0] if len(value_counts) > 0 else 0

        summary_stats.append({
            'variable': var,
            'type': 'categorical',
            'count': len(df),
            'unique_values': df[var].nunique(),
            'top_category': top_category,
            'top_category_count': top_count,
            'top_category_pct': (top_count / len(df) * 100) if len(df) > 0 else 0
        })

    summary_df = pd.DataFrame(summary_stats)

    logger.info(f"  Computed statistics for {len(summary_stats)} variables")

    return summary_df, df


def plot_coverage_trend(coverage_df, output_path):
    """Plot machine coverage trend over time."""
    logger.info("\nCreating machine coverage trend plot...")

    apply_plot_style()

    fig, ax = plt.subplots(figsize=(14, 8))

    # Convert month to datetime for better x-axis formatting
    coverage_df['date'] = pd.to_datetime(coverage_df['month'], format='%Y%m')

    # Plot coverage rate as percentage
    ax.plot(coverage_df['date'], coverage_df['coverage_rate'] * 100,
            color=UCHICAGO_MAROON, linewidth=3, marker='o', markersize=4)

    # Add horizontal line at mean
    mean_coverage = coverage_df['coverage_rate'].mean() * 100
    ax.axhline(mean_coverage, color='gray', linestyle='--', linewidth=2, alpha=0.5,
               label=f'Mean: {mean_coverage:.1f}%')

    ax.set_xlabel('Month', fontsize=14)
    ax.set_ylabel('Coverage Rate (%)', fontsize=14)
    ax.set_title('Machine Coverage: % of Machines with Person-Level Data', fontsize=16, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved coverage trend plot to {output_path}")


def plot_persons_per_machine_distribution(relationship_df, output_path):
    """Plot distribution of persons per machine over time."""
    logger.info("\nCreating persons-per-machine distribution plot...")

    apply_plot_style()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Convert month to datetime for better x-axis formatting
    relationship_df['date'] = pd.to_datetime(relationship_df['month'], format='%Y%m')

    # Left plot: Average persons per machine over time
    ax1.plot(relationship_df['date'], relationship_df['avg_persons_per_machine'],
             color=UCHICAGO_MAROON, linewidth=3, marker='o', markersize=4)
    ax1.set_xlabel('Month', fontsize=14)
    ax1.set_ylabel('Average Persons per Machine', fontsize=14)
    ax1.set_title('Average Persons per Machine Over Time', fontsize=16, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # Right plot: Proportion of machines with multiple persons
    pct_multi_person = (relationship_df['machines_with_multiple_persons'] /
                        relationship_df['unique_machines'] * 100)
    ax2.plot(relationship_df['date'], pct_multi_person,
             color=COLOR_PALETTE[1], linewidth=3, marker='o', markersize=4)
    ax2.set_xlabel('Month', fontsize=14)
    ax2.set_ylabel('% of Machines', fontsize=14)
    ax2.set_title('Machines with Multiple Persons (%)', fontsize=16, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved persons-per-machine distribution plot to {output_path}")


def plot_demographic_summary(df, output_path):
    """Create comprehensive summary plot of person demographics."""
    logger.info("\nCreating demographic summary plot...")

    apply_plot_style()

    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    fig.suptitle('Person Demographics Summary (Jan 2022)', fontweight='bold')

    # Age distribution
    axes[0, 0].hist(df['age'], bins=30, color=UCHICAGO_MAROON, edgecolor='white')
    axes[0, 0].set_xlabel('Age')
    axes[0, 0].set_ylabel('Count')
    axes[0, 0].set_title('Age Distribution')

    # Gender
    gender_counts = df['gender'].value_counts()
    axes[0, 1].bar(range(len(gender_counts)), gender_counts.values, color=UCHICAGO_MAROON)
    axes[0, 1].set_xticks(range(len(gender_counts)))
    axes[0, 1].set_xticklabels(gender_counts.index, rotation=45, ha='right')
    axes[0, 1].set_ylabel('Count')
    axes[0, 1].set_title('Gender Distribution')

    # Children
    children_counts = df['children'].value_counts()
    axes[0, 2].bar(range(len(children_counts)), children_counts.values, color=UCHICAGO_MAROON)
    axes[0, 2].set_xticks(range(len(children_counts)))
    axes[0, 2].set_xticklabels(children_counts.index, rotation=45, ha='right')
    axes[0, 2].set_ylabel('Count')
    axes[0, 2].set_title('Children in Household')

    # Household Size
    hh_size_counts = df['HH_Size'].value_counts().sort_index()
    axes[1, 0].bar(range(len(hh_size_counts)), hh_size_counts.values, color=UCHICAGO_MAROON)
    axes[1, 0].set_xticks(range(len(hh_size_counts)))
    axes[1, 0].set_xticklabels(hh_size_counts.index, rotation=45, ha='right')
    axes[1, 0].set_ylabel('Count')
    axes[1, 0].set_title('Household Size')

    # Ethnicity (top 10)
    ethnicity_counts = df['ethnicity'].value_counts().head(10)
    axes[1, 1].barh(range(len(ethnicity_counts)), ethnicity_counts.values, color=UCHICAGO_MAROON)
    axes[1, 1].set_yticks(range(len(ethnicity_counts)))
    axes[1, 1].set_yticklabels(ethnicity_counts.index)
    axes[1, 1].set_xlabel('Count')
    axes[1, 1].set_title('Ethnicity (Top 10)')

    # Race (top 10)
    race_counts = df['race'].value_counts().head(10)
    axes[1, 2].barh(range(len(race_counts)), race_counts.values, color=UCHICAGO_MAROON)
    axes[1, 2].set_yticks(range(len(race_counts)))
    axes[1, 2].set_yticklabels(race_counts.index)
    axes[1, 2].set_xlabel('Count')
    axes[1, 2].set_title('Race (Top 10)')

    # Income (HHI) - top 10
    hhi_counts = df['HHI_USD'].value_counts().head(10)
    axes[2, 0].barh(range(len(hhi_counts)), hhi_counts.values, color=UCHICAGO_MAROON)
    axes[2, 0].set_yticks(range(len(hhi_counts)))
    axes[2, 0].set_yticklabels(hhi_counts.index, fontsize=9)
    axes[2, 0].set_xlabel('Count')
    axes[2, 0].set_title('Household Income (Top 10)')

    # Top 15 metros
    metro_counts = df['metro'].value_counts().head(15)
    axes[2, 1].barh(range(len(metro_counts)), metro_counts.values, color=UCHICAGO_MAROON)
    axes[2, 1].set_yticks(range(len(metro_counts)))
    axes[2, 1].set_yticklabels(metro_counts.index, fontsize=9)
    axes[2, 1].set_xlabel('Count')
    axes[2, 1].set_title('Top 15 Metro Areas')

    # Device type
    device_counts = df['device_type'].value_counts()
    axes[2, 2].bar(range(len(device_counts)), device_counts.values, color=UCHICAGO_MAROON)
    axes[2, 2].set_xticks(range(len(device_counts)))
    axes[2, 2].set_xticklabels(device_counts.index, rotation=45, ha='right')
    axes[2, 2].set_ylabel('Count')
    axes[2, 2].set_title('Device Type')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved summary plot to {output_path}")


def generate_analysis_report(relationship_df, summary_df, coverage_df, primary_person_findings, output_path):
    """Generate comprehensive text report."""
    logger.info("\nGenerating analysis report...")

    with open(output_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PERSON DEMOGRAPHICS ANALYSIS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        # Person-Machine Relationship
        f.write("1. PERSON-MACHINE RELATIONSHIP\n")
        f.write("-" * 80 + "\n")

        avg_persons_per_machine = relationship_df['avg_persons_per_machine'].mean()
        max_persons_per_machine = relationship_df['max_persons_per_machine'].max()
        avg_machines_per_person = relationship_df['avg_machines_per_person'].mean()
        max_machines_per_person = relationship_df['max_machines_per_person'].max()

        f.write(f"Average persons per machine: {avg_persons_per_machine:.2f}\n")
        f.write(f"Maximum persons per machine: {int(max_persons_per_machine)}\n")
        f.write(f"Average machines per person: {avg_machines_per_person:.2f}\n")
        f.write(f"Maximum machines per person: {int(max_machines_per_person)}\n\n")

        # Determine relationship type
        if avg_persons_per_machine > 1.1 and avg_machines_per_person > 1.1:
            relationship_type = "Many-to-Many"
        elif avg_persons_per_machine > 1.1:
            relationship_type = "Many-to-One (multiple persons per machine)"
        elif avg_machines_per_person > 1.1:
            relationship_type = "One-to-Many (multiple machines per person)"
        else:
            relationship_type = "Approximately One-to-One"

        f.write(f"Relationship Type: {relationship_type}\n\n")

        # Machine Coverage
        f.write("2. MACHINE COVERAGE (% WITH PERSON DATA)\n")
        f.write("-" * 80 + "\n")

        avg_coverage = coverage_df['coverage_rate'].mean() * 100
        min_coverage = coverage_df['coverage_rate'].min() * 100
        max_coverage = coverage_df['coverage_rate'].max() * 100

        first_month_coverage = coverage_df.iloc[0]
        last_month_coverage = coverage_df.iloc[-1]

        f.write(f"Average coverage across all months: {avg_coverage:.1f}%\n")
        f.write(f"Range: {min_coverage:.1f}% to {max_coverage:.1f}%\n\n")

        f.write(f"First month ({first_month_coverage['month']}):\n")
        f.write(f"  - Total machines: {first_month_coverage['total_machines']:,.0f}\n")
        f.write(f"  - Machines with person data: {first_month_coverage['machines_with_persons']:,.0f}\n")
        f.write(f"  - Machines without person data: {first_month_coverage['machines_without_persons']:,.0f}\n")
        f.write(f"  - Coverage rate: {first_month_coverage['coverage_rate']*100:.1f}%\n\n")

        f.write(f"Last month ({last_month_coverage['month']}):\n")
        f.write(f"  - Total machines: {last_month_coverage['total_machines']:,.0f}\n")
        f.write(f"  - Machines with person data: {last_month_coverage['machines_with_persons']:,.0f}\n")
        f.write(f"  - Machines without person data: {last_month_coverage['machines_without_persons']:,.0f}\n")
        f.write(f"  - Coverage rate: {last_month_coverage['coverage_rate']*100:.1f}%\n\n")

        # Primary Person Findings
        f.write("3. PRIMARY PERSON INVESTIGATION\n")
        f.write("-" * 80 + "\n")

        f.write(f"Primary person pattern: {primary_person_findings['method']}\n")
        f.write(f"Analysis based on {primary_person_findings['sample_size']} multi-person machines\n\n")

        f.write(f"Ordering patterns:\n")
        f.write(f"  - Sorted by age (descending): {primary_person_findings['pct_sorted_by_age']:.1f}%\n")
        f.write(f"  - Sorted by person_id: {primary_person_findings['pct_sorted_by_person_id']:.1f}%\n\n")

        if primary_person_findings['has_primary_person']:
            f.write("Recommendation: Use first person listed as primary person.\n\n")
        else:
            f.write("Recommendation: No consistent ordering found. Use first person as default.\n\n")

        # Panel size over time
        f.write("4. PANEL SIZE OVER TIME\n")
        f.write("-" * 80 + "\n")
        first_month = relationship_df.iloc[0]
        last_month = relationship_df.iloc[-1]

        f.write(f"First month ({first_month['month']}):\n")
        f.write(f"  - Persons: {first_month['unique_persons']:,.0f}\n")
        f.write(f"  - Machines: {first_month['unique_machines']:,.0f}\n\n")

        f.write(f"Last month ({last_month['month']}):\n")
        f.write(f"  - Persons: {last_month['unique_persons']:,.0f}\n")
        f.write(f"  - Machines: {last_month['unique_machines']:,.0f}\n\n")

        # Summary statistics
        f.write("5. DEMOGRAPHIC SUMMARY STATISTICS (JAN 2022)\n")
        f.write("-" * 80 + "\n")

        for _, row in summary_df.iterrows():
            f.write(f"\n{row['variable'].upper()}:\n")
            if row['type'] == 'numeric':
                f.write(f"  Mean: {row['mean']:.1f}\n")
                f.write(f"  Std: {row['std']:.1f}\n")
                f.write(f"  Min: {row['min']:.0f}\n")
                f.write(f"  Median: {row['median']:.0f}\n")
                f.write(f"  Max: {row['max']:.0f}\n")
                f.write(f"  Unique values: {row['unique_values']:.0f}\n")
            else:
                f.write(f"  Unique categories: {row['unique_values']:.0f}\n")
                f.write(f"  Most common: {row['top_category']} ({row['top_category_pct']:.1f}%)\n")

        f.write("\n" + "=" * 80 + "\n")

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
    logger.info("PERSON DEMOGRAPHICS ANALYSIS")
    logger.info("=" * 80)

    # Step 1: Analyze person-machine relationships
    relationship_df = analyze_person_machine_relationship(raw_dir)
    relationship_df.to_csv(
        output_dir / 'person_machine_relationship.csv',
        index=False
    )

    # Step 2: Calculate machine coverage
    coverage_df = calculate_machine_coverage(raw_dir)
    coverage_df.to_csv(
        output_dir / 'machine_person_coverage.csv',
        index=False
    )

    # Step 3: Investigate primary person concept
    primary_person_findings = investigate_primary_person(raw_dir, sample_month='202201')

    # Step 4: Compute summary statistics
    summary_df, sample_df = compute_summary_statistics(raw_dir)
    summary_df.to_csv(
        output_dir / 'person_summary_statistics.csv',
        index=False
    )

    # Step 5: Create visualizations
    plot_demographic_summary(
        sample_df,
        output_dir / 'person_demographics_summary.png'
    )

    plot_coverage_trend(
        coverage_df,
        output_dir / 'machine_coverage_trend.png'
    )

    plot_persons_per_machine_distribution(
        relationship_df,
        output_dir / 'persons_per_machine_distribution.png'
    )

    # Step 6: Generate report
    generate_analysis_report(
        relationship_df,
        summary_df,
        coverage_df,
        primary_person_findings,
        data_dir / 'person_analysis_report.txt'
    )

    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"\nOutputs saved to:")
    logger.info(f"  Data: {data_dir}/")
    logger.info(f"  Outputs: {output_dir}/")


if __name__ == "__main__":
    main()
