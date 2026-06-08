#!/bin/bash
# Master script for mobile analysis pipeline.
# Uses the combined dataset (desktop_mobile_machine_panel), filtered to mobile==1.
# Requires data/intermediate_combined/ to exist — run make_combined.sh first.
# Run from project root: sbatch code/analysis/make_mobile.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=analysis_pipeline_mobile
#SBATCH --output=logs/analysis_mobile_%j.out
#SBATCH --error=logs/analysis_mobile_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=128G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

# mobile_combined: reads data/intermediate_combined/, filters to mobile==1,
# writes to output/analysis/mobile/ (same destination as the old mobile pipeline).
export ANALYSIS_MODE=mobile_combined

echo "============================================"
echo "ANALYSIS PIPELINE (MOBILE)"
echo "Started at: $(date)"
echo "============================================"

# echo ""
# echo "=== prepare_combined_old.R ==="
# Rscript code/analysis/archive/prepare_combined_old.R

# echo ""
# echo "=== run_regressions.R (mobile_combined) ==="
# RUN_MODE=mobile_combined Rscript code/analysis/run_regressions.R

# echo ""
# echo "=== compare_time_series.py ==="
# python code/analysis/compare_time_series.py

echo ""
echo "=== create_event_study_plots_old.R ==="
Rscript code/analysis/archive/create_event_study_plots_old.R

echo ""
echo "=== create_decomposition_plots_old.R ==="
Rscript code/analysis/archive/create_decomposition_plots_old.R

echo ""
echo "=== create_heterogeneity_plots_old.R ==="
Rscript code/analysis/archive/create_heterogeneity_plots_old.R

echo ""
echo "=== create_summary_table_old.R ==="
Rscript code/analysis/archive/create_summary_table_old.R

echo ""
echo "=== create_normalized_het_regressions_old.R (~5-10 min) ==="
Rscript code/analysis/archive/create_normalized_het_regressions_old.R

echo ""
echo "=== create_normalized_het_table_old.R ==="
Rscript code/analysis/archive/create_normalized_het_table_old.R

echo ""
echo "=== create_normalized_het_figures_old.R ==="
Rscript code/analysis/archive/create_normalized_het_figures_old.R

echo ""
echo "============================================"
echo "ANALYSIS PIPELINE (MOBILE) COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
