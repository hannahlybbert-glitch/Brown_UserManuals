# Author: Hannah Lybbert
# Created: 02/11/2026
# Purpose: Identify top 5 XXX Adult websites from January 2022 to use across entire sample

"""
Identifies Top 5 XXX Adult Websites from January 2022
Uses these consistently across all months in the sample
Other XXX Adult websites (not in top 5) will be pooled together in script 2

Output: top5_xxx_websites.csv with website names and metadata
"""

import pandas as pd
import numpy as np
import os

# For cluster: comment out the os.chdir line
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory
project_root = os.getcwd()

print("="*80)
print("IDENTIFY TOP 5 XXX ADULT WEBSITES (from January 2022)")
print("="*80)

# File paths
sessions_file = os.path.join(project_root, "data", "ProcessComscore", "merged_session_files", "merged_sessions_202201.parquet")
output_file = os.path.join(project_root, "data", "Aggregation", "top5_xxx_websites.csv")

# Create output directory if needed
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Load January 2022 sessions
print(f"\nLoading January 2022 sessions: {sessions_file}")
columns_to_read = ['duration', 'top_web_name', 'subcategory']
sessions = pd.read_parquet(sessions_file, columns=columns_to_read)
print(f"Loaded {len(sessions):,} sessions")

# Filter to positive duration only
sessions = sessions[sessions['duration'] > 0].copy()
print(f"After filtering zero duration: {len(sessions):,} sessions")

# Identify top 5 XXX Adult websites by total duration
print("\nIdentifying top 5 XXX Adult websites...")
xxx_adult_sessions = sessions[sessions['subcategory'] == 'XXX Adult'].copy()
print(f"Found {len(xxx_adult_sessions):,} XXX Adult sessions")

# Calculate total duration per website
website_totals = xxx_adult_sessions.groupby('top_web_name')['duration'].sum().sort_values(ascending=False)

print(f"\nTop 10 XXX Adult websites by total duration:")
for i, (website, duration) in enumerate(website_totals.head(10).items(), 1):
    print(f"{i:2d}. {website:35s} {duration:15,.0f} seconds ({duration/3600:10,.1f} hours)")

# Get top 5
top_5_websites = website_totals.head(5).index.tolist()
print(f"\nTop 5 websites selected:")
for i, website in enumerate(top_5_websites, 1):
    print(f"  {i}. {website}")

# Create output dataframe
output_data = []

# Add top 5
for rank, website in enumerate(top_5_websites, 1):
    duration = website_totals[website]
    output_data.append({
        'website_name': website,
        'rank': rank,
        'total_duration_seconds': duration,
        'total_duration_hours': duration / 3600
    })

output_df = pd.DataFrame(output_data)

# Save to CSV
print(f"\nSaving to {output_file}")
output_df.to_csv(output_file, index=False)

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Top 5 XXX Adult websites identified from January 2022")
print(f"These will be tracked consistently across all months")
print(f"Other XXX Adult websites will be pooled as 'other_XXX_sites' in script 2")
print(f"\nOutput saved to: {output_file}")
print(f"Total websites: {len(output_df)}")
print("\n" + "="*80)
print("COMPLETE")
print("="*80)
