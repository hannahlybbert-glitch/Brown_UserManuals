#!/bin/bash
# Author: Emily Davis
# Created: 03/10/2026
# Purpose: Master script for mobile machine-level aggregation pipeline (scripts 2–5)
# Run from project root: ./code/Aggregation/master_mobile.sh
# Processes all months from 202201 to 202412 (36 months)
# Note: Script 1 (top5_xxx_websites.csv) is shared with the desktop pipeline — run once from master.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=mobile_aggregation_pipeline
#SBATCH --output=logs/mobile_aggregation_%j.out
#SBATCH --error=logs/mobile_aggregation_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=64G

set -euo pipefail

# # Load required module.
# module unload python
# module load python/anaconda-2024.10
# source /software/python-anaconda-2024.10-el8-x86_64/etc/profile.d/conda.sh
# conda activate age-verification

echo "============================================"
echo "MOBILE AGGREGATION PIPELINE"
echo "Started at: $(date)"
echo "============================================"

# ==============================================================================
# STEP 2: CREATE MOBILE INTERMEDIATE SESSION FILES  (once per month)
# ==============================================================================
echo ""
echo "STEP 2: Creating mobile intermediate session files..."
for year in 2022 2023 2024; do
   for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
       MONTH_ID="${year}${month}"
       echo "  Processing ${MONTH_ID}..."
       python3 code/Aggregation/2_create_mobile_intermediate_sessions.py ${MONTH_ID}
   done
done

# # ==============================================================================
# # STEP 3: BUILD MOBILE MACHINE ROSTER  (run once after step 2)
# # ==============================================================================
# echo ""
# echo "STEP 3: Building mobile machine roster..."
# python3 code/Aggregation/3_build_mobile_machine_roster.py

# ==============================================================================
# STEP 4: AGGREGATE MOBILE MACHINE × MONTH  (once per month)
# ==============================================================================
echo ""
echo "STEP 4: Aggregating mobile sessions by machine and month..."
for year in 2022 2023 2024; do
   for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
       MONTH_ID="${year}${month}"
       echo "  Processing ${MONTH_ID}..."
       python3 code/Aggregation/4_aggregate_mobile_machine_month.py ${MONTH_ID}
   done
done

# ==============================================================================
# STEP 5: ASSEMBLE FINAL MOBILE MACHINE PANEL  (run once, after all of step 4)
# ==============================================================================
echo ""
echo "STEP 5: Assembling final mobile machine panel..."
python3 code/Aggregation/5_assemble_mobile_machine_panel.py

# # ==============================================================================
# # STEP 6: DIAGNOSTICS  (run separately after verifying outputs)
# # ==============================================================================
# echo ""
# echo "STEP 6: Running pipeline diagnostics..."
# python3 code/Aggregation/diagnose_mobile_pipeline.py

# ==============================================================================
# PIPELINE COMPLETE
# ==============================================================================
echo ""
echo "============================================"
echo "MOBILE AGGREGATION PIPELINE COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
echo ""
echo "Outputs:"
echo "  data/Aggregation/mobile_machine_panel/machine_week_presence.parquet"
echo "  data/Aggregation/mobile_machine_panel/boundary_weeks.csv"
echo "  data/Aggregation/mobile_machine_panel/monthly/{category}/  (792 monthly files, 22 categories × 36 months)"
echo "  data/Aggregation/mobile_machine_panel/machine_aggregated_{category}.parquet  (22 files)"
