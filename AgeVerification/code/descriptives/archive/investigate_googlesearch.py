#!/usr/bin/env python3
# Author: Emily
# Created: 2026-01-30
# Purpose: Analyze how people navigate to adult sites - via Google/Bing search vs. direct navigation.
#          This analysis can be compared with Google Trends data for validation.
# Inputs (internal): merged session parquet files, crosswalk files
# Outputs: Summary tables showing share of searches to adult sites and share of adult visits from search

import pandas as pd
from pathlib import Path

import os

# Set working directory to local git repo
os.chdir("/Users/emilydavis/Documents/gitrepos/AgeVerification")

# Config
DATA_DIR = Path("data/ProcessComscore")
OUTPUT_DIR = Path("output/descriptives")

# Month configurations: (month_id, session_file_suffix)
MONTHS = [
    (265, "202201"),
    (300, "202412"),
]

# Major adult sites to analyze
MAJOR_SITES = ["pornhub", "xvideos", "xnxx", "xhamster", "chaturbate"]

# Search engine top_web_ids
GOOGLE_TOP_WEB_ID = '590133'
MICROSOFT_TOP_WEB_ID = '11320'  # Microsoft Sites (includes Bing)


def load_search_pattern_ids(month_id: int) -> tuple:
    """Load pattern_ids for Google and Microsoft Sites."""
    crosswalk_path = DATA_DIR / "intermediate" / str(month_id) / "crosswalk.parquet"
    crosswalk = pd.read_parquet(crosswalk_path)
    crosswalk['top_web_id'] = crosswalk['top_web_id'].astype(str)
    crosswalk['pattern_id'] = crosswalk['pattern_id'].astype(str)

    google_patterns = set(crosswalk[crosswalk['top_web_id'] == GOOGLE_TOP_WEB_ID]['pattern_id'].tolist())
    microsoft_patterns = set(crosswalk[crosswalk['top_web_id'] == MICROSOFT_TOP_WEB_ID]['pattern_id'].tolist())

    return google_patterns, microsoft_patterns


def load_sessions(session_suffix: str) -> pd.DataFrame:
    """Load merged sessions parquet file."""
    session_path = DATA_DIR / "merged_session_files" / f"merged_sessions_{session_suffix}.parquet"
    if not session_path.exists():
        raise FileNotFoundError(f"Session file not found: {session_path}")

    print(f"Loading sessions from: {session_path}")
    df = pd.read_parquet(session_path)
    print(f"  Loaded {len(df):,} sessions")
    return df


def get_referrer_info(df: pd.DataFrame, crosswalk_path: Path, web_chars_path: Path) -> pd.DataFrame:
    """Add referrer subcategory to dataframe by looking up ref_pattern_id."""
    crosswalk = pd.read_parquet(crosswalk_path)
    crosswalk['pattern_id'] = crosswalk['pattern_id'].astype(str)
    crosswalk['top_web_id'] = crosswalk['top_web_id'].astype(str)

    web_chars = pd.read_parquet(web_chars_path)
    web_chars['top_web_id'] = web_chars['top_web_id'].astype(str)

    ref_mapping = crosswalk.merge(web_chars[['top_web_id', 'subcategory', 'top_web_name']],
                                   on='top_web_id', how='left')
    ref_mapping = ref_mapping.rename(columns={
        'subcategory': 'ref_subcategory',
        'top_web_name': 'ref_web_name'
    })

    df['ref_pattern_id_str'] = df['ref_pattern_id'].astype(str)
    df = df.merge(ref_mapping[['pattern_id', 'ref_subcategory', 'ref_web_name']],
                  left_on='ref_pattern_id_str', right_on='pattern_id',
                  how='left', suffixes=('', '_ref'))

    return df


