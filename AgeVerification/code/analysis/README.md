# Analysis Pipeline

All scripts run from the **project root** (`AgeVerification/`).

---

## Overview

The pipeline has two stages: **data prep** then **regressions**, followed by independent **output scripts** that all read from `regression_results.rds`.

```
prepare_desktop.R ──────────────────────────────────────────────────────────────┐
compare_time_series.py  (standalone; needs raw parquets)                        │
                                                                                 │
                            ┌────────────────────────────────────────────────────┤
                            ▼                                                    │
                     run_regressions.R                                           │
                            │                                                    │
       ┌────────────────────┼─────────────────────────┐                         │
       ▼                    ▼                          ▼                         │
create_event_study_plots.R  create_heterogeneity_plots.R  diagnostics.R         │
create_decomposition_plots.R                                                     │
create_regression_table.R                                                           │
                                                                                 ▼
                                              create_normalized_het_regressions.R
                                                     │
                                         ┌───────────┴────────────┐
                                         ▼                         ▼
                              create_normalized_het_table.R  create_normalized_het_figures.R
```

### Running

```bash
# Full pipeline on cluster
sbatch code/analysis/make.sh

# Run all regressions locally
Rscript code/analysis/run_regressions.R

# Run only specific sections (args can be combined)
Rscript code/analysis/run_regressions.R event pooled
Rscript code/analysis/run_regressions.R het
Rscript code/analysis/run_regressions.R diagnostics
```

Sections accumulate into `regression_results.rds` — running a subset does not overwrite results from other sections.

### `run_regressions.R` sections

| CLI arg | What it runs |
|---------|-------------|
| `event` | Stacked TWFE event-study (week-by-week `i(rel_week, treated)`) for all sites × DVs |
| `pooled` | Three-period pooled ATT (pre / short-term / long-term) for all sites × DVs |
| `het` | Interacted pooled spec with gender × age × children covariates; requires `het_covs.rds` |
| `diagnostics` | Balanced-panel regressions for `BAL_SITES` (all_xxx, Pornhub, xVideos) |

Default (no args): all four sections.

### Sites (`SITES_FULL` in `_source/config.R`)

All regressions loop over: **All XXX (pooled)**, Pornhub, xVideos, xHamster, XNXX, Chaturbate, Other XXX, All other sites.
Balanced-panel diagnostics use the first three only (`BAL_SITES`).

### Dependent variables (`dvs` in `_source/config.R`)

| Key | Description |
|-----|-------------|
| `over60` | Binary: any visit > 60s on site that week |
| `win_min` | Minutes/machine/week, winsorized at site-specific p95 (computed over 2022) |

Both DVs are run for every site × section combination.

### Shared source files (`_source/`)

**`config.R`** — sourced by every script. Defines all paths (`data_dir`, `int_dir`, `out_int_dir`), site lists (`SITES_FULL`, `BAL_SITES`, `XXX_SLUGS`), DV metadata, period windows (`PRE_WINDOW`, `SHORT_WINDOW`, `LONG_WINDOW`), and plot colors. To change which sites or DVs are run, or to adjust the event window or pooled periods, edit this file.

**`helpers.R`** — sourced after `config.R`. Provides shared functions used across scripts:

| Function | Used by |
|----------|---------|
| `load_site_duration()` | Reads duration parquet for one site (or sum across `XXX_SLUGS`) | `run_regressions.R`, `diagnostics.R` |
| `compute_p95_2022()` | p95 winsorization threshold from 2022 baseline weeks only | `run_regressions.R`, `diagnostics.R` |
| `build_xxx_win_wide()` | Pre-builds per-site win_min wide table for additive all-XXX construction | `prepare.R` |
| `attach_dvs()` | Attaches `over60` and `win_min` to a panel given a site key | `run_regressions.R` |
| `extract_coefs()` | Tidies event-study coefficients from a fixest fit into a data frame | `run_regressions.R` |
| `run_pooled()` | Three-period pooled TWFE spec; returns named list of β/SE/p/N | `run_regressions.R` |
| `run_interacted()` | Fully interacted pooled spec (het section); interactions with age, kids, income, past XXX use | `run_regressions.R` |
| `build_het_covariates()` | Builds machine×cohort-level het covariates from pre-period data | `run_regressions.R` |
| `save_event_study_plot()` | Renders and saves a standard single-series event-study PNG | `create_event_study_plots.R` |
| `fmt_coef()` | Formats β (SE) string for tables | `diagnostics.R` |

