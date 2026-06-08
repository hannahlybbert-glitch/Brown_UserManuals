#!/bin/bash
# Submit all three combined regression jobs in parallel.
# Assumes data/intermediate_combined/ intermediates already exist
# (i.e., prepare_combined.R has been run).
#
# Usage (from project root):
#   bash code/analysis/submit_combined_parallel.sh

set -euo pipefail

echo "Submitting combined regression jobs in parallel..."

JOB1=$(sbatch --parsable code/analysis/make_regressions_combined.sh)
JOB2=$(sbatch --parsable code/analysis/make_regressions_desktop_combined.sh)
JOB3=$(sbatch --parsable code/analysis/make_regressions_mobile_combined.sh)

echo "  Submitted combined         → job $JOB1"
echo "  Submitted desktop_combined → job $JOB2"
echo "  Submitted mobile_combined  → job $JOB3"
echo ""
echo "Monitor with:"
echo "  squeue -u \$USER"
echo "  tail -f logs/regressions_combined_${JOB1}.out"
echo "  tail -f logs/regressions_desktop_combined_${JOB2}.out"
echo "  tail -f logs/regressions_mobile_combined_${JOB3}.out"
