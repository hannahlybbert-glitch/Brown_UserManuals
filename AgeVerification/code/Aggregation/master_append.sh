#!/bin/bash
# Author: Hannah Lybbert
# Created: 03/30/2026
# Purpose: Append desktop and mobile machine panels (script 6)
# Run from project root: ./code/Aggregation/master_append.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=append_panels
#SBATCH --output=logs/append_panels_%j.out
#SBATCH --error=logs/append_panels_%j.err
#SBATCH --time=01:00:00
#SBATCH --mem=32G

set -euo pipefail

# # Load required module.
# module unload python
# module load python/anaconda-2024.10
# source /software/python-anaconda-2024.10-el8-x86_64/etc/profile.d/conda.sh
# conda activate age-verification

echo "============================================"
echo "APPEND DESKTOP AND MOBILE PANELS"
echo "Started at: $(date)"
echo "============================================"

# ==============================================================================
# STEP 6: APPEND DESKTOP AND MOBILE MACHINE PANELS
# ==============================================================================
echo ""
echo "STEP 6: Appending desktop and mobile machine panels..."
python3 code/Aggregation/6_append_desktop_mobile_panels.py

# ==============================================================================
# COMPLETE
# ==============================================================================
echo ""
echo "============================================"
echo "APPEND COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
echo ""
echo "Output:"
echo "  data/Aggregation/desktop_mobile_machine_panel/machine_aggregated_{category}.parquet"