def analyze_month(month_id: int, session_suffix: str) -> dict:
    """Analyze search patterns for a single month and return results dict."""

    print(f"\nProcessing month {month_id} ({session_suffix})...")

    # Load data
    google_patterns, microsoft_patterns = load_search_pattern_ids(month_id)
    print(f"  Google pattern_ids: {len(google_patterns):,}")
    print(f"  Microsoft pattern_ids: {len(microsoft_patterns):,}")

    df = load_sessions(session_suffix)

    # Add referrer info
    crosswalk_path = DATA_DIR / "intermediate" / str(month_id) / "crosswalk.parquet"
    web_chars_path = DATA_DIR / "intermediate" / str(month_id) / "web_characteristics.parquet"
    df = get_referrer_info(df, crosswalk_path, web_chars_path)

    # Identify referrer types
    df['ref_pattern_id'] = df['ref_pattern_id'].astype(str)
    df['from_google'] = df['ref_pattern_id'].isin(google_patterns)
    df['from_microsoft'] = df['ref_pattern_id'].isin(microsoft_patterns)
    df['from_search'] = df['from_google'] | df['from_microsoft']
    df['is_direct'] = df['ref_pattern_id'] == '0'
    df['is_xxx_adult'] = df['subcategory'] == 'XXX Adult'
    df['top_web_name_lower'] = df['top_web_name'].str.lower()

    # Overall stats
    total_sessions = len(df)
    google_sessions = df['from_google'].sum()
    microsoft_sessions = df['from_microsoft'].sum()
    search_sessions = df['from_search'].sum()
    xxx_sessions = df['is_xxx_adult'].sum()

    # XXX Adult breakdown
    xxx_df = df[df['is_xxx_adult']].copy()
    xxx_direct = xxx_df['is_direct'].sum()
    xxx_google = xxx_df['from_google'].sum()
    xxx_microsoft = xxx_df['from_microsoft'].sum()
    xxx_search = xxx_df['from_search'].sum()
    xxx_other = len(xxx_df) - xxx_direct - xxx_search

    # Site-specific results
    site_results = {}
    for site in MAJOR_SITES:
        site_mask = xxx_df['top_web_name_lower'].str.contains(site, na=False)
        site_sessions = xxx_df[site_mask]

        if len(site_sessions) == 0:
            continue

        site_results[site] = {
            'total': len(site_sessions),
            'google': site_sessions['from_google'].sum(),
            'microsoft': site_sessions['from_microsoft'].sum(),
            'search': site_sessions['from_search'].sum(),
            'direct': site_sessions['is_direct'].sum(),
        }

    # Other referrer breakdown (excluding direct, Google, Microsoft)
    other_referrers = xxx_df[~xxx_df['is_direct'] & ~xxx_df['from_search']].copy()
    other_subcat_counts = other_referrers['ref_subcategory'].value_counts().head(5).to_dict()
    other_site_counts = other_referrers['ref_web_name'].value_counts().head(10).to_dict()

    return {
        'month_id': month_id,
        'session_suffix': session_suffix,
        'total_sessions': total_sessions,
        'google_sessions': google_sessions,
        'microsoft_sessions': microsoft_sessions,
        'search_sessions': search_sessions,
        'xxx_sessions': xxx_sessions,
        'xxx_direct': xxx_direct,
        'xxx_google': xxx_google,
        'xxx_microsoft': xxx_microsoft,
        'xxx_search': xxx_search,
        'xxx_other': xxx_other,
        'site_results': site_results,
        'other_subcat_counts': other_subcat_counts,
        'other_site_counts': other_site_counts,
        'other_referrers_total': len(other_referrers),
    }


