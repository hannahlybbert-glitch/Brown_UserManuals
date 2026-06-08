"""
Pornhub session duration (pre-law period only, Jan-Mar 2022).

Figure 1: CDF of sessions (two panels, 0-5 min and 0-30 min).
Figure 2: Concentration curve — cumulative share of total minutes vs. duration threshold,
          overlaid with session CDF. Duration winsorized at 95th percentile.
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

PALETTE = ['#8c1515', '#0B3954', '#9a8873', '#b4adea', '#aceb98']
os.makedirs("output/descriptives/pages_assessment", exist_ok=True)

df = pd.read_parquet("data/ProcessComscore/merged_cat_session_files/pornhub_sessions.parquet")
dur = df["duration"].dropna()

p95 = np.percentile(dur, 95)
p99 = np.percentile(dur, 99)
pct_over_30m = (dur > 1800).mean() * 100

print(f"N sessions: {len(dur):,}")
print(f"Median: {dur.median():.0f}s  P95: {p95:.0f}s  P99: {p99:.0f}s")
print(f"% > 30 min: {pct_over_30m:.1f}%")

# ── Figure 1: session CDFs ──────────────────────────────────────────────────
def cdf_xy(series, cap):
    s = np.sort(series[series <= cap].values)
    y = np.arange(1, len(s) + 1) / len(series)
    return s, y

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
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v/60:.0f}"))
    ax.set_xlabel("Session duration (minutes)", fontsize=10)
    ax.set_ylabel("Cumulative share of sessions", fontsize=10)
    ax.set_title(label, fontsize=11, fontweight='bold')
    ax.set_xlim(0, cap)
    ax.set_ylim(0, 1.0)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(which='minor', bottom=False, left=False)

fig.text(0.5, -0.04,
         f"Pornhub desktop sessions, Jan–Mar 2022 (N={len(dur):,.0f}). "
         f"{pct_over_30m:.1f}% of sessions exceed 30 min and are excluded from right panel.",
         ha='center', fontsize=8, color='#555555')

fig.savefig("output/descriptives/pages_assessment/duration_cdf_pornhub.png",
            dpi=150, bbox_inches='tight')
print("Saved → duration_cdf_pornhub.png")

# ── Figure 2: concentration curve ──────────────────────────────────────────
# Winsorize at p95
dur_w = dur.clip(upper=p95)
total_min = dur_w.sum()

# Sort and build both curves over the winsorized support
sorted_dur = np.sort(dur_w.values)
n = len(sorted_dur)

# Session CDF: share of sessions with duration <= t
session_cdf = np.arange(1, n + 1) / n

# Minutes CDF: cumulative minutes from shortest sessions / total minutes
minute_cdf = np.cumsum(sorted_dur) / total_min

fig2, ax = plt.subplots(figsize=(7, 5))

ax.plot(sorted_dur, minute_cdf,  color=PALETTE[0], lw=2,   label="Share of total minutes")
ax.plot(sorted_dur, session_cdf, color=PALETTE[1], lw=2, ls='--', label="Share of sessions (CDF)")

# annotate the gap at a few reference points
for ref_s, ref_label in [(60, "1 min"), (300, "5 min"), (p95, "P95")]:
    s_share = (dur_w <= ref_s).mean()
    m_share = dur_w[dur_w <= ref_s].sum() / total_min
    ax.annotate(
        f"{m_share:.0%} of minutes\n({s_share:.0%} of sessions)",
        xy=(ref_s, m_share), xytext=(ref_s + p95 * 0.04, m_share - 0.08),
        fontsize=7.5, color='#444444',
        arrowprops=dict(arrowstyle='->', color='#888888', lw=0.8),
    )

ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v/60:.0f}"))
ax.set_xlabel("Session duration threshold (minutes, winsorized at P95)", fontsize=10)
ax.set_ylabel("Cumulative share", fontsize=10)
ax.set_title("Concentration of session minutes by duration\nPornhub desktop, Jan–Mar 2022",
             fontsize=11, fontweight='bold')
ax.set_xlim(0, p95)
ax.set_ylim(0, 1.0)
ax.spines[['top', 'right']].set_visible(False)
ax.tick_params(which='minor', bottom=False, left=False)
ax.legend(fontsize=9, frameon=False)

fig2.text(0.5, -0.03,
          f"Duration winsorized at P95 ({p95:.0f}s ≈ {p95/60:.0f} min). "
          f"N={len(dur):,.0f} sessions.",
          ha='center', fontsize=8, color='#555555')

fig2.savefig("output/descriptives/pages_assessment/duration_concentration_pornhub.png",
             dpi=150, bbox_inches='tight')
print("Saved → duration_concentration_pornhub.png")

# ── Figure 3: histogram of session duration ─────────────────────────────────
# Truncate display at 15 min; winsorize at p95 for the histogram bins
HIST_CAP = 900   # 15 min display cap
dur_hist = dur.clip(upper=p95)
pct_shown = (dur <= HIST_CAP).mean() * 100

fig3, ax = plt.subplots(figsize=(7, 4.5))
ax.hist(dur_hist[dur_hist <= HIST_CAP], bins=90, color=PALETTE[0],
        edgecolor='white', linewidth=0.3)
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v/60:.0f}"))
ax.set_xlabel("Session duration (minutes)", fontsize=10)
ax.set_ylabel("Number of sessions", fontsize=10)
ax.set_title("Histogram of Pornhub session duration\nDesktop, Jan–Mar 2022",
             fontsize=11, fontweight='bold')
ax.set_xlim(0, HIST_CAP)
ax.spines[['top', 'right']].set_visible(False)
ax.tick_params(which='minor', bottom=False, left=False)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))

fig3.text(0.5, -0.03,
          f"Displayed up to 15 min ({pct_shown:.1f}% of sessions). "
          f"Duration winsorized at P95 ({p95:.0f}s) before binning. N={len(dur):,.0f}.",
          ha='center', fontsize=8, color='#555555')

fig3.savefig("output/descriptives/pages_assessment/duration_histogram_pornhub.png",
             dpi=150, bbox_inches='tight')
print("Saved → duration_histogram_pornhub.png")

# ── Figure 4: CDFs by number of pages ───────────────────────────────────────
CAP_4 = 480   # 8 min

pages_groups = {
    "1 page":   df["pages"] == 1,
    "2 pages":  df["pages"] == 2,
    "3 pages":  df["pages"] == 3,
    "4–5 pages":  df["pages"].between(4, 5),
    "6–10 pages": df["pages"].between(6, 10),
    "11+ pages":  df["pages"] >= 11,
}

# Extend palette to 6 colors
colors6 = PALETTE + ['#5c7a5c']

fig4, ax = plt.subplots(figsize=(7, 5))

for (label, mask), color in zip(pages_groups.items(), colors6):
    group_dur = dur[mask.values]
    within = group_dur[group_dur <= CAP_4]
    x = np.sort(within.values)
    # CDF denominator = full group size (so curve tops out at share within cap)
    y = np.arange(1, len(x) + 1) / len(group_dur)
    n = len(group_dur)
    ax.plot(x, y, color=color, lw=1.8, label=f"{label}  (n={n:,})")

ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v/60:.0f}"))
ax.set_xlabel("Session duration (minutes)", fontsize=10)
ax.set_ylabel("Cumulative share of sessions", fontsize=10)
ax.set_title("CDF of session duration by number of pages\nPornhub desktop, Jan–Mar 2022",
             fontsize=11, fontweight='bold')
ax.set_xlim(0, CAP_4)
ax.set_ylim(0, 1.0)
ax.spines[['top', 'right']].set_visible(False)
ax.tick_params(which='minor', bottom=False, left=False)
ax.legend(fontsize=8.5, frameon=False, title="Pages per session", title_fontsize=9)

fig4.text(0.5, -0.03,
          "X-axis truncated at 8 min. CDF denominator = all sessions in each pages group.",
          ha='center', fontsize=8, color='#555555')

fig4.savefig("output/descriptives/pages_assessment/duration_cdf_by_pages_pornhub.png",
             dpi=150, bbox_inches='tight')
print("Saved → duration_cdf_by_pages_pornhub.png")
