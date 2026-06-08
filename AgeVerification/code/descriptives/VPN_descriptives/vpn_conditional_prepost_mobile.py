# Author: Matt Brown, assisted by Claude
# Created: 03/13/2026
# Purpose: Mobile version of vpn_conditional_prepost.py — four-bar chart showing
#          P(ever VPN | visited PH in period) for treated/control × pre/post,
#          using mobile machine panel data.

"""
VPN Adoption Conditional on Pornhub Visits: Treated vs. Control, Pre vs. Post (Mobile)
=======================================================================================

Identical logic to vpn_conditional_prepost.py but reads from:
  data/Aggregation/mobile_machine_panel/
  data/ProcessComscore/Intermediate/265/mobile_to_state_lookup.parquet

Outputs go to output/descriptives/vpn_conditional_prepost_mobile/

See vpn_conditional_prepost.py for full figure description and stacking design.

Run from project root:
  python3 code/descriptives/VPN_descriptives/vpn_conditional_prepost_mobile.py
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

warnings.filterwarnings("ignore")

file_dir     = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))
sys.path.insert(0, os.path.join(project_root, "code"))
from plot_style import apply_plot_style, COLOR_PALETTE

apply_plot_style()

# =============================================================================
# CONFIG
# =============================================================================

XXX_SITES = [
    "PORNHUB.COM",
]

VPN_TYPES = ["VPNclean", "allVPN"]

T_MIN, T_MAX    = -16, 8
CUTOFF_DATE     = pd.Timestamp("2024-11-24")
EXCLUDE_STATES  = {"DC", "XX", "ZZ"}
EXCLUDE_TREATED = {"TX"}

SITE_LABELS = {
    "PORNHUB.COM": "Pornhub",
}
VPN_LABELS = {
    "VPNclean": "VPN (clean list)",
    "allVPN":   "All VPN",
}

C_TREATED = COLOR_PALETTE[0]
C_CONTROL = COLOR_PALETTE[2]

data_dir = os.path.join(project_root, "data", "Aggregation", "mobile_machine_panel")
out_base = os.path.join(project_root, "output", "descriptives", "VPN_descriptives", "vpn_conditional_prepost_mobile")
os.makedirs(out_base, exist_ok=True)

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
print(f"  Qualifying ({len(qualifying)}): {qualifying}")
print(f"  Pooled (excl. TX): {qualifying_pooled}")

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

print("Loading machine_week_presence (to identify all panel states)...")
presence_states = (
    pd.read_parquet(os.path.join(data_dir, "machine_week_presence.parquet"),
                    columns=["machine_id"])
    .merge(demos[["machine_id", "state"]], on="machine_id", how="left")
)
all_panel_states = set(
    presence_states["state"].dropna().unique()
) - EXCLUDE_STATES
del presence_states

control_states = all_panel_states - set(treated_states_all)
print(f"  Control states ({len(control_states)}): {sorted(control_states)}")

del demos

# =============================================================================
# HELPER
# =============================================================================

def wavg(vals, weights):
    pairs = [(v, w) for v, w in zip(vals, weights) if not np.isnan(v) and w > 0]
    if not pairs:
        return np.nan
    v_arr, w_arr = zip(*pairs)
    return np.average(v_arr, weights=w_arr)


# =============================================================================
# MAIN LOOP
# =============================================================================

for vpn_type in VPN_TYPES:
    print(f"\n{'='*60}")
    print(f"VPN type: {vpn_type}")
    print(f"{'='*60}")

    vpn_subdir = "" if vpn_type == "VPNclean" else vpn_type
    out_dir = os.path.join(out_base, vpn_subdir)
    os.makedirs(out_dir, exist_ok=True)

    print(f"  Loading {vpn_type} panel (nonzero only)...")
    ever_vpn = set(
        pd.read_parquet(
            os.path.join(data_dir, f"machine_aggregated_{vpn_type}.parquet"),
            columns=["machine_id", "total_duration"],
        )
        .query("total_duration > 0")["machine_id"]
        .unique()
    )
    print(f"  Machines ever visiting {vpn_type}: {len(ever_vpn):,}")

    for xxx_site in XXX_SITES:
        site_label = SITE_LABELS[xxx_site]
        vpn_label  = VPN_LABELS[vpn_type]
        print(f"\n  --- {xxx_site} ---")

        print(f"    Loading {xxx_site} panel (nonzero only)...")
        xxx_pos = (
            pd.read_parquet(
                os.path.join(data_dir, f"machine_aggregated_{xxx_site}.parquet"),
                columns=["machine_id", "week_of_sample", "total_duration"],
            )
            .query("total_duration > 0")[["machine_id", "week_of_sample"]]
            .copy()
        )
        xxx_pos["state"] = xxx_pos["machine_id"].map(machine_state)
        xxx_pos = xxx_pos[xxx_pos["state"].notna()].copy()

        ctrl_xxx = xxx_pos[xxx_pos["state"].isin(control_states)]

        tpre_share,  tpost_share  = {}, {}
        cpre_share,  cpost_share  = {}, {}
        weights = {}

        for state in qualifying_pooled:
            wos        = law_wos[state]
            pre_weeks  = set(range(wos + T_MIN, wos))
            post_weeks = set(range(wos,          wos + T_MAX + 1))

            state_xxx  = xxx_pos[xxx_pos["state"] == state]
            t_pre_ids  = set(state_xxx[state_xxx["week_of_sample"].isin(pre_weeks)] ["machine_id"])
            t_post_ids = set(state_xxx[state_xxx["week_of_sample"].isin(post_weeks)]["machine_id"])

            n_tpre = len(t_pre_ids)
            if n_tpre == 0:
                print(f"    {state}: no treated-pre {site_label} visitors — skipping")
                continue

            c_pre_ids  = set(ctrl_xxx[ctrl_xxx["week_of_sample"].isin(pre_weeks)] ["machine_id"])
            c_post_ids = set(ctrl_xxx[ctrl_xxx["week_of_sample"].isin(post_weeks)]["machine_id"])

            n_tpost = len(t_post_ids)
            n_cpre  = len(c_pre_ids)
            n_cpost = len(c_post_ids)

            print(f"    {state}: t_pre={n_tpre:,}  t_post={n_tpost:,}  "
                  f"c_pre={n_cpre:,}  c_post={n_cpost:,}")

            tpre_share[state]  = len(t_pre_ids  & ever_vpn) / n_tpre
            tpost_share[state] = (len(t_post_ids & ever_vpn) / n_tpost
                                  if n_tpost > 0 else np.nan)
            cpre_share[state]  = (len(c_pre_ids  & ever_vpn) / n_cpre
                                  if n_cpre  > 0 else np.nan)
            cpost_share[state] = (len(c_post_ids & ever_vpn) / n_cpost
                                  if n_cpost > 0 else np.nan)
            weights[state] = n_tpre

        pool_states = [s for s in qualifying_pooled if s in weights]
        w           = [weights[s] for s in pool_states]

        pooled = {
            "tpre":  wavg([tpre_share[s]  for s in pool_states], w),
            "tpost": wavg([tpost_share[s] for s in pool_states], w),
            "cpre":  wavg([cpre_share[s]  for s in pool_states], w),
            "cpost": wavg([cpost_share[s] for s in pool_states], w),
        }

        print(f"    Pooled shares — "
              f"T-pre: {pooled['tpre']:.3%}  T-post: {pooled['tpost']:.3%}  "
              f"C-pre: {pooled['cpre']:.3%}  C-post: {pooled['cpost']:.3%}")

        fig, ax = plt.subplots(figsize=(8, 5))

        x       = np.array([0, 1, 2.6, 3.6])
        keys    = ["tpre", "tpost", "cpre", "cpost"]
        vals    = [pooled[k] for k in keys]
        colors  = [C_TREATED, C_TREATED, C_CONTROL, C_CONTROL]
        alphas  = [0.5,       1.0,       0.5,       1.0      ]
        hatches = ["//",      "",        "//",       ""       ]

        for xi, val, col, alph, hatch in zip(x, vals, colors, alphas, hatches):
            ax.bar(xi, val, color=col, alpha=alph, width=0.8,
                   hatch=hatch, edgecolor="white", linewidth=0.8)
            ax.text(xi, val + 0.002, f"{val:.2%}",
                    ha="center", va="bottom", fontsize=10)

        ax.set_xticks([0.5, 3.1])
        ax.set_xticklabels(
            [f"Treated states\n({site_label} visitors)",
             f"Control states\n({site_label} visitors)"],
            fontsize=11,
        )

        pre_patch  = mpatches.Patch(facecolor="#888888", hatch="//", edgecolor="white",
                                    alpha=0.6, label=f"Pre-law window (t={T_MIN} to −1)")
        post_patch = mpatches.Patch(facecolor="#888888", edgecolor="white",
                                    label=f"Post-law window (t=0 to {T_MAX})")
        ax.legend(handles=[pre_patch, post_patch], fontsize=9, loc="upper right")

        ax.set_ylabel(f"P(ever visited {vpn_label} site)")
        ax.set_title(
            f"P(ever VPN | visited {site_label}) — Treated vs. Control, Pre vs. Post (Mobile)\n"
            f"Pooled {len(pool_states)} treated states (excl. TX), "
            f"weighted by treated-pre cohort size",
            fontsize=11,
        )
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1%}"))
        ax.set_xlim(-0.6, 4.2)
        finite_vals = [v for v in vals if not np.isnan(v)]
        ax.set_ylim(0, max(finite_vals) * 1.3 if finite_vals else 0.1)

        plt.tight_layout()
        tag      = f"{vpn_type}_{xxx_site.replace('.', '_')}"
        out_path = os.path.join(out_dir, f"conditional_prepost_{tag}.png")
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"    Saved: {out_path}")

print("\nDone.")