---

## Script Reference

### `prepare.R`
Builds the stacked panel and site-level wide files used by all downstream regressions.

- **Requires:** `data/Aggregation/machine_panel/`, `data/ProcessComscore/full_demographics/full_machine_person_demos.parquet`, `raw/statelaws/statelaws_dates.csv`
- **Outputs:** `data/intermediate/stacked_panel.rds`, `data/intermediate/xxx_win_wide.rds`
- **Runtime:** ~80s
- **Usage:** `Rscript code/analysis/prepare.R`

---

### `compare_time_series.py`
Per-state time series plots of adult site engagement around law effective dates.

- **Requires:** `data/intermediate/stacked_panel.rds`
- **Outputs:** `output/analysis/compare_time_series/{share_60s,winsorized_p95}/` — one PNG per state
- **Runtime:** ~2 min
- **Usage:** `python3 code/analysis/compare_time_series.py`

---

### `prepare_het.R`
Builds the heterogeneity covariate file (`het_covs.rds`). Run once after `prepare.R`; not needed for the main regressions.

- **Requires:** `data/intermediate/stacked_panel.rds`, demographics parquet
- **Outputs:** `data/intermediate/het_covs.rds`
- **Runtime:** ~160s
- **Usage:** `Rscript code/analysis/prepare_het.R`

---

### `run_regressions.R`
Master regression script. Runs stacked TWFE event-study and pooled two-period regressions for all sites × DVs. Accepts CLI section arguments to run subsets.

- **Requires:** `data/intermediate/stacked_panel.rds`, `data/intermediate/het_covs.rds` (for `het`)
- **Outputs:** `output/analysis/intermediate/regression_results.rds`
- **Runtime:** ~60 min (full); ~15 min per section
- **Usage:**
  ```bash
  Rscript code/analysis/run_regressions.R              # all sections
  Rscript code/analysis/run_regressions.R event pooled # specific sections
  Rscript code/analysis/run_regressions.R het          # heterogeneity only
  ```
- **CLI args:** `event` `pooled` `het` `diagnostics`

---

### `create_event_study_plots.R`
Reads regression results and produces event-study plots for all sites × DVs.

- **Requires:** `output/analysis/intermediate/regression_results.rds`
- **Outputs:** `output/analysis/event_study/` — `{slug}_{dv}.png` and `{slug}_{dv}_coefs.csv` (16 PNGs + 16 CSVs)
- **Runtime:** ~1 min
- **Usage:** `Rscript code/analysis/create_event_study_plots.R`

---

### `create_heterogeneity_plots.R`
Plots short-term and long-term ATTs by subgroup (gender, age, children) for each site.

- **Requires:** `output/analysis/intermediate/regression_results.rds`
- **Outputs:** `output/analysis/heterogeneity_plots/` — `heterogeneity_interacted_{slug}_{ST|LT}.png` (16 PNGs: 8 sites × ST/LT)
- **Runtime:** ~1 min
- **Usage:** `Rscript code/analysis/create_heterogeneity_plots.R`

---

### `create_decomposition_plots.R`
Waterfall and dot-plot decompositions of the All XXX pooled ATT into site-level contributions. Short-term and long-term periods only.

- **Requires:** `output/analysis/intermediate/regression_results.rds`
- **Outputs:** `output/analysis/full_sample/` — `decomp_waterfall_{dv}.png`, `decomp_dotplot_{dv}.png` (4 PNGs total)
- **Runtime:** ~1 min
- **Usage:** `Rscript code/analysis/create_decomposition_plots.R`

---

### `create_regression_table.R`
Produces the main results table (pooled ATTs for all sites × DVs).

- **Requires:** `output/analysis/intermediate/regression_results.rds`
- **Outputs:** `output/analysis/full_sample/full_sample_table_{dv}.md`, `output/analysis/full_sample/full_sample_table_{dv}.tex` (4 files: `over60` and `win_min`)
- **Runtime:** ~1 min
- **Usage:** `Rscript code/analysis/create_regression_table.R`

---

### `diagnostics.R`
Balanced panel checks, SE driver diagnostics (Moulton factor, ICC, clustered vs. robust), and portfolio plots.

