<!-- # Author: Hannah Lybbert
# Created: 06/08/2026
# Updated: 06/08/2026
# Purpose: Provide guide for using the Comscore data.  -->


# Comscore Data Guide

## Overview

Comscore is a panel-based web browsing dataset. Panelists install Comscore software on their devices, and the software logs every website visit. Our data spans **January 2022 – December 2024 (36 months)** and covers desktop and mobile browsing in the United States. 


This guide covers:
1. What the raw Comscore data looks like
2. Key concepts you need to understand about the data structure
3. How we processed and enriched the raw data
4. The key output files you are likely to work with


---

## 1. Raw Data Files

All raw data lives in `raw/`. It is large and lives only on the cluster (not synced to GitHub). Reference the comscore code book in [Codebooks.pdf](https://github.com/hannahlybbert-glitch/Brown_UserManuals/blob/main/AgeVerification/code/Codebooks.pdf) to understand the data files better as I wont go into detail on _all_ the raw files here.

**Note:** We have both desktop and mobile data. The raw session data and demographics data for mobile and desktop are in separate files while the Lookup files are the same across both. I will mostly talk about desktop data here, but the same structure generally applies for the mobile data.

### 1a. Session Files
**Location:** `raw/desktop_day_session/`
**File pattern:** `comscore_desktop_day_session_{month_id}m.txt[.gz]`

These are the core of the Comscore data. Each row is a **browsing session** — one continuous visit to a website.

| Column | Description |
|---|---|
| `machine_id` | Unique identifier for the device |
| `person_id` | Unique identifier for the household member using the device |
| `session_id` | Unique identifier for the session |
| `time_id` | Date identifier (integer; requires a lookup to convert to a real date) |
| `first_ss2k` | Session start time (seconds since Jan 1, 2000) |
| `pages` | Number of pages viewed during the session |
| `duration` | Session duration in seconds |
| `pattern_id` | Website identifier — see Section 2 for why this is tricky |
| `ref_pattern_id` | Referring website's pattern_id |

Raw files have **no header row** — column names must be applied when reading. Files are tab-delimited (ie row values are separated by a tab). On the cluster they are compressed (`.txt.gz`); when you download them locally they will be uncompressed (`.txt`). Make sure your scripts handle both automatically (add this to your `SCRIPT_BEST_PRACTICES.md` file, Claude is good at doing this).

### 1b. Machine Demographics Files
**Location:** `raw/desktop_demographics/`
**File patterns:**
- `US_comscore_machine_demos_{YYYYMM}.txt[.gz]` — one row per machine enrolled in Comscore that month
- `US_comscore_person_demos_{YYYYMM}.txt[.gz]` — one row per household member (person) on each machine that month

**Machine demo columns:** `machine_id`, `country`, `region`, `time_zone_bias`, `computer_location`, `hoh_age`, `hh_income`, `children_present`, `hh_size`, `month_id`

**Person demo columns:** `person_id`, `machine_id`, `gender`, `age`, `children_present`, `hh_income`, `hh_size`, `ethnicity_id`, `race_id`, `computer_location`, `country`, `region`, `time_zone_bias`, `month_id`

Like the session files, demo files have **no header row** and are tab-delimited.

### 1c. Lookup Tables
**Location:** `raw/Lookups/`

| File pattern | Purpose |
|---|---|
| `time_lookup/comscore_time_lookup_{YYYYMM}.txt[.gz]` | Maps `time_id` integers to calendar dates |
| `traffic_category_map/comscore_category_map_{YYYYMM}.txt[.gz]` | Maps `pattern_id` to website name, category, and hierarchy |


**Category map columns**:

| Column | Description |
|---|---|
| `month_id` | Internal Comscore month identifier (see the time_lookup files for clarification) |
| `pattern_id` | Website identifier for this month |
| `web_id` | Node ID in the category hierarchy (multiple `pattern_id` can map to the same `web_id`)|
| `web_name` | Website/entity name |
| `level_name` | Name of this level in the hierarchy |
| `level_id` | Numeric level in the hierarchy |
| `parent_id` | Parent node's `web_id` (parent/root website has `parent_id == 1`) |
| `subcategory` | Subcategory label (e.g., `"News/Information"`) |
| `category` | Top-level category label (e.g., `"General News"`)|
| `Magazine` | Binary flag — 1 if classified as a magazine |
| `Streaming_Video` | Binary flag |
| `Blog` | Binary flag |
| `Streaming_Audio` | Binary flag |
| `Cable_Broadcast_TV` | Binary flag |
| `Radio` | Binary flag |
| `Newspaper` | Binary flag |

The **traffic category map** is the key to identifying websites. It originally didn't have a clean indicator across all months of the root website for each sub-website. So, we built a new variable `top_web_id` which is built by following the `parent_id` up the hierarchy until reaching the root (`parent_id == 1`), at which point the current `web_id` is the root and that becomes the stable `top_web_id`. See section 2a below.

---

## 2. Key Concepts

### 2a. Pattern ID vs. Top Web ID

**`pattern_id`** is the raw website identifier in the session files. The problem is that **pattern IDs can change from month to month** for the same website. So you cannot just merge on `pattern_id` across months or you will lose or misattribute visits.

**`top_web_id`** is an identifier we create by traversing the website category hierarchy in the traffic category map. Each website belongs to a hierarchy (e.g., a specific URL → domain → parent company). By walking up this tree to the root node, we get a stable "top-level" ID for each website that is consistent across months. 


**Crosswalk:** For each month, we build a `crosswalk.parquet` file that maps `pattern_id → top_web_id`. This is recreated monthly (since the raw pattern IDs change) but the resulting `top_web_id` values are consistent across all months.

**Script:** `code/ProcessComscore/create_crosswalk_file.py`
* You do not need to build your own crosswalk, use this one!

**Output:** `data/ProcessComscore/intermediate/{month_id}/crosswalk.parquet`
* Two columns `pattern_id` and `top_web_id`
* One crosswalk per month of that month's specific sites and the associated `top_web_id`


### 2b. Machine ID vs. Person ID

- A **machine** is a unique device (desktop, laptop).
- A **person** is a household member who uses the machine.
- Multiple people can share one machine in the desktop data (about 18% of the sample shares a machine).
- Mobile data is a 1:1 machine:person ratio.

We almost always work at the **machine level** for analysis. Person-level data is used to enrich machine-level demographics (e.g., to get a gender for the machine, we look at the gender of the person or persons who use it).

**Gender of Desktops** (`merge_full_demographics.py`):
For shared machines, gender is not obvious, so we define gender for desktops as follows:
- Machine has exactly 1 person with known gender → use that person's gender (`Male` / `Female`)
- Machine has multiple persons → `Shared`
- No valid gender found → `Unknown`

### 2c. Demographics

Not all machines in our sample have demographic information. Some individuals in the panel opted out of sharing their demographic information. Depending on the project, you might need to exclude the machines that do not have demographic information.

### 2d. NULL vs. Zero Total Duration

In the final machine-week panel files, `total_duration` can be one of three things:

| Value | Meaning |
|---|---|
| A positive number | Machine was in the Comscore panel that week and visited websites in this category |
| `0` | Machine **was** in the panel that week but had **zero** usage in this category |
| `NaN` (NULL) | Machine was **not** in the panel that week — no data exists for them |

We track panel membership separately using `machine_week_presence.parquet` (built by `3_build_machine_roster.py`) to make this distinction.

### 2e. Month ID vs. YYYYMM

You will see two ways months are referenced:
- **YYYYMM** (e.g., `202201`) — the standard human-readable year-month string. Used as command-line arguments.
- **`month_id`** — an internal Comscore integer identifier that appears inside the data files. This is read from the first row of the category map or demographics file. Used for file naming in intermediate outputs.

All our scripts accept YYYYMM as an argument (meaning "run this script just for the data in a given YYYYMM") and internally derive the `month_id` from the raw files.

### 2f. State Assignment

Comscore tracks machines by their DMA (Designated Market Area) code. A DMA can span multiple states. Our pipeline (in `create_machine_state_lookup.py`) maps each machine's DMA to a state using a county-level population crosswalk:
- If one state accounts for more than 50% of the DMA's population → assign that state to the machine
    - Note: it might make sense to use an 80% threshold instead of 50%, but that is an easy fix
- Otherwise → drop from state-level analysis

You can find this Comscore market to state mapping in `data/ProcessAuxiliary/DMA_market_state/comscore_market_state.csv`

Special codes to be aware of:
- **`XX`** — person missing demographic information
- **`ZZ`** — unkown region
- **`US`** — generic US, not state-assigned


---

## 3. Processing Pipeline

The raw Comscore data goes through one essential pre-processing phase and a second phase that builds a machine panel. You do not need to re-code the first phase, instead I recommend that you just grab the needed data files from data/ProcessComscore/ and rely on those (see section 4 below). The machine panel pipeline is currently specific to our previous analysis, but with Claude's help you could use the structure of the current code to produce a pipeline that could work for a new project! 

### Phase 1: ProcessComscore
**Code:** `code/ProcessComscore/`
**Master script:** `code/ProcessComscore/master.sh`

This phase takes the raw session files and enriches them with website names, categories, machine demographics, and state assignments. It processes all 36 months. Note that we do this for both desktop and mobile in separate pipelines, here I will explain the desktop pipeline but the mobile pipeline mimics it.

#### Step-by-step
Read through these steps if you are curious to know how we built the final enriched session files, or you can skip to the reference table to understand the variables in the enriched session files.

| Step | Script | What it does | Output file & columns |
|---|---|---|---|
| 1 | `create_machine_characteristics.py` | Reads all 36 months of machine and person demo files and collapses to one row per machine, keeping the **first observed** value for each demographic variable. Person-level variables (gender, age, etc.) are aggregated to the machine using the agreement rule: 1 person → use their value; multiple people who agree → use that value; multiple people who disagree → set to missing. Run **once**. | `data/ProcessComscore/machine_characteristics.csv` — `machine_id`, `country`, `metro_area`, `DMA_code`, `device_type`, `age_range`, `HHI`, `children`, `household_size`, `person_gender`, `person_age`, `person_children`, `person_HHI_USD`, `person_HH_Size`, `person_ethnicity`, `person_race` |
| 2 | `create_crosswalk_file.py YYYYMM` | Reads the monthly traffic category map and builds a `pattern_id → top_web_id` mapping by traversing the parent hierarchy to the root. Recreated each month because raw `pattern_id`s change. | `data/ProcessComscore/intermediate/{month_id}/crosswalk.parquet` — `pattern_id`, `top_web_id` |
| 3 | `create_web_characteristics.py YYYYMM` | Reads the traffic category map and keeps only root-level rows (`parent_id == 1`) to build a lookup of `top_web_id → top_web_name, category, subcategory`. Also adds `vpn_clean_site` (NordVPN, ExpressVPN, Surfshark) and `vpn_site` (all other whitelisted VPN providers) flags using explicit name whitelists. | `data/ProcessComscore/intermediate/{month_id}/web_characteristics.parquet` — `top_web_id`, `top_web_name`, `category`, `subcategory`, `vpn_clean_site`, `vpn_site`, `github_porn_domain` |
| 4 | `create_machine_state_lookup.py YYYYMM` | Reads the monthly machine demo file to get each machine's DMA code, then uses a county-level population crosswalk to assign a US state. If one state accounts for >90% of DMA population, that state is assigned; otherwise the machine is dropped from state-level analysis. | `data/ProcessComscore/intermediate/{month_id}/machine_to_state_lookup.parquet` — `machine_id`, `state`, `majority_share` |
| 5 | `merge_into_sessions.py YYYYMM` | The main merge step. Takes the raw session file for one month and merges on: crosswalk (to get `top_web_id`), web characteristics (to get website name, category, VPN flags), machine characteristics (to get DMA code), and state lookup (to get state). | `data/ProcessComscore/merged_session_files/merged_sessions_{YYYYMM}.parquet` — all raw session columns plus all columns from steps 1–4 (see full column list below) |
| 6 | `create_full_demographics.py` | Builds machine and person demographic reference files that span the **full 36-month sample**. Critically, it sources the universe of machines and persons from the **session files** (not the demo files alone) so that machines with an enrollment lag are still captured. For each machine/person, it left-joins the demo file to get demographic attributes. Run **once**. | `data/ProcessComscore/full_demographics/machine_demographics.parquet` — `machine_id`, `have_demos`, `country`, `region`, `time_zone_bias`, `computer_location`, `hoh_age`, `hh_income`, `children_present`, `hh_size`, `state`, `majority_share` <br><br> `data/ProcessComscore/full_demographics/person_demographics.parquet` — `person_id`, `machine_id`, `have_demos`, `gender`, `age`, `children_present`, `hh_income`, `hh_size`, `ethnicity_id`, `race_id`, `computer_location`, `country`, `region`, `time_zone_bias` |
| 7 | `merge_full_demographics.py` | Collapses the person-level file onto the machine-level file to produce a single row per machine. The only person variable requiring special handling is gender: 1 person → their gender; multiple persons → `Shared`; no valid gender → `Unknown`. This produces the master demographic file used in analysis. Run **once**. | `data/ProcessComscore/full_demographics/full_machine_person_demos.parquet` — `machine_id`, `have_demos`, `person_count`, `gender`, `country`, `region`, `time_zone_bias`, `computer_location`, `hoh_age`, `hh_income`, `children_present`, `hh_size`, `state`, `majority_share` |

Steps 2–5 run per month (pass YYYYMM as argument). Steps 6–7 run once across the full sample.

#### Enriched Session Files Reference Table

After Phase 1, each month's sessions are saved as `data/ProcessComscore/merged_session_files/merged_sessions_{YYYYMM}.parquet`. These are the enriched session files.

| Column | New | Source | Description |
|---|---|---|---|
| `machine_id` | | raw session | Unique device identifier |
| `person_id` | | raw session | Unique household member identifier |
| `session_id` | | raw session | Unique session identifier |
| `time_id` | | raw session | Date integer — join to time lookup to get calendar date |
| `first_ss2k` | | raw session | Session start time (seconds since Jan 1, 2000) |
| `pages` | | raw session | Number of pages viewed in the session |
| `duration` | | raw session | Session duration in seconds |
| `pattern_id` | | raw session | Raw monthly website identifier |
| `ref_pattern_id` | | raw session | Referring website's `pattern_id` |
| `top_web_id` | ✓ | crosswalk | Stable root-level website identifier (consistent across months) |
| `top_web_name` | ✓ | web_characteristics | Human-readable website name |
| `category` | ✓ | web_characteristics | Top-level category (e.g., `"Sports"`, `"Entertainment"`) |
| `subcategory` | ✓ | web_characteristics | Subcategory (e.g., `"XXX Adult"`) |
| `vpn_site` | ✓ | web_characteristics | True if site is a whitelisted VPN provider |
| `vpn_clean_site` | ✓ | web_characteristics | True if site is NordVPN, ExpressVPN, or Surfshark |
| `github_porn_domain` | ✓ | web_characteristics | True if site matched an external list of known porn domains |
| `country` | ✓ | machine_characteristics | Country code |
| `metro_area` | ✓ | machine_characteristics | Metro area name |
| `DMA_code` | ✓ | machine_characteristics | Designated Market Area code |
| `device_type` | ✓ | machine_characteristics | Device type |
| `age_range` | ✓ | machine_characteristics | Head-of-household age range |
| `HHI` | ✓ | machine_characteristics | Household income category |
| `children` | ✓ | machine_characteristics | Children present in household |
| `household_size` | ✓ | machine_characteristics | Household size |
| `person_gender` | ✓ | machine_characteristics | Gender aggregated from person demo file |
| `person_age` | ✓ | machine_characteristics | Age aggregated from person demo file |
| `person_children` | ✓ | machine_characteristics | Children present (person-level) |
| `person_HHI_USD` | ✓ | machine_characteristics | Household income (person-level) |
| `person_HH_Size` | ✓ | machine_characteristics | Household size (person-level) |
| `person_ethnicity` | ✓ | machine_characteristics | Ethnicity |
| `person_race` | ✓ | machine_characteristics | Race |
| `state` | ✓ | machine_to_state_lookup | 2-letter state code (`XX` = unknown, `ZZ` = outside US) |
| `majority_share` | ✓ | machine_to_state_lookup | Fraction of DMA population in the assigned state |
| `month_id` | ✓ | derived | Internal Comscore month identifier |

### Phase 2: Aggregation
**Code:** `code/Aggregation/`
**Master script:** `code/Aggregation/master.sh`

This phase aggregates the session-level data into a machine × week panel, one file per website category. There are 5 numbered scripts (1–5, with script 7 producing the final analysis panel). We do the aggregation separate for desktop and mobile but script 7 merges the desktop and mobile panels into one. 

| Script | What it does |
|---|---|
| `1_identify_top_websites.py` | Identify the top 5 XXX Adult sites by January 2022 usage |
| `2_create_intermediate_sessions.py YYYYMM` | Add `week_of_sample` and `coarse_category`; winsorize session level duration at 95th percentile |
| `3_build_machine_roster.py` | Build `machine_week_presence.parquet` (panel membership tracker) |
| `4_aggregate_machine_month.py YYYYMM` | Aggregate sessions to machine × week × category |
| `5_assemble_machine_panel.py` | Combine 36 monthly files per category into a final panel file for each category. Each output file has just three columns `machine_id` `week_of_sample` and `total_duration` |

#### week_of_sample

Week 1 = the week of January 1, 2022. Week numbers increase from there continuously through December 2024 (ending around week 156–157). This variable is created in script 2 and used throughout the panel.

#### Coarse categories

Script 2 assigns each session to a coarse category. This is like the website the session took place on (ex. Facebook or Reddit)

---

## 4. Key Output Files

These are the files you can probably use directly with maybe slight modifications for your specific project. 

### `full_machine_person_demos.parquet`
**Location:** `data/ProcessComscore/full_demographics/full_machine_person_demos.parquet`
**Built by:** `create_full_demographics.py` + `merge_full_demographics.py`

One row per unique machine ever observed in the sample. This is the master demographic reference file.

| Column | Type | Description |
|---|---|---|
| `machine_id` | str | Unique device identifier (key) |
| `have_demos` | int (0/1) | 1 if machine appeared in Comscore's demographics file; 0 if session-only |
| `person_count` | int | Number of unique persons ever using this machine |
| `gender` | str | `Male`, `Female`, `Shared`, or `Unknown` — see Section 2b |
| `country` | str | Country code |
| `region` | str | Comscore region |
| `time_zone_bias` | str | Timezone offset |
| `computer_location` | str | Home / Work / etc. |
| `hoh_age` | str | Head of household age bin (e.g., `"25-34"`) |
| `hh_income` | str | Household income category |
| `children_present` | str | `"Children:Yes"` or `"Children:No"` |
| `hh_size` | int | Household size |
| `state` | str | 2-letter state code (`XX` = missing demo info, `ZZ` = unknown) |
| `majority_share` | float | Fraction of DMA population in the assigned state (1.0 if unambiguous) |

**Note on `have_demos`:** For most analyses you will want to filter to `have_demos == 1`. Machines with `have_demos == 0` appear in sessions but have no registered demographic profile — we cannot assign them a state, income, or any other demographic.

### `merged_sessions_{YYYYMM}.parquet`
**Location:** `data/ProcessComscore/merged_session_files/`

One file per month, one row per session. These are the enriched session files (see Section 3 for all columns). Use these if you need session-level data.

### `machine_aggregated_{category}.parquet`
**Location:** `data/Aggregation/machine_panel/`

One file per coarse category (e.g., `machine_aggregated_PORNHUB.COM.parquet`). Each file contains the full machine × week panel for that category/website. If you want to get these panels but for another website, you need to edit script 2 and add add the site as a coarse category to be tracked across the panel.

| Column | Description |
|---|---|
| `machine_id` | Device identifier |
| `week_of_sample` | Week number (1 = week of Jan 1, 2022) |
| `total_duration` | Total seconds spent on this category that week (0 = in panel, no use; NaN = not in panel) |

### `machine_week_presence.parquet`
**Location:** `data/Aggregation/machine_panel/machine_week_presence.parquet`

One row per (machine_id, week) pair where the machine was observed in any session. Use this to distinguish NULL from zero as described in Section 2c.




## General Tips (in progress)
* If you are ever unsure how to handle some data, ask Claude to search the Age Verification scripts to see if we have handled it first
* If you can't remember the columns in a certain file just ask Claude and it will tell you!
