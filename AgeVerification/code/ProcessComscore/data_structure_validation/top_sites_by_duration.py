# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-12
# Updated: 2026-05-22
# Purpose: Scan 2022 merged session parquet files and compute the top 100
#          websites ranked by total time spent (duration), summed across
#          2022 only. Session durations are winsorized at the P95 of all
#          2022 sessions before summing (matching Script 2 behaviour).
#
# Input:  data/ProcessComscore/merged_session_files/merged_sessions_2022*.parquet
# Output: output/ProcessComscore/data_structure_validation/top_sites_by_duration.csv
#
# Usage:
#   python3 code/ProcessComscore/data_structure_validation/top_sites_by_duration.py

import os
import glob
import sys
import pandas as pd
import pyarrow.parquet as pq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# CONFIG
# ============================================================================

TOP_N       = 100
TOP_N_TEX   = 50
TOP_N_ADULT = 100
READ_COLS = ['top_web_id', 'top_web_name', 'category', 'subcategory', 'duration']

# ============================================================================
# PATHS
# ============================================================================

ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
data_dir  = os.path.join(ROOT, 'data', 'ProcessComscore', 'merged_session_files')
out_dir   = os.path.join(ROOT, 'output', 'ProcessComscore', 'data_structure_validation')
out_path        = os.path.join(out_dir, 'top_sites_by_duration.csv')
adult_out_path       = os.path.join(out_dir, 'top_adult_sites.csv')
top25_adult_out_path        = os.path.join(out_dir, 'top25_adult_sites.csv')
top25_adult_visits_out_path = os.path.join(out_dir, 'top25_adult_sites_visits.csv')
tex_path        = os.path.join(out_dir, 'top_sites_by_duration.tex')
chart_path      = os.path.join(out_dir, 'top_sites_by_duration.png')
os.makedirs(out_dir, exist_ok=True)

files = sorted(glob.glob(os.path.join(data_dir, 'merged_sessions_2022*.parquet')))

if not files:
    print(f"ERROR: No merged session files found in {data_dir}")
    raise SystemExit(1)

# ============================================================================
# ACCUMULATE
# ============================================================================

print("=" * 70)
print("TOP SITES BY DURATION — 2022 merged session files (session-level P95 winsorization)")
print("=" * 70)
print(f"Files to scan: {len(files)}")
for f in files:
    print(f"  {os.path.basename(f)}")
print()

# ============================================================================
# PASS 1: compute P95 session duration threshold across all 2022 sessions
# ============================================================================

print("Pass 1: computing P95 session duration threshold ...")
dur_chunks = []
for path in files:
    s = pd.read_parquet(path, columns=['duration'])['duration']
    s = pd.to_numeric(s, errors='coerce').fillna(0)
    dur_chunks.append(s)

p95_duration = pd.concat(dur_chunks).quantile(0.95)
print(f"  P95 session duration (2022): {p95_duration:.1f} seconds")
print()
del dur_chunks

# ============================================================================
# PASS 2: accumulate winsorized durations by site
# ============================================================================

# Accumulators keyed by top_web_id
duration_totals = {}   # top_web_id -> total duration (seconds)
session_counts  = {}   # top_web_id -> session count
site_meta       = {}   # top_web_id -> (top_web_name, category, subcategory)

grand_duration = 0
grand_sessions = 0

print("Pass 2: accumulating winsorized durations by site ...")
for path in files:
    fname = os.path.basename(path)
    print(f"  Processing {fname} ...", end=' ', flush=True)

    # Read only needed columns — much faster than loading full file
    schema = pq.read_schema(path)
    available = [c for c in READ_COLS if c in schema.names]
    missing   = [c for c in READ_COLS if c not in schema.names]
    if missing:
        print(f"\n    WARNING: missing columns {missing}, skipping file")
        continue

    df = pd.read_parquet(path, columns=available)

    # Coerce duration to numeric (some files may store as object)
    df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0)

    # Winsorize at session level (P95 computed in pass 1)
    df['duration'] = df['duration'].clip(upper=p95_duration)

    file_sessions = len(df)
    file_duration = df['duration'].sum()
    grand_sessions += file_sessions
    grand_duration += file_duration

    # Group by site and accumulate
    grp = df.groupby('top_web_id', dropna=False).agg(
        duration_sum=('duration', 'sum'),
        session_n=('duration', 'count'),
        top_web_name=('top_web_name', 'first'),
        category=('category', 'first'),
        subcategory=('subcategory', 'first'),
    ).reset_index()

    for _, row in grp.iterrows():
        wid = row['top_web_id']
        duration_totals[wid] = duration_totals.get(wid, 0) + row['duration_sum']
        session_counts[wid]  = session_counts.get(wid, 0)  + row['session_n']
        if wid not in site_meta:
            site_meta[wid] = (row['top_web_name'], row['category'], row['subcategory'])

    print(f"{file_sessions:,} sessions, {file_duration/3600:.0f}h")

# ============================================================================
# RANK AND OUTPUT
# ============================================================================

print()
print("Building rankings ...")

