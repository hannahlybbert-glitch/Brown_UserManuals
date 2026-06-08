#!/bin/bash
# Run VPN event study restricted to machines that NEVER visited an XXX site — desktop + mobile.
# Run from project root: sbatch code/analysis/make_vpn_noxxx.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=vpn_noxxx_event_study
#SBATCH --output=logs/vpn_noxxx_%j.out
#SBATCH --error=logs/vpn_noxxx_%j.err
#SBATCH --time=02:00:00
#SBATCH --mem=128G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

echo "============================================"
echo "VPN NEVER-XXX EVENT STUDY — DESKTOP"
echo "Started at: $(date)"
echo "============================================"

echo ""
echo "=== run_regressions.R vpn_noxxx (desktop) ==="
Rscript code/analysis/run_regressions.R vpn_noxxx

echo ""
echo "=== create_event_study_plots.R (desktop) ==="
Rscript code/analysis/create_event_study_plots.R

echo ""
echo "============================================"
echo "VPN NEVER-XXX EVENT STUDY — MOBILE"
echo "Started at: $(date)"
echo "============================================"

export ANALYSIS_MODE=mobile

echo ""
echo "=== run_regressions.R vpn_noxxx (mobile) ==="
Rscript code/analysis/run_regressions.R vpn_noxxx

echo ""
echo "=== create_event_study_plots.R (mobile) ==="
Rscript code/analysis/create_event_study_plots.R

echo ""
echo "============================================"
echo "DONE"
echo "Finished at: $(date)"
echo "============================================"