- **Requires:** `output/analysis/intermediate/regression_results.rds`, `data/intermediate/stacked_panel.rds`
- **Outputs:** all under `output/analysis/diagnostics/`
  - `se_diagnostics/` — `memo_se_drivers.md`, `forest_state_atts.png`, `forest_state_atts_xnxx_{dv}.png`, `pornhub_state_level.csv`, `se_comparison.csv`, `xnxx_state_level_{dv}.csv`
  - `event_study_balanced/` — `{slug}_{dv}_balanced_comparison.png` (6 PNGs), `balanced_comparison_{dv}.md` (2 MDs)
  - `portfolio_diagnostics/` — `scatter_ph_vs_sub{_children}.png`, `cdf_sub_share{_children}.png` (4 PNGs)
- **Runtime:** ~10 min
- **Usage:** `Rscript code/analysis/diagnostics.R`

---

### `create_normalized_het_regressions.R`
Runs site × subgroup TWFE regressions for PH, xVideos, and XNXX across 17
subgroups (full sample; PH and all-XXX pre-period usage bins; age, income, kids).
Normalizes betas by the estimated counterfactual PH denominator
$E[Y^{\text{PH}}(0)_g] = \bar{y}^{\text{PH}}_{g,\text{treated,post}} - \hat\beta^{\text{PH}}_g$.

- **Requires:** `data/intermediate/stacked_panel.rds`, `data/intermediate/xxx_win_wide.rds`, `data/intermediate/het_covs.rds`
- **Outputs:** `data/intermediate/normalized_het_results.rds`
- **Runtime:** ~5–10 min (cluster)
- **Usage:** `Rscript code/analysis/create_normalized_het_regressions.R`

---

### `create_normalized_het_table.R`
Reads normalized regression results and writes landscape LaTeX tables (ST and LT)
and a CSV summary.

- **Requires:** `data/intermediate/normalized_het_results.rds`
- **Outputs:** `output/analysis/normalized_het/{ST,LT}_table.tex`, `output/analysis/normalized_het/normalized_het_results.csv`
- **Runtime:** ~1 min
- **Usage:** `Rscript code/analysis/create_normalized_het_table.R`

---

### `create_normalized_het_figures.R`
Bar-chart decomposition and scatter plots of the normalized het results.

- **Requires:** `data/intermediate/normalized_het_results.rds`
- **Outputs:** `output/analysis/normalized_het/fig{1,2,3}_*.png`
- **Runtime:** ~1 min
- **Usage:** `Rscript code/analysis/create_normalized_het_figures.R`

---

### `create_normalized_het_bootstrap.R` *(optional; not in main pipeline)*
Pairs cluster bootstrap (B=100) for SEs on the normalized het table. Parallelized
via `mclapply`; set `DRY_RUN <- TRUE` to validate without bootstrapping.

- **Requires:** `data/intermediate/stacked_panel.rds`, `data/intermediate/xxx_win_wide.rds`, `data/intermediate/het_covs.rds`, `data/intermediate/normalized_het_results.rds`
- **Outputs:** `data/intermediate/normalized_het_bootstrap.rds`
- **Runtime:** ~10 min (cluster, B=100)
- **Usage:** `Rscript code/analysis/create_normalized_het_bootstrap.R`

---

## Key Inputs

| File | Description |
|------|-------------|
| `data/Aggregation/machine_panel/machine_week_presence.parquet` | Panel denominator (machine × week) |
| `data/Aggregation/machine_panel/machine_aggregated_SITE.parquet` | Per-site duration (one file per site) |
| `data/Aggregation/final_aggregated.csv` | `week_of_sample → week_start_date` calendar map |
| `data/ProcessComscore/full_demographics/full_machine_person_demos.parquet` | Machine-level demographics |
| `raw/statelaws/statelaws_dates.csv` | Law effective dates by state |

---

## Key Constants (`_source/config.R`)

```r
EXCLUDE_STATES  <- c("DC", "XX", "ZZ")
EXCLUDE_TREATED <- "TX"          # TX law enjoined; excluded from pooled specs

CUTOFF_DATE     <- as.Date("2024-11-24")
T_MIN <- -16L; T_MAX <- 8L      # 25-week event window

XXX_SLUGS <- c("PORNHUB.COM", "CHATURBATE.COM", "XHAMSTER.COM",
               "XNXX.COM",    "XVIDEOS.COM",    "other_XXX_sites")

# Pooled spec windows
PRE_WINDOW   <- -16:-5   # placebo pre-period
SHORT_WINDOW <-   0:3    # short-term ATT
LONG_WINDOW  <-   4:8    # long-term ATT
```

