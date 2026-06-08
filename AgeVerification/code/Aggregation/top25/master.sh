#!/bin/bash
# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Master script for top-25 desktop aggregation pipeline (scripts 2b, 4b, 5b)
# Run from project root: sbatch code/Aggregation/top25/master.sh
#
# Prereq: top25_adult_sites.csv must exist at
#   output/ProcessComscore/data_structure_validation/top25_adult_sites.csv
#   (produced by top_sites_by_duration.py)
#
# After this completes, run master_mobile.sh, then master_append.sh.

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=top25_aggregation_desktop
#SBATCH --output=logs/top25_aggregation_desktop_%j.out
#SBATCH --error=logs/top25_aggregation_desktop_%j.err
#SBATCH --time=08:00:00
#SBATCH --mem=64G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

export ANALYSIS_MODE=combined

echo "============================================"
echo "TOP-25 AGGREGATION PIPELINE (DESKTOP)"
echo "Started at: $(date)"
echo "============================================"

# ==============================================================================
# STEP 2b: CREATE INTERMEDIATE SESSION FILES  (once per month)
# ==============================================================================
echo ""
echo "STEP 2b: Creating top-25 intermediate session files (desktop)..."
for year in 2022 2023 2024; do
    for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
        MONTH_ID="${year}${month}"
        echo "  Processing ${MONTH_ID}..."
        python3 code/Aggregation/top25/2b_create_intermediate_sessions.py ${MONTH_ID}
    done
done

# ==============================================================================
# STEP 4b: AGGREGATE MACHINE x MONTH  (once per month)
# ==============================================================================
echo ""
echo "STEP 4b: Aggregating top-25 sessions by machine and month (desktop)..."
for year in 2022 2023 2024; do
    for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
        MONTH_ID="${year}${month}"
        echo "  Processing ${MONTH_ID}..."
        python3 code/Aggregation/top25/4b_aggregate_machine_month.py ${MONTH_ID}
    done
done

# ==============================================================================
# STEP 5b: ASSEMBLE FINAL MACHINE PANEL  (run once, after all of step 4b)
# ==============================================================================
echo ""
echo "STEP 5b: Assembling final top-25 machine panel (desktop)..."
python3 code/Aggregation/top25/5b_assemble_machine_panel.py

# ==============================================================================
# PIPELINE COMPLETE
# ==============================================================================
echo ""
echo "============================================"
echo "TOP-25 DESKTOP AGGREGATION COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
echo ""
echo "Outputs:"
echo "  data/Aggregation/top25/intermediate/          (36 monthly intermediate files)"
echo "  data/Aggregation/top25/machine_panel/monthly/ (936 monthly category files)"
echo "  data/Aggregation/top25/machine_panel/machine_aggregated_{category}.parquet (26 files)"
echo ""
echo "Next steps:"
echo "  sbatch code/Aggregation/top25/master_mobile.sh"
echo "  sbatch code/Aggregation/top25/master_append.sh  (after mobile completes)"
