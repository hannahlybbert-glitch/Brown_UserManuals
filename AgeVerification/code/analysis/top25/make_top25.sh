#!/bin/bash
# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Run top-25 adult site regression pipeline.
#          Runs pooled TWFE regressions for 26 sites then builds the output table.
# Run from project root: sbatch code/analysis/top25/make_top25.sh
#
# Prereqs:
#   data/Aggregation/top25/desktop_mobile_machine_panel/  [from master_append.sh]
#   data/intermediate_combined/stacked_panel.rds           [from prepare_combined.R]

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=top25_analysis
#SBATCH --output=logs/top25_analysis_%j.out
#SBATCH --error=logs/top25_analysis_%j.err
#SBATCH --time=01:00:00
#SBATCH --mem=16G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

export ANALYSIS_MODE=combined

echo "============================================"
echo "TOP-25 ANALYSIS PIPELINE"
echo "Started at: $(date)"
echo "============================================"

# echo ""
# echo "=== prepare_top25.R ==="
# Rscript code/analysis/top25/prepare_top25.R

# echo ""
# echo "=== run_regressions_top25.R ==="
# Rscript code/analysis/top25/run_regressions_top25.R

# echo ""
# echo "=== create_regression_table_top25.R ==="
# Rscript code/analysis/top25/create_regression_table_top25.R

# echo ""
# echo "=== create_regression_plot_top25.R ==="
# Rscript code/analysis/top25/create_regression_plot_top25.R

echo ""
echo "=== create_decomp_plots2.R ==="
Rscript code/analysis/create_decomp_plots2.R

# echo ""
# echo "=== create_decomp_table.R ==="
# Rscript code/analysis/top25/create_decomp_table.R

echo ""
echo "============================================"
echo "TOP-25 ANALYSIS PIPELINE COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
echo ""
echo "Outputs:"
echo "  output/analysis/combined/top_25/intermediate/regression_results_top25.rds"
echo "  output/analysis/combined/top_25/top25_regression_table.md"
echo "  output/analysis/combined/top_25/top25_regression_table.tex"
echo "  output/analysis/combined/top_25/top25_regression_plot.png"
echo "  output/analysis/combined/top_25/waterfalls/decomp2_waterfall_win_min.png"
echo "  output/analysis/combined/top_25/waterfalls/waterfall_main.png"
echo "  output/analysis/combined/top_25/waterfalls/waterfall_main_V2.png"
echo "  output/analysis/combined/top_25/waterfalls/decomp2_waterfall_win_min_base.png"
echo "  output/analysis/combined/top_25/decomp_regression_table.md"
echo "  output/analysis/combined/top_25/decomp_regression_table.tex"
