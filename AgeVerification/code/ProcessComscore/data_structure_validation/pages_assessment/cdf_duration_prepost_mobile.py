"""
Session duration CDFs and concentration curves for mobile sessions:
  1. Full-data CDFs (all years, all mobile sessions)
  2. Pre vs. post law passage for treated states (±90-day window around each state's law date)

Sites: Pornhub, Xvideos, XNXX
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import timedelta

PALETTE = ['#8c1515', '#0B3954', '#9a8873', '#b4adea', '#aceb98']
COLORS6 = PALETTE + ['#5c7a5c']
OUTDIR  = "output/descriptives/pages_assessment"
os.makedirs(OUTDIR, exist_ok=True)

WINDOW_DAYS = 90

SITES = [
    ("pornhub", "Pornhub"),
    ("xvideos", "Xvideos"),
    ("xnxx",    "XNXX"),
]

def spine_clean(ax):
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(which='minor', bottom=False, left=False)

def fmt_min(ax):
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v/60:.0f}"))

def cdf_xy(series, cap):
    s = np.sort(series[series <= cap].values)
    y = np.arange(1, len(s) + 1) / len(series)
    return s, y

def concentration_xy(series, p95):
    dur_w      = series.clip(upper=p95)
    total      = dur_w.sum()
    sorted_dur = np.sort(dur_w.values)
    session_cdf = np.arange(1, len(sorted_dur) + 1) / len(sorted_dur)
    minute_cdf  = np.cumsum(sorted_dur) / total
    return sorted_dur, session_cdf, minute_cdf, p95

def pages_groups(df, dur):
    return {
        "1 page":     dur[df["pages"].eq(1).values],
        "2 pages":    dur[df["pages"].eq(2).values],
        "3 pages":    dur[df["pages"].eq(3).values],
        "4–5 pages":  dur[df["pages"].between(4, 5).values],
        "6–10 pages": dur[df["pages"].between(6, 10).values],
        "11+ pages":  dur[df["pages"].ge(11).values],
    }


for slug, display_name in SITES:
    print(f"\n{'─'*55}\n{display_name} (mobile)")
    df = pd.read_parquet(
        f"data/ProcessComscore/merged_cat_session_files/mobile_{slug}_sessions.parquet"
    )
    dur_all = df["duration"].dropna()
    p95_all = np.percentile(dur_all, 95)
    N_all   = len(dur_all)

    note_base = f"{display_name} mobile, 2022–2024 (N={N_all:,.0f})."

    # ── 1. Full-data session CDF (two panels) ────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.subplots_adjust(wspace=0.35)
    for ax, cap, label in zip(axes, [300, 1800], ["0–5 minutes", "0–30 minutes"]):
        x, y = cdf_xy(dur_all, cap)
        ax.plot(x, y, color=PALETTE[0], lw=1.8)
        share_in = (dur_all <= cap).mean()
        ax.axhline(share_in, color='grey', lw=0.8, ls='--')
        ax.text(cap * 0.97, share_in + 0.015,
                f"{share_in:.0%} ≤ {cap//60} min",
                ha='right', va='bottom', fontsize=8, color='grey')
        fmt_min(ax); spine_clean(ax)
        ax.set_xlabel("Session duration (minutes)", fontsize=10)
        ax.set_ylabel("Cumulative share of sessions", fontsize=10)
        ax.set_title(label, fontsize=11, fontweight='bold')
        ax.set_xlim(0, cap); ax.set_ylim(0, 1.0)
    fig.suptitle(f"CDF of {display_name} session duration — Mobile, 2022–2024",
                 fontsize=12, fontweight='bold', y=1.02)
    pct_over_30m = (dur_all > 1800).mean() * 100
    fig.text(0.5, -0.04, note_base +
             f" {pct_over_30m:.1f}% of sessions exceed 30 min (excluded from right panel).",
             ha='center', fontsize=8, color='#555555')
    fig.savefig(f"{OUTDIR}/full_duration_cdf_{slug}_mobile.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved full_duration_cdf_{slug}_mobile.png")

    # ── 2. Full-data concentration curve ─────────────────────────────────────
    sorted_dur, session_cdf, minute_cdf, p95 = concentration_xy(dur_all, p95_all)
    fig2, ax = plt.subplots(figsize=(7, 5))
    ax.plot(sorted_dur, minute_cdf,  color=PALETTE[0], lw=2,        label="Share of total minutes")
    ax.plot(sorted_dur, session_cdf, color=PALETTE[1], lw=2, ls='--', label="Share of sessions (CDF)")
    for ref_s in [60, 300, p95]:
        dur_w  = dur_all.clip(upper=p95)
        s_shr  = (dur_w <= ref_s).mean()
        m_shr  = dur_w[dur_w <= ref_s].sum() / dur_w.sum()
        ax.annotate(f"{m_shr:.0%} of minutes\n({s_shr:.0%} of sessions)",
                    xy=(ref_s, m_shr), xytext=(ref_s + p95 * 0.04, m_shr - 0.08),
                    fontsize=7.5, color='#444444',
                    arrowprops=dict(arrowstyle='->', color='#888888', lw=0.8))
    fmt_min(ax); spine_clean(ax)
    ax.set_xlabel("Session duration threshold (minutes, winsorized at P95)", fontsize=10)
    ax.set_ylabel("Cumulative share", fontsize=10)
    ax.set_title(f"Concentration of session minutes — {display_name}\nMobile, 2022–2024",
                 fontsize=11, fontweight='bold')
    ax.set_xlim(0, p95); ax.set_ylim(0, 1.0)
    ax.legend(fontsize=9, frameon=False)
    fig2.text(0.5, -0.03,
              f"Duration winsorized at P95 ({p95:.0f}s ≈ {p95/60:.1f} min). {note_base}",
              ha='center', fontsize=8, color='#555555')
    fig2.savefig(f"{OUTDIR}/full_duration_concentration_{slug}_mobile.png", dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f"  Saved full_duration_concentration_{slug}_mobile.png")

    # ── 3. Full-data CDF by pages ─────────────────────────────────────────────
    if "pages" in df.columns:
        CAP_PG = 480
        fig3, ax = plt.subplots(figsize=(7, 5))
        for (label, series), color in zip(pages_groups(df, dur_all).items(), COLORS6):
            if len(series) < 10:
                continue
            x_c, y_c = cdf_xy(series, CAP_PG)
            ax.plot(x_c, y_c, color=color, lw=1.8, label=f"{label}  (n={len(series):,})")
        fmt_min(ax); spine_clean(ax)
        ax.set_xlabel("Session duration (minutes)", fontsize=10)
        ax.set_ylabel("Cumulative share of sessions", fontsize=10)
        ax.set_title(f"CDF by pages — {display_name}\nMobile, 2022–2024",
                     fontsize=11, fontweight='bold')
        ax.set_xlim(0, CAP_PG); ax.set_ylim(0, 1.0)
        ax.legend(fontsize=8.5, frameon=False, title="Pages per session", title_fontsize=9)
        fig3.text(0.5, -0.03, f"X-axis truncated at 8 min. {note_base}",
                  ha='center', fontsize=8, color='#555555')
        fig3.savefig(f"{OUTDIR}/full_duration_cdf_by_pages_{slug}_mobile.png", dpi=150, bbox_inches='tight')
        plt.close(fig3)
        print(f"  Saved full_duration_cdf_by_pages_{slug}_mobile.png")

    # ── 4. Pre vs. post — treated states ±90 days around law passage ──────────
    law_dates = (df[df["post"] == 1]
                 .groupby("state")["date"]
                 .min()
                 .rename("law_date"))

    treated_df = df[df["treated"] == 1].copy()
    treated_df = treated_df.join(law_dates, on="state")

    delta     = pd.to_timedelta(WINDOW_DAYS, unit='D')
    pre_mask  = (treated_df["date"] >= treated_df["law_date"] - delta) & \
                (treated_df["date"] <  treated_df["law_date"])
    post_mask = (treated_df["date"] >= treated_df["law_date"]) & \
                (treated_df["date"] <  treated_df["law_date"] + delta)

    dur_pre  = treated_df.loc[pre_mask,  "duration"].dropna()
    dur_post = treated_df.loc[post_mask, "duration"].dropna()
    dur_ctrl = df.loc[df["treated"] == 0, "duration"].dropna()

    print(f"  Pre: N={len(dur_pre):,}   Post: N={len(dur_post):,}   Control: N={len(dur_ctrl):,}")

    p95_pre = np.percentile(dur_pre, 95) if len(dur_pre) > 0 else p95_all

    # 4a. CDF pre/post (two panels)
    fig4, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    fig4.subplots_adjust(wspace=0.35)
    groups_pp = [
        (dur_pre,  PALETTE[1], f"Pre-law  (n={len(dur_pre):,})"),
        (dur_post, PALETTE[0], f"Post-law (n={len(dur_post):,})"),
        (dur_ctrl, PALETTE[2], f"Control states (n={len(dur_ctrl):,})"),
    ]
    for ax, cap, panel_label in zip(axes, [300, 1800], ["0–5 minutes", "0–30 minutes"]):
        for dur_g, color, label in groups_pp:
            if len(dur_g) < 10:
                continue
            x_c, y_c = cdf_xy(dur_g, cap)
            ax.plot(x_c, y_c, color=color, lw=1.8, label=label)
        fmt_min(ax); spine_clean(ax)
        ax.set_xlabel("Session duration (minutes)", fontsize=10)
        ax.set_ylabel("Cumulative share of sessions", fontsize=10)
        ax.set_title(panel_label, fontsize=11, fontweight='bold')
        ax.set_xlim(0, cap); ax.set_ylim(0, 1.0)
    axes[0].legend(fontsize=8, frameon=False)
    fig4.suptitle(
        f"CDF of {display_name} session duration — Mobile, treated states pre vs. post law",
        fontsize=12, fontweight='bold', y=1.02)
    fig4.text(0.5, -0.04,
              f"±{WINDOW_DAYS}-day window around each state's law date. "
              f"Control states shown over full 2022–2024 period.",
              ha='center', fontsize=8, color='#555555')
    fig4.savefig(f"{OUTDIR}/prepost_duration_cdf_{slug}_mobile.png", dpi=150, bbox_inches='tight')
    plt.close(fig4)
    print(f"  Saved prepost_duration_cdf_{slug}_mobile.png")

    # 4b. Concentration curves pre/post
    fig5, ax = plt.subplots(figsize=(7, 5))
    for dur_g, color, label, ls in [
        (dur_pre,  PALETTE[1], "Pre-law (treated)",  '-'),
        (dur_post, PALETTE[0], "Post-law (treated)", '-'),
        (dur_ctrl, PALETTE[2], "Control states",     '--'),
    ]:
        if len(dur_g) < 10:
            continue
        dur_w    = dur_g.clip(upper=p95_pre)
        total    = dur_w.sum()
        sd       = np.sort(dur_w.values)
        sess_cdf = np.arange(1, len(sd) + 1) / len(sd)
        min_cdf  = np.cumsum(sd) / total
        ax.plot(sd, min_cdf,  color=color, lw=2,   ls=ls, label=f"{label} — minutes")
        ax.plot(sd, sess_cdf, color=color, lw=1.2, ls=':', alpha=0.6, label=f"{label} — sessions")

    fmt_min(ax); spine_clean(ax)
    ax.set_xlabel(f"Session duration threshold (minutes, winsorized at pre-law P95={p95_pre:.0f}s)",
                  fontsize=9)
    ax.set_ylabel("Cumulative share", fontsize=10)
    ax.set_title(f"Concentration curves — {display_name}\nMobile, treated states pre vs. post law",
                 fontsize=11, fontweight='bold')
    ax.set_xlim(0, p95_pre); ax.set_ylim(0, 1.0)
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0],[0], color=PALETTE[1], lw=2,   label="Pre-law (treated)"),
        Line2D([0],[0], color=PALETTE[0], lw=2,   label="Post-law (treated)"),
        Line2D([0],[0], color=PALETTE[2], lw=2, ls='--', label="Control states"),
        Line2D([0],[0], color='grey',     lw=2,   label="Solid = minutes share"),
        Line2D([0],[0], color='grey',     lw=1.2, ls=':', label="Dotted = sessions share"),
    ]
    ax.legend(handles=handles, fontsize=8, frameon=False)
    fig5.text(0.5, -0.03,
              f"±{WINDOW_DAYS}-day window around each state's law date. Winsorized at pre-law P95.",
              ha='center', fontsize=8, color='#555555')
    fig5.savefig(f"{OUTDIR}/prepost_concentration_{slug}_mobile.png", dpi=150, bbox_inches='tight')
    plt.close(fig5)
    print(f"  Saved prepost_concentration_{slug}_mobile.png")
