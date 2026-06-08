#!/bin/bash
# Pornhub event study split by pre-period CleanVPN status — desktop only.
# Run from project root: sbatch code/analysis/make_ph_vpnsplit.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=ph_vpnsplit
#SBATCH --output=logs/ph_vpnsplit_%j.out
#SBATCH --error=logs/ph_vpnsplit_%j.err
#SBATCH --time=01:00:00
#SBATCH --mem=128G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

echo "============================================"
echo "PORNHUB VPN-SPLIT EVENT STUDY — DESKTOP"
echo "Started at: $(date)"
echo "============================================"

echo ""
echo "=== run_regressions.R ph_vpnsplit ==="
Rscript code/analysis/run_regressions.R ph_vpnsplit

echo ""
echo "=== create_ph_vpnsplit_plots.R ==="
Rscript code/analysis/create_ph_vpnsplit_plots.R

echo ""
echo "============================================"
echo "DONE"
echo "Finished at: $(date)"
echo "============================================"
