#!/bin/bash
# Master script for DMA Market State pipeline
# Run from project root: ./code/ProcessAuxiliary/DMA_market_state/master.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=DMA_market_state_pipeline
#SBATCH --output=logs/DMA_market_state_%j.out
#SBATCH --error=logs/DMA_market_state_%j.err
#SBATCH --time=02:00:00
#SBATCH --mem=32G

# DMA Market State Processing Pipeline
# Author: Hannah Lybbert
# Created: 02/05/2026
# Purpose: Map DMA markets to ComScore markets and create state lookup

set -e  # Exit on error

# Create logs directory if it doesn't exist
mkdir -p logs

# Print start time
echo "================================================================================"
echo "DMA Market State Processing Pipeline Started"
echo "================================================================================"
echo "Start time: $(date)"
echo ""

# ============================================================================
# MAIN PIPELINE - Creates output files
# ============================================================================

# Step 1: Map DMA markets to ComScore markets
echo "Step 1: Mapping DMA markets to ComScore markets..."
python3 code/ProcessAuxiliary/DMA_market_state/DMA_ComScore_Market.py
echo "✓ DMA-ComScore mapping complete"
echo ""

# Step 2: Create ComScore market to state lookup
echo "Step 2: Creating ComScore market-to-state lookup..."
python3 code/ProcessAuxiliary/DMA_market_state/create_comscore_market_state.py
echo "✓ ComScore market-to-state lookup complete"
echo ""

# ============================================================================
# DIAGNOSTIC SCRIPTS - Console output only, no files created
# These scripts verify data quality and matching
# ============================================================================

echo "================================================================================"
echo "Running diagnostic scripts (console output only)..."
echo "================================================================================"
echo ""

# Diagnostic: Test merge of demographics to state
echo "Diagnostic: Testing merge of demographics to state..."
python3 code/ProcessAuxiliary/DMA_market_state/test_merge_demos_to_state.py
echo "✓ Demographics merge test complete"
echo ""

# ============================================================================
# Pipeline Complete
# ============================================================================

echo "================================================================================"
echo "DMA Market State Processing Pipeline Complete"
echo "================================================================================"
echo "End time: $(date)"
echo ""
echo "Output files created:"
echo "  - data/ProcessAuxiliary/DMA_market_state/DMA_comscore_check_mapping.csv"
echo "  - data/ProcessAuxiliary/DMA_market_state/DMA_comscore_mapping.csv"
echo "  - data/ProcessAuxiliary/DMA_market_state/comscore_market_state.csv"
echo ""
echo "All processing complete!"
