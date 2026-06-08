#!/bin/bash
# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Master script for top-25 mobile aggregation pipeline (scripts 2b, 4b, 5b mobile)
# Run from project root: sbatch code/Aggregation/top25/master_mobile.sh
#
# Can run concurrently with master.sh (desktop) — they write to separate directories.
# After both complete, run master_append.sh.

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=top25_aggregation_mobile
#SBATCH --output=logs/top25_aggregation_mobile_%j.out
#SBATCH --error=logs/top25_aggregation_mobile_%j.err
#SBATCH --time=08:00:00
#SBATCH --mem=64G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

echo "============================================"
echo "TOP-25 AGGREGATION PIPELINE (MOBILE)"
echo "Started at: $(date)"
echo "============================================"

# ==============================================================================
# STEP 2b: CREATE MOBILE INTERMEDIATE SESSION FILES  (once per month)
# ==============================================================================
echo ""
echo "STEP 2b: Creating top-25 intermediate session files (mobile)..."
for year in 2022 2023 2024; do
    for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
        MONTH_ID="${year}${month}"
        echo "  Processing ${MONTH_ID}..."
        python3 code/Aggregation/top25/2b_create_mobile_intermediate_sessions.py ${MONTH_ID}
    done
done

# ==============================================================================
# STEP 4b: AGGREGATE MOBILE MACHINE x MONTH  (once per month)
# ==============================================================================
echo ""
echo "STEP 4b: Aggregating top-25 sessions by machine and month (mobile)..."
for year in 2022 2023 2024; do
    for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
        MONTH_ID="${year}${month}"
        echo "  Processing ${MONTH_ID}..."
        python3 code/Aggregation/top25/4b_aggregate_mobile_machine_month.py ${MONTH_ID}
    done
done

# ==============================================================================
# STEP 5b: ASSEMBLE FINAL MOBILE MACHINE PANEL  (run once, after all of step 4b)
# ==============================================================================
echo ""
echo "STEP 5b: Assembling final top-25 machine panel (mobile)..."
python3 code/Aggregation/top25/5b_assemble_mobile_machine_panel.py

# ==============================================================================
# PIPELINE COMPLETE
# ==============================================================================
echo ""
echo "============================================"
echo "TOP-25 MOBILE AGGREGATION COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
echo ""
echo "Outputs:"
echo "  data/Aggregation/top25/mobile_intermediate/          (36 monthly intermediate files)"
echo "  data/Aggregation/top25/mobile_machine_panel/monthly/ (936 monthly category files)"
echo "  data/Aggregation/top25/mobile_machine_panel/machine_aggregated_{category}.parquet (26 files)"
echo ""
echo "Next step (after desktop also completes):"
echo "  sbatch code/Aggregation/top25/master_append.sh"
