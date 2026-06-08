#!/bin/bash
# Author: Hannah Lybbert
# Created: 2026-05-28
# Purpose: Run scripts 2 and 4 for 2024 only (desktop pipeline).
#          Runs in parallel with master.sh (which handles 2022–2023 script 2).
#          After both finish, re-run master.sh with script 2 commented out
#          to complete script 4 for all years and script 5.
# Run from project root: ./code/Aggregation/master2.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=agg_2024_desktop
#SBATCH --output=logs/agg_2024_%j.out
#SBATCH --error=logs/agg_2024_%j.err
#SBATCH --time=03:00:00
#SBATCH --mem=64G

set -euo pipefail

# # Load required module.
# module unload python
# module load python/anaconda-2024.10
# source /software/python-anaconda-2024.10-el8-x86_64/etc/profile.d/conda.sh
# conda activate age-verification

echo "============================================"
echo "AGGREGATION PIPELINE"
echo "Started at: $(date)"
echo "============================================"

# # ==============================================================================
# # STEP 1: IDENTIFY TOP 5 XXX ADULT WEBSITES  (run once)
# # ==============================================================================
# echo ""
# echo "STEP 1: Identifying top 5 XXX Adult websites from January 2022..."
# python3 code/Aggregation/1_identify_top_websites.py

# ==============================================================================
# STEP 2: CREATE INTERMEDIATE SESSION FILES  (once per month)
# ==============================================================================
echo ""
echo "STEP 2: Creating intermediate session files..."
for year in 2024; do
    for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
        MONTH_ID="${year}${month}"
        echo "  Processing ${MONTH_ID}..."
        python3 code/Aggregation/2_create_intermediate_sessions.py ${MONTH_ID}
    done
done

# ==============================================================================
# STEP 4: AGGREGATE MACHINE × MONTH  (once per month)
# ==============================================================================
echo ""
echo "STEP 4: Aggregating sessions by machine and month..."
for year in 2024; do
    for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
        MONTH_ID="${year}${month}"
        echo "  Processing ${MONTH_ID}..."
        python3 code/Aggregation/4_aggregate_machine_month.py ${MONTH_ID}
    done
done

# ==============================================================================
# PIPELINE COMPLETE
# ==============================================================================
echo ""
echo "============================================"
echo "AGGREGATION PIPELINE COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
echo ""
echo "Outputs:"
echo "  data/Aggregation/machine_activity/machine_week_activity.parquet"
