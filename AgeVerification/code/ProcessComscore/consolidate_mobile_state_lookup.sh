#!/bin/bash
# Author: Emily Davis, assisted by Claude
# Created: 2026-03-11
# Purpose: Combine per-month mobile_to_state_lookup.parquet files into a single
#          data/Aggregation/mobile_to_state_lookup.parquet for the analysis pipeline.
# Run from project root: sbatch code/ProcessComscore/consolidate_mobile_state_lookup.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=consolidate_mobile_lookup
#SBATCH --output=logs/consolidate_mobile_lookup_%j.out
#SBATCH --error=logs/consolidate_mobile_lookup_%j.err
#SBATCH --time=00:30:00
#SBATCH --mem=8G

set -euo pipefail

# # Load required module.
# module unload python
# module load python/anaconda-2024.10
# source /software/python-anaconda-2024.10-el8-x86_64/etc/profile.d/conda.sh
# conda activate age-verification

echo "============================================"
echo "CONSOLIDATE MOBILE STATE LOOKUP"
echo "Started at: $(date)"
echo "============================================"

python3 code/ProcessComscore/consolidate_mobile_state_lookup.py

echo ""
echo "============================================"
echo "COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
echo ""
echo "Output: data/Aggregation/mobile_to_state_lookup.parquet"
