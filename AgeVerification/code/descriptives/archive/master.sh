#!/bin/bash
# Master script for Comscore merge pipeline
# Run from project root: ./code/ProcessComscore/master.sh
# Processes all months from 202201 to 202412 (36 months)

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=merge_pipeline
#SBATCH --output=logs/merge_%j.out
#SBATCH --error=logs/merge_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=128G

set -euo pipefail

# # Load required module. (recent version of python good at handling parquet.)
# module unload python
# module load python/anaconda-2024.10                                                                                    
# conda activate age-verification         

echo "============================================"
echo "MERGE PIPELINE."
echo "Started at: $(date)"
echo "============================================"

# Step 1: Create machine characteristics
echo ""
echo "Session January 2022: descriptives"
python3 code/descriptives/session_summary_statistics.py

# Individual-level usage distribution histograms (winsorization diagnostic)
# python3 code/descriptives/indiv_descriptives_histogram_matt.py

# Control state time series — 4 iterative aggregation refinements from individual panel
# python3 code/descriptives/indiv_timeseries_control_matt.py

# Control state time series — decomposition by site (winsorized overall, panel size, % active, intensity)
# python3 code/descriptives/indiv_timeseries_decomposition_matt.py

# xVideos/XNXX mid-2024 break: pre/post state scatter and demographic breakdown
# python3 code/descriptives/xvideos_xnxx_diagnostic_matt.py
