#!/bin/bash
# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-28
# Purpose: Run control-sites regression pipeline.
# Run from project root: sbatch code/analysis/control_sites/make_control_sites.sh
#
# Prereqs:
#   data/Aggregation/desktop_mobile_machine_panel/  [from main aggregation pipeline]
#   data/intermediate_combined/stacked_panel.rds    [from prepare_combined.R]

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=control_sites_analysis
#SBATCH --output=logs/control_sites_analysis_%j.out
#SBATCH --error=logs/control_sites_analysis_%j.err
#SBATCH --time=01:00:00
#SBATCH --mem=16G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

export ANALYSIS_MODE=combined

echo "============================================"
echo "CONTROL SITES ANALYSIS PIPELINE"
echo "Started at: $(date)"
echo "============================================"

# echo ""
# echo "=== prepare_control_sites.R ==="
# Rscript code/analysis/control_sites/prepare_control_sites.R

# echo ""
# echo "=== run_regressions_controls.R ==="
# Rscript code/analysis/control_sites/run_regressions_controls.R

echo ""
echo "=== create_regression_plot_controls.R ==="
Rscript code/analysis/control_sites/create_regression_plot_controls.R

echo ""
echo "============================================"
echo "CONTROL SITES ANALYSIS PIPELINE COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
echo ""
echo "Outputs:"
echo "  data/intermediate_combined/controls_win_wide.rds"
echo "  output/analysis/combined/control_sites/intermediate/regression_results_controls.rds"
echo "  output/analysis/combined/control_sites/controls_regression_plot.png"
