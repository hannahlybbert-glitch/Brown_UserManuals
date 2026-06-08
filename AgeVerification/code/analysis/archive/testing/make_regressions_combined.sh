#!/bin/bash
# Regressions for combined (desktop + mobile) mode only.
# Requires data/intermediate_combined/ intermediates to already exist.
# Run standalone:  sbatch code/analysis/make_regressions_combined.sh
# Or use submit_combined_parallel.sh to submit all three modes at once.

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=regressions_combined
#SBATCH --output=logs/regressions_combined_%j.out
#SBATCH --error=logs/regressions_combined_%j.err
#SBATCH --time=03:00:00
#SBATCH --mem=128G

source /software/python-anaconda-2022.05-el8-x86_64/etc/profile.d/conda.sh
conda activate age-verification

set -euo pipefail

echo "============================================"
echo "REGRESSIONS — combined"
echo "Started at: $(date)"
echo "============================================"

echo ""
echo "=== run_regressions.R (combined) ==="
RUN_MODE=combined Rscript code/analysis/run_regressions.R

echo ""
echo "============================================"
echo "REGRESSIONS — combined COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
