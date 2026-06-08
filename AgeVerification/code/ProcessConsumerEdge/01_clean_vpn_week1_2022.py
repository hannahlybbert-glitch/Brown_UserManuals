import glob
import os
import pandas as pd

SRC_DIR = "raw/dewey-downloads/daily-spend-breakout-by-brand-and-state"
OUT_PATH = "data/ConsumerEdge/vpn_week1_2022.csv"

VPN_BRANDS = {
    18937: "NORDVPN",
    23012: "EXPRESS VPN",
    21761: "PROTONVPN",   # plan had 21791 (BIOVEA); correct ID is 21761
    20485: "PUREVPN",
    17728: "STRONG VPN",
    21746: "CYBERGHOST VPN",
    # VYPRVPN (21941) has no observations in week 1 2022 data
}

files = sorted(glob.glob(os.path.join(SRC_DIR, "2022-01-0[1-7]--data_*.csv.gz")))
print(f"Found {len(files)} files")

df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
print(f"Raw rows: {len(df):,}")

df = df[df["BRAND_ID"].isin(VPN_BRANDS)].copy()
df = df.drop(columns=["VERSION"])

print(f"Filtered rows: {len(df):,}")
print(f"Brands: {df['BRAND_NAME'].nunique()}")
print(f"Dates: {sorted(df['TRANS_DATE'].unique())}")

df.to_csv(OUT_PATH, index=False)
print(f"Saved to {OUT_PATH}")
