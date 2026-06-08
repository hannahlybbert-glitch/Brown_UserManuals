#!/bin/bash
# Author: Hannah Lybbert
# Created: 02/11/2026 (updated: 02/24/2026)
# Purpose: Master script for machine-level aggregation pipeline (scripts 1–5 + diagnostics)
# Run from project root: ./code/Aggregation/master.sh
# Processes all months from 202201 to 202412 (36 months)

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=aggregation_pipeline
#SBATCH --output=logs/aggregation_%j.out
#SBATCH --error=logs/aggregation_%j.err
#SBATCH --time=04:00:00
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

# # ==============================================================================
# # STEP 2: CREATE INTERMEDIATE SESSION FILES  (once per month)
# # ==============================================================================
# echo ""
# echo "STEP 2: Creating intermediate session files..."
# for year in 2022 2023 2024; do
#     for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
#         MONTH_ID="${year}${month}"
#         echo "  Processing ${MONTH_ID}..."
#         python3 code/Aggregation/2_create_intermediate_sessions.py ${MONTH_ID}
#     done
# done

# # ==============================================================================
# # STEP 3: BUILD MACHINE ROSTER  (unchanged — skip)
# # ==============================================================================
# echo ""
# echo "STEP 3: Building machine roster..."
# python3 code/Aggregation/3_build_machine_roster.py

# ==============================================================================
# STEP 4: AGGREGATE MACHINE × MONTH  (once per month)
# ==============================================================================
echo ""
echo "STEP 4: Aggregating sessions by machine and month..."
for year in 2022 2023; do
    for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
        MONTH_ID="${year}${month}"
        echo "  Processing ${MONTH_ID}..."
        python3 code/Aggregation/4_aggregate_machine_month.py ${MONTH_ID}
    done
done

# ==============================================================================
# STEP 5: ASSEMBLE FINAL MACHINE PANEL  (run once, after all of step 4)
# ==============================================================================
echo ""
echo "STEP 5: Assembling final machine panel..."
python3 code/Aggregation/5_assemble_machine_panel.py

# # ==============================================================================
# # STEP 6: DIAGNOSTICS  (run separately after verifying outputs)
# # ==============================================================================
# echo ""
# echo "STEP 6: Running pipeline diagnostics..."
# python3 code/Aggregation/diagnose_test_pipeline.py

# # ==============================================================================
# # STEP 7: BUILD MACHINE-WEEK ACTIVITY FILE
# # ==============================================================================
# echo ""
# echo "STEP 7: Building machine-week activity panel..."
# python3 code/Aggregation/7_machine_week_activity.py

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
