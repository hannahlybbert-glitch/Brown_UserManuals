#!/bin/bash
# Master script for desktop analysis pipeline.
# Uses the combined dataset (desktop_mobile_machine_panel), filtered to mobile==0.
# Requires data/intermediate_combined/ to exist — run make_combined.sh first.
# Run from project root: sbatch code/analysis/make_desktop.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=analysis_pipeline_desktop
#SBATCH --output=logs/analysis_%j.out
#SBATCH --error=logs/analysis_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=128G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

# desktop_combined: reads data/intermediate_combined/, filters to mobile==0,
# writes to output/analysis/ (same destination as the old desktop pipeline).
export ANALYSIS_MODE=desktop_combined

echo "============================================"
echo "ANALYSIS PIPELINE (DESKTOP)"
echo "Started at: $(date)"
echo "============================================"

# echo ""
# echo "=== prepare_combined_old.R ==="
# Rscript code/analysis/archive/prepare_combined_old.R

# echo ""
# echo "=== run_regressions.R (desktop_combined) ==="
# RUN_MODE=desktop_combined Rscript code/analysis/run_regressions.R

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
echo "ANALYSIS PIPELINE (DESKTOP) COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
