#!/bin/bash
# Shell wrapper to run top_sites_by_duration.py on the cluster.
# Run from project root: sbatch code/ProcessComscore/data_structure_validation/top_sites_by_duration.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=top_sites_duration
#SBATCH --output=logs/top_sites_duration_%j.out
#SBATCH --error=logs/top_sites_duration_%j.err
#SBATCH --time=02:00:00
#SBATCH --mem=48G

set -euo pipefail

echo "============================================"
echo "TOP SITES BY DURATION"
echo "Started at: $(date)"
echo "============================================"

python3 code/ProcessComscore/data_structure_validation/top_sites_by_duration.py

echo ""
echo "============================================"
echo "COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
