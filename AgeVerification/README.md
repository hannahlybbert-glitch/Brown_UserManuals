# Comscore Data Processing Pipeline

This repository contains a general-purpose data processing pipeline for working with Comscore web browsing data.

## Overview

The pipeline provides tools for:
- Cleaning and processing Comscore session data
- Creating crosswalk files to link pattern_ids across time periods
- Merging with lookup tables (time, demographics, website categories)
- Geographic assignment (machine → state via DMA mapping)
- Building analysis-ready datasets

## Project Structure

```
├── code/
│   ├── ProcessComscore/           # Main data processing pipeline
│   │   └── master.sh              # Merges Comscore sessions with all lookups
│   ├── ProcessAuxiliary/
│   │   ├── DMA_County/            # DMA-to-county geographic crosswalks
│   │   │   └── master.sh          # Creates DMA-to-state population shares
│   │   ├── DMA_market_state/      # DMA-to-ComScore market mapping
│   │   │   └── master.sh          # Maps ComScore markets to states
│   │   └── Aggregation/           # Monthly aggregation scripts
│   └── descriptives/              # Exploratory analysis scripts
│       └── master.sh              # Runs descriptive analyses
├── data/                          # Processed outputs (mirrors code/ structure)
├── output/                        # Analysis outputs and figures
├── paper/                         # Research paper files
└── raw/                           # Raw Comscore data (not in repo)
```

## Pipeline Execution Order

**Run all scripts from project root.** Order matters due to dependencies:

```bash
# Step 1: Geographic lookups (run once, or when raw DMA data changes)
./code/ProcessAuxiliary/DMA_County/master.sh          # Creates DMA → state shares
./code/ProcessAuxiliary/DMA_market_state/master.sh    # Creates ComScore market → state

# Step 2: Main data processing (processes all 36 months: 202201-202412)
./code/ProcessComscore/master.sh                      # Merges sessions with all lookups

# Step 3: Analysis (after data is processed)
./code/descriptives/master.sh                         # Summary statistics and figures
```

**Dependency chain:**
- `DMA_County/master.sh` → produces `DMA_state_shares.csv`
- `DMA_market_state/master.sh` → uses DMA shares, produces `comscore_market_state.csv`
- `ProcessComscore/master.sh` → uses market-state mapping for final merge

## What Each Pipeline Does

| Script | Purpose | Output |
|--------|---------|--------|
| `DMA_County/master.sh` | Cleans Nielsen/Census data, creates DMA-to-state population shares | `DMA_state_shares.csv` |
| `DMA_market_state/master.sh` | Maps DMA markets to ComScore markets, assigns states | `comscore_market_state.csv` |
| `ProcessComscore/master.sh` | Merges raw sessions with time, web, demographic, and geographic lookups | `merged_sessions_YYYYMM.parquet` |
| `descriptives/master.sh` | Runs descriptive analysis on processed data | Summary tables, figures |

## Quick Start

See `code/SCRIPT_BEST_PRACTICES.md` for a style and directory structure guide.

See `CODE_DEBT.md` for known issues and planned cleanup work.

See `raw/documentation/` for documentation of the raw data files.

## Dependencies

- Python 3.11+
- pandas
- numpy
- pyarrow (for parquet files)
- fuzzywuzzy (for DMA name matching)

## Data Sources

This pipeline is designed to work with Comscore web browsing data, including:
- Desktop day session files
- Mobile session files
- Time lookup tables
- Traffic category maps
- Demographics data (desktop and mobile)
- Nielsen DMA data
- Census county population data

## Syncing Code to RCC Cluster

To sync the `code/` folder to the UChicago RCC Midway cluster:

```bash
rsync -avz --delete --no-g --chmod=D775,F775 code/ <cnetid>@midway3.rcc.uchicago.edu:/project/mattbrownecon/AgeVerification/code/
```

**Flags explained:**
- `--delete` removes files in the target that don't exist locally (only affects `code/`, not your data)
- `--no-g` lets the server's setgid bit assign group ownership (ensures files get `pi-mattbrownecon` group)
- `--chmod=D775,F775` sets permissions so all team members can read/write/execute

## Running Scripts on RCC Cluster

### One-time setup: Create the conda environment

```bash
module load python/anaconda-2022.05
conda env create -f environment.yml
```

### One-time setup: Install R packages

```bash
module load R/X.X.X   # Hannah or Emily: pick the most recent R version available.
                      # Check with: module avail R
Rscript install_packages.R
```

### Before submitting jobs: Activate the environment

```bash
module load python/anaconda-2022.05
conda activate age-verification
sbatch code/ProcessComscore/master.sh
```

Check job status with `squeue -u <cnetid>`.

Please write master scripts so that they will be called from the root directory of the project (`AgeVerification/`). Use relative path names. Comment out local directory names before pushing to git, but ESPECIALLY before syncing to Midway.

### SBATCH directives

Include these `#SBATCH` directives at the top of your `.sh` file:

```bash
#!/bin/bash

#SBATCH --partition=caslake          # Partition to use
#SBATCH --account=pi-<pi_cnetid>     # PI account for billing

#SBATCH --job-name=my_job            # Job name (appears in squeue)
#SBATCH --output=logs/job_%j.out     # Standard output (%j = job ID)
#SBATCH --error=logs/job_%j.err      # Standard error
#SBATCH --time=04:00:00              # Max runtime (HH:MM:SS)
#SBATCH --mem=64G                    # Memory allocation

# Your script commands here...
```

### Making changes/updating the environment.yml

If you need to add dependencies (packages) to the environment.yml file, follow these steps
1. Open environment.yml file and make needed changes
2. Sync local computer to midway cluster using the following command
   ```
   rsync -avz --delete --no-g --chmod=D775,F775 environment.yml hlybbert@midway3.rcc.uchicago.edu:/project/mattbrownecon/AgeVerification/environment.yml
   ```
3. Run the following commands from the cluster terminal to update the environment
   ```
   conda activate age-verification
   conda env update --file /project/mattbrownecon/AgeVerification/environment.yml --prune
   ```
