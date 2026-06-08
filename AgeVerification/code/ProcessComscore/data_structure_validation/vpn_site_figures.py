# Author: Hannah Lybbert
# Created: 2026-03-04
# Purpose: VPN site time series figures.
#
# Produces:
#   vpn_timeseries_YYYYMMDD_HHMMSS.png — two-panel time series:
#     Panel 1 — clean VPN visitor share of panel by month
#     Panel 2 — % of VPN visitors also visiting XXX that month
#
# Usage:
#   python code/ProcessComscore/data_structure_validation/vpn_site_figures.py
#   python code/ProcessComscore/data_structure_validation/vpn_site_figures.py --project-root /abs/path

'''
Input:  data/ProcessComscore/merged_session_files/merged_sessions_YYYYMM.parquet
Output: output/figures/vpn_timeseries_*.png
'''

import argparse
import os
import sys
from glob import glob
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # non-interactive backend for cluster
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pyarrow.parquet as pq

# ══════════════════════════════════════════════════════════════════════════════
# ARGS
# ══════════════════════════════════════════════════════════════════════════════
parser = argparse.ArgumentParser(description="VPN site figures.")
parser.add_argument("--project-root", default=None,
                    help="Absolute path to project root. Default: four levels up from this script.")
args = parser.parse_args()

try:
    _here = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _here = os.getcwd()

project_root = (
    os.path.abspath(args.project_root) if args.project_root
    else os.path.abspath(os.path.join(_here, '..', '..', '..'))
)

# ══════════════════════════════════════════════════════════════════════════════
# VPN SITE DEFINITIONS (mirror of create_web_characteristics.py)
# ══════════════════════════════════════════════════════════════════════════════
VPN_WHITELIST = {
    'NORDVPN.COM',
    'SURFSHARK.COM',
    'TOTALVPN.COM',
    'EXPRESSVPN.COM',
    'CYBERGHOSTVPN.COM Sites',
    'PRIVATEINTERNETACCESS.COM',
    'PUREVPN.COM',
    'TunnelBear Sites',
    'HIDE.ME',
    'WINDSCRIBE.COM',
    'PERFECT-PRIVACY.COM',
    'Symantec',
    'Gen Digital Inc. (Formally Symantec - NortonLifeLock)',
    'BITDEFENDER.COM',
}
ANTIVIRUS_SITES = {'Symantec', 'Gen Digital Inc. (Formally Symantec - NortonLifeLock)', 'BITDEFENDER.COM'}
DYNAMIC_VPN_KEYWORDS = 'protonvpn|mullvad|hotshield|privadovpn|ivpn|airvpn'


def is_vpn_site(s):
    return s.isin(VPN_WHITELIST) | s.str.lower().str.contains(DYNAMIC_VPN_KEYWORDS, na=False)


def month_id_to_date(month_id):
    """Convert Comscore month_id to Timestamp. month_id 265 = Jan 2022."""
    offset = int(month_id) - 265
    return pd.Timestamp(year=2022 + offset // 12, month=1 + offset % 12, day=1)


# ══════════════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════════════
merged_dir = os.path.join(project_root, 'data', 'ProcessComscore', 'merged_session_files')
out_dir    = os.path.join(project_root, 'output', 'figures')
os.makedirs(out_dir, exist_ok=True)

parquet_files = sorted(glob(os.path.join(merged_dir, 'merged_sessions_*.parquet')))
if not parquet_files:
    print(f"ERROR: No parquet files found in {merged_dir}")
    sys.exit(1)

_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
NEEDED_COLS = ['person_id', 'top_web_name', 'subcategory', 'month_id']

# ══════════════════════════════════════════════════════════════════════════════
# ACCUMULATE STATS — one file at a time
# ══════════════════════════════════════════════════════════════════════════════
monthly_rows = []

print(f"Processing {len(parquet_files)} file(s)...")
for fpath in parquet_files:
    fname = os.path.basename(fpath)

    available  = pq.read_schema(fpath).names
    cols       = [c for c in NEEDED_COLS if c in available]
    df         = pd.read_parquet(fpath, columns=cols)

    df['vpn_site']     = is_vpn_site(df['top_web_name'])
    df['is_antivirus'] = df['top_web_name'].isin(ANTIVIRUS_SITES)
    df['is_clean_vpn'] = df['vpn_site'] & ~df['is_antivirus']

    vpn_df       = df[df['vpn_site']]
    clean_vpn_df = df[df['is_clean_vpn']]
    xxx_df       = df[df['subcategory'] == 'XXX Adult']

    month_id = df['month_id'].iloc[0]

    xxx_set = set(xxx_df['person_id'].dropna().unique())
    vpn_set = set(vpn_df['person_id'].dropna().unique())
    overlap = len(xxx_set & vpn_set)

    monthly_rows.append({
        'date':               month_id_to_date(month_id),
        'total_persons':      df['person_id'].nunique(),
        'clean_vpn_persons':  clean_vpn_df['person_id'].nunique(),
        'overlap_pct_of_vpn': overlap / len(vpn_set) * 100 if vpn_set else np.nan,
    })

    del df, vpn_df, clean_vpn_df, xxx_df
    print(f"  {fname}: done")

monthly = pd.DataFrame(monthly_rows).sort_values('date')
monthly['clean_vpn_pct'] = monthly['clean_vpn_persons'] / monthly['total_persons'] * 100

print(f"\nAll files processed. Generating figures...\n")

# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 1+2: Two-panel time series
# ══════════════════════════════════════════════════════════════════════════════
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
fig.subplots_adjust(hspace=0.08)

# Panel 1: clean VPN share of panel
ax1.plot(monthly['date'], monthly['clean_vpn_pct'],
         color='steelblue', linewidth=1.8, marker='o', markersize=4)
ax1.set_ylabel('Clean VPN visitors\n(% of monthly panel)', fontsize=11)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1f}%'))
ax1.grid(axis='y', linestyle='--', alpha=0.4)
ax1.spines[['top', 'right']].set_visible(False)

# Panel 2: % of VPN visitors also visiting XXX that month
ax2.plot(monthly['date'], monthly['overlap_pct_of_vpn'],
         color='firebrick', linewidth=1.8, marker='o', markersize=4)
ax2.axhline(monthly['overlap_pct_of_vpn'].mean(), color='firebrick',
            linewidth=1, linestyle='--', alpha=0.5, label=f"36-month avg: {monthly['overlap_pct_of_vpn'].mean():.1f}%")
ax2.legend(fontsize=9, frameon=False)
ax2.set_ylabel('VPN visitors also visiting\nXXX that month (% of VPN)', fontsize=11)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
ax2.grid(axis='y', linestyle='--', alpha=0.4)
ax2.spines[['top', 'right']].set_visible(False)

ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right')

fig.suptitle('VPN site usage — Jan 2022 to Dec 2024', fontsize=13, y=0.99)

ts_path = os.path.join(out_dir, f'vpn_timeseries_{_ts}.png')
fig.savefig(ts_path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {ts_path}")
print("\nDone.")
