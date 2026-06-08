#!/bin/bash
# Run VPN pooled regressions (XXX visitors + never XXX) and generate VPN summary
# tables for desktop and mobile.
# Run from project root: sbatch code/analysis/make_vpn_tables.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=vpn_tables
#SBATCH --output=logs/vpn_tables_%j.out
#SBATCH --error=logs/vpn_tables_%j.err
#SBATCH --time=02:00:00
#SBATCH --mem=128G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

echo "============================================"
echo "VPN TABLES — DESKTOP"
echo "Started at: $(date)"
echo "============================================"

echo ""
echo "=== run_regressions.R vpn_xxx vpn_noxxx (desktop) ==="
Rscript code/analysis/run_regressions.R vpn_xxx vpn_noxxx

echo ""
echo "=== create_regression_table.R (desktop) ==="
Rscript code/analysis/create_regression_table.R

echo ""
echo "============================================"
echo "VPN TABLES — MOBILE"
echo "Started at: $(date)"
echo "============================================"

export ANALYSIS_MODE=mobile

echo ""
echo "=== run_regressions.R vpn_xxx vpn_noxxx (mobile) ==="
Rscript code/analysis/run_regressions.R vpn_xxx vpn_noxxx

echo ""
echo "=== create_regression_table.R (mobile) ==="
Rscript code/analysis/create_regression_table.R

echo ""
echo "============================================"
echo "DONE"
echo "Finished at: $(date)"
echo "============================================"
