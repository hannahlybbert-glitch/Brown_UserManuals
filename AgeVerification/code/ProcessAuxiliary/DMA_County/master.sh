#!/bin/bash
# Master script for DMA County pipeline
# Run from project root: ./code/ProcessAuxiliary/DMA_County/master.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=DMA_County_pipeline
#SBATCH --output=logs/DMA_County_%j.out
#SBATCH --error=logs/DMA_County_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=64G

# DMA County Processing Pipeline
# Author: Hannah Lybbert
# Created: 01/29/2026
# Purpose: Process Nielsen DMA data and Census county data to create DMA state shares (issue #12)

set -e  # Exit on error

# Create logs directory if it doesn't exist
mkdir -p logs

# Print start time
echo "================================================================================"
echo "DMA County Processing Pipeline Started"
echo "================================================================================"
echo "Start time: $(date)"
echo ""

# ============================================================================
# MAIN PIPELINE - Creates output files
# ============================================================================

# Step 1: Clean Nielsen ZIP to DMA file
echo "Step 1: Cleaning Nielsen ZIP to DMA file..."
python3 code/ProcessAuxiliary/DMA_County/nielsen_cleaning.py
echo "✓ Nielsen cleaning complete"
echo ""

# Step 2: Clean county population file
echo "Step 2: Cleaning county population file..."
python3 code/ProcessAuxiliary/DMA_County/county_pop_cleaning.py
echo "✓ County population cleaning complete"
echo ""

# Step 3: Standardize county names and handle split counties
echo "Step 3: Standardizing county names and handling split counties..."
python3 code/ProcessAuxiliary/DMA_County/standardize_county_pop_to_zip_dma.py
echo "✓ County standardization complete"
echo ""

# Step 4: Create DMA-to-state shares
echo "Step 4: Creating DMA-to-state shares..."
python3 code/ProcessAuxiliary/DMA_County/create_DMA_state_shares.py
echo "✓ DMA-to-state shares complete"
echo ""

# Step 5: Visualize threshold tradeoff
echo "Step 5: Visualizing threshold tradeoff..."
python3 code/ProcessAuxiliary/DMA_County/visualize_threshold_tradeoff.py
echo "✓ Threshold visualization complete"
echo ""

# ============================================================================
# DIAGNOSTIC SCRIPTS - Console output only, no files created
# These scripts verify data quality and matching
# ============================================================================

echo "================================================================================"
echo "Running diagnostic scripts (console output only)..."
echo "================================================================================"
echo ""

# Diagnostic 1: Compare county names
echo "Diagnostic 1: Comparing county names..."
python3 code/ProcessAuxiliary/DMA_County/compare_county_names.py
echo "✓ County name comparison complete"
echo ""

# Diagnostic 2: Investigate unmatched counties
echo "Diagnostic 2: Investigating unmatched counties..."
python3 code/ProcessAuxiliary/DMA_County/investigate_unmatched_counties.py
echo "✓ Unmatched county investigation complete"
echo ""

# Diagnostic 3: Final match comparison
echo "Diagnostic 3: Final match comparison..."
python3 code/ProcessAuxiliary/DMA_County/final_match_comparison.py
echo "✓ Final match comparison complete"
echo ""

# ============================================================================
# Pipeline Complete
# ============================================================================

echo "================================================================================"
echo "DMA County Processing Pipeline Complete"
echo "================================================================================"
echo "End time: $(date)"
echo ""
echo "Output files created:"
echo "  - data/ProcessAuxiliary/DMA_County/ZIP_to_DMA_clean.csv"
echo "  - data/ProcessAuxiliary/DMA_County/co_est2022_pop_clean.csv"
echo "  - data/ProcessAuxiliary/DMA_County/co_est2022_pop_standardized.csv"
echo "  - data/ProcessAuxiliary/DMA_County/DMA_state_shares.csv"
echo "  - data/ProcessAuxiliary/DMA_County/DMA_summary.csv"
echo "  - output/figures/DMA_threshold_tradeoff.png"
echo ""
echo "All processing complete!"
