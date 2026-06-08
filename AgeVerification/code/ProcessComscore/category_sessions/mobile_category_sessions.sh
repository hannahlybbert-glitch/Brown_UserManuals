#!/bin/bash
# Shell wrapper to run create_mobile_category_sessions_files.py on the cluster
# Run from project root: sbatch code/ProcessComscore/category_sessions/mobile_category_sessions.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=mobile_category_sessions
#SBATCH --output=logs/mobile_category_sessions_%j.out
#SBATCH --error=logs/mobile_category_sessions_%j.err
#SBATCH --time=02:00:00
#SBATCH --mem=32G

set -euo pipefail

echo "============================================"
echo "CREATE CATEGORY SESSIONS FILES (MOBILE)"
echo "Started at: $(date)"
echo "============================================"

python3 code/ProcessComscore/category_sessions/create_mobile_category_sessions_files.py

echo ""
echo "============================================"
echo "COMPLETE"
echo "Finished at: $(date)"
echo "============================================"
