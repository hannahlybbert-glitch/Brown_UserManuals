# Author: Hannah Lybbert
# Created: 02/03/2026
# Purpose: Descriptives comparing sample pre/post dropping exclude==1
# NOTE: All descriptives exclude machines with 'Unknown' region (360 machines, 0.16%)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Set working directory
os.chdir("C:/Users/hlybbert/OneDrive - The University of Chicago/Documents/AgeVerification")

output_dir = "output/descriptives/demo_market_descriptives"
os.makedirs(output_dir, exist_ok=True)

# Load state-merged desktop demographics
desktop_df = pd.read_csv("data/ProcessAuxiliary/DMA_market_state/test/desktop_demos_with_state_202201.csv")

# Drop Unknown region observations
unknown_count = (desktop_df['region'] == 'Unknown').sum()
desktop_df = desktop_df[desktop_df['region'] != 'Unknown']
print(f"Dropped {unknown_count:,} machines with 'Unknown' region\n")

# --- Parse fields ---

# Age: lower bound of range (e.g., "45-54" -> 45, "65 and Over" -> 65)
desktop_df['age_lower'] = (desktop_df['hoh_age']
    .str.replace('"', '', regex=False)
    .str.extract(r'(\d+)')[0]
    .astype('Int64'))

# HH Income: lower bound (e.g., "HHI US: 150k-199.999k" -> 150000)
def parse_income(val):
    if pd.isna(val):
        return None
    val = str(val).replace('"', '').strip()
    if 'less' in val.lower():
        return 0
    for prefix in ['HHI US: ', 'HHI USD:']:
        if val.startswith(prefix):
            val = val[len(prefix):].strip()
            break
    lower = val.split('-')[0].replace('+', '').strip()
    if 'k' in lower.lower():
        return int(float(lower.lower().replace('k', '')) * 1000)
    return int(float(lower.replace(',', '')))

desktop_df['income_lower'] = desktop_df['hh_income'].apply(parse_income)

# Children: Yes/No (e.g., "Children:Yes" -> Yes)
desktop_df['children'] = (desktop_df['children_present']
    .str.replace('"', '', regex=False)
    .str.replace('Children:', '', regex=False)
    .str.strip())

# HH Size: extract integer (e.g., "HH Size: 3" -> 3, "5 or More" -> 5)
desktop_df['hh_size_num'] = (desktop_df['hh_size']
    .str.replace('"', '', regex=False)
    .str.extract(r'(\d+)')[0]
    .astype('Int64'))

# --- Split samples ---
df_before = desktop_df.copy()                              # exclude==1 included
df_after = desktop_df[desktop_df['exclude'] == 0].copy()   # exclude==1 dropped

print(f"Total machines (All regions): {len(df_before):,}")
print(f"Total machines (<0.2 minority share):  {len(df_after):,}")
print(f"Machines removed (exclude==1):        {len(df_before) - len(df_after):,}")

# --- Interleaved descriptives (a = before, b = after) ---

print("\n" + "=" * 80)
print("1. Number of States")
print("=" * 80)
print(f"  1a (All regions): {df_before['majority_state'].nunique()}")
print(f"  1b (<0.2 minority share):  {df_after['majority_state'].nunique()}")

print("\n" + "=" * 80)
print("2. Number of ComScore Markets (Regions)")
print("=" * 80)
print(f"  2a (All regions): {df_before['region'].nunique()}")
print(f"  2b (<0.2 minority share):  {df_after['region'].nunique()}")

print("\n" + "=" * 80)
print("3. Top 20 ComScore Markets by Number of Users")
print("=" * 80)
print("\n  3a (All regions):")
print(df_before['region'].value_counts().head(20).to_string())
print("\n  3b (<0.2 minority share):")
print(df_after['region'].value_counts().head(20).to_string())

# Grouped horizontal bar chart: top 20 markets
top_markets = df_before['region'].value_counts().head(20).index.tolist()
before_counts = df_before['region'].value_counts().reindex(top_markets).fillna(0)
after_counts = df_after['region'].value_counts().reindex(top_markets).fillna(0)

