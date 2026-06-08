"""
Pre vs. post law plots for treated states (±14-day window) — mobile sessions:
  A. CDF of session duration by pages group, pre/post — PH and Xvideos
  B. Distribution of page counts, pre/post — PH and Xvideos
  C. TE on sessions and minutes by session-length bucket — PH and Xvideos
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D

PALETTE  = ['#8c1515', '#0B3954', '#9a8873', '#b4adea', '#aceb98']
OUTDIR   = "output/descriptives/pages_assessment"
WINDOW   = 14   # days

os.makedirs(OUTDIR, exist_ok=True)

def spine_clean(ax):
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(which='minor', bottom=False, left=False)

def fmt_min(ax):
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v/60:.0f}"))

def get_windows(df):
    law_dates = (df[df["post"] == 1].groupby("state")["date"].min().rename("law_date"))
    tr = df[df["treated"] == 1].copy().join(law_dates, on="state")
    delta = pd.to_timedelta(WINDOW, unit="D")
    pre  = tr[(tr["date"] >= tr["law_date"] - delta) & (tr["date"] <  tr["law_date"])]
    post = tr[(tr["date"] >= tr["law_date"])          & (tr["date"] <  tr["law_date"] + delta)]
    return pre, post

def cdf_xy(series, cap):
    s = np.sort(series[series <= cap].values)
    y = np.arange(1, len(s) + 1) / len(series)
    return s, y


SITES = [("pornhub", "Pornhub"), ("xvideos", "Xvideos")]

for slug, display_name in SITES:
    print(f"\n{'─'*50}\n{display_name} (mobile)")
    df        = pd.read_parquet(
        f"data/ProcessComscore/merged_cat_session_files/mobile_{slug}_sessions.parquet"
    )
    pre, post = get_windows(df)

    has_pages = "pages" in df.columns

    # ── A. CDF by pages group, pre vs. post ──────────────────────────────────
    if has_pages:
        CAP = 480  # 8 min
        pages_groups = {
            "1 page":   lambda d: d["pages"] == 1,
            "2–3 pages": lambda d: d["pages"].between(2, 3),
            "4–9 pages": lambda d: d["pages"].between(4, 9),
            "10+ pages": lambda d: d["pages"] >= 10,
        }
        colors4 = [PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[4]]

        fig, ax = plt.subplots(figsize=(7, 5))
        for (label, mask_fn), color in zip(pages_groups.items(), colors4):
            for period_df, ls, period_label in [(pre, '-', 'Pre'), (post, '--', 'Post')]:
                dur = period_df.loc[mask_fn(period_df), "duration"].dropna()
                if len(dur) < 10:
                    continue
                x_c, y_c = cdf_xy(dur, CAP)
                lw = 2.0 if ls == '-' else 1.6
                ax.plot(x_c, y_c, color=color, lw=lw, ls=ls,
                        label=f"{label} — {period_label} (n={len(dur):,})")

        fmt_min(ax); spine_clean(ax)
        ax.set_xlabel("Session duration (minutes)", fontsize=10)
        ax.set_ylabel("Cumulative share of sessions", fontsize=10)
        ax.set_title(f"CDF of session duration by pages — {display_name} (mobile)\nTreated states: pre (solid) vs. post (dashed) law",
                     fontsize=11, fontweight='bold')
        ax.set_xlim(0, CAP); ax.set_ylim(0, 1.0)
        ax.legend(fontsize=7.5, frameon=False, ncol=2)
        fig.text(0.5, -0.03, f"±{WINDOW}-day window around each state's law date. X-axis truncated at 8 min.",
                 ha='center', fontsize=8, color='#555555')
        fig.savefig(f"{OUTDIR}/prepost_cdf_by_pages_{slug}_mobile.png", dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved prepost_cdf_by_pages_{slug}_mobile.png")

    # ── B. Distribution of page counts, pre vs. post ──────────────────────────
    if has_pages:
        MAX_PAGES = 20
        pre_pg  = pre["pages"].dropna()
        post_pg = post["pages"].dropna()

        pre_share  = pre_pg[pre_pg <= MAX_PAGES].value_counts(normalize=True).sort_index()
        post_share = post_pg[post_pg <= MAX_PAGES].value_counts(normalize=True).sort_index()

        pages_idx = np.arange(1, MAX_PAGES + 1)
        pre_vals  = [pre_share.get(float(p), 0) for p in pages_idx]
        post_vals = [post_share.get(float(p), 0) for p in pages_idx]

        x = np.arange(len(pages_idx))
        w = 0.38
        fig2, ax = plt.subplots(figsize=(9, 4.5))
        ax.bar(x - w/2, pre_vals,  width=w, color=PALETTE[1], label=f"Pre-law  (n={len(pre_pg):,})",  alpha=0.9)
        ax.bar(x + w/2, post_vals, width=w, color=PALETTE[0], label=f"Post-law (n={len(post_pg):,})", alpha=0.9)
        ax.set_xticks(x); ax.set_xticklabels(pages_idx, fontsize=8)
        ax.set_xlabel("Number of pages per session", fontsize=10)
        ax.set_ylabel("Share of sessions", fontsize=10)
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1, decimals=0))
        ax.set_title(f"Distribution of pages per session — {display_name} (mobile)\nTreated states: pre vs. post law",
                     fontsize=11, fontweight='bold')
        spine_clean(ax)
        ax.legend(fontsize=9, frameon=False)
        pct_over = (pre_pg > MAX_PAGES).mean()
        fig2.text(0.5, -0.03,
                  f"Sessions with >{MAX_PAGES} pages excluded ({pct_over:.1%} of pre-law sessions). "
                  f"±{WINDOW}-day window.",
                  ha='center', fontsize=8, color='#555555')
        fig2.savefig(f"{OUTDIR}/prepost_pages_dist_{slug}_mobile.png", dpi=150, bbox_inches='tight')
        plt.close(fig2)
        print(f"  Saved prepost_pages_dist_{slug}_mobile.png")

    # ── C. TE on sessions and minutes by session-length bucket ────────────────
    edges_min = list(range(0, 16)) + [np.inf]
    edges_sec = [e * 60 for e in edges_min]

    labels_b = [f"{edges_min[i]}–{edges_min[i+1]}" if edges_min[i+1] != np.inf
                else f"{edges_min[i]}+"
                for i in range(len(edges_min) - 1)]

    def bucket_stats(subset):
        dur = subset["duration"].dropna()
        counts  = np.zeros(len(labels_b))
        minutes = np.zeros(len(labels_b))
        for i in range(len(labels_b)):
            lo, hi = edges_sec[i], edges_sec[i+1]
            mask = (dur >= lo) & (dur < hi)
            counts[i]  = mask.sum()
            minutes[i] = dur[mask].sum() / 60
        return counts, minutes

    pre_counts,  pre_mins  = bucket_stats(pre)
    post_counts, post_mins = bucket_stats(post)

    diff_counts = post_counts - pre_counts
    diff_mins   = post_mins   - pre_mins

    with np.errstate(divide='ignore', invalid='ignore'):
        pct_counts = np.where(pre_counts > 0, diff_counts / pre_counts, np.nan)
        pct_mins   = np.where(pre_mins   > 0, diff_mins   / pre_mins,   np.nan)

    x = np.arange(len(labels_b))

    def bar_color_arr(vals):
        return [PALETTE[0] if (v is not None and not np.isnan(v) and v >= 0)
                else PALETTE[1] for v in vals]

    for mode in ['absolute', 'proportional']:
        if mode == 'absolute':
            cnt_vals, min_vals = diff_counts, diff_mins
            cnt_fmt = ticker.FuncFormatter(lambda v, _: f"{v:+.0f}")
            min_fmt = ticker.FuncFormatter(lambda v, _: f"{v:+,.0f}")
            cnt_lbl, min_lbl = "Post − Pre\n(# sessions)", "Post − Pre\n(total minutes)"
            fname   = f"prepost_te_buckets_{slug}_mobile.png"
            title_sfx = "Absolute change"
        else:
            cnt_vals, min_vals = pct_counts, pct_mins
            cnt_fmt = ticker.PercentFormatter(xmax=1, decimals=0)
            min_fmt = ticker.PercentFormatter(xmax=1, decimals=0)
            cnt_lbl = "% change\n(sessions)"
            min_lbl = "% change\n(total minutes)"
            fname   = f"prepost_te_buckets_pct_{slug}_mobile.png"
            title_sfx = "Proportional change (relative to pre-law baseline)"

        fig3, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        fig3.subplots_adjust(hspace=0.12)

        axes[0].bar(x, cnt_vals, color=bar_color_arr(cnt_vals), edgecolor='white', linewidth=0.4)
        axes[0].axhline(0, color='black', lw=0.8)
        axes[0].set_ylabel(cnt_lbl, fontsize=10)
        axes[0].set_title(
            f"Law's effect on sessions and minutes by session-length bucket\n"
            f"{display_name} (mobile) — Treated states, ±{WINDOW}-day window — {title_sfx}",
            fontsize=11, fontweight='bold')
        spine_clean(axes[0])
        axes[0].yaxis.set_major_formatter(cnt_fmt)

        axes[1].bar(x, min_vals, color=bar_color_arr(min_vals), edgecolor='white', linewidth=0.4)
        axes[1].axhline(0, color='black', lw=0.8)
        axes[1].set_ylabel(min_lbl, fontsize=10)
        axes[1].set_xlabel("Session length bucket (minutes)", fontsize=10)
        spine_clean(axes[1])
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(labels_b, rotation=45, ha='right', fontsize=8)
        axes[1].yaxis.set_major_formatter(min_fmt)

        legend_els = [
            Line2D([0],[0], color=PALETTE[0], lw=8, label="Post > Pre"),
            Line2D([0],[0], color=PALETTE[1], lw=8, label="Post < Pre"),
        ]
        axes[0].legend(handles=legend_els, fontsize=9, frameon=False)

        fig3.text(0.5, -0.02,
                  f"±{WINDOW}-day window around each state's law date. "
                  f"Pre window used as baseline for proportional version.",
                  ha='center', fontsize=8, color='#555555')
        fig3.savefig(f"{OUTDIR}/{fname}", dpi=150, bbox_inches='tight')
        plt.close(fig3)
        print(f"  Saved {fname}")
