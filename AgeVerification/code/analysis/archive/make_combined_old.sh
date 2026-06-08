#!/bin/bash
# Master script for combined (desktop + mobile) analysis pipeline.
# Run from project root: sbatch code/analysis/make_combined.sh
#
# Data prep (prepare_combined.R) creates data/intermediate_combined/, which is
# shared by make_desktop.sh and make_mobile.sh. Run this first if starting fresh.

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=analysis_pipeline_combined
#SBATCH --output=logs/analysis_combined_%j.out
#SBATCH --error=logs/analysis_combined_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=128G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

export ANALYSIS_MODE=combined

echo "============================================"
echo "ANALYSIS PIPELINE (COMBINED)"
echo "Started at: $(date)"
echo "============================================"

# echo ""
# echo "=== prepare_combined_old.R ==="
# Rscript code/analysis/archive/prepare_combined_old.R

# echo ""
# echo "=== run_regressions.R (combined) ==="
# RUN_MODE=combined Rscript code/analysis/run_regressions.R

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
echo "ANALYSIS PIPELINE (COMBINED) COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