def print_combined_tables(results: list):
    """Print tables with both months side-by-side."""

    r1, r2 = results[0], results[1]
    m1, m2 = r1['session_suffix'], r2['session_suffix']

    print(f"\n{'='*80}")
    print("TABLE 1: Overall Search Engine Analysis")
    print(f"{'='*80}\n")

    print(f"| Metric | {m1} | {m2} |")
    print("|--------|--------|--------|")
    print(f"| Total sessions | {r1['total_sessions']:,} | {r2['total_sessions']:,} |")
    print(f"| Google-referred sessions | {r1['google_sessions']:,} ({100*r1['google_sessions']/r1['total_sessions']:.1f}%) | {r2['google_sessions']:,} ({100*r2['google_sessions']/r2['total_sessions']:.1f}%) |")
    print(f"| Microsoft-referred sessions | {r1['microsoft_sessions']:,} ({100*r1['microsoft_sessions']/r1['total_sessions']:.1f}%) | {r2['microsoft_sessions']:,} ({100*r2['microsoft_sessions']/r2['total_sessions']:.1f}%) |")
    print(f"| XXX Adult sessions | {r1['xxx_sessions']:,} ({100*r1['xxx_sessions']/r1['total_sessions']:.1f}%) | {r2['xxx_sessions']:,} ({100*r2['xxx_sessions']/r2['total_sessions']:.1f}%) |")

    print(f"\n{'='*80}")
    print("TABLE 2: Key Measures - Search to Adult Site Navigation")
    print(f"{'='*80}\n")

    # Calculate key measures
    g_to_xxx_1 = 100 * r1['xxx_google'] / r1['google_sessions']
    g_to_xxx_2 = 100 * r2['xxx_google'] / r2['google_sessions']
    m_to_xxx_1 = 100 * r1['xxx_microsoft'] / r1['microsoft_sessions']
    m_to_xxx_2 = 100 * r2['xxx_microsoft'] / r2['microsoft_sessions']

    xxx_from_g_1 = 100 * r1['xxx_google'] / r1['xxx_sessions']
    xxx_from_g_2 = 100 * r2['xxx_google'] / r2['xxx_sessions']
    xxx_from_m_1 = 100 * r1['xxx_microsoft'] / r1['xxx_sessions']
    xxx_from_m_2 = 100 * r2['xxx_microsoft'] / r2['xxx_sessions']
    xxx_from_s_1 = 100 * r1['xxx_search'] / r1['xxx_sessions']
    xxx_from_s_2 = 100 * r2['xxx_search'] / r2['xxx_sessions']

    print(f"| Measure | {m1} | {m2} |")
    print("|---------|--------|--------|")
    print(f"| Share of Google searches → XXX Adult | {g_to_xxx_1:.3f}% | {g_to_xxx_2:.3f}% |")
    print(f"| Share of Microsoft searches → XXX Adult | {m_to_xxx_1:.3f}% | {m_to_xxx_2:.3f}% |")
    print(f"| Share of XXX Adult ← Google | {xxx_from_g_1:.2f}% | {xxx_from_g_2:.2f}% |")
    print(f"| Share of XXX Adult ← Microsoft | {xxx_from_m_1:.2f}% | {xxx_from_m_2:.2f}% |")
    print(f"| Share of XXX Adult ← Any Search | {xxx_from_s_1:.2f}% | {xxx_from_s_2:.2f}% |")

    print(f"\n{'='*80}")
    print("TABLE 3: XXX Adult Sessions by Referrer Type")
    print(f"{'='*80}\n")

    xxx_direct_pct_1 = 100 * r1['xxx_direct'] / r1['xxx_sessions']
    xxx_direct_pct_2 = 100 * r2['xxx_direct'] / r2['xxx_sessions']
    xxx_other_pct_1 = 100 * r1['xxx_other'] / r1['xxx_sessions']
    xxx_other_pct_2 = 100 * r2['xxx_other'] / r2['xxx_sessions']

    print(f"| Referrer Type | {m1} Sessions | {m1} % | {m2} Sessions | {m2} % |")
    print("|---------------|--------------|--------|--------------|--------|")
    print(f"| Direct (no referrer) | {r1['xxx_direct']:,} | {xxx_direct_pct_1:.2f}% | {r2['xxx_direct']:,} | {xxx_direct_pct_2:.2f}% |")
    print(f"| Google | {r1['xxx_google']:,} | {xxx_from_g_1:.2f}% | {r2['xxx_google']:,} | {xxx_from_g_2:.2f}% |")
    print(f"| Microsoft (Bing) | {r1['xxx_microsoft']:,} | {xxx_from_m_1:.2f}% | {r2['xxx_microsoft']:,} | {xxx_from_m_2:.2f}% |")
    print(f"| Other website | {r1['xxx_other']:,} | {xxx_other_pct_1:.2f}% | {r2['xxx_other']:,} | {xxx_other_pct_2:.2f}% |")

    print(f"\n{'='*80}")
    print("TABLE 4: Breakdown by Major Adult Site - % from Google")
    print(f"{'='*80}\n")

    print(f"| Site | {m1} Total | {m1} % Google | {m2} Total | {m2} % Google |")
    print("|------|-----------|--------------|-----------|--------------|")
    for site in MAJOR_SITES:
        s1 = r1['site_results'].get(site, {})
        s2 = r2['site_results'].get(site, {})
        if s1 and s2:
            pct1 = 100 * s1['google'] / s1['total'] if s1['total'] > 0 else 0
            pct2 = 100 * s2['google'] / s2['total'] if s2['total'] > 0 else 0
            print(f"| {site.upper()} | {s1['total']:,} | {pct1:.2f}% | {s2['total']:,} | {pct2:.2f}% |")

    print(f"\n{'='*80}")
    print("TABLE 5: Breakdown by Major Adult Site - % from Microsoft (Bing)")
    print(f"{'='*80}\n")

    print(f"| Site | {m1} % Microsoft | {m2} % Microsoft |")
    print("|------|-----------------|-----------------|")
    for site in MAJOR_SITES:
        s1 = r1['site_results'].get(site, {})
        s2 = r2['site_results'].get(site, {})
        if s1 and s2:
            pct1 = 100 * s1['microsoft'] / s1['total'] if s1['total'] > 0 else 0
            pct2 = 100 * s2['microsoft'] / s2['total'] if s2['total'] > 0 else 0
            print(f"| {site.upper()} | {pct1:.2f}% | {pct2:.2f}% |")

    print(f"\n{'='*80}")
    print("TABLE 6: Breakdown by Major Adult Site - % from Any Search Engine")
    print(f"{'='*80}\n")

    print(f"| Site | {m1} % Search | {m2} % Search |")
    print("|------|-------------|-------------|")
    for site in MAJOR_SITES:
        s1 = r1['site_results'].get(site, {})
        s2 = r2['site_results'].get(site, {})
        if s1 and s2:
            pct1 = 100 * s1['search'] / s1['total'] if s1['total'] > 0 else 0
            pct2 = 100 * s2['search'] / s2['total'] if s2['total'] > 0 else 0
            print(f"| {site.upper()} | {pct1:.2f}% | {pct2:.2f}% |")

    print(f"\n{'='*80}")
    print("TABLE 7: Breakdown by Major Adult Site - % Direct Navigation")
    print(f"{'='*80}\n")

    print(f"| Site | {m1} % Direct | {m2} % Direct |")
    print("|------|-------------|-------------|")
    for site in MAJOR_SITES:
        s1 = r1['site_results'].get(site, {})
        s2 = r2['site_results'].get(site, {})
        if s1 and s2:
            pct1 = 100 * s1['direct'] / s1['total'] if s1['total'] > 0 else 0
            pct2 = 100 * s2['direct'] / s2['total'] if s2['total'] > 0 else 0
            print(f"| {site.upper()} | {pct1:.2f}% | {pct2:.2f}% |")

    print(f"\n{'='*80}")
    print("TABLE 8: 'Other Website' Referrers - Top Subcategories")
    print(f"{'='*80}\n")

    # Get union of top subcategories
    all_subcats = set(r1['other_subcat_counts'].keys()) | set(r2['other_subcat_counts'].keys())
    subcat_data = []
    for subcat in all_subcats:
        c1 = r1['other_subcat_counts'].get(subcat, 0)
        c2 = r2['other_subcat_counts'].get(subcat, 0)
        subcat_data.append((subcat, c1, c2, c1 + c2))
    subcat_data.sort(key=lambda x: -x[3])

    print(f"| Referrer Subcategory | {m1} Sessions | {m1} % | {m2} Sessions | {m2} % |")
    print("|---------------------|--------------|--------|--------------|--------|")
    for subcat, c1, c2, _ in subcat_data[:7]:
        subcat_name = subcat if pd.notna(subcat) else "Unknown"
        pct1 = 100 * c1 / r1['other_referrers_total'] if r1['other_referrers_total'] > 0 else 0
        pct2 = 100 * c2 / r2['other_referrers_total'] if r2['other_referrers_total'] > 0 else 0
        print(f"| {subcat_name} | {c1:,} | {pct1:.2f}% | {c2:,} | {pct2:.2f}% |")

    print(f"\n{'='*80}")
    print("TABLE 9: 'Other Website' Referrers - Top Specific Sites")
    print(f"{'='*80}\n")

    # Get union of top sites
    all_sites = set(r1['other_site_counts'].keys()) | set(r2['other_site_counts'].keys())
    site_data = []
    for site in all_sites:
        c1 = r1['other_site_counts'].get(site, 0)
        c2 = r2['other_site_counts'].get(site, 0)
        site_data.append((site, c1, c2, c1 + c2))
    site_data.sort(key=lambda x: -x[3])

    print(f"| Referrer Website | {m1} Sessions | {m1} % | {m2} Sessions | {m2} % |")
    print("|-----------------|--------------|--------|--------------|--------|")
    for site, c1, c2, _ in site_data[:10]:
        site_name = site if pd.notna(site) else "Unknown"
        pct1 = 100 * c1 / r1['other_referrers_total'] if r1['other_referrers_total'] > 0 else 0
        pct2 = 100 * c2 / r2['other_referrers_total'] if r2['other_referrers_total'] > 0 else 0
        print(f"| {site_name} | {c1:,} | {pct1:.2f}% | {c2:,} | {pct2:.2f}% |")


def main():
    print("=" * 80)
    print("SEARCH ENGINE NAVIGATION ANALYSIS")
    print("Analyzing how people navigate to adult websites (Google, Bing, Direct)")
    print("=" * 80)

    results = []
    for month_id, session_suffix in MONTHS:
        try:
            result = analyze_month(month_id, session_suffix)
            results.append(result)
        except FileNotFoundError as e:
            print(f"\nSkipping month {month_id}: {e}")

    if len(results) == 2:
        print_combined_tables(results)
    elif len(results) == 1:
        print("\nOnly one month available, cannot create comparison tables.")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
