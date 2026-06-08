"""
Time series plots for VPN ConsumerEdge panel (brand x state x week).

Produces:
  1. Weekly national spend by brand (line plot, all brands)
  2. Weekly national transaction count by brand
  3. Weekly spend: NordVPN vs ExpressVPN only (cleaner two-brand comparison)

Output: output/figures/ConsumerEdge/
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

OUT_DIR = "output/descriptives/ConsumerEdge"
PALETTE = ["#8c1515", "#0B3954", "#9a8873", "#b4adea", "#aceb98", "#e07b39", "#5c6bc0"]

# --- house style ---
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "xtick.bottom": True,
    "ytick.left": True,
    "xtick.minor.visible": False,
    "ytick.minor.visible": False,
    "font.size": 11,
    "axes.labelsize": 11,
    "legend.frameon": False,
})

# Load and aggregate to national weekly totals
df = pd.read_csv("data/ConsumerEdge/vpn_state_week_2022_2024.csv", parse_dates=["week_start"])
df = df[df["week_start"].dt.year.between(2022, 2024)]

national = (
    df.groupby(["BRAND_NAME", "week_start"])
    .agg(spend=("spend", "sum"), trans=("trans", "sum"))
    .reset_index()
)

brands = sorted(national["BRAND_NAME"].unique())
color_map = dict(zip(brands, PALETTE))

# --- Plot 1: Weekly national spend, all brands ---
fig, ax = plt.subplots(figsize=(10, 5))
for brand in brands:
    sub = national[national["BRAND_NAME"] == brand].sort_values("week_start")
    ax.plot(sub["week_start"], sub["spend"] / 1e3, label=brand,
            color=color_map[brand], linewidth=1.4)

ax.set_xlabel("Week")
ax.set_ylabel("Spend ($000s, panel-weighted)")
ax.set_title("Weekly VPN Spend by Brand, 2022–2024")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}K"))
ax.legend(fontsize=9, loc="upper left")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/spend_timeseries_all_brands.png", dpi=150)
plt.close()

# --- Plot 2: Weekly national transactions, all brands ---
fig, ax = plt.subplots(figsize=(10, 5))
for brand in brands:
    sub = national[national["BRAND_NAME"] == brand].sort_values("week_start")
    ax.plot(sub["week_start"], sub["trans"], label=brand,
            color=color_map[brand], linewidth=1.4)

ax.set_xlabel("Week")
ax.set_ylabel("Transaction count (panel-weighted)")
ax.set_title("Weekly VPN Transactions by Brand, 2022–2024")
ax.legend(fontsize=9, loc="upper left")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/trans_timeseries_all_brands.png", dpi=150)
plt.close()

# --- Plot 3: Spend share by brand (stacked area) ---
pivot = (
    national.pivot_table(index="week_start", columns="BRAND_NAME", values="spend", aggfunc="sum")
    .sort_index()
    .fillna(0)
)
# Order by total spend descending
col_order = pivot.sum().sort_values(ascending=False).index.tolist()
pivot = pivot[col_order]

fig, ax = plt.subplots(figsize=(10, 5))
ax.stackplot(pivot.index, [pivot[b] / 1e3 for b in col_order],
             labels=col_order,
             colors=[color_map[b] for b in col_order],
             alpha=0.85)
ax.set_xlabel("Week")
ax.set_ylabel("Spend ($000s, panel-weighted)")
ax.set_title("Weekly VPN Spend Share by Brand, 2022–2024")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}K"))
ax.legend(fontsize=9, loc="upper left", reverse=True)
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/spend_stacked_area.png", dpi=150)
plt.close()

print("Saved 3 plots to", OUT_DIR)
