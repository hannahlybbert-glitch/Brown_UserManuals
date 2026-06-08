#!/usr/bin/env python3
# Author: Emily
# Created: 2026-01-26
# Purpose: Compares Comscore's XXX Adult classification against GitHub porn domain blocklist.
# Inputs (internal): data/ProcessComscore/intermediate/{month}/web_characteristics.parquet
# Inputs (external): GitHub Bon-Appetit/porn-domains blocklist (cached to data/external/github_porn_domains.txt)
# Outputs: Summary tables (Tables 1-4) for each month; Category 3 sites saved to data/analysis/category3_{month}.csv

import json
import urllib.request
from collections import Counter
from pathlib import Path

import pandas as pd
import os

# Set working directory to local git repo                                                                                                                                      
# os.chdir("/Users/emilydavis/Documents/gitrepos/AgeVerification")

# Config
DATA_DIR = Path("data/ProcessComscore/intermediate")
CACHE_PATH = Path("data/external/github_porn_domains.txt")
OUTPUT_DIR = Path("data/analysis")
META_URL = "https://raw.githubusercontent.com/Bon-Appetit/porn-domains/main/meta.json"
BASE_URL = "https://raw.githubusercontent.com/Bon-Appetit/porn-domains/main/"

MONTHS = [265, 300]

SECOND_LEVEL_TLDS = {'co.uk', 'org.uk', 'com.br', 'com.au', 'co.nz', 'co.jp',
                     'co.kr', 'com.mx', 'com.ar', 'com.co', 'co.za'}


def extract_base_domain(domain: str) -> str:
    """Extract base domain (e.g., xxx.tumblr.com -> tumblr.com)."""
    domain = domain.lower().strip()
    if domain.startswith('www.'):
        domain = domain[4:]
    parts = domain.split('.')
    if len(parts) <= 2:
        return domain
    if len(parts) >= 3 and '.'.join(parts[-2:]) in SECOND_LEVEL_TLDS:
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])


def load_github_domains():
    """Load GitHub porn domains, return both raw and base domain sets."""
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            raw = [line.strip().lower() for line in f if line.strip()]
    else:
        with urllib.request.urlopen(META_URL, timeout=30) as r:
            meta = json.loads(r.read().decode('utf-8'))
        url = BASE_URL + meta['blocklist']['name']
        with urllib.request.urlopen(url, timeout=120) as r:
            raw = [line.strip().lower() for line in r.read().decode('utf-8').split('\n') if line.strip()]
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, 'w') as f:
            f.write('\n'.join(raw))

    base = set(extract_base_domain(d) for d in raw)
    return raw, base


