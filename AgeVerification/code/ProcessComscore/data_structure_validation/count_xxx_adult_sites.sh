#!/bin/bash
# Shell wrapper to run count_xxx_adult_sites.py on the cluster.
# Run from project root: sbatch code/ProcessComscore/data_structure_validation/count_xxx_adult_sites.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=count_xxx_adult
#SBATCH --output=logs/count_xxx_adult_%j.out
#SBATCH --error=logs/count_xxx_adult_%j.err
#SBATCH --time=01:00:00
#SBATCH --mem=16G

set -euo pipefail

echo "============================================"
echo "COUNT XXX ADULT SITES"
echo "Started at: $(date)"
echo "============================================"

python3 code/ProcessComscore/data_structure_validation/count_xxx_adult_sites.py

echo ""
echo "============================================"
echo "COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
