# Author: Hannah Lybbert
# Created: 01/28/2026
# Purpose: Visualize the tradeoff between threshold and DMA inclusion/exclusion (Git Issue #12)

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Set working directory - comment out for portability
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# Read DMA summary data
dma_summary = pd.read_csv(os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "DMA_summary.csv"))

print(f"Total DMAs: {len(dma_summary)}")
print(f"Single-state DMAs: {len(dma_summary[dma_summary['num_states'] == 1])}")
print(f"Multi-state DMAs: {len(dma_summary[dma_summary['num_states'] > 1])}")

# Define threshold range
thresholds = np.arange(0, 0.21, 0.02)

# Calculate number of DMAs excluded and included at each threshold
excluded_counts = []
included_counts = []

for threshold in thresholds:
    # Exclude DMAs where minority_share > threshold
    excluded = len(dma_summary[dma_summary['minority_share'] > threshold])
    included = len(dma_summary[dma_summary['minority_share'] <= threshold])

    excluded_counts.append(excluded)
    included_counts.append(included)

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Number of DMAs EXCLUDED
ax1.plot(thresholds * 100, excluded_counts, marker='o', linewidth=2, markersize=6, color='#d62728')
ax1.fill_between(thresholds * 100, 0, excluded_counts, alpha=0.3, color='#d62728')
ax1.set_xlabel('Minority Share Threshold (%)', fontsize=12)
ax1.set_ylabel('Number of DMAs Excluded', fontsize=12)
ax1.set_title('DMAs Excluded by Minority Share Threshold', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.set_xlim(-0.5, 20.5)
ax1.set_ylim(0, max(excluded_counts) * 1.1)

# Add annotations for key thresholds
for i, thresh in enumerate([0, 0.05, 0.10, 0.15, 0.20]):
    idx = int(thresh / 0.02)
    ax1.annotate(f'{excluded_counts[idx]} DMAs',
                xy=(thresh * 100, excluded_counts[idx]),
                xytext=(5, 5), textcoords='offset points',
                fontsize=9, alpha=0.8)

# Plot 2: Number of DMAs INCLUDED
ax2.plot(thresholds * 100, included_counts, marker='o', linewidth=2, markersize=6, color='#2ca02c')
ax2.fill_between(thresholds * 100, 0, included_counts, alpha=0.3, color='#2ca02c')
ax2.set_xlabel('Minority Share Threshold (%)', fontsize=12)
ax2.set_ylabel('Number of DMAs Included', fontsize=12)
ax2.set_title('DMAs Included by Minority Share Threshold', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.set_xlim(-0.5, 20.5)
ax2.set_ylim(0, len(dma_summary) * 1.05)

# Add annotations for key thresholds
for i, thresh in enumerate([0, 0.05, 0.10, 0.15, 0.20]):
    idx = int(thresh / 0.02)
    ax2.annotate(f'{included_counts[idx]} DMAs',
                xy=(thresh * 100, included_counts[idx]),
                xytext=(5, -15), textcoords='offset points',
                fontsize=9, alpha=0.8)

plt.tight_layout()

# Save figure
output_file = os.path.join(project_root, "output", "figures", "DMA_threshold_tradeoff.png")
os.makedirs(os.path.dirname(output_file), exist_ok=True)
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\nFigure saved to: {output_file}")

# plt.show()

# Print detailed table
print("\n" + "=" * 80)
print("THRESHOLD ANALYSIS TABLE")
print("=" * 80)
print(f"{'Threshold':<12} {'DMAs Excluded':<18} {'DMAs Included':<18} {'% Included':<12}")
print("-" * 80)
for i, threshold in enumerate(thresholds):
    pct_included = (included_counts[i] / len(dma_summary)) * 100
    print(f"{threshold*100:>6.0f}%      {excluded_counts[i]:>8}          {included_counts[i]:>8}          {pct_included:>6.1f}%")

print("\n" + "=" * 80)
print("KEY INSIGHTS")
print("=" * 80)

# Find thresholds where we keep 90%, 95%, 99% of DMAs
for pct_target in [90, 95, 99]:
    for i, threshold in enumerate(thresholds):
        pct_included = (included_counts[i] / len(dma_summary)) * 100
        if pct_included >= pct_target:
            print(f"To include {pct_target}% of DMAs: threshold = {threshold*100:.0f}% "
                  f"({included_counts[i]} DMAs included, {excluded_counts[i]} excluded)")
            break