rows = []
for wid, total_dur in duration_totals.items():
    name, cat, subcat = site_meta.get(wid, ('', '', ''))
    rows.append({
        'top_web_id':    wid,
        'top_web_name':  name,
        'category':      cat,
        'subcategory':   subcat,
        'total_duration': total_dur,
        'duration_pct':  100 * total_dur / grand_duration if grand_duration > 0 else 0,
        'session_count': session_counts[wid],
        'session_pct':   100 * session_counts[wid] / grand_sessions if grand_sessions > 0 else 0,
    })

out_df = (
    pd.DataFrame(rows)
    .sort_values('total_duration', ascending=False)
    .head(TOP_N)
    .reset_index(drop=True)
)
out_df.insert(0, 'rank', out_df.index + 1)

out_df.to_csv(out_path, index=False)

# XXX Adult top-N slice (drawn from all sites, not just the top-100 cutoff)
all_df = pd.DataFrame(rows).sort_values('total_duration', ascending=False)
adult_df = (
    all_df[all_df['subcategory'] == 'XXX Adult']
    .head(TOP_N_ADULT)
    .reset_index(drop=True)
)
adult_df.insert(0, 'rank', adult_df.index + 1)
adult_df.to_csv(adult_out_path, index=False)

adult_df[['rank', 'top_web_id', 'top_web_name']].head(25).to_csv(top25_adult_out_path, index=False)

# Top 25 XXX Adult sites by session count (visits), drawn from same top-100-by-duration pool
adult_visits_df = (
    all_df[all_df['subcategory'] == 'XXX Adult']
    .sort_values('session_count', ascending=False)
    .head(25)
    .reset_index(drop=True)
)
adult_visits_df.insert(0, 'rank', adult_visits_df.index + 1)
adult_visits_df[['rank', 'top_web_id', 'top_web_name']].to_csv(top25_adult_visits_out_path, index=False)

# ============================================================================
# LaTeX OUTPUT (top 50)
# ============================================================================

def esc(s):
    s = str(s) if s is not None else ''
    return (s.replace('&', r'\&')
             .replace('%', r'\%')
             .replace('_', r'\_')
             .replace('#', r'\#')
             .replace('$', r'\$'))

tex_df = out_df.head(TOP_N_TEX)

tex_rows = []
for _, row in tex_df.iterrows():
    hrs = row['total_duration'] / 3600
    tex_rows.append(
        f"  {int(row['rank'])} & {esc(row['top_web_name'])} & "
        f"{esc(row['category'])} & {hrs:,.0f} \\\\"
    )

tex_lines = [
    r"\begin{tabular}{rlll}",
    r"\toprule",
    r"  Rank & Site & Category & Total Duration (hrs) \\",
    r"\midrule",
] + tex_rows + [
    r"\bottomrule",
    r"\end{tabular}",
]

with open(tex_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(tex_lines) + '\n')

# ============================================================================
# SUMMARY
# ============================================================================

# ============================================================================
# BAR CHART (top 50, longest to shortest top-to-bottom)
# ============================================================================

chart_df = out_df.head(TOP_N_TEX).copy()
chart_df['duration_hrs'] = chart_df['total_duration'] / 3600
# Reverse so rank 1 is at the top
chart_df = chart_df.iloc[::-1].reset_index(drop=True)

fig, ax = plt.subplots(figsize=(10, 14))
bars = ax.barh(
    chart_df['top_web_name'],
    chart_df['duration_hrs'],
    color='#0B3954',
    edgecolor='none',
    height=0.7,
)
ax.set_xlabel('Total Duration (hours)', fontsize=11)
ax.set_title(f'Top {TOP_N_TEX} Sites by Total Time Spent', fontsize=13)
ax.tick_params(axis='y', labelsize=8)
ax.tick_params(axis='x', labelsize=9)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
fig.savefig(chart_path, dpi=150, bbox_inches='tight')
plt.close(fig)

# ============================================================================
# SUMMARY
# ============================================================================

print()
print("=" * 70)
print(f"Grand total: {grand_sessions:,} sessions, {grand_duration/3600:,.0f} hours")
print(f"Unique sites: {len(duration_totals):,}")
print()
print(f"Top {TOP_N} sites (CSV):              {out_path}")
print(f"Top {TOP_N_ADULT} XXX Adult sites (CSV): {adult_out_path}")
print(f"Top 25 XXX Adult sites (slim CSV): {top25_adult_out_path}")
print(f"Top 25 XXX Adult sites by visits:  {top25_adult_visits_out_path}")
print(f"Top {TOP_N_TEX} sites (LaTeX):        {tex_path}")
print(f"Top {TOP_N_TEX} sites (chart):        {chart_path}")
print()
print(f"{'Rank':<5} {'Site':<35} {'Duration (hrs)':>15} {'Dur %':>7} {'Sessions':>10}")
print("-" * 75)
for _, row in out_df.head(20).iterrows():
    name = str(row['top_web_name'])[:34]
    print(f"{int(row['rank']):<5} {name:<35} {row['total_duration']/3600:>15,.0f} "
          f"{row['duration_pct']:>6.2f}% {int(row['session_count']):>10,}")

print()
print("=" * 70)
print("DONE")
print("=" * 70)
