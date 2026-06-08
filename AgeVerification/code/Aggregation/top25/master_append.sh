#!/bin/bash
# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Append top-25 desktop and mobile panels into combined files.
# Run from project root: sbatch code/Aggregation/top25/master_append.sh
#
# Prereq: both master.sh (desktop) and master_mobile.sh (mobile) must have
# completed successfully before running this script.

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=top25_aggregation_append
#SBATCH --output=logs/top25_aggregation_append_%j.out
#SBATCH --error=logs/top25_aggregation_append_%j.err
#SBATCH --time=02:00:00
#SBATCH --mem=32G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

echo "============================================"
echo "TOP-25 AGGREGATION PIPELINE (APPEND)"
echo "Started at: $(date)"
echo "============================================"

# ==============================================================================
# STEP 6b: APPEND DESKTOP AND MOBILE PANELS
# ==============================================================================
echo ""
echo "STEP 6b: Appending desktop and mobile top-25 panels..."
python3 code/Aggregation/top25/6b_append_desktop_mobile_panels.py

# ==============================================================================
# PIPELINE COMPLETE
# ==============================================================================
echo ""
echo "============================================"
echo "TOP-25 APPEND COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
echo ""
echo "Final output:"
echo "  data/Aggregation/top25/desktop_mobile_machine_panel/machine_aggregated_{category}.parquet"
echo "  (26 files: 25 named sites + other_adult)"
