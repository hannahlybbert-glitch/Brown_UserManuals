"""
Compare Mobile vs Desktop XXX Adult Visitor Demographics: January 2022

Demographic comparison of XXX Adult visitors across platforms using
machine-level demographics (no person-level aggregation).

- Mobile: gender and exact age from mobile demographics
- Desktop: age_range from machine demographics (no machine-level gender available)

1. Gender breakdown (mobile only — desktop lacks machine-level gender)
2. Age category breakdown (both platforms)
3. Gender x age category breakdown (mobile only)

Usage:
    python code/descriptives/mobile/compare_jan22_mobilevsdesktop_demos.py

Outputs:
    - output/descriptives/mobile/compare_xxx_demos_gender_202201.csv
    - output/descriptives/mobile/compare_xxx_demos_age_202201.csv
    - output/descriptives/mobile/compare_xxx_demos_gender_age_202201.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path.cwd()
DATA_DIR = BASE_DIR / 'data' / 'ProcessComscore' / 'merged_session_files'
OUTPUT_DIR = BASE_DIR / 'output' / 'descriptives' / 'mobile'

MONTH_ID = '202201'

# Age bins to match desktop's machine-level age_range categories
AGE_BINS = [17, 24, 34, 44, 54, 64, 200]
AGE_LABELS = ['18-24', '25-34', '35-44', '45-54', '55-64', '65+']

# Desktop age_range values to our standardized labels
DESKTOP_AGE_MAP = {
    '18-24': '18-24',
    '25-34': '25-34',
    '35-44': '35-44',
    '45-54': '45-54',
    '55-64': '55-64',
    '65 and Over': '65+',
}


def load_xxx_visitors():
    """Load unique XXX Adult visitors with machine-level demographics."""

    # Mobile: gender and exact age available
    logger.info("Loading mobile data...")
    mob = pd.read_parquet(
        DATA_DIR / f'merged_mobile_sessions_{MONTH_ID}.parquet',
        columns=['machine_id', 'subcategory', 'age', 'gender']
    )
    mob['machine_id'] = mob['machine_id'].astype(str)
    mob_xxx = mob[mob['subcategory'] == 'XXX Adult'].drop_duplicates('machine_id')[['machine_id', 'age', 'gender']].copy()
    mob_xxx['age_group'] = pd.cut(mob_xxx['age'], bins=AGE_BINS, labels=AGE_LABELS)
    logger.info(f"  Mobile XXX visitors: {len(mob_xxx):,}")
    logger.info(f"  Gender missing: {mob_xxx['gender'].isna().sum():,}")
    logger.info(f"  Age missing: {mob_xxx['age'].isna().sum():,}")

    # Desktop: machine-level age_range only (no machine-level gender)
    logger.info("Loading desktop data...")
    desk = pd.read_parquet(
        DATA_DIR / f'merged_sessions_{MONTH_ID}.parquet',
        columns=['machine_id', 'subcategory', 'age_range']
    )
    desk['machine_id'] = desk['machine_id'].astype(str)
    desk_xxx = desk[desk['subcategory'] == 'XXX Adult'].drop_duplicates('machine_id')[['machine_id', 'age_range']].copy()
    desk_xxx['age_group'] = desk_xxx['age_range'].map(DESKTOP_AGE_MAP)
    logger.info(f"  Desktop XXX visitors: {len(desk_xxx):,}")
    logger.info(f"  age_range missing: {desk_xxx['age_range'].isna().sum():,}")
    logger.info(f"  Note: No machine-level gender available for desktop")

    return mob_xxx, desk_xxx


def compute_gender_breakdown(mob_xxx):
    """Compute gender shares for mobile XXX visitors (desktop lacks machine-level gender)."""
    logger.info("\nComputing gender breakdown (mobile only)...")

    total = len(mob_xxx)
    rows = []
    for g in ['Male', 'Female']:
        count = (mob_xxx['gender'] == g).sum()
        rows.append({
            'platform': 'mobile',
            'gender': g,
            'visitors': count,
            'share': count / total,
        })

    result = pd.DataFrame(rows)

    for _, row in result.iterrows():
        logger.info(f"  {row['gender']}: {row['visitors']:,} ({row['share']*100:.1f}%)")

    return result


def compute_age_breakdown(mob_xxx, desk_xxx):
    """Compute age group shares for XXX visitors on each platform."""
    logger.info("\nComputing age group breakdown...")

    rows = []
    for platform, df in [('mobile', mob_xxx), ('desktop', desk_xxx)]:
        known = df[df['age_group'].notna()]
        total = len(known)
        for ag in AGE_LABELS:
            count = (known['age_group'] == ag).sum()
            rows.append({
                'platform': platform,
                'age_group': ag,
                'visitors': count,
                'share': count / total,
                'total_with_age': total,
                'total_visitors': len(df),
            })

    result = pd.DataFrame(rows)

    for platform in ['mobile', 'desktop']:
        sub = result[result['platform'] == platform]
        total = sub['total_visitors'].iloc[0]
        missing = total - sub['total_with_age'].iloc[0]
        logger.info(f"  {platform.capitalize()} (age missing: {missing:,} / {total:,}):")
        for _, row in sub.iterrows():
            logger.info(f"    {row['age_group']}: {row['visitors']:,} ({row['share']*100:.1f}%)")

    return result


def compute_gender_age_breakdown(mob_xxx):
    """Compute gender x age group shares for mobile XXX visitors."""
    logger.info("\nComputing gender x age group breakdown (mobile only)...")

    known = mob_xxx[mob_xxx['gender'].notna() & mob_xxx['age_group'].notna()]
    total = len(known)

    rows = []
    for g in ['Male', 'Female']:
        for ag in AGE_LABELS:
            count = ((known['gender'] == g) & (known['age_group'] == ag)).sum()
            rows.append({
                'gender': g,
                'age_group': ag,
                'visitors': count,
                'share_of_all': count / total,
            })

    result = pd.DataFrame(rows)

    # Compute within-gender shares
    for g in ['Male', 'Female']:
        mask = result['gender'] == g
        gender_total = result.loc[mask, 'visitors'].sum()
        result.loc[mask, 'share_within_gender'] = result.loc[mask, 'visitors'] / gender_total

    for g in ['Male', 'Female']:
        gsub = result[result['gender'] == g]
        logger.info(f"  {g}:")
        for _, row in gsub.iterrows():
            logger.info(f"    {row['age_group']}: {row['visitors']:,} ({row['share_within_gender']*100:.1f}% of {g}, {row['share_of_all']*100:.1f}% of all)")

    return result


def main():
    logger.info("=" * 70)
    logger.info("MOBILE vs DESKTOP XXX ADULT DEMOGRAPHICS: January 2022")
    logger.info("(Using machine-level demographics)")
    logger.info("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mob_xxx, desk_xxx = load_xxx_visitors()

    # 1. Gender (mobile only)
    logger.info("\n" + "-" * 70)
    logger.info("1. GENDER BREAKDOWN (mobile only — desktop has no machine-level gender)")
    logger.info("-" * 70)
    gender_df = compute_gender_breakdown(mob_xxx)
    gender_df.to_csv(OUTPUT_DIR / f'compare_xxx_demos_gender_{MONTH_ID}.csv', index=False)

    # 2. Age (both platforms)
    logger.info("\n" + "-" * 70)
    logger.info("2. AGE GROUP BREAKDOWN (both platforms)")
    logger.info("-" * 70)
    age_df = compute_age_breakdown(mob_xxx, desk_xxx)
    age_df.to_csv(OUTPUT_DIR / f'compare_xxx_demos_age_{MONTH_ID}.csv', index=False)

    # 3. Gender x Age (mobile only)
    logger.info("\n" + "-" * 70)
    logger.info("3. GENDER x AGE GROUP BREAKDOWN (mobile only)")
    logger.info("-" * 70)
    gender_age_df = compute_gender_age_breakdown(mob_xxx)
    gender_age_df.to_csv(OUTPUT_DIR / f'compare_xxx_demos_gender_age_{MONTH_ID}.csv', index=False)

    logger.info("\n" + "=" * 70)
    logger.info("COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Output saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
