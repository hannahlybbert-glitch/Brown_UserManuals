"""
Point plot of DiD estimates under alternative winsorization choices — Pornhub.
Reads winsorization_robustness.csv produced by winsorization_robustness.R.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.gridspec as gridspec

PALETTE = ['#8c1515', '#0B3954', '#9a8873', '#b4adea', '#aceb98']
OUTDIR  = "output/descriptives/pages_assessment"

df = pd.read_csv(f"{OUTDIR}/winsorization_robustness.csv")

# Display order and labels
LABEL_MAP = {
    "mw_p95":    "P95\n(main)",
    "mw_p96":    "P96",
    "mw_p97":    "P97",
    "mw_p98":    "P98",
    "mw_p99":    "P99",
    "mw_p99_5":  "P99.5",
    "sess_p95":  "P95",
    "sess_p96":  "P96",
    "sess_p97":  "P97",
    "sess_p98":  "P98",
    "sess_p99":  "P99",
    "sess_p99_5": "P99.5",
}
ORDER = [
    "mw_p95", "mw_p96", "mw_p97", "mw_p98", "mw_p99", "mw_p99_5",
    "sess_p95", "sess_p96", "sess_p97", "sess_p98", "sess_p99", "sess_p99_5",
]
df["sort_order"] = df["label"].map({k: i for i, k in enumerate(ORDER)})
df = df.sort_values("sort_order").reset_index(drop=True)

x = np.arange(len(df))
OFFSET = 0.15   # horizontal jitter between short and long series

fig = plt.figure(figsize=(14, 7))
gs  = gridspec.GridSpec(2, 1, height_ratios=[4, 1.4], hspace=0.08)
ax  = fig.add_subplot(gs[0])
axt = fig.add_subplot(gs[1])

# ── point plot ────────────────────────────────────────────────────────────────
for col, (period, label_txt, ci_lo, ci_hi, offset) in enumerate([
    ("beta_short", "Short-run (weeks 0–3)", "ci_lo_short", "ci_hi_short", -OFFSET),
    ("beta_long",  "Long-run (weeks 4–8)",  "ci_lo_long",  "ci_hi_long",  +OFFSET),
]):
    xp = x + offset
    ax.errorbar(
        xp, df[period],
        yerr=[df[period] - df[ci_lo], df[ci_hi] - df[period]],
        fmt='o', color=PALETTE[col], capsize=4, lw=1.4,
        markersize=7, markeredgecolor='white', markeredgewidth=0.8,
        label=label_txt, zorder=3,
    )

# Dotted separator between machine-week and session-level groups
n_mw = (df["type"] == "machine-week").sum()
ax.axvline(n_mw - 0.5, color='grey', lw=0.9, ls=':')


ax.axhline(0, color='black', lw=0.9)

# Mark main analysis (P95) with a faint shaded band spanning its CI
main = df[df["label"] == "mw_p95"].iloc[0]
ax.axhspan(main["ci_lo_short"], main["ci_hi_short"],
           color=PALETTE[0], alpha=0.08, zorder=0)

ax.set_xticks(x)
ax.set_xticklabels([''] * len(x))   # labels go in table below
ax.tick_params(axis='x', length=4)
ax.set_xlim(-0.6, len(x) - 0.4)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:+.2f}"))
ax.tick_params(axis='y', labelsize=11)
ax.set_ylabel("Minutes per machine-week (β)", fontsize=12)
ax.set_title(
    "Pornhub: pooled DiD under alternative winsorization choices\n"
    "Stacked TWFE | machine×cohort + cohort×week FE | SE clustered by state",
    fontsize=12, fontweight='bold', pad=8)
ax.spines[['top', 'right']].set_visible(False)
ax.tick_params(which='minor', bottom=False, left=False)
ax.legend(fontsize=10, frameon=False)

# ── table: threshold and baseline mean ────────────────────────────────────────
axt.set_xlim(-0.6, len(x) - 0.4)
axt.set_ylim(0, 1)
axt.axis('off')

ROW_Y   = {"lbl": 0.82, "thresh": 0.50, "base": 0.16}
ROW_LBL = {"lbl": "Winsorization", "thresh": "Threshold (min)", "base": "Baseline mean (min)"}
ROW_COL = {"lbl": '#555555', "thresh": '#333333', "base": '#333333'}

for key in ("lbl", "thresh", "base"):
    axt.text(-0.01, ROW_Y[key], ROW_LBL[key],
             transform=axt.transAxes,
             ha='right', va='center', fontsize=10,
             fontweight='bold', color=ROW_COL[key])

for i, row in df.iterrows():
    xp = x[i]
    axt.text(xp, ROW_Y["lbl"],
             LABEL_MAP.get(row["label"], row["label"]),
             ha='center', va='center', fontsize=9.5, color=ROW_COL["lbl"])
    axt.text(xp, ROW_Y["thresh"],
             f"{row['threshold_sec']/60:.1f}",
             ha='center', va='center', fontsize=10, color=ROW_COL["thresh"])
    axt.text(xp, ROW_Y["base"],
             f"{row['baseline_short']:.2f}",
             ha='center', va='center', fontsize=10, color=ROW_COL["base"])

for y_sep in [0.34, 0.67]:
    axt.axhline(y_sep, color='#cccccc', lw=0.8, xmin=0.0, xmax=1.0)

# Separator and group labels in table
axt.axvline(n_mw - 0.5, color='grey', lw=0.9, ls=':', ymin=0, ymax=1)
axt.text((n_mw - 1) / 2, 1.08, "Machine-week winsorization",
         ha='center', va='bottom', fontsize=9.5, color='#555555',
         style='italic', transform=axt.transData)
axt.text(n_mw + (len(df) - n_mw - 1) / 2, 1.08, "Session-level winsorization",
         ha='center', va='bottom', fontsize=9.5, color='#555555',
         style='italic', transform=axt.transData)

fig.text(
    0.5, -0.01,
    "Machine-week thresholds computed from 2022 baseline distribution (weeks 1–52, treated+control). "
    "Session P95 from control-state sessions (treated==0). Baseline mean = E[win_min | control, short-run post].",
    ha='center', fontsize=8.5, color='#555555')

path = f"{OUTDIR}/winsorization_robustness_ph.png"
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"Saved → {path}")
