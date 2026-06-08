"""
Plot DiD estimates by session-length bucket as % change vs. control-post mean.
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
    """Shorten bucket label: winsorized last bucket → 'X+'; strip newlines."""
    # "(25,29.4]\n(win.)" → "25+"
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

    # Short bucket labels for table row (computed once from short-run rows)
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

        # ── bars ──────────────────────────────────────────────────────────────
        bar_colors = [color if v <= 0 else PALETTE[2] for v in bkt["pct_change"]]
        ax.bar(x_bkt, bkt["pct_change"] * 100, color=bar_colors,
               alpha=0.85, width=0.7, edgecolor='white', linewidth=0.3)
        ax.errorbar(x_bkt, bkt["pct_change"] * 100,
                    yerr=[
                        (bkt["pct_change"] - bkt["pct_ci_lo"]) * 100,
                        (bkt["pct_ci_hi"] - bkt["pct_change"]) * 100,
                    ],
                    fmt='none', color='black', capsize=4, lw=1.2)

        # ── "all" anchor ───────────────────────────────────────────────────────
        if len(tot):
            ax.bar(x_tot, tot["pct_change"].iloc[0] * 100,
                   color=color, alpha=0.35, width=0.7,
                   edgecolor=color, linewidth=1.4)
            ax.errorbar(x_tot, tot["pct_change"].iloc[0] * 100,
                        yerr=[[
                            (tot["pct_change"].iloc[0] - tot["pct_ci_lo"].iloc[0]) * 100
                        ], [
                            (tot["pct_ci_hi"].iloc[0] - tot["pct_change"].iloc[0]) * 100
                        ]],
                        fmt='none', color='black', capsize=4, lw=1.2)
            ax.axvline(n_bkt + 0.2, color='grey', lw=0.8, ls=':')

        ax.axhline(0, color='black', lw=0.9)

        # ── bar axis: tick marks only — labels live in table below ────────────
        xticks = list(x_bkt) + ([x_tot] if len(tot) else [])
        ax.set_xticks(xticks)
        ax.set_xticklabels([''] * len(xticks))
        ax.tick_params(axis='x', length=4)
        ax.set_xlim(-0.6, x_max)
        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
        ax.tick_params(axis='y', labelsize=11)
        ax.set_title(period_label, fontsize=13, fontweight='bold', pad=8)
        ax.spines[['top', 'right']].set_visible(False)
        ax.tick_params(which='minor', bottom=False, left=False)
        if col == 0:
            ax.set_ylabel("% change vs. control-period post mean", fontsize=12)
        else:
            ax.tick_params(axis='y', left=False)

        # ── table: three rows — duration per session / sessions % / minutes % ─
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

        # Row labels: placed just outside left axis edge using transAxes coords
        for key in ("dur", "sess", "min"):
            axt.text(-0.01, ROW_Y[key], ROW_LBL[key],
                     transform=axt.transAxes,
                     ha='right', va='center', fontsize=10,
                     fontweight='bold', color=ROW_COL[key])

        # Values aligned with each bar
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

        # "all" column
        if len(tot):
            axt.text(x_tot, ROW_Y["dur"],  "all",
                     ha='center', va='center', fontsize=10, color=ROW_COL["dur"])
            axt.text(x_tot, ROW_Y["sess"], "—",
                     ha='center', va='center', fontsize=10, color='grey')
            axt.text(x_tot, ROW_Y["min"],  "—",
                     ha='center', va='center', fontsize=10, color='grey')

        # separator lines between rows
        for y_sep in [0.34, 0.67]:
            axt.axhline(y_sep, color='#cccccc', lw=0.8, xmin=0.0, xmax=1.0)

    fig.suptitle(
        f"Law's effect on winsorized session minutes by duration bucket — {site}\n"
        "Stacked TWFE | machine×cohort + cohort×week FE | SE clustered by state",
        fontsize=13, fontweight='bold', y=1.01)
    fig.text(
        0.5, -0.01,
        "Buckets: per-session duration; last bucket winsorized at per-session P95. "
        "Y-axis: β / mean(DV | control, post). Shaded bar = pooled (all-bucket) regression.",
        ha='center', fontsize=9.5, color='#555555')

    path = f"{OUTDIR}/did_buckets_{slug}.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved → {path}")
