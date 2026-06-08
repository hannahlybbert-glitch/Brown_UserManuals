# Author: Hannah Lybbert
# Created: 2026-03-04
# Purpose: Diagnostics on VPN traffic prevalence using merged_sessions parquet files.
#          Runs on existing merged_sessions_YYYYMM.parquet files (which already have
#          top_web_name). Applies VPN whitelist inline — no need to re-run merge pipeline.
#
# Usage:
#   python code/ProcessComscore/data_structure_validation/vpn_site_diagnostics.py
#   python code/ProcessComscore/data_structure_validation/vpn_site_diagnostics.py --project-root /abs/path

'''
Input:  data/ProcessComscore/merged_session_files/merged_sessions_YYYYMM.parquet
Output: printed to stdout + timestamped log in data/ProcessComscore/

Processes one file at a time to avoid loading all 36 months into memory at once.
Accumulates small aggregated results across months, then prints all sections.

Sections:
  1. Per-site visitor and session counts
  2. Overall VPN visitors (share of total)
  3. Time trends (monthly)
  4. State-level breakdown
  5. Overlap with XXX Adult visitors
  6. VPN usage intensity
'''

import argparse
import os
import sys
from glob import glob
from datetime import datetime

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# ══════════════════════════════════════════════════════════════════════════════
# ARGS
# ══════════════════════════════════════════════════════════════════════════════
parser = argparse.ArgumentParser(description="VPN site diagnostics on merged_sessions parquet files.")
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
# 1a. Confirmed root Properties (whitelist)
# Symantec and BITDEFENDER.COM are broad antivirus companies — VPN sessions
# are overcounted; tracked separately in diagnostics.
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

# Antivirus/broad companies that overcount VPN — reported separately
ANTIVIRUS_SITES = {'Symantec', 'Gen Digital Inc. (Formally Symantec - NortonLifeLock)', 'BITDEFENDER.COM'}

# 1b. Dynamic keywords for 6 sites with unknown top_web_name
DYNAMIC_VPN_KEYWORDS = 'protonvpn|mullvad|hotshield|privadovpn|ivpn|airvpn'


def is_vpn_site(top_web_name_series):
    """Return boolean Series: True if top_web_name is a VPN site."""
    return (
        top_web_name_series.isin(VPN_WHITELIST) |
        top_web_name_series.str.lower().str.contains(DYNAMIC_VPN_KEYWORDS, na=False)
    )


# ══════════════════════════════════════════════════════════════════════════════
# TEE — write to stdout AND a timestamped log file
# ══════════════════════════════════════════════════════════════════════════════
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
_real_stdout = sys.stdout


class _Tee:
    def __init__(self, path):
        self._f = open(path, 'w', encoding='utf-8', errors='replace')

    def write(self, m):
        self._f.write(m)
        _real_stdout.write(m)

    def flush(self):
        self._f.flush()
        _real_stdout.flush()

    def close(self):
        self._f.close()

    def reconfigure(self, **kw):
        pass  # no-op; real stdout already reconfigured above


log_dir = os.path.join(project_root, 'data', 'ProcessComscore')
os.makedirs(log_dir, exist_ok=True)
_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
log_path = os.path.join(log_dir, f'vpn_site_diagnostics_{_ts}.log')
sys.stdout = _Tee(log_path)

# ══════════════════════════════════════════════════════════════════════════════
# FIND FILES
# ══════════════════════════════════════════════════════════════════════════════
merged_dir = os.path.join(project_root, 'data', 'ProcessComscore', 'merged_session_files')
parquet_files = sorted(glob(os.path.join(merged_dir, 'merged_sessions_*.parquet')))

if not parquet_files:
    print(f"ERROR: No merged_sessions parquet files found in {merged_dir}")
    sys.exit(1)

print('=' * 80)
print('VPN SITE DIAGNOSTICS')
print('=' * 80)
print(f'Project root : {project_root}')
print(f'Log file     : {log_path}')
print(f'Files found  : {len(parquet_files)}')
for f in parquet_files:
    print(f'  {os.path.basename(f)}')
