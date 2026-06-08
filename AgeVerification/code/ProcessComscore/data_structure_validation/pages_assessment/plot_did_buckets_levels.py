"""
Point plot of DiD level effects (minutes per machine-week) by session-length bucket.
Reads did_bucket_results.csv produced by did_session_buckets.R.
"""
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker

PALETTE = ['#8c1515', '#0B3954', '#9a8873', '#b4adea', '#aceb98']
OUTDIR  = "output/descriptives/pages_assessment"

df = pd.read_csv(f"{OUTDIR}/did_bucket_results.csv")


def short_label(lbl):
    m = re.match(r'\((\d+),.*\(win\.\)', str(lbl), re.DOTALL)
    if m:
        return f"{m.group(1)}+"
    return str(lbl).replace("\n", " ")


for site in df["site"].unique():
    slug  = site.lower()
    color = PALETTE[0] if site == "Pornhub" else PALETTE[1]
    sub   = df[df["site"] == site].copy().sort_values("bucket")

    buckets  = sub[~sub["is_total"]].reset_index(drop=True)
    total_pt = sub[sub["is_total"]].reset_index(drop=True)

    n_bkt = len(buckets[buckets["period"] == "short"])
    x_bkt = np.arange(n_bkt)
    x_tot = n_bkt + 0.9
    x_max = x_tot + 0.6

    bkt_short = (buckets[buckets["period"] == "short"]
                 .reset_index(drop=True)["bucket_label"]
                 .apply(short_label)
                 .tolist())

    fig = plt.figure(figsize=(max(13, n_bkt * 1.4 + 4), 8))
    gs  = gridspec.GridSpec(
        2, 2,
        height_ratios=[5, 1.8],
        hspace=0.05,
        wspace=0.35,
    )

    ax_bars  = [fig.add_subplot(gs[0, c]) for c in range(2)]
    ax_table = [fig.add_subplot(gs[1, c]) for c in range(2)]
    ax_bars[1].sharey(ax_bars[0])

    for col, (period, period_label) in enumerate([
        ("short", "Short-run (weeks 0–3)"),
        ("long",  "Long-run (weeks 4–8)"),
    ]):
        ax  = ax_bars[col]
        axt = ax_table[col]
        bkt = buckets[buckets["period"] == period].reset_index(drop=True)
        tot = total_pt[total_pt["period"] == period].reset_index(drop=True)

        # ── points + CI ────────────────────────────────────────────────────────
        ax.errorbar(
            x_bkt, bkt["beta_m"],
            yerr=[
                bkt["beta_m"] - bkt["ci_lo_m"],
                bkt["ci_hi_m"] - bkt["beta_m"],
            ],
            fmt='o', color=color, capsize=4, lw=1.4,
            markersize=7, markeredgecolor='white', markeredgewidth=0.8,
            zorder=3,
        )

        # ── "all" anchor ───────────────────────────────────────────────────────
        if len(tot):
            ax.errorbar(
                x_tot, tot["beta_m"].iloc[0],
                yerr=[[tot["beta_m"].iloc[0] - tot["ci_lo_m"].iloc[0]],
                      [tot["ci_hi_m"].iloc[0] - tot["beta_m"].iloc[0]]],
                fmt='D', color=color, alpha=0.45, capsize=4, lw=1.4,
                markersize=7, markeredgecolor=color, markeredgewidth=1.2,
                zorder=3,
            )
            ax.axvline(n_bkt + 0.2, color='grey', lw=0.8, ls=':')

        ax.axhline(0, color='black', lw=0.9)

        # ── formatting ─────────────────────────────────────────────────────────
        xticks = list(x_bkt) + ([x_tot] if len(tot) else [])
        ax.set_xticks(xticks)
        ax.set_xticklabels([''] * len(xticks))
        ax.tick_params(axis='x', length=4)
        ax.set_xlim(-0.6, x_max)
        ax.tick_params(axis='y', labelsize=11)
        ax.set_title(period_label, fontsize=13, fontweight='bold', pad=8)
        ax.spines[['top', 'right']].set_visible(False)
        ax.tick_params(which='minor', bottom=False, left=False)
        if col == 0:
            ax.set_ylabel("Minutes per machine-week (β)", fontsize=12)
        else:
            ax.tick_params(axis='y', left=False)

        # ── table ──────────────────────────────────────────────────────────────
        axt.set_xlim(-0.6, x_max)
        axt.set_ylim(0, 1)
        axt.axis('off')

        ROW_Y   = {"dur": 0.82, "sess": 0.50, "min": 0.16}
        ROW_LBL = {
            "dur":  "Duration\nper session (min)",
            "sess": "Sessions %",
            "min":  "Time %",
        }
        ROW_COL = {"dur": '#555555', "sess": '#333333', "min": '#333333'}

        for key in ("dur", "sess", "min"):
            axt.text(-0.01, ROW_Y[key], ROW_LBL[key],
                     transform=axt.transAxes,
                     ha='right', va='center', fontsize=10,
                     fontweight='bold', color=ROW_COL[key])

        for i, row in bkt.iterrows():
            x_pos = x_bkt[i]
            axt.text(x_pos, ROW_Y["dur"], bkt_short[i],
                     ha='center', va='center', fontsize=10, color=ROW_COL["dur"])
            s = row["share_sessions"]
            if pd.notna(s):
                axt.text(x_pos, ROW_Y["sess"], f"{s:.0%}",
                         ha='center', va='center', fontsize=10, color=ROW_COL["sess"])
            m = row["share_minutes"]
            if pd.notna(m):
                axt.text(x_pos, ROW_Y["min"], f"{m:.0%}",
                         ha='center', va='center', fontsize=10, color=ROW_COL["min"])

        if len(tot):
            axt.text(x_tot, ROW_Y["dur"],  "all",
                     ha='center', va='center', fontsize=10, color=ROW_COL["dur"])
            axt.text(x_tot, ROW_Y["sess"], "—",
                     ha='center', va='center', fontsize=10, color='grey')
            axt.text(x_tot, ROW_Y["min"],  "—",
                     ha='center', va='center', fontsize=10, color='grey')

        for y_sep in [0.34, 0.67]:
            axt.axhline(y_sep, color='#cccccc', lw=0.8, xmin=0.0, xmax=1.0)

    fig.suptitle(
        f"Law's effect on winsorized session minutes by duration bucket — {site}\n"
        "Stacked TWFE | machine×cohort + cohort×week FE | SE clustered by state",
        fontsize=13, fontweight='bold', y=1.01)
    fig.text(
        0.5, -0.01,
        "Buckets: per-session duration; last bucket winsorized at per-session P95. "
        "Y-axis: β in minutes per machine-week. Diamond = pooled (all-bucket) regression.",
        ha='center', fontsize=9.5, color='#555555')

    path = f"{OUTDIR}/did_buckets_levels_{slug}.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved → {path}")
