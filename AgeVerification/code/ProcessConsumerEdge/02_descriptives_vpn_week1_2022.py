import os
import pandas as pd

IN_PATH = "data/ConsumerEdge/vpn_week1_2022.csv"
OUT_DIR = "output/descriptives/ConsumerEdge"

df = pd.read_csv(IN_PATH)

# 1. Total spend & transactions by brand
spend_by_brand = (
    df.groupby(["BRAND_ID", "BRAND_NAME"])
    .agg(total_spend=("SPEND_AMOUNT", "sum"), total_trans=("TRANS_COUNT", "sum"))
    .reset_index()
    .sort_values("total_spend", ascending=False)
)
spend_by_brand.to_csv(os.path.join(OUT_DIR, "spend_by_brand.csv"), index=False)

# 2. Daily spend by brand
daily_spend = (
    df.groupby(["BRAND_ID", "BRAND_NAME", "TRANS_DATE"])
    .agg(spend=("SPEND_AMOUNT", "sum"), trans=("TRANS_COUNT", "sum"))
    .reset_index()
    .sort_values(["BRAND_NAME", "TRANS_DATE"])
)
daily_spend.to_csv(os.path.join(OUT_DIR, "daily_spend_by_brand.csv"), index=False)

# 3. State-level spend by brand
spend_by_brand_state = (
    df.groupby(["BRAND_ID", "BRAND_NAME", "STATE_ABBR"])
    .agg(spend=("SPEND_AMOUNT", "sum"), trans=("TRANS_COUNT", "sum"))
    .reset_index()
    .sort_values(["BRAND_NAME", "STATE_ABBR"])
)
spend_by_brand_state.to_csv(os.path.join(OUT_DIR, "spend_by_brand_state.csv"), index=False)

# 4. Coverage: state-days observed per brand
coverage = (
    df.groupby(["BRAND_ID", "BRAND_NAME"])
    .apply(lambda x: x[["STATE_ABBR", "TRANS_DATE"]].drop_duplicates().shape[0], include_groups=False)
    .reset_index(name="state_days_observed")
    .sort_values("state_days_observed", ascending=False)
)
coverage.to_csv(os.path.join(OUT_DIR, "coverage_by_brand.csv"), index=False)

print("Summary:")
print(spend_by_brand.to_string(index=False))
print(f"\nCoverage:\n{coverage.to_string(index=False)}")