print()

NEEDED_COLS = ['person_id', 'top_web_name', 'subcategory', 'month_id', 'state']

# ══════════════════════════════════════════════════════════════════════════════
# ACCUMULATORS
# ══════════════════════════════════════════════════════════════════════════════
# Section 1: per-site pooled counts
site_sessions = {}       # {top_web_name -> int}
site_persons = {}        # {top_web_name -> set of person_ids}

# Sections 2 & 3: one dict per month + pooled person sets
monthly_rows = []
all_persons_set = set()
all_vpn_persons_set = set()
all_clean_vpn_persons_set = set()

# Section 4: state-level (sets for deduplication across months)
state_total = {}         # {state -> set of person_ids}
state_vpn = {}
state_clean = {}
has_state_data = False

# Section 5: per-month overlap rows
overlap_rows = []

# Section 6: VPN session counts per person (accumulated across all months)
vpn_counts = {}          # {person_id -> int}
clean_vpn_counts = {}    # {person_id -> int}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP — one file at a time
# ══════════════════════════════════════════════════════════════════════════════
print('Processing files...')
for fpath in parquet_files:
    fname = os.path.basename(fpath)

    # Read parquet schema without loading data, then load only needed columns
    available = pq.read_schema(fpath).names
    cols_to_read = [c for c in NEEDED_COLS if c in available]
    missing = [c for c in NEEDED_COLS if c not in available]
    if missing:
        print(f'  WARNING [{fname}]: missing columns {missing} — will use NaN.')

    df = pd.read_parquet(fpath, columns=cols_to_read)
    for c in missing:
        df[c] = np.nan

    # Flag VPN sites
    df['vpn_site'] = is_vpn_site(df['top_web_name'])
    df['is_antivirus_vpn'] = df['top_web_name'].isin(ANTIVIRUS_SITES)
    df['is_clean_vpn'] = df['vpn_site'] & ~df['is_antivirus_vpn']

    vpn_df      = df[df['vpn_site']]
    clean_vpn_df = df[df['is_clean_vpn']]
    av_df       = df[df['is_antivirus_vpn']]
    xxx_df      = df[df['subcategory'] == 'XXX Adult']

    month_id = df['month_id'].iloc[0]
    print(f'  {fname}: {len(df):,} sessions, {df["vpn_site"].sum():,} VPN sessions')

    # --- Section 1: per-site accumulation ---
    for name, grp in vpn_df.groupby('top_web_name', dropna=False):
        if name not in site_sessions:
            site_sessions[name] = 0
            site_persons[name] = set()
        site_sessions[name] += len(grp)
        site_persons[name].update(grp['person_id'].dropna().unique())

    # --- Sections 2 & 3: monthly stats + pooled sets ---
    monthly_rows.append({
        'month_id':          month_id,
        'total_persons':     df['person_id'].nunique(),
        'total_sessions':    len(df),
        'vpn_persons':       vpn_df['person_id'].nunique(),
        'vpn_sessions':      len(vpn_df),
        'clean_vpn_persons': clean_vpn_df['person_id'].nunique(),
        'clean_vpn_sessions': len(clean_vpn_df),
        'av_vpn_persons':    av_df['person_id'].nunique(),
        'av_vpn_sessions':   len(av_df),
    })
    all_persons_set.update(df['person_id'].dropna().unique())
    all_vpn_persons_set.update(vpn_df['person_id'].dropna().unique())
    all_clean_vpn_persons_set.update(clean_vpn_df['person_id'].dropna().unique())

    # --- Section 4: state-level ---
    if not df['state'].isna().all():
        has_state_data = True
        for state, grp in df.groupby('state', dropna=True):
            state_total.setdefault(state, set()).update(grp['person_id'].dropna().unique())
        for state, grp in vpn_df.groupby('state', dropna=True):
            state_vpn.setdefault(state, set()).update(grp['person_id'].dropna().unique())
        for state, grp in clean_vpn_df.groupby('state', dropna=True):
            state_clean.setdefault(state, set()).update(grp['person_id'].dropna().unique())

    # --- Section 5: per-month overlap ---
    xxx_set   = set(xxx_df['person_id'].dropna().unique())
    vpn_set   = set(vpn_df['person_id'].dropna().unique())
    clean_set = set(clean_vpn_df['person_id'].dropna().unique())
    overlap       = len(xxx_set & vpn_set)
    clean_overlap = len(xxx_set & clean_set)
    overlap_rows.append({
        'month_id':               month_id,
        'xxx_visitors':           len(xxx_set),
        'vpn_visitors':           len(vpn_set),
        'overlap_both':           overlap,
        'clean_vpn_xxx_overlap':  clean_overlap,
        'overlap_pct_of_xxx':     round(overlap / len(xxx_set) * 100, 3) if xxx_set else np.nan,
        'overlap_pct_of_vpn':     round(overlap / len(vpn_set) * 100, 3) if vpn_set else np.nan,
        'clean_overlap_pct_of_xxx': round(clean_overlap / len(xxx_set) * 100, 3) if xxx_set else np.nan,
    })
    # --- Section 6: VPN session counts per person ---
    for pid, cnt in vpn_df.groupby('person_id', dropna=True).size().items():
        vpn_counts[pid] = vpn_counts.get(pid, 0) + cnt
    for pid, cnt in clean_vpn_df.groupby('person_id', dropna=True).size().items():
        clean_vpn_counts[pid] = clean_vpn_counts.get(pid, 0) + cnt

    del df, vpn_df, clean_vpn_df, av_df, xxx_df