---

## Output Structure

```
output/analysis/
├── intermediate/
│   └── regression_results.rds          # all regression output (source for all plot scripts)
├── event_study/
│   ├── {slug}_{dv}.png                 # 16 event-study plots
│   └── {slug}_{dv}_coefs.csv           # 16 coefficient CSVs
├── diagnostics/
│   ├── event_study_balanced/
│   │   ├── {slug}_{dv}_balanced_comparison.png
│   │   └── balanced_comparison_{dv}.md
│   ├── portfolio_diagnostics/
│   │   ├── scatter_ph_vs_sub{_children}.png
│   │   └── cdf_sub_share{_children}.png
│   └── se_diagnostics/
│       ├── memo_se_drivers.md
│       ├── forest_state_atts.png
│       ├── forest_state_atts_xnxx_{dv}.png
│       ├── pornhub_state_level.csv
│       ├── se_comparison.csv
│       └── xnxx_state_level_{dv}.csv
├── full_sample/
│   ├── decomp_waterfall_{dv}.png       # waterfall decomposition (ST/LT)
│   ├── decomp_dotplot_{dv}.png         # dot-plot decomposition (ST/LT)
│   ├── full_sample_table_{dv}.md       # main results table (markdown)
│   └── full_sample_table_{dv}.tex      # main results table (LaTeX)
├── heterogeneity_plots/
│   └── heterogeneity_interacted_{slug}_{ST|LT}.png   # 16 heterogeneity plots
├── normalized_het/
│   ├── ST_table.tex                    # normalized het table, short run
│   ├── LT_table.tex                    # normalized het table, long run
│   ├── normalized_het_results.csv      # normalized betas + E[Y(0)] for all subgroups
│   ├── fig1_{ph,xxx}_tercile_{st,lt}.png  # decomposition by usage bin
│   ├── fig2_ph_vs_xv_{st,lt}.png       # PH decline vs. xVideos substitution
│   └── fig3_by_char_{st,lt}.png        # decomposition by demographic group
└── compare_time_series/
    ├── share_60s/                      # per-state >60s time series
    └── winsorized_p95/                 # per-state win. minutes time series
```

---

## Mobile Extension

> **Status:** In progress — Issue #28 (emjdavis25). The mobile Aggregation pipeline must produce the files listed below before the analysis pipeline can run on mobile data.

### What `#28` must deliver

The mobile aggregation pipeline needs to produce the same file structure as the desktop pipeline, with two additions:

| File | Description |
|------|-------------|
| `data/Aggregation/machine_panel_mobile/machine_week_presence.parquet` | Mobile panel denominator |
| `data/Aggregation/machine_panel_mobile/machine_aggregated_SITE.parquet` | Per-site mobile duration |
| `data/ProcessComscore/mobile_characteristics.csv` | Machine-level mobile demographics |
| `data/Aggregation/mobile_to_state_lookup.parquet` | Machine → state mapping (state not in demo file) |

### Analysis pipeline changes

Two new files will handle the desktop/mobile differences; all other scripts run **unchanged** (they only read from `int_dir`).

**`_source/config_mobile.R`** — overrides the three paths that differ:
```r
data_dir  <- file.path(project_root, "data", "Aggregation", "machine_panel_mobile")
demo_file <- file.path(project_root, "data", "ProcessComscore", "mobile_characteristics.csv")
int_dir   <- file.path(project_root, "data", "intermediate_mobile")
```
All other constants (`XXX_SLUGS`, `SITES_FULL`, windows, etc.) are inherited from `config.R`.

**`prepare_mobile.R`** — mirrors `prepare.R` with demographic column remapping:

| Field | Desktop (`full_machine_person_demos.parquet`) | Mobile (`mobile_characteristics.csv`) |
|-------|-----------------------------------------------|---------------------------------------|
| Age | `hoh_age` (string: "18-24", "25-34", …) | `age` (numeric) → bin to same strings |
| Income | `hh_income` (categorical string) | `hh_income` (numeric code) → recode |
| Kids | `children_present` ("Children:Yes") | `children_present` (0/1) → recode |
| State | in demo file | from `mobile_to_state_lookup.parquet` (join needed) |

Mobile demographics are already machine-level (no person-to-machine aggregation step needed). After remapping, `prepare_mobile.R` calls the same `build_stacked_panel()` and `build_xxx_win_wide()` functions as `prepare.R`.
