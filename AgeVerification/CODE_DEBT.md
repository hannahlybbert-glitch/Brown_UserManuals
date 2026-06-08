# Code Debt and Cleanup Plan

This document tracks known issues, inconsistencies, and planned improvements.

---

## High Priority: Hardcoded Paths

**Issue:** 11 files contain `os.chdir()` calls with user-specific paths, blocking collaboration and HPC execution.

**Files affected:**

| File | Path Type |
|------|-----------|
| `descriptives/investigate_googlesearch.py` | Mac (Emily) |
| `descriptives/investigate_googlesearch_seqsessions.py` | Mac (Emily) |
| `descriptives/explore_alternatesites.py` | Mac (Emily) |
| `descriptives/category3_traffic_analysis.py` | Mac (Emily) |
| `descriptives/desktop_market_descriptives.py` | Windows/OneDrive (Hannah) |
| `descriptives/desktop_mobile_demographics.py` | Windows/OneDrive (Hannah) |
| `data_structure_validation/desktop_demos.py` | Windows (Hannah) |
| `data_structure_validation/person_demos.py` | Windows (Hannah) |
| `Aggregation/aggregation_script_202201.py` | Windows/OneDrive (Hannah) |

**Action:** Comment out all `os.chdir()` calls. Scripts should use relative paths from project root.

---

## Medium Priority: Files to Delete

| File | Lines | Reason |
|------|-------|--------|
| `code/ProcessComscore/data_structure_validation/desktop_demos.py` | 32 | Quick test script with no docstring, hardcoded paths. `analyze_person_demos.py` provides full functionality. |
| `code/ProcessComscore/data_structure_validation/person_demos.py` | 33 | Quick test script with no docstring, hardcoded paths. `analyze_person_demos.py` provides full functionality. |

---

## Medium Priority: Incomplete master.sh

**File:** `code/descriptives/master.sh`

**Issue:** Contains full SBATCH header but only calls one script (`session_summary_statistics.py`). Appears to be a copy-paste from ProcessComscore that was never completed.

**Options:**
1. Complete it with all descriptive analysis scripts
2. Delete it if scripts are meant to run individually

**Recommendation:** Delete.

---

## Medium Priority: Naming Convention

### Standard Prefixes

All Python scripts should use one of these prefixes:

| Prefix | Purpose | When to Use |
|--------|---------|-------------|
| `create_` | Generates new data files (lookups, crosswalks) | Output is a .csv/.parquet consumed by other scripts |
| `merge_` | Combines multiple data sources | Joining tables, concatenating files |
| `clean_` | Data cleaning and standardization | Fixing formats, removing invalid rows |
| `standardize_` | Normalizes naming/formatting across sources | Reconciling county names, string matching |
| `analyze_` | Full analysis with outputs/visualizations | Produces figures, tables |
| `validate_` | Data quality checks | Verifying assumptions, checking completeness |
| `visualize_` | Creates plots/figures only | Pure visualization, no data transformation |
| `compare_` | Compares datasets or approaches | Side-by-side analysis, diff reports |
| `test_` | Unit tests or integration tests | Verification scripts for pipelines |

We can modify these prefixes as time goes on.

### Retired Prefixes

- `investigate_` → rename to `analyze_` (produces outputs) or delete if scratch work
- `explore_` → rename to `analyze_` or delete if temporary

### Scripts to Rename

| Current Name | Proposed Name | Location |
|--------------|---------------|----------|
| `investigate_googlesearch.py` | `analyze_googlesearch_referrers.py` | descriptives/ |
| `investigate_googlesearch_seqsessions.py` | `analyze_googlesearch_sequences.py` | descriptives/ |
| `investigate_sunbiz.py` | `analyze_sunbiz.py` | descriptives/ |
| `investigate_unmatched_counties.py` | `compare_unmatched_counties.py` | DMA_County/ |
| `explore_alternatesites.py` | `analyze_alternatesites.py` | descriptives/ |
| `browsing_patterns.py` | `analyze_browsing_patterns.py` | descriptives/ |
| `session_summary_statistics.py` | `analyze_session_statistics.py` | descriptives/ |
| `top_websites_comparison.py` | `compare_top_websites.py` | descriptives/ |
| `category3_traffic_analysis.py` | `analyze_category3_traffic.py` | descriptives/ |
| `desktop_market_descriptives.py` | `analyze_desktop_market.py` | descriptives/ |
| `desktop_mobile_demographics.py` | `analyze_desktop_mobile_demos.py` | descriptives/ |
| `aggregation_script_202201.py` | `create_aggregation_202201.py` | Aggregation/ |
| `county_pop_cleaning.py` | `clean_county_pop.py` | DMA_County/ |
| `nielsen_cleaning.py` | `clean_nielsen_zip_dma.py` | DMA_County/ |
| `final_match_comparison.py` | `compare_final_match.py` | DMA_County/ |
| `DMA_ComScore_Market.py` | `create_DMA_comscore_mapping.py` | DMA_market_state/ |

---

## Low Priority: Commented-Out Code

Many files contain:
- Commented `os.chdir()` statements for local testing
- Commented module loading for HPC

Per `SCRIPT_BEST_PRACTICES.md` section 6, these should be removed. Clean up systematically during next maintenance pass.

---

## Changelog

- 2026-02-05: Initial documentation created
