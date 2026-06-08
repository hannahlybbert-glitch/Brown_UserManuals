#!/bin/bash
# Shell wrapper to run validate_googletrends_mobile.py on the cluster
# Run from project root: sbatch code/descriptives/googletrends/validate_googletrends_mobile.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=validate_gtrends_mobile
#SBATCH --output=logs/validate_googletrends_mobile_%j.out
#SBATCH --error=logs/validate_googletrends_mobile_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=64G

set -euo pipefail

echo "============================================"
echo "VALIDATE GOOGLE TRENDS - MOBILE"
echo "Started at: $(date)"
echo "============================================"

python3 code/descriptives/googletrends/validate_googletrends_mobile.py

echo ""
echo "============================================"
echo "COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
