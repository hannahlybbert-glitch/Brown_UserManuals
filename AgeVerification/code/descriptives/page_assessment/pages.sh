#!/bin/bash
# Shell wrapper to run pages assessment scripts on the cluster
# Run from project root: sbatch code/descriptives/page_assessment/pages.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=pages_assessment
#SBATCH --output=logs/pages_assessment_%j.out
#SBATCH --error=logs/pages_assessment_%j.err
#SBATCH --time=02:00:00
#SBATCH --mem=16G

set -euo pipefail

echo "============================================"
echo "PAGES ASSESSMENT"
echo "Started at: $(date)"
echo "============================================"

python3 code/descriptives/page_assessment/num_pages_assessment.py

echo ""
echo "============================================"
echo "DURATION CDF"
echo "============================================"

python3 code/descriptives/page_assessment/duration_cdf.py

echo ""
echo "============================================"
echo "COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