fig, ax = plt.subplots(figsize=(10, 8))
y = np.arange(len(top_markets))
bar_height = 0.35
ax.barh(y - bar_height / 2, before_counts, height=bar_height, label='All regions', color='steelblue')
ax.barh(y + bar_height / 2, after_counts, height=bar_height, label='<0.2 minority share', color='coral')
ax.set_yticks(y)
ax.set_yticklabels(top_markets)
ax.set_xlabel('Number of Users')
ax.set_title('Top 20 ComScore Markets by Number of Users')
ax.legend()
ax.invert_yaxis()
ax.xaxis.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "top20_markets.png"), dpi=150, bbox_inches='tight')
plt.show()

print("\n" + "=" * 80)
print("4. Age Distribution (lower bound of range)")
print("=" * 80)
print("\n  4a (All regions):")
print(df_before['age_lower'].value_counts().sort_index().to_string())
print("\n  4b (<0.2 minority share):")
print(df_after['age_lower'].value_counts().sort_index().to_string())

# Overlaid histogram: age
fig, ax = plt.subplots(figsize=(10, 5))
age_bins = sorted(df_before['age_lower'].dropna().unique().tolist()) + [df_before['age_lower'].max() + 5]
ax.hist(df_before['age_lower'].dropna(), bins=age_bins, alpha=0.5, label='All regions', edgecolor='black')
ax.hist(df_after['age_lower'].dropna(), bins=age_bins, alpha=0.5, label='<0.2 minority share', edgecolor='black')
ax.set_xticks(age_bins[:-1])
ax.set_xlabel('Age (lower bound of range)')
ax.set_ylabel('Count')
ax.set_title('Age Distribution')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "age_distribution.png"), dpi=150, bbox_inches='tight')
plt.show()

print("\n" + "=" * 80)
print("5. Household Income Distribution (lower bound)")
print("=" * 80)
print("\n  5a (All regions):")
print(df_before['income_lower'].value_counts().sort_index().to_string())
print("\n  5b (<0.2 minority share):")
print(df_after['income_lower'].value_counts().sort_index().to_string())

# Overlaid histogram: household income
fig, ax = plt.subplots(figsize=(10, 5))
income_bins = sorted(df_before['income_lower'].dropna().unique().tolist()) + [df_before['income_lower'].max() + 25000]
ax.hist(df_before['income_lower'].dropna(), bins=income_bins, alpha=0.5, label='All regions', edgecolor='black')
ax.hist(df_after['income_lower'].dropna(), bins=income_bins, alpha=0.5, label='<0.2 minority share', edgecolor='black')
ax.set_xticks(income_bins[:-1])
ax.set_xticklabels([f'${int(x/1000)}k' if x >= 1000 else '$0' for x in income_bins[:-1]], rotation=45)
ax.set_xlabel('Household Income (lower bound)')
ax.set_ylabel('Count')
ax.set_title('Household Income Distribution')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "income_distribution.png"), dpi=150, bbox_inches='tight')
plt.show()

print("\n" + "=" * 80)
print("6. Share of HH with Children Present")
print("=" * 80)
print("\n  6a (All regions):")
print((df_before['children'].value_counts(normalize=True) * 100).round(2).to_string())
print("\n  6b (<0.2 minority share):")
print((df_after['children'].value_counts(normalize=True) * 100).round(2).to_string())

print("\n" + "=" * 80)
print("7. Household Size Distribution")
print("=" * 80)
print("\n  7a (All regions):")
print(df_before['hh_size_num'].value_counts().sort_index().to_string())
print("\n  7b (<0.2 minority share):")
print(df_after['hh_size_num'].value_counts().sort_index().to_string())

# Overlaid histogram: household size
fig, ax = plt.subplots(figsize=(10, 5))
size_values = sorted(df_before['hh_size_num'].dropna().unique().tolist())
size_bins = [v - 0.5 for v in size_values] + [size_values[-1] + 0.5]
ax.hist(df_before['hh_size_num'].dropna(), bins=size_bins, alpha=0.5, label='All regions', edgecolor='black')
ax.hist(df_after['hh_size_num'].dropna(), bins=size_bins, alpha=0.5, label='<0.2 minority share', edgecolor='black')
ax.set_xticks(size_values)
ax.set_xlabel('Household Size')
ax.set_ylabel('Count')
ax.set_title('Household Size Distribution')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "hh_size_distribution.png"), dpi=150, bbox_inches='tight')
plt.show()
