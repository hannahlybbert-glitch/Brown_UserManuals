"""
Session duration plots for mobile Pornhub, Xvideos, and XNXX (2022–2024).

Per site:
  Fig 1: CDF (two panels: 0-5 min, 0-30 min)
  Fig 2: Concentration curve (cumulative share of minutes vs. duration, winsorized at P95)
  Fig 3: Histogram (displayed up to 15 min)
  Fig 4: CDFs by number of pages (truncated at 8 min)
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

PALETTE  = ['#8c1515', '#0B3954', '#9a8873', '#b4adea', '#aceb98']
COLORS6  = PALETTE + ['#5c7a5c']
OUTDIR   = "output/descriptives/pages_assessment"
os.makedirs(OUTDIR, exist_ok=True)

SITES = [
    ("pornhub", "Pornhub"),
    ("xvideos", "Xvideos"),
    ("xnxx",    "XNXX"),
]

def fmt_min(ax, which="x"):
    fmt = ticker.FuncFormatter(lambda v, _: f"{v/60:.0f}")
    if which == "x":
        ax.xaxis.set_major_formatter(fmt)
    else:
        ax.yaxis.set_major_formatter(fmt)

def spine_clean(ax):
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(which='minor', bottom=False, left=False)

def cdf_xy(series, cap, denom=None):
    if denom is None:
        denom = len(series)
    s = np.sort(series[series <= cap].values)
    y = np.arange(1, len(s) + 1) / denom
    return s, y


for slug, display_name in SITES:
    df  = pd.read_parquet(
        f"data/ProcessComscore/merged_cat_session_files/mobile_{slug}_sessions.parquet"
    )
    dur = df["duration"].dropna()

    p95          = np.percentile(dur, 95)
    pct_over_30m = (dur > 1800).mean() * 100
    N            = len(dur)

    print(f"\n{'─'*50}")
    print(f"{display_name} (mobile): N={N:,}  median={dur.median():.0f}s  P95={p95:.0f}s  >30min={pct_over_30m:.1f}%")

    note_base = f"{display_name} mobile sessions, 2022–2024 (N={N:,.0f})."

    # ── Fig 1: session CDFs (0-5 min and 0-30 min) ───────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.subplots_adjust(wspace=0.35)

    for ax, cap, label in zip(axes, [300, 1800], ["0–5 minutes", "0–30 minutes"]):
        x, y = cdf_xy(dur, cap)
        ax.plot(x, y, color=PALETTE[0], lw=1.8)
        share_in = (dur <= cap).mean()
        ax.axhline(share_in, color='grey', lw=0.8, ls='--')
        ax.text(cap * 0.97, share_in + 0.015,
                f"{share_in:.0%} ≤ {cap//60} min",
                ha='right', va='bottom', fontsize=8, color='grey')
        fmt_min(ax)
        ax.set_xlabel("Session duration (minutes)", fontsize=10)
        ax.set_ylabel("Cumulative share of sessions", fontsize=10)
        ax.set_title(label, fontsize=11, fontweight='bold')
        ax.set_xlim(0, cap)
        ax.set_ylim(0, 1.0)
        spine_clean(ax)

    fig.suptitle(f"CDF of {display_name} session duration — Mobile, 2022–2024",
                 fontsize=12, fontweight='bold', y=1.02)
    fig.text(0.5, -0.04,
             note_base + f" {pct_over_30m:.1f}% of sessions exceed 30 min (excluded from right panel).",
             ha='center', fontsize=8, color='#555555')
    fig.savefig(f"{OUTDIR}/duration_cdf_{slug}_mobile.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved duration_cdf_{slug}_mobile.png")

    # ── Fig 2: concentration curve ────────────────────────────────────────────
    dur_w      = dur.clip(upper=p95)
    total_min  = dur_w.sum()
    sorted_dur = np.sort(dur_w.values)
    n          = len(sorted_dur)
    session_cdf = np.arange(1, n + 1) / n
    minute_cdf  = np.cumsum(sorted_dur) / total_min

    fig2, ax = plt.subplots(figsize=(7, 5))
    ax.plot(sorted_dur, minute_cdf,  color=PALETTE[0], lw=2,        label="Share of total minutes")
    ax.plot(sorted_dur, session_cdf, color=PALETTE[1], lw=2, ls='--', label="Share of sessions (CDF)")

    for ref_s in [60, 300, p95]:
        s_share = (dur_w <= ref_s).mean()
        m_share = dur_w[dur_w <= ref_s].sum() / total_min
        ax.annotate(
            f"{m_share:.0%} of minutes\n({s_share:.0%} of sessions)",
            xy=(ref_s, m_share), xytext=(ref_s + p95 * 0.04, m_share - 0.08),
            fontsize=7.5, color='#444444',
            arrowprops=dict(arrowstyle='->', color='#888888', lw=0.8),
        )

    fmt_min(ax)
    ax.set_xlabel("Session duration threshold (minutes, winsorized at P95)", fontsize=10)
    ax.set_ylabel("Cumulative share", fontsize=10)
    ax.set_title(f"Concentration of session minutes by duration\n{display_name} mobile, 2022–2024",
                 fontsize=11, fontweight='bold')
    ax.set_xlim(0, p95)
    ax.set_ylim(0, 1.0)
    spine_clean(ax)
    ax.legend(fontsize=9, frameon=False)
    fig2.text(0.5, -0.03,
              f"Duration winsorized at P95 ({p95:.0f}s ≈ {p95/60:.1f} min). N={N:,.0f} sessions.",
              ha='center', fontsize=8, color='#555555')
    fig2.savefig(f"{OUTDIR}/duration_concentration_{slug}_mobile.png", dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f"  Saved duration_concentration_{slug}_mobile.png")

    # ── Fig 3: histogram (display up to 15 min) ───────────────────────────────
    HIST_CAP  = 900
    dur_hist  = dur.clip(upper=p95)
    pct_shown = (dur <= HIST_CAP).mean() * 100

    fig3, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(dur_hist[dur_hist <= HIST_CAP], bins=90, color=PALETTE[0],
            edgecolor='white', linewidth=0.3)
    fmt_min(ax)
    ax.set_xlabel("Session duration (minutes)", fontsize=10)
    ax.set_ylabel("Number of sessions", fontsize=10)
    ax.set_title(f"Histogram of {display_name} session duration\nMobile, 2022–2024",
                 fontsize=11, fontweight='bold')
    ax.set_xlim(0, HIST_CAP)
    spine_clean(ax)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
    fig3.text(0.5, -0.03,
              f"Displayed up to 15 min ({pct_shown:.1f}% of sessions). "
              f"Duration winsorized at P95 ({p95:.0f}s) before binning. N={N:,.0f}.",
              ha='center', fontsize=8, color='#555555')
    fig3.savefig(f"{OUTDIR}/duration_histogram_{slug}_mobile.png", dpi=150, bbox_inches='tight')
    plt.close(fig3)
    print(f"  Saved duration_histogram_{slug}_mobile.png")

    # ── Fig 4: CDFs by pages group (truncated at 8 min) ──────────────────────
    if "pages" not in df.columns:
        print(f"  Skipping pages CDF — no 'pages' column in mobile data")
        continue

    CAP_4 = 480
    pages_groups = {
        "1 page":     df["pages"] == 1,
        "2 pages":    df["pages"] == 2,
        "3 pages":    df["pages"] == 3,
        "4–5 pages":  df["pages"].between(4, 5),
        "6–10 pages": df["pages"].between(6, 10),
        "11+ pages":  df["pages"] >= 11,
    }

    fig4, ax = plt.subplots(figsize=(7, 5))
    for (label, mask), color in zip(pages_groups.items(), COLORS6):
        group_dur = dur[mask.values]
        if len(group_dur) < 10:
            continue
        x_c, y_c = cdf_xy(group_dur, CAP_4, denom=len(group_dur))
        ax.plot(x_c, y_c, color=color, lw=1.8, label=f"{label}  (n={len(group_dur):,})")

    fmt_min(ax)
    ax.set_xlabel("Session duration (minutes)", fontsize=10)
    ax.set_ylabel("Cumulative share of sessions", fontsize=10)
    ax.set_title(f"CDF of session duration by number of pages\n{display_name} mobile, 2022–2024",
                 fontsize=11, fontweight='bold')
    ax.set_xlim(0, CAP_4)
    ax.set_ylim(0, 1.0)
    spine_clean(ax)
    ax.legend(fontsize=8.5, frameon=False, title="Pages per session", title_fontsize=9)
    fig4.text(0.5, -0.03,
              "X-axis truncated at 8 min. CDF denominator = all sessions in each pages group.",
              ha='center', fontsize=8, color='#555555')
    fig4.savefig(f"{OUTDIR}/duration_cdf_by_pages_{slug}_mobile.png", dpi=150, bbox_inches='tight')
    plt.close(fig4)
    print(f"  Saved duration_cdf_by_pages_{slug}_mobile.png")
