#!/bin/bash
# Run VPN event study restricted to pre-period XXX visitors only — desktop + mobile.
# Run from project root: sbatch code/analysis/make_vpn_xxx.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=vpn_xxx_event_study
#SBATCH --output=logs/vpn_xxx_%j.out
#SBATCH --error=logs/vpn_xxx_%j.err
#SBATCH --time=02:00:00
#SBATCH --mem=128G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

echo "============================================"
echo "VPN XXX-VISITOR EVENT STUDY — DESKTOP"
echo "Started at: $(date)"
echo "============================================"

echo ""
echo "=== run_regressions.R vpn_xxx (desktop) ==="
Rscript code/analysis/run_regressions.R vpn_xxx

echo ""
echo "=== create_event_study_plots.R (desktop) ==="
Rscript code/analysis/create_event_study_plots.R

echo ""
echo "============================================"
echo "VPN XXX-VISITOR EVENT STUDY — MOBILE"
echo "Started at: $(date)"
echo "============================================"

export ANALYSIS_MODE=mobile

echo ""
echo "=== run_regressions.R vpn_xxx (mobile) ==="
Rscript code/analysis/run_regressions.R vpn_xxx

echo ""
echo "=== create_event_study_plots.R (mobile) ==="
Rscript code/analysis/create_event_study_plots.R

echo ""
echo "============================================"
echo "DONE"
echo "Finished at: $(date)"
echo "============================================"