def analyze_month(month: int, github_raw: list, github_base: set):
    """Run analysis for a single month and save Category 3 to CSV."""

    data_path = DATA_DIR / str(month) / "web_characteristics.parquet"
    if not data_path.exists():
        print(f"WARNING: Data not found for month {month}: {data_path}")
        return

    comscore = pd.read_parquet(data_path)
    comscore['normalized'] = comscore['top_web_name'].str.lower().str.strip()

    # Create sets
    comscore_xxx = set(comscore[comscore['subcategory'] == 'XXX Adult']['normalized'])
    comscore_all = set(comscore['normalized'])

    # Set operations
    in_both = comscore_xxx & github_base
    only_comscore = comscore_xxx - github_base
    only_github = github_base - comscore_xxx
    cat3 = (github_base & comscore_all) - comscore_xxx  # In Comscore, not XXX Adult

    print(f"\n{'='*70}")
    print(f"MONTH {month}")
    print(f"{'='*70}")

    # ===========================================
    # TABLE 1: Overlap Analysis
    # ===========================================
    print("\n## Table 1: Overlap Analysis\n")
    print(f"- Comscore XXX Adult sites: {len(comscore_xxx):,}")
    print(f"- GitHub base domains: {len(github_base):,}\n")
    print("| Set | Description | Count | % of Comscore | % of GitHub |")
    print("|-----|-------------|------:|--------------:|------------:|")
    print(f"| A | In BOTH | {len(in_both):,} | {100*len(in_both)/len(comscore_xxx):.1f}% | {100*len(in_both)/len(github_base):.1f}% |")
    print(f"| B | Only Comscore | {len(only_comscore):,} | {100*len(only_comscore)/len(comscore_xxx):.1f}% | - |")
    print(f"| C | Only GitHub | {len(only_github):,} | - | {100*len(only_github)/len(github_base):.1f}% |")

    # ===========================================
    # TABLE 2: GitHub Domain Validation
    # ===========================================
    cat1 = github_base & comscore_xxx
    cat2 = github_base - comscore_all

    print("\n## Table 2: GitHub Domain Validation\n")
    print("| Category | Description | Count | % |")
    print("|----------|-------------|------:|--:|")
    print(f"| 1 | In Comscore as XXX Adult | {len(cat1):,} | {100*len(cat1)/len(github_base):.1f}% |")
    print(f"| 2 | Not in Comscore | {len(cat2):,} | {100*len(cat2)/len(github_base):.1f}% |")
    print(f"| 3 | In Comscore, not XXX Adult | {len(cat3):,} | {100*len(cat3)/len(github_base):.1f}% |")

    # ===========================================
    # TABLE 3: Category 3 by Comscore Subcategory
    # ===========================================
    name_to_subcat = dict(zip(comscore['normalized'], comscore['subcategory']))
    cat3_subcats = Counter(name_to_subcat.get(d, 'Unknown') for d in cat3)

    print("\n## Table 3: Category 3 Breakdown by Comscore Subcategory\n")
    print("| Subcategory | Count | % |")
    print("|-------------|------:|--:|")
    for subcat, count in cat3_subcats.most_common(15):
        print(f"| {subcat} | {count:,} | {100*count/len(cat3):.1f}% |")

    # ===========================================
    # TABLE 4: GitHub List Composition
    # ===========================================
    tumblr_count = sum(1 for d in github_raw if d.endswith('.tumblr.com'))
    blogspot_count = sum(1 for d in github_raw if '.blogspot.' in d)
    other_platform = sum(1 for d in github_raw if any(p in d for p in ['.wordpress.com', '.livejournal.com', '.weebly.com']))
    platform_total = tumblr_count + blogspot_count + other_platform
    standalone = len(github_raw) - platform_total

    print("\n## Table 4: GitHub List Composition\n")
    print(f"Raw entries: {len(github_raw):,} → Base domains: {len(github_base):,}\n")
    print("| Type | Count | % |")
    print("|------|------:|--:|")
    print(f"| Tumblr subdomains | {tumblr_count:,} | {100*tumblr_count/len(github_raw):.1f}% |")
    print(f"| Blogspot subdomains | {blogspot_count:,} | {100*blogspot_count/len(github_raw):.1f}% |")
    print(f"| Other platform subdomains | {other_platform:,} | {100*other_platform/len(github_raw):.1f}% |")
    print(f"| **Standalone domains** | {standalone:,} | {100*standalone/len(github_raw):.1f}% |")

    # ===========================================
    # Save Category 3 to CSV
    # ===========================================
    cat3_data = [(d, name_to_subcat.get(d, 'Unknown')) for d in cat3]
    cat3_df = pd.DataFrame(cat3_data, columns=['domain', 'comscore_subcategory'])
    cat3_df = cat3_df.sort_values('domain')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"category3_{month}.csv"
    cat3_df.to_csv(output_path, index=False)

    print(f"\n---\nCategory 3 sites ({len(cat3_df):,}) saved to: {output_path}")


def main():
    # Load GitHub data once
    github_raw, github_base = load_github_domains()

    # Analyze each month
    for month in MONTHS:
        analyze_month(month, github_raw, github_base)


if __name__ == "__main__":
    main()
