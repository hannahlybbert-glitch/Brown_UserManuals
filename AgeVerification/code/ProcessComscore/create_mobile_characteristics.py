"""
Create Mobile Machine-Level Characteristics File

This script creates a unique machine-level characteristics file for mobile data by:
1. Loading mobile demographics from all available months
2. Keeping first observed values for each machine_id (no person-to-machine aggregation needed)

Mobile demographics are already at the individual/machine level, unlike desktop which
requires person-to-machine aggregation.

Usage:
    python3 code/ProcessComscore/create_mobile_characteristics.py

Output:
    - data/ProcessComscore/mobile_characteristics.csv
    - Columns: machine_id, platform, age, gender, hh_income, hh_size,
               children_present, region, race, hispanic
"""

import pandas as pd
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Column names for mobile demographics file
MOBILE_COLUMNS = [
    'month_id', 'platform', 'machine_id', 'age', 'gender',
    'hh_income', 'hh_size', 'children_present', 'region', 'race', 'hispanic'
]


def load_all_mobile_demographics(raw_dir):
    """
    Load mobile demographics from all available months and keep first observed value.

    Returns:
        DataFrame with unique machine_id and first observed characteristics
    """
    logger.info("\nLoading mobile demographics from all available months...")

    # Find all available mobile demographics files
    files = sorted(raw_dir.glob('US_comscore_mobile_demos_*.txt*'))

    if not files:
        logger.error(f"No mobile demographics files found in {raw_dir}")
        raise FileNotFoundError(f"No mobile demographics files found in {raw_dir}")

    all_demos = []
    files_loaded = 0

    for i, file_path in enumerate(files, 1):
        # Skip if this is a .gz and the uncompressed version was already processed
        if not str(file_path).endswith('.gz') and Path(str(file_path) + '.gz') in files:
            continue

        compression = 'gzip' if str(file_path).endswith('.gz') else None

        df = pd.read_csv(
            file_path,
            sep='\t',
            compression=compression,
            header=None,
            names=MOBILE_COLUMNS,
            dtype={'machine_id': str, 'month_id': str},
            low_memory=False
        )

        # Clean quotes from string columns
        string_cols = ['platform', 'gender', 'hh_income', 'hh_size',
                       'children_present', 'region', 'race', 'hispanic']
        for col in string_cols:
            df[col] = df[col].astype(str).str.strip('"').str.strip("'")

        files_loaded += 1
        logger.info(f"  [{files_loaded}/{len(files)}] {file_path.name}: {len(df):,} rows, {df['machine_id'].nunique():,} unique machines")

        all_demos.append(df)

    # Concatenate all months
    logger.info(f"\nCombining {files_loaded} months...")
    combined = pd.concat(all_demos, ignore_index=True)
    logger.info(f"  Total rows across all months: {len(combined):,}")
    logger.info(f"  Total unique machines across all months: {combined['machine_id'].nunique():,}")

    # How many machines appear in multiple months?
    months_per_machine = combined.groupby('machine_id')['month_id'].nunique()
    logger.info(f"  Machines appearing in 1 month: {(months_per_machine == 1).sum():,}")
    if files_loaded > 1:
        logger.info(f"  Machines appearing in 2+ months: {(months_per_machine >= 2).sum():,}")
        logger.info(f"  Machines appearing in all {files_loaded} months: {(months_per_machine == files_loaded).sum():,}")

    # Sort by month_id to ensure first observed values come first
    combined = combined.sort_values('month_id')

    # Keep first observed value for each machine
    mobile_chars = combined.groupby('machine_id', as_index=False).first()

    # Drop month_id since we're using first observed
    mobile_chars = mobile_chars.drop(columns=['month_id'])

    logger.info(f"  Final unique machines (after dedup): {len(mobile_chars):,}")

    return mobile_chars


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("CREATING MOBILE CHARACTERISTICS FILE")
    logger.info("=" * 80)

    # Define paths
    base_dir = Path.cwd()
    raw_dir = base_dir / 'raw' / 'mobile_demographics'
    output_path = base_dir / 'data' / 'ProcessComscore' / 'mobile_characteristics.csv'

    # Load and process
    mobile_chars = load_all_mobile_demographics(raw_dir)

    # Save to file
    logger.info(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mobile_chars.to_csv(output_path, index=False)

    # Summary statistics
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Total machines: {len(mobile_chars):,}")
    logger.info(f"\nCharacteristic coverage:")
    for col in mobile_chars.columns:
        if col == 'machine_id':
            continue
        coverage = mobile_chars[col].notna().sum()
        pct = coverage / len(mobile_chars) * 100
        logger.info(f"  {col}: {coverage:,} ({pct:.1f}%)")

    logger.info("\n" + "=" * 80)
    logger.info("COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
