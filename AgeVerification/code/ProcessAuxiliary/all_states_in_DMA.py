"""
Purpose: Collapse DMA_state_shares.csv to one row per ComScore market with:
  - comscore_market : ComScore market name (via DMA_comscore_mapping.csv)
  - all_states      : comma-separated list of all states in the DMA (alphabetical)
  - majority_share  : highest state_share in that DMA

Input:  data/ProcessAuxiliary/DMA_County/DMA_state_shares.csv
        data/ProcessAuxiliary/DMA_market_state/DMA_comscore_mapping.csv
Output: data/ProcessAuxiliary/DMA_County/all_states_in_DMA.csv
"""

import pandas as pd
from pathlib import Path

project_root  = Path(__file__).resolve().parents[2]
shares_file   = project_root / "data" / "ProcessAuxiliary" / "DMA_County" / "DMA_state_shares.csv"
mapping_file  = project_root / "data" / "ProcessAuxiliary" / "DMA_market_state" / "DMA_comscore_mapping.csv"
output_file   = project_root / "data" / "ProcessAuxiliary" / "DMA_County" / "all_states_in_DMA.csv"

shares  = pd.read_csv(shares_file)
mapping = pd.read_csv(mapping_file, usecols=["DMA_code", "comscore_market_full"])

df = shares.merge(mapping, on="DMA_code", how="left")

n_unmatched = df["comscore_market_full"].isna().sum()
if n_unmatched:
    unmatched_dmas = df.loc[df["comscore_market_full"].isna(), "DMA_name"].unique()
    print(f"Warning: {n_unmatched} rows have no ComScore match — dropping:")
    for name in unmatched_dmas:
        print(f"  {name}")
    df = df.dropna(subset=["comscore_market_full"])

result = (
    df.groupby("comscore_market_full", sort=False)
    .agg(
        all_states    =("state", lambda s: ", ".join(sorted(s))),
        majority_share=("state_share", "max"),
    )
    .reset_index()
    .rename(columns={"comscore_market_full": "comscore_market"})
    [["comscore_market", "all_states", "majority_share"]]
    .sort_values("comscore_market")
)

result.to_csv(output_file, index=False)
print(f"Wrote {len(result)} rows to {output_file}")
