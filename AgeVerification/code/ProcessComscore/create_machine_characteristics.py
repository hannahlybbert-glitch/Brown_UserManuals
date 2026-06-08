"""
Create Machine-Level Characteristics File

This script creates a unique machine-level characteristics file by:
1. Combining machine characteristics from all 36 months
2. Merging person-level characteristics using specific aggregation rules
3. Using first observed values for each machine

Person characteristic rules:
- If 1 person linked to machine: Use that person's characteristics
- If multiple persons who agree: Use the agreed value
- If multiple persons who disagree: Set to missing
- If no person linked: Set to missing

Usage:
    python3 code/ProcessComscore/create_machine_characteristics.py

Output:
    - data/ProcessComscore/machine_characteristics.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Column names for machine and person files
MACHINE_COLUMNS = [
    'machine_id', 'country', 'metro_area', 'DMA_code', 'device_type',
    'age_range', 'HHI', 'children', 'household_size', 'month_id'
]

PERSON_COLUMNS = [
    'person_id', 'machine_id', 'gender', 'age', 'children',
    'HHI_USD', 'HH_Size', 'ethnicity', 'race', 'device_type',
    'country', 'metro', 'DMA', 'month_id'
]


def generate_month_list():
    """Generate list of month IDs from Jan 2022 to Dec 2024."""
    months = pd.date_range('2022-01', '2024-12', freq='MS')
    month_ids = [d.strftime('%Y%m') for d in months]
    return month_ids


def load_all_machine_characteristics(raw_dir):
    """
    Load machine characteristics from all months and keep first observed value.

    Returns:
        DataFrame with unique machine_id and first observed characteristics
    """
    logger.info("\nLoading machine characteristics from all months...")

    month_ids = generate_month_list()
    all_machines = []

    for i, month_id in enumerate(month_ids, 1):
        file_path = raw_dir / f'US_comscore_machine_demos_{month_id}.txt.gz'

        if not file_path.exists():
            logger.warning(f"  [{i}/36] File not found: {file_path.name}")
            continue

        logger.info(f"  [{i}/36] Loading {month_id}...")

        df = pd.read_csv(
            file_path,
            sep='\t',
            compression='gzip',
            header=None,
            names=MACHINE_COLUMNS,
            dtype={'machine_id': str, 'DMA_code': str, 'month_id': str},
            low_memory=False
        )

        # Clean quotes from string columns
        string_cols = ['country', 'metro_area', 'device_type', 'age_range',
                      'HHI', 'children', 'household_size']
        for col in string_cols:
            df[col] = df[col].astype(str).str.strip('"').str.strip("'")

        all_machines.append(df)

    # Concatenate all months
    logger.info("\nCombining all months...")
    combined = pd.concat(all_machines, ignore_index=True)

    # Sort by month to ensure first observed values come first
    combined = combined.sort_values('month_id')

    # Keep first observed value for each machine
    machine_chars = combined.groupby('machine_id', as_index=False).first()

    # Drop month_id since we're using first observed
    machine_chars = machine_chars.drop(columns=['month_id'])

    logger.info(f"  Total unique machines: {len(machine_chars):,}")

    return machine_chars


def load_all_person_characteristics(raw_dir):
    """
    Load person characteristics from all months.

    Returns:
        DataFrame with all person-month observations
    """
    logger.info("\nLoading person characteristics from all months...")

    month_ids = generate_month_list()
    all_persons = []

    for i, month_id in enumerate(month_ids, 1):
        file_path = raw_dir / f'US_comscore_person_demos_{month_id}.txt.gz'

        if not file_path.exists():
            logger.warning(f"  [{i}/36] File not found: {file_path.name}")
            continue

        logger.info(f"  [{i}/36] Loading {month_id}...")

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

        all_persons.append(df)

    # Concatenate all months
    logger.info("\nCombining all person observations...")
    combined = pd.concat(all_persons, ignore_index=True)

    # Sort by month to ensure first observed values come first
    combined = combined.sort_values('month_id')

    logger.info(f"  Total person-month observations: {len(combined):,}")
    logger.info(f"  Unique persons: {combined['person_id'].nunique():,}")
    logger.info(f"  Unique machines with persons: {combined['machine_id'].nunique():,}")

    return combined


def aggregate_person_characteristics_by_machine(persons_df):
    """
    Aggregate person characteristics to machine level using specific rules.

    Rules:
    - If 1 person ever linked: Use their first observed characteristics
    - If multiple persons who all agree: Use agreed value
    - If multiple persons who disagree: Set to missing
    - If no person linked: Will be missing (machine not in this dataframe)

    Returns:
        DataFrame with machine_id and aggregated person characteristics
    """
    logger.info("\nAggregating person characteristics to machine level...")

    # Person characteristics to aggregate
    person_vars = ['gender', 'age', 'children', 'HHI_USD', 'HH_Size', 'ethnicity', 'race']

    # For each machine, get first observation of each person
    # (to handle same person appearing in multiple months)
    logger.info("  Getting first observation for each person...")
    first_person_obs = persons_df.sort_values('month_id').groupby(['machine_id', 'person_id'], as_index=False).first()

    # Now aggregate to machine level
    logger.info("  Aggregating to machine level...")

    machine_person_chars = []

    for machine_id, group in first_person_obs.groupby('machine_id'):
        machine_chars = {'machine_id': machine_id}
        num_persons = len(group)

        for var in person_vars:
            if num_persons == 1:
                # Single person: use their value
                machine_chars[f'person_{var}'] = group[var].iloc[0]
            else:
                # Multiple persons: check if they agree
                unique_values = group[var].dropna().unique()

                if len(unique_values) == 0:
                    # All missing
                    machine_chars[f'person_{var}'] = np.nan
                elif len(unique_values) == 1:
                    # All agree
                    machine_chars[f'person_{var}'] = unique_values[0]
                else:
                    # Disagree - set to missing
                    machine_chars[f'person_{var}'] = np.nan

        machine_person_chars.append(machine_chars)

    machine_person_df = pd.DataFrame(machine_person_chars)

    logger.info(f"  Aggregated person characteristics for {len(machine_person_df):,} machines")

    # Report coverage statistics
    logger.info("\n  Person characteristic coverage:")
    for var in person_vars:
        col_name = f'person_{var}'
        coverage = machine_person_df[col_name].notna().sum()
        pct = coverage / len(machine_person_df) * 100
        logger.info(f"    {col_name}: {coverage:,} machines ({pct:.1f}%)")

    return machine_person_df


def create_machine_characteristics_file(raw_dir, output_path):
    """
    Main function to create machine characteristics file.
    """
    logger.info("=" * 80)
    logger.info("CREATING MACHINE CHARACTERISTICS FILE")
    logger.info("=" * 80)

    # Step 1: Load machine characteristics
    machine_chars = load_all_machine_characteristics(raw_dir)

    # Step 2: Load person characteristics
    persons_df = load_all_person_characteristics(raw_dir)

    # Step 3: Aggregate person characteristics to machine level
    person_chars = aggregate_person_characteristics_by_machine(persons_df)

    # Step 4: Merge machine and person characteristics
    logger.info("\nMerging machine and person characteristics...")
    final_df = machine_chars.merge(person_chars, on='machine_id', how='left')

    logger.info(f"  Final dataset: {len(final_df):,} machines")
    logger.info(f"  Total columns: {len(final_df.columns)}")

    # Step 5: Save to file
    logger.info(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_path, index=False)

    # Summary statistics
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Total machines: {len(final_df):,}")
    logger.info(f"\nMachine-level characteristics (from machine demos):")
    logger.info(f"  country: {final_df['country'].notna().sum():,} ({final_df['country'].notna().sum()/len(final_df)*100:.1f}%)")
    logger.info(f"  metro_area: {final_df['metro_area'].notna().sum():,} ({final_df['metro_area'].notna().sum()/len(final_df)*100:.1f}%)")
    logger.info(f"  device_type: {final_df['device_type'].notna().sum():,} ({final_df['device_type'].notna().sum()/len(final_df)*100:.1f}%)")
    logger.info(f"  age_range: {final_df['age_range'].notna().sum():,} ({final_df['age_range'].notna().sum()/len(final_df)*100:.1f}%)")

    logger.info(f"\nPerson-level characteristics (aggregated to machine):")
    person_cols = [col for col in final_df.columns if col.startswith('person_')]
    for col in person_cols:
        coverage = final_df[col].notna().sum()
        pct = coverage / len(final_df) * 100
        logger.info(f"  {col}: {coverage:,} ({pct:.1f}%)")

    logger.info("\n" + "=" * 80)
    logger.info("COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"\nOutput saved to: {output_path}")

    return final_df


def main():
    """Main execution function."""

    # Define paths
    base_dir = Path.cwd()
    raw_dir = base_dir / 'raw' / 'desktop_demographics'
    output_path = base_dir / 'data' / 'ProcessComscore' / 'machine_characteristics.csv'

    # Create machine characteristics file
    create_machine_characteristics_file(raw_dir, output_path)


if __name__ == "__main__":
    main()
