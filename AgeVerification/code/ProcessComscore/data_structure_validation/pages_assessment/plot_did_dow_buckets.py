"""
Plot DiD estimates by day-of-week as % change vs. control-post mean.
Reads did_dow_results.csv produced by did_dow_buckets.R.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker

PALETTE = ['#8c1515', '#0B3954', '#9a8873', '#b4adea', '#aceb98']
OUTDIR  = "output/descriptives/pages_assessment"

df = pd.read_csv(f"{OUTDIR}/did_dow_results.csv")

for site in df["site"].unique():
    slug  = site.lower()
    color = PALETTE[0] if site == "Pornhub" else PALETTE[1]
    sub   = df[df["site"] == site].copy().sort_values("dow")

    buckets  = sub[~sub["is_total"]].reset_index(drop=True)
    total_pt = sub[sub["is_total"]].reset_index(drop=True)

    n_bkt = len(buckets[buckets["period"] == "short"])  # should be 7
    x_bkt = np.arange(n_bkt)
    x_tot = n_bkt + 0.9
    x_max = x_tot + 0.6

    dow_labels = (
        buckets[buckets["period"] == "short"]
        .reset_index(drop=True)["dow_label"]
        .tolist()
    )

    fig = plt.figure(figsize=(13, 7))
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
                    fmt='none', color='black', capsize=3, lw=1.1)

        # Vertical separator between weekdays and weekend
        ax.axvline(4.5, color='grey', lw=0.8, ls='--', alpha=0.6)

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
                        fmt='none', color='black', capsize=3, lw=1.1)
            ax.axvline(n_bkt + 0.2, color='grey', lw=0.8, ls=':')

        ax.axhline(0, color='black', lw=0.9)

        # ── bar axis formatting ────────────────────────────────────────────────
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

        # ── table ──────────────────────────────────────────────────────────────
        axt.set_xlim(-0.6, x_max)
        axt.set_ylim(0, 1)
        axt.axis('off')

        ROW_Y   = {"dow": 0.78, "sess": 0.48, "min": 0.16}
        ROW_LBL = {
            "dow":  "Day",
            "sess": "Sessions %",
            "min":  "Time %",
        }
        ROW_COL = {"dow": '#555555', "sess": '#333333', "min": '#333333'}

        for key in ("dow", "sess", "min"):
            axt.text(-0.01, ROW_Y[key], ROW_LBL[key],
                     transform=axt.transAxes,
                     ha='right', va='center', fontsize=10,
                     fontweight='bold', color=ROW_COL[key])

        # Weekend shading
        axt.axvspan(4.5, n_bkt - 0.5, color='#f5f5f5', zorder=0)
        ax.axvspan(4.5, n_bkt - 0.5, color='#f5f5f5', zorder=0)

        for i, row in bkt.iterrows():
            x_pos = x_bkt[i]
            axt.text(x_pos, ROW_Y["dow"], dow_labels[i],
                     ha='center', va='center', fontsize=10, color=ROW_COL["dow"],
                     fontweight='bold' if dow_labels[i] in ('Sat', 'Sun') else 'normal')
            s = row["share_sessions"]
            if pd.notna(s):
                axt.text(x_pos, ROW_Y["sess"], f"{s:.0%}",
                         ha='center', va='center', fontsize=9.5, color=ROW_COL["sess"])
            m = row["share_minutes"]
            if pd.notna(m):
                axt.text(x_pos, ROW_Y["min"], f"{m:.0%}",
                         ha='center', va='center', fontsize=9.5, color=ROW_COL["min"])

        if len(tot):
            axt.text(x_tot, ROW_Y["dow"], "All",
                     ha='center', va='center', fontsize=9.5, color=ROW_COL["dow"])
            axt.text(x_tot, ROW_Y["sess"], "—",
                     ha='center', va='center', fontsize=9.5, color='grey')
            axt.text(x_tot, ROW_Y["min"],  "—",
                     ha='center', va='center', fontsize=9.5, color='grey')

        for y_sep in [0.34, 0.63]:
            axt.axhline(y_sep, color='#cccccc', lw=0.8, xmin=0.0, xmax=1.0)

        # Weekend label
        axt.text(5.0, 1.08, "Weekend", ha='center', va='bottom',
                 fontsize=8.5, color='#777777', style='italic',
                 transform=axt.transData)

    fig.suptitle(
        f"Law's effect on winsorized session minutes by day of week — {site}\n"
        "Stacked TWFE | machine×cohort + cohort×week FE | SE clustered by state",
        fontsize=13, fontweight='bold', y=1.01)
    fig.text(
        0.5, -0.01,
        "Day derived from session date column (local date). "
        "DV: winsorized minutes (session P95) from sessions on each day summed per machine-week. "
        "Shaded bar = pooled regression. Shaded region = Sat–Sun.",
        ha='center', fontsize=9, color='#555555')

    path = f"{OUTDIR}/did_dow_buckets_{slug}.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved → {path}")
