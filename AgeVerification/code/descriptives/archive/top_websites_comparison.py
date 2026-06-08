"""
Compare top 500 websites between Jan 2022 and Feb 2023.
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path('data/ProcessComscore/merged_session_files')

def get_top_websites(month, top_n=500):
    """Get top N websites by session count for a given month."""
    df = pd.read_parquet(
        DATA_DIR / f'merged_sessions_{month}.parquet',
        columns=['top_web_name', 'session_id', 'duration']
    )

    top = df.groupby('top_web_name').agg(
        sessions=('session_id', 'size'),
        total_hours=('duration', lambda x: x.sum() / 3600)
    ).sort_values('sessions', ascending=False).head(top_n)

    top['pct'] = top['sessions'] / len(df) * 100
    top = top.reset_index()
    top['rank'] = range(1, len(top) + 1)

    return top

def main():
    for month, label in [('202201', 'Jan 2022'), ('202302', 'Feb 2023')]:
        print(f"\n{'='*80}")
        print(f"TOP 500 WEBSITES - {label}")
        print('='*80)

        top = get_top_websites(month)

        for _, row in top.iterrows():
            print(f"{row['rank']:3d}. {row['top_web_name']:45s} {row['sessions']:>10,} ({row['pct']:>5.2f}%)")

if __name__ == "__main__":
    main()