print(f'\nProcessed {len(monthly_rows)} month(s).')
print()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Per-site visitor and session counts (pooled across all months)
# ══════════════════════════════════════════════════════════════════════════════
print('=' * 80)
print('SECTION 1 — Per-site visitor and session counts (all months pooled)')
print('=' * 80)

site_stats = pd.DataFrame([
    {
        'top_web_name':       name,
        'unique_persons':     len(site_persons[name]),
        'sessions':           site_sessions[name],
        'sessions_per_visitor': round(site_sessions[name] / len(site_persons[name]), 1)
                               if site_persons[name] else np.nan,
    }
    for name in site_sessions
]).set_index('top_web_name').sort_values('unique_persons', ascending=False)

av_mask = site_stats.index.isin(ANTIVIRUS_SITES)

print('\nAll VPN sites:')
print(site_stats.to_string())

print('\nAntivirus/broad companies (overcount note):')
print(site_stats[av_mask].to_string())

print('\nClean VPN-only sites:')
print(site_stats[~av_mask].to_string())

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Overall VPN visitors (share of total unique persons)
# ══════════════════════════════════════════════════════════════════════════════
print()
print('=' * 80)
print('SECTION 2 — Overall VPN visitors (share of total unique persons)')
print('=' * 80)

total_persons     = len(all_persons_set)
vpn_persons       = len(all_vpn_persons_set)
clean_vpn_persons = len(all_clean_vpn_persons_set)

print(f'\nTotal unique persons (all months)    : {total_persons:,}')
print(f'VPN visitors (any VPN site)          : {vpn_persons:,}  ({vpn_persons / total_persons * 100:.2f}% of total)')
print(f'Clean VPN visitors (excl. antivirus) : {clean_vpn_persons:,}  ({clean_vpn_persons / total_persons * 100:.2f}% of total)')

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Time trends (monthly)
# ══════════════════════════════════════════════════════════════════════════════
print()
print('=' * 80)
print('SECTION 3 — Time trends (per month)')
print('=' * 80)

monthly_trends = pd.DataFrame(monthly_rows).set_index('month_id').sort_index()
monthly_trends['vpn_share_pct'] = (
    monthly_trends['vpn_persons'] / monthly_trends['total_persons'] * 100
).round(3)
monthly_trends['clean_vpn_share_pct'] = (
    monthly_trends['clean_vpn_persons'] / monthly_trends['total_persons'] * 100
).round(3)

print('\nMonthly VPN trends:')
print(monthly_trends.to_string())

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — State-level breakdown
# ══════════════════════════════════════════════════════════════════════════════
print()
print('=' * 80)
print('SECTION 4 — State-level breakdown')
print('=' * 80)

