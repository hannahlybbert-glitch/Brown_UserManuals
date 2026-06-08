# Author: Matt Brown, assisted by Claude
# Created: 03/13/2026
# Purpose: Mobile version of vpn_descriptives.py — same summary statistics
#          and descriptives on VPN usage, using mobile machine panel data.

"""
VPN Concentration — Descriptive Statistics (Mobile)
====================================================

Identical logic to vpn_descriptives.py but reads from:
  data/Aggregation/mobile_machine_panel/
  data/Aggregation/mobile_to_state_lookup.parquet   (machine_id → state)

Outputs go to output/descriptives/vpn_concentration_mobile/descriptives/

Run from project root:
  python3 code/descriptives/VPN_descriptives/vpn_descriptives_mobile.py
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

file_dir     = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))
sys.path.insert(0, os.path.join(project_root, "code"))
from plot_style import apply_plot_style, COLOR_PALETTE

apply_plot_style()

# =============================================================================
# CONFIG
# =============================================================================

XXX_SITES_ADULT = [
    "PORNHUB.COM",
    "XVIDEOS.COM",
    "XHAMSTER.COM",
    "XNXX.COM",
    "CHATURBATE.COM",
    "other_XXX_sites",
]

VPN_TYPES = ["VPNclean", "allVPN"]

CUTOFF_DATE     = pd.Timestamp("2024-11-24")
EXCLUDE_STATES  = {"DC", "XX", "ZZ"}
EXCLUDE_TREATED = {"TX"}

data_dir = os.path.join(project_root, "data", "Aggregation", "mobile_machine_panel")
out_dir  = os.path.join(project_root, "output", "descriptives", "VPN_descriptives",
                        "vpn_concentration_mobile", "descriptives")
os.makedirs(out_dir, exist_ok=True)

# =============================================================================
# SHARED DATA LOAD
# =============================================================================

print("Loading state laws...")
laws = pd.read_csv(os.path.join(project_root, "raw", "statelaws", "statelaws_dates.csv"))
law_date = {
    row["state"]: pd.to_datetime(row["day_effective"], format="%d%b%Y")
    for _, row in laws.iterrows()
    if pd.notna(row.get("day_effective"))
}
treated_states_all = sorted(law_date.keys())
qualifying = [
    s for s in treated_states_all
    if law_date[s] < CUTOFF_DATE and s not in EXCLUDE_STATES
]
qualifying_pooled = [s for s in qualifying if s not in EXCLUDE_TREATED]

_base = pd.Timestamp("2022-01-01")
law_wos = {
    state: int((law_date[state] - _base).days // 7) + 1
    for state in qualifying
}

print("Loading mobile machine → state lookup...")
demos = (
    pd.read_parquet(
        os.path.join(project_root, "data", "ProcessComscore", "Intermediate",
                     "265", "mobile_to_state_lookup.parquet"),
        columns=["machine_id", "state"],
    )
    .drop_duplicates(subset="machine_id")
    .pipe(lambda d: d[~d["state"].isin(EXCLUDE_STATES)])
)
machine_state = demos.set_index("machine_id")["state"].to_dict()
del demos

print("Loading machine_week_presence...")
presence = pd.read_parquet(os.path.join(data_dir, "machine_week_presence.parquet"))
presence["state"] = presence["machine_id"].map(machine_state)
presence = presence[presence["state"].notna() & ~presence["state"].isin(EXCLUDE_STATES)]

# =============================================================================
# MACHINE GROUPS
# =============================================================================

all_machines     = set(machine_state.keys())
treated_machines = {mid for mid, s in machine_state.items() if s in qualifying}
control_machines = {mid for mid, s in machine_state.items() if s not in treated_states_all}

machine_law_wos  = {mid: law_wos[s]
                    for mid, s in machine_state.items() if s in qualifying}

# =============================================================================
# BUILD "EVER XXX VISITOR" FLAG
# =============================================================================

print("Building XXX visitor set...")
ever_xxx = set()
for site in XXX_SITES_ADULT:
    ids = (
        pd.read_parquet(
            os.path.join(data_dir, f"machine_aggregated_{site}.parquet"),
            columns=["machine_id", "total_duration"],
        )
        .query("total_duration > 0")["machine_id"]
        .unique()
    )
    ever_xxx.update(ids)
ever_xxx = ever_xxx & all_machines
print(f"  Machines that ever visited any adult XXX site: {len(ever_xxx):,}")

# =============================================================================
# LOAD VPN PANELS AND COMPUTE ALL STATS
# =============================================================================

vpn_stats = {}

for vpn_type in VPN_TYPES:
    print(f"\nLoading {vpn_type}...")
    vpn = (
        pd.read_parquet(
            os.path.join(data_dir, f"machine_aggregated_{vpn_type}.parquet"),
            columns=["machine_id", "week_of_sample", "total_duration"],
        )
        .query("total_duration > 0")
        .copy()
    )
    vpn["state"] = vpn["machine_id"].map(machine_state)
    vpn = vpn[vpn["state"].notna()].copy()

    ever_vpn = set(vpn["machine_id"].unique())

    vpn_treated = vpn[vpn["machine_id"].isin(treated_machines)].copy()
    vpn_treated["law_wos"] = vpn_treated["machine_id"].map(machine_law_wos)
    vpn_pre_ids  = set(vpn_treated[vpn_treated["week_of_sample"] <  vpn_treated["law_wos"]]["machine_id"])
    vpn_post_ids = set(vpn_treated[vpn_treated["week_of_sample"] >= vpn_treated["law_wos"]]["machine_id"])
    vpn_both_ids = vpn_pre_ids & vpn_post_ids
    vpn_pre_only_ids  = vpn_pre_ids  - vpn_post_ids
    vpn_post_only_ids = vpn_post_ids - vpn_pre_ids

    freq = vpn.groupby("machine_id")["week_of_sample"].nunique()
    freq_treated = freq[freq.index.isin(treated_machines)]
    freq_control = freq[freq.index.isin(control_machines)]

    dur_all     = vpn["total_duration"] / 60
    dur_treated = vpn.loc[vpn["machine_id"].isin(treated_machines), "total_duration"] / 60
    dur_control = vpn.loc[vpn["machine_id"].isin(control_machines), "total_duration"] / 60

    vpn_stats[vpn_type] = {
        "ever_vpn":           ever_vpn,
        "vpn_pre_ids":        vpn_pre_ids,
        "vpn_post_ids":       vpn_post_ids,
        "vpn_both_ids":       vpn_both_ids,
        "vpn_pre_only_ids":   vpn_pre_only_ids,
        "vpn_post_only_ids":  vpn_post_only_ids,
        "freq_all":           freq,
        "freq_treated":       freq_treated,
        "freq_control":       freq_control,
        "dur_all":            dur_all,
        "dur_treated":        dur_treated,
        "dur_control":        dur_control,
    }

# =============================================================================
# HELPER — format percentage
# =============================================================================

def pct(n, d):
    return f"{100 * n / d:.2f}%" if d > 0 else "  N/A "

def row(label, clean_n, clean_d, all_n, all_d, width=38):
    return (f"  {label:<{width}}"
            f"{pct(clean_n, clean_d):>10}"
            f"{pct(all_n,   all_d):>10}")

# =============================================================================
# PRINT DESCRIPTIVES
# =============================================================================

W = 60
s = vpn_stats

print("\n")
print("=" * W)
print("  VPN DESCRIPTIVE STATISTICS — AgeVerification Sample (MOBILE)")
print("=" * W)

print("\nSAMPLE OVERVIEW")
print(f"  {'Total unique machines in panel:':<42} {len(all_machines):>10,}")
print(f"  {'Treated state machines (incl. TX):':<42} {len(treated_machines):>10,}")
print(f"  {'Control state machines (no law):':<42} {len(control_machines):>10,}")
other_n = len(all_machines) - len(treated_machines) - len(control_machines)
print(f"  {'Other (law after sample cutoff, etc.):':<42} {other_n:>10,}")
print(f"  {'Ever visited any adult XXX site:':<42} {len(ever_xxx):>10,}")
print(f"    {'  of which in treated states (incl. TX):':<40} {len(ever_xxx & treated_machines):>10,}")
print(f"    {'  of which in control states:':<40} {len(ever_xxx & control_machines):>10,}")

print("\nVPN SITE PREVALENCE — ALL MACHINES")
print(f"  {'':38}{'VPNclean':>10}{'allVPN':>10}")
print(f"  {'-'*58}")
cv, av = s["VPNclean"]["ever_vpn"], s["allVPN"]["ever_vpn"]
print(row("All machines",                      len(cv),                      len(all_machines),
                                               len(av),                      len(all_machines)))
print(row("Treated states (incl. TX)",         len(cv & treated_machines),   len(treated_machines),
                                               len(av & treated_machines),   len(treated_machines)))
print(row("Control states (no law)",           len(cv & control_machines),   len(control_machines),
                                               len(av & control_machines),   len(control_machines)))

print("\nVPN PREVALENCE — PRE vs POST LAW (treated states incl. TX)")
print(f"  {'':38}{'VPNclean':>10}{'allVPN':>10}")
print(f"  {'-'*58}")
n_treated = len(treated_machines)
print(row("Any visit in full sample",
          len(cv & treated_machines), n_treated,
          len(av & treated_machines), n_treated))
print(row("Pre-law visits only",
          len(s["VPNclean"]["vpn_pre_only_ids"]),  n_treated,
          len(s["allVPN"]["vpn_pre_only_ids"]),     n_treated))
print(row("Post-law visits only",
          len(s["VPNclean"]["vpn_post_only_ids"]), n_treated,
          len(s["allVPN"]["vpn_post_only_ids"]),    n_treated))
print(row("Both pre and post",
          len(s["VPNclean"]["vpn_both_ids"]),      n_treated,
          len(s["allVPN"]["vpn_both_ids"]),         n_treated))
print(f"\n  Note: pre/post splits sum to 'any visit'; a machine can appear in")
print(f"  pre-only, post-only, or both — not mutually exclusive with 'any'.")

print("\nVPN PREVALENCE BY XXX VISITOR STATUS")
print(f"  {'':38}{'VPNclean':>10}{'allVPN':>10}")
print(f"  {'-'*58}")
non_xxx = all_machines - ever_xxx
print(row("XXX visitors (any adult site)",
          len(cv & ever_xxx), len(ever_xxx),
          len(av & ever_xxx), len(ever_xxx)))
print(row("Non-XXX visitors",
          len(cv & non_xxx),  len(non_xxx),
          len(av & non_xxx),  len(non_xxx)))

print("\nCROSS-TAB: TREATED × XXX VISITOR")
print(f"  {'':38}{'VPNclean':>10}{'allVPN':>10}")
print(f"  {'-'*58}")
t_xxx  = treated_machines & ever_xxx
t_nxxx = treated_machines - ever_xxx
c_xxx  = control_machines & ever_xxx
c_nxxx = control_machines - ever_xxx
print(row("Treated + XXX visitor",   len(cv & t_xxx),  len(t_xxx),  len(av & t_xxx),  len(t_xxx)))
print(row("Treated + non-XXX",       len(cv & t_nxxx), len(t_nxxx), len(av & t_nxxx), len(t_nxxx)))
print(row("Control + XXX visitor",   len(cv & c_xxx),  len(c_xxx),  len(av & c_xxx),  len(c_xxx)))
print(row("Control + non-XXX",       len(cv & c_nxxx), len(c_nxxx), len(av & c_nxxx), len(c_nxxx)))

print("\nVPN VISIT FREQUENCY (among machines that ever visited VPN)")
print(f"  {'':38}{'VPNclean':>10}{'allVPN':>10}")
print(f"  {'-'*58}")

for label, key in [("All VPN visitors", "freq_all"),
                   ("  Treated states", "freq_treated"),
                   ("  Control states", "freq_control")]:
    fc = s["VPNclean"][key]
    fa = s["allVPN"][key]
    print(f"\n  {label}")
    print(f"  {'  N machines:':<38}{len(fc):>10,}{len(fa):>10,}")
    print(f"  {'  Median weeks:':<38}{fc.median():>9.1f}{fa.median():>10.1f}")
    print(f"  {'  Mean weeks:':<38}{fc.mean():>9.1f}{fa.mean():>10.1f}")
    print(f"  {'  75th percentile:':<38}{fc.quantile(0.75):>9.1f}{fa.quantile(0.75):>10.1f}")
    print(f"  {'  90th percentile:':<38}{fc.quantile(0.90):>9.1f}{fa.quantile(0.90):>10.1f}")
    pct_1c  = (fc == 1).mean()
    pct_1a  = (fa == 1).mean()
    pct_25c = ((fc >= 2) & (fc <= 5)).mean()
    pct_25a = ((fa >= 2) & (fa <= 5)).mean()
    pct_6c  = (fc >= 6).mean()
    pct_6a  = (fa >= 6).mean()
    print(f"  {'  1 week only:':<38}{pct_1c:>9.1%}{pct_1a:>10.1%}")
    print(f"  {'  2–5 weeks:':<38}{pct_25c:>9.1%}{pct_25a:>10.1%}")
    print(f"  {'  6+ weeks:':<38}{pct_6c:>9.1%}{pct_6a:>10.1%}")

# =============================================================================
# HISTOGRAM — VPN visit frequency distribution
# =============================================================================

print("\nGenerating frequency histogram...")

CAP = 15

fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

for ax, vpn_type in zip(axes, VPN_TYPES):
    freq_all  = s[vpn_type]["freq_all"]
    freq_t    = s[vpn_type]["freq_treated"]
    freq_c    = s[vpn_type]["freq_control"]

    def cap_series(ser):
        return ser.clip(upper=CAP)

    bins = list(range(1, CAP + 2))

    counts_t, _ = np.histogram(cap_series(freq_t), bins=bins)
    counts_c, _ = np.histogram(cap_series(freq_c), bins=bins)

    x = np.arange(1, CAP + 1)
    width = 0.4

    ax.bar(x - width/2, counts_t / len(freq_t),
           width=width, color=COLOR_PALETTE[0], alpha=0.85, label="Treated (incl. TX)")
    ax.bar(x + width/2, counts_c / len(freq_c),
           width=width, color=COLOR_PALETTE[2], alpha=0.85, label="Control")

    xlabels = [str(i) for i in range(1, CAP)] + [f"{CAP}+"]
    ax.set_xticks(x)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel("Distinct weeks with VPN site visit")
    ax.set_ylabel("Share of VPN visitors")
    ax.set_title(f"{vpn_type}: VPN visit frequency — Mobile")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1%}"))
    ax.legend(fontsize=9)

plt.suptitle("How often do VPN site visitors actually visit VPN sites? (Mobile)",
             fontsize=13, y=1.01)
plt.tight_layout()

hist_path = os.path.join(out_dir, "vpn_frequency_histogram.png")
fig.savefig(hist_path, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"  Histogram saved: {hist_path}")

# =============================================================================
# HISTOGRAM — VPN session duration distribution
# =============================================================================

# ------------------------------------------------------------------
print("\nVPN SESSION DURATION (minutes per machine-week, among VPN visitor-weeks)")
print(f"  {'':38}{'VPNclean':>10}{'allVPN':>10}")
print(f"  {'-'*58}")

for label, key in [("All VPN visitor-weeks", "dur_all"),
                   ("  Treated states",      "dur_treated"),
                   ("  Control states",      "dur_control")]:
    dc = s["VPNclean"][key]
    da = s["allVPN"][key]
    print(f"\n  {label}")
    print(f"  {'  N machine-weeks:':<38}{len(dc):>10,}{len(da):>10,}")
    print(f"  {'  Median (min):':<38}{dc.median():>9.1f}{da.median():>10.1f}")
    print(f"  {'  Mean (min):':<38}{dc.mean():>9.1f}{da.mean():>10.1f}")
    print(f"  {'  75th percentile (min):':<38}{dc.quantile(0.75):>9.1f}{da.quantile(0.75):>10.1f}")
    print(f"  {'  90th percentile (min):':<38}{dc.quantile(0.90):>9.1f}{da.quantile(0.90):>10.1f}")
    pct_u5c  = (dc <  5).mean()
    pct_u5a  = (da <  5).mean()
    pct_530c = ((dc >= 5) & (dc < 30)).mean()
    pct_530a = ((da >= 5) & (da < 30)).mean()
    pct_30c  = (dc >= 30).mean()
    pct_30a  = (da >= 30).mean()
    print(f"  {'  < 5 min:':<38}{pct_u5c:>9.1%}{pct_u5a:>10.1%}")
    print(f"  {'  5–30 min:':<38}{pct_530c:>9.1%}{pct_530a:>10.1%}")
    print(f"  {'  30+ min:':<38}{pct_30c:>9.1%}{pct_30a:>10.1%}")

print("\nGenerating session duration histogram...")

DUR_CAP    = 60
bin_edges  = list(range(0, 11)) + [20, 30, 40, 50, 60, DUR_CAP + 1]
bin_labels = (
    [f"{i}–{i+1}" for i in range(0, 10)]
    + ["10–20", "20–30", "30–40", "40–50", "50–60", "60+"]
)

fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

for ax, vpn_type in zip(axes, VPN_TYPES):
    dur_t = s[vpn_type]["dur_treated"].clip(upper=DUR_CAP)
    dur_c = s[vpn_type]["dur_control"].clip(upper=DUR_CAP)

    counts_t, _ = np.histogram(dur_t, bins=bin_edges)
    counts_c, _ = np.histogram(dur_c, bins=bin_edges)

    x     = np.arange(len(bin_labels))
    width = 0.4

    ax.bar(x - width/2, counts_t / len(dur_t),
           width=width, color=COLOR_PALETTE[0], alpha=0.85, label="Treated (excl. TX)")
    ax.bar(x + width/2, counts_c / len(dur_c),
           width=width, color=COLOR_PALETTE[2], alpha=0.85, label="Control")

    ax.set_xticks(x)
    ax.set_xticklabels(bin_labels, rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Total time on VPN site that week (minutes)")
    ax.set_ylabel("Share of VPN visitor-weeks")
    ax.set_title(f"{vpn_type}: VPN session duration — Mobile")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1%}"))
    ax.legend(fontsize=9)

plt.suptitle("How long do machines spend on VPN sites per week? (Mobile)",
             fontsize=13, y=1.01)
plt.tight_layout()

dur_hist_path = os.path.join(out_dir, "vpn_duration_histogram.png")
fig.savefig(dur_hist_path, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"  Histogram saved: {dur_hist_path}")

print("\nDone.")
