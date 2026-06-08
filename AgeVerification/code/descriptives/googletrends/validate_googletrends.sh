#!/bin/bash
# Shell wrapper to run validate_googletrends.py on the cluster
# Run from project root: sbatch code/descriptives/googletrends/validate_googletrends.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=validate_gtrends
#SBATCH --output=logs/validate_googletrends_%j.out
#SBATCH --error=logs/validate_googletrends_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=64G

set -euo pipefail

echo "============================================"
echo "VALIDATE GOOGLE TRENDS"
echo "Started at: $(date)"
echo "============================================"

python3 code/descriptives/googletrends/validate_googletrends.py

echo ""
echo "============================================"
echo "COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