if not has_state_data:
    print('\nWARNING: state column is all NaN — state breakdown not available.')
else:
    all_states = sorted(state_total.keys())
    state_rows = []
    for state in all_states:
        tot  = len(state_total.get(state, set()))
        vpn  = len(state_vpn.get(state, set()))
        cln  = len(state_clean.get(state, set()))
        state_rows.append({
            'state':               state,
            'total_persons':       tot,
            'vpn_persons':         vpn,
            'clean_vpn_persons':   cln,
            'vpn_rate_pct':        round(vpn / tot * 100, 3) if tot else np.nan,
            'clean_vpn_rate_pct':  round(cln / tot * 100, 3) if tot else np.nan,
        })
    state_stats = (
        pd.DataFrame(state_rows)
        .set_index('state')
        .sort_values('vpn_rate_pct', ascending=False)
    )
    print('\nVPN visitor rate by state (sorted by VPN rate):')
    print(state_stats.to_string())

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Overlap with XXX Adult visitors
# ══════════════════════════════════════════════════════════════════════════════
print()
print('=' * 80)
print('SECTION 5 — Overlap: VPN visitors AND XXX Adult visitors (same month)')
print('=' * 80)

overlap_df = pd.DataFrame(overlap_rows).set_index('month_id').sort_index()
print('\nMonthly overlap between VPN visitors and XXX Adult visitors:')
print(overlap_df.to_string())

avg_vpn_xxx    = overlap_df['overlap_pct_of_vpn'].mean()
avg_xxx_vpn    = overlap_df['overlap_pct_of_xxx'].mean()
avg_clean_xxx  = overlap_df['clean_overlap_pct_of_xxx'].mean()
print(f'\nSimple average across {len(overlap_df)} months:')
print(f'  % of VPN visitors also visiting XXX that month       : {avg_vpn_xxx:.1f}%')
print(f'  % of XXX visitors also visiting a VPN that month     : {avg_xxx_vpn:.1f}%')
print(f'  % of XXX visitors also visiting a clean VPN that month: {avg_clean_xxx:.1f}%')

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — VPN usage intensity
# ══════════════════════════════════════════════════════════════════════════════
print()
print('=' * 80)
print('SECTION 6 — VPN usage intensity (sessions per VPN visitor)')
print('=' * 80)

if not vpn_counts:
    print('\nNo VPN visitors found.')
else:
    vpn_series = pd.Series(vpn_counts, name='vpn_session_count')
    pcts = [50, 75, 90, 95, 99]
    quantiles = vpn_series.quantile([p / 100 for p in pcts])
    print(f'\nVPN session count per visitor (N={len(vpn_series):,} unique persons):')
    print(f'  Mean   : {vpn_series.mean():.1f}')
    print(f'  Median : {vpn_series.median():.1f}')
    for p, val in zip(pcts, quantiles):
        print(f'  p{p:02d}    : {val:.0f}')
    print(f'  Max    : {vpn_series.max():.0f}')
    one_session = (vpn_series == 1).sum()
    repeat      = (vpn_series > 1).sum()
    print(f'\n  Single-session VPN visitors      : {one_session:,}  ({one_session / len(vpn_series) * 100:.1f}%)')
    print(f'  Repeat VPN visitors (>1 session) : {repeat:,}  ({repeat / len(vpn_series) * 100:.1f}%)')

    if clean_vpn_counts:
        clean_series = pd.Series(clean_vpn_counts, name='vpn_session_count')
        print(f'\nClean VPN only (excl. antivirus), N={len(clean_series):,} unique persons:')
        print(f'  Mean   : {clean_series.mean():.1f}')
        print(f'  Median : {clean_series.median():.1f}')
        clean_one = (clean_series == 1).sum()
        print(f'  Single-session : {clean_one:,}  ({clean_one / len(clean_series) * 100:.1f}%)')

print()
print('=' * 80)
print('DONE')
print(f'Log saved to: {log_path}')
print('=' * 80)
