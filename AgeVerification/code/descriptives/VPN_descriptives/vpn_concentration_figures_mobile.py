# Author: Matt Brown, assisted by Claude
# Created: 03/13/2026
# Purpose: Mobile version of vpn_concentration_figures.py — three complementary
#          figures examining VPN usage concentration among post-treatment XXX
#          site visitors in treated states, using mobile machine panel data.

"""
VPN Concentration Among Post-Treatment XXX Visitors (Mobile)
=============================================================

Identical logic to vpn_concentration_figures.py but reads from:
  data/Aggregation/mobile_machine_panel/
  data/ProcessComscore/Intermediate/265/mobile_to_state_lookup.parquet

Outputs go to output/descriptives/vpn_concentration_mobile/

See vpn_concentration_figures.py for full figure descriptions.

Run from project root:
  python3 code/descriptives/VPN_descriptives/vpn_concentration_figures_mobile.py
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

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
    "PORNHUB.COM":     "Pornhub",
    "XVIDEOS.COM":     "xVideos",
    "XHAMSTER.COM":    "xHamster",
    "XNXX.COM":        "XNXX",
    "CHATURBATE.COM":  "Chaturbate",
    "other_XXX_sites": "Other XXX",
    "all_other_sites": "All other sites",
}
VPN_LABELS = {
    "VPNclean": "VPN (clean list)",
    "allVPN":   "All VPN",
}

C_POST  = COLOR_PALETTE[0]
C_PRE   = COLOR_PALETTE[1]
C_ALL   = COLOR_PALETTE[2]
C_STATE = "#BBBBBB"

data_dir = os.path.join(project_root, "data", "Aggregation", "mobile_machine_panel")
out_base = os.path.join(project_root, "output", "descriptives", "VPN_descriptives", "vpn_concentration_mobile")

# =============================================================================
# SHARED DATA LOAD
# =============================================================================

print("Loading week→date map...")
week_dates = (
    pd.read_csv(
        os.path.join(project_root, "data", "Aggregation", "aggregated_file",
                     "final_aggregated.csv"),
        usecols=["week_of_sample", "week_start_date"],
    )
    .drop_duplicates()
    .assign(week_start_date=lambda d: pd.to_datetime(d["week_start_date"]))
    .set_index("week_of_sample")["week_start_date"]
)

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

print("Loading machine_week_presence...")
presence = (
    pd.read_parquet(os.path.join(data_dir, "machine_week_presence.parquet"))
    .merge(demos[["machine_id", "state"]], on="machine_id", how="left")
    .pipe(lambda d: d[d["state"].notna() & ~d["state"].isin(EXCLUDE_STATES)])
)

denom = (
    presence.groupby(["state", "week_of_sample"])
    .size()
    .reset_index(name="machine_count")
)
denom_dict = denom.set_index(["state", "week_of_sample"])["machine_count"].to_dict()

state_machines = presence.groupby("state")["machine_id"].apply(set).to_dict()

del demos

# =============================================================================
# HELPER — weighted average across pooled states
# =============================================================================

def wavg(vals, weights):
    pairs = [(v, w) for v, w in zip(vals, weights) if not np.isnan(v) and w > 0]
    if not pairs:
        return np.nan
    v_arr, w_arr = zip(*pairs)
    return np.average(v_arr, weights=w_arr)


# =============================================================================
# FIGURE FUNCTIONS
# =============================================================================

def make_fig_a(post_shares, pre_shares, all_shares, cohort_sizes,
               site_label, vpn_label, out_path, ylabel=None):
    states_pool = [s for s in qualifying_pooled if s in post_shares]
    weights = [cohort_sizes[s] for s in states_pool]

    pooled = {
        "post":  wavg([post_shares[s] for s in states_pool], weights),
        "pre":   wavg([pre_shares[s]  for s in states_pool], weights),
        "all":   wavg([all_shares[s]  for s in states_pool], weights),
    }

    fig, ax = plt.subplots(figsize=(7, 5))
    groups = [f"Post-treatment\n{site_label} visitors",
              f"Pre-only\n{site_label} visitors",
              "All active\nmachines"]
    values = [pooled["post"], pooled["pre"], pooled["all"]]
    colors = [C_POST, C_PRE, C_ALL]
    bars = ax.bar(groups, values, color=colors, width=0.5, edgecolor="white",
                  linewidth=0.8)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.002,
                f"{val:.1%}", ha="center", va="bottom", fontsize=11)

    ax.set_ylabel(ylabel if ylabel is not None else f"Share ever visited {vpn_label} site")
    ax.set_title(
        f"Ever-visited {vpn_label}: {site_label} cohorts vs. baseline (Mobile)\n"
        f"Pooled across {len(states_pool)} treated states (excl. TX), "
        f"machine-count weighted",
        fontsize=12,
    )
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.set_ylim(0, max(values) * 1.25)

    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"    static_bar saved: {out_path}")


def make_fig_b(post_rates, all_rates, cohort_sizes, site_label, vpn_label, out_path, ylabel=None):
    t_range = list(range(T_MIN, T_MAX + 1))
    states_pool = [s for s in qualifying_pooled if s in post_rates]
    weights = [cohort_sizes[s] for s in states_pool]

    pooled_post = []
    pooled_all  = []
    for t in t_range:
        pooled_post.append(
            wavg([post_rates[s].get(t, np.nan) for s in states_pool], weights)
        )
        pooled_all.append(
            wavg([all_rates[s].get(t, np.nan)  for s in states_pool], weights)
        )

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(t_range, pooled_post, color=C_POST, linewidth=2.5, zorder=3,
            label=f"Post-treatment {site_label} cohort (pooled, weighted)")
    ax.plot(t_range, pooled_all,  color=C_ALL,  linewidth=2.5, zorder=3,
            linestyle="--",
            label="All active machines in treated states (pooled, weighted)")

    ax.axvline(0, color="gray", linestyle=":", linewidth=1, zorder=2)
    ax.text(0.3, ax.get_ylim()[1] * 0.97, "Law\neffective", fontsize=8,
            color="gray", va="top")

    ax.set_xlabel("Weeks relative to law effective date")
    ax.set_ylabel(ylabel if ylabel is not None else "Share visited VPN that week")
    ax.set_title(
        f"Weekly {vpn_label} visit rate: {site_label} cohort vs. all active machines (Mobile)\n"
        f"Pooled weighted avg across treated states (excl. TX)",
        fontsize=12,
    )
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2%}"))
    ax.legend(fontsize=9, loc="upper left")

    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"    time_series saved: {out_path}")


def make_fig_c(post_pre, post_post, all_pre, all_post, cohort_sizes,
               all_pre_n, all_post_n,
               site_label, vpn_label, out_path, ylabel=None):
    states_pool = [s for s in qualifying_pooled if s in post_pre]
    weights     = [cohort_sizes[s] for s in states_pool]

    p = {
        "cohort_pre":  wavg([post_pre[s]  for s in states_pool], weights),
        "cohort_post": wavg([post_post[s] for s in states_pool], weights),
        "all_pre":     wavg([all_pre[s]   for s in states_pool], weights),
        "all_post":    wavg([all_post[s]  for s in states_pool], weights),
    }

    fig, ax = plt.subplots(figsize=(8, 5))

    x       = np.array([0, 1, 2.6, 3.6])
    keys    = ["cohort_pre", "cohort_post", "all_pre", "all_post"]
    vals    = [p[k] for k in keys]
    colors  = [C_POST, C_POST, C_ALL, C_ALL]
    alphas  = [0.5, 1.0, 0.5, 1.0]
    hatches = ["//", "", "//", ""]

    bars = []
    for xi, val, col, alph, hatch in zip(x, vals, colors, alphas, hatches):
        b = ax.bar(xi, val, color=col, alpha=alph, width=0.8,
                   hatch=hatch, edgecolor="white", linewidth=0.8)
        bars.append(b)
        ax.text(xi, val + 0.002, f"{val:.2%}", ha="center", va="bottom", fontsize=10)

    ax.set_xticks([0.5, 3.1])
    ax.set_xticklabels(
        [f"Post-treatment {site_label} visitors", "All active machines (baseline)"],
        fontsize=11,
    )

    pre_patch  = mpatches.Patch(facecolor="#888888", hatch="//", edgecolor="white",
                                alpha=0.6, label=f"Pre-law window (t={T_MIN} to −1)")
    post_patch = mpatches.Patch(facecolor="#888888", edgecolor="white",
                                label=f"Post-law window (t=0 to {T_MAX})")
    ax.legend(handles=[pre_patch, post_patch], fontsize=9, loc="upper right")

    ax.set_ylabel(ylabel if ylabel is not None else "Share visited VPN at least once")
    ax.set_title(
        f"{vpn_label} usage: pre- vs. post-law window (Mobile)\n"
        f"{site_label} cohort vs. all active machines — pooled {len(states_pool)} states (excl. TX)",
        fontsize=12,
    )
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1%}"))
    ax.set_xlim(-0.6, 4.2)
    ax.set_ylim(0, max(vals) * 1.3)

    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"    pre_post saved: {out_path}")


# =============================================================================
# MAIN LOOP
# =============================================================================

for vpn_type in VPN_TYPES:
    print(f"\n{'='*60}")
    print(f"VPN type: {vpn_type}")
    print(f"{'='*60}")

    vpn_subdir = "" if vpn_type == "VPNclean" else vpn_type
    OUT_DIRS = {
        fig_type: os.path.join(out_base, fig_type, vpn_subdir)
        for fig_type in ("static_bar", "time_series", "pre_post")
    }
    for d in OUT_DIRS.values():
        os.makedirs(d, exist_ok=True)

    print(f"  Loading {vpn_type} parquet (nonzero only)...")
    vpn_raw = (
        pd.read_parquet(
            os.path.join(data_dir, f"machine_aggregated_{vpn_type}.parquet"),
            columns=["machine_id", "week_of_sample", "total_duration"],
        )
        .query("total_duration > 0")
        .copy()
    )
    vpn_raw["state"] = vpn_raw["machine_id"].map(machine_state)
    vpn_raw = vpn_raw[vpn_raw["state"].notna()].copy()
    vpn_pos = vpn_raw[["machine_id", "week_of_sample", "state"]].copy()

    ever_vpn    = set(vpn_raw["machine_id"].unique())
    ever_vpn_5s = set(vpn_raw[vpn_raw["total_duration"] > 5]["machine_id"].unique())
    print(f"  Machines with any {vpn_type} visit: {len(ever_vpn):,}")
    print(f"  Machines with any {vpn_type} visit >5s: {len(ever_vpn_5s):,}")

    vpn_sw = (
        vpn_pos.groupby(["state", "week_of_sample"])["machine_id"]
        .nunique()
        .to_dict()
    )

    vpn_pos_5s = vpn_raw[vpn_raw["total_duration"] > 5][
        ["machine_id", "week_of_sample", "state"]
    ].copy()
    vpn_sw_5s = (
        vpn_pos_5s.groupby(["state", "week_of_sample"])["machine_id"]
        .nunique()
        .to_dict()
    )

    for xxx_site in XXX_SITES:
        site_label = SITE_LABELS[xxx_site]
        vpn_label  = VPN_LABELS[vpn_type]
        print(f"\n  --- {xxx_site} ---")

        print(f"    Loading {xxx_site} parquet (nonzero only)...")
        xxx_raw = (
            pd.read_parquet(
                os.path.join(data_dir, f"machine_aggregated_{xxx_site}.parquet"),
                columns=["machine_id", "week_of_sample", "total_duration"],
            )
            .query("total_duration > 0")
            .copy()
        )
        xxx_raw["state"] = xxx_raw["machine_id"].map(machine_state)
        xxx_raw = xxx_raw[xxx_raw["state"].notna()].copy()
        xxx_pos = xxx_raw[["machine_id", "week_of_sample", "state"]].copy()

        post_ever, pre_ever, all_ever = {}, {}, {}
        cohort_sizes = {}
        _post_ids_by_state, _pre_ids_by_state, _all_ids_by_state = {}, {}, {}
        _all_pres_pre_by_state, _all_pres_post_by_state = {}, {}

        post_weekly = {}
        all_weekly  = {}

        post_pre_win, post_post_win = {}, {}
        all_pre_win,  all_post_win  = {}, {}
        all_pre_win_n, all_post_win_n = {}, {}

        for state in qualifying:
            wos_law = law_wos[state]

            state_xxx = xxx_pos[xxx_pos["state"] == state]

            post_ids = set(
                state_xxx[state_xxx["week_of_sample"] >= wos_law]["machine_id"].unique()
            )
            pre_ids  = set(
                state_xxx[state_xxx["week_of_sample"] <  wos_law]["machine_id"].unique()
            ) - post_ids
            all_ids  = state_machines.get(state, set())

            n_post = len(post_ids)
            n_pre  = len(pre_ids)
            n_all  = len(all_ids)

            if n_post == 0:
                print(f"    {state}: no post-treatment {site_label} visitors — skipping")
                continue

            cohort_sizes[state] = n_post
            print(f"    {state}: post={n_post:,}  pre-only={n_pre:,}  all={n_all:,}")

            post_ever[state] = len(post_ids & ever_vpn) / n_post
            pre_ever[state]  = (len(pre_ids  & ever_vpn) / n_pre)  if n_pre  > 0 else np.nan
            all_ever[state]  = (len(all_ids  & ever_vpn) / n_all)  if n_all  > 0 else np.nan
            _post_ids_by_state[state] = post_ids
            _pre_ids_by_state[state]  = pre_ids
            _all_ids_by_state[state]  = all_ids

            cohort_vpn = vpn_pos[vpn_pos["machine_id"].isin(post_ids)]
            cohort_vpn_by_week = cohort_vpn["week_of_sample"].value_counts().to_dict()

            post_weekly[state] = {}
            all_weekly[state]  = {}
            for t in range(T_MIN, T_MAX + 1):
                wos_t = wos_law + t
                post_weekly[state][t] = cohort_vpn_by_week.get(wos_t, 0) / n_post
                denom_t = denom_dict.get((state, wos_t), 0)
                num_t   = vpn_sw.get((state, wos_t), 0)
                all_weekly[state][t] = (num_t / denom_t) if denom_t > 0 else np.nan

            pre_weeks  = range(wos_law + T_MIN, wos_law)
            post_weeks = range(wos_law, wos_law + T_MAX + 1)

            cohort_vpn_pre_ids  = set(
                cohort_vpn[cohort_vpn["week_of_sample"].isin(pre_weeks)]["machine_id"]
            )
            cohort_vpn_post_ids = set(
                cohort_vpn[cohort_vpn["week_of_sample"].isin(post_weeks)]["machine_id"]
            )
            post_pre_win[state]  = len(cohort_vpn_pre_ids)  / n_post
            post_post_win[state] = len(cohort_vpn_post_ids) / n_post

            state_vpn = vpn_pos[vpn_pos["state"] == state]
            all_vpn_pre_ids  = set(
                state_vpn[state_vpn["week_of_sample"].isin(pre_weeks)]["machine_id"]
            )
            all_vpn_post_ids = set(
                state_vpn[state_vpn["week_of_sample"].isin(post_weeks)]["machine_id"]
            )
            state_pres = presence[presence["state"] == state]
            all_pres_pre  = set(
                state_pres[state_pres["week_of_sample"].isin(pre_weeks)]["machine_id"]
            )
            all_pres_post = set(
                state_pres[state_pres["week_of_sample"].isin(post_weeks)]["machine_id"]
            )
            all_pre_win[state]    = (len(all_vpn_pre_ids)  / len(all_pres_pre))  if all_pres_pre  else np.nan
            all_post_win[state]   = (len(all_vpn_post_ids) / len(all_pres_post)) if all_pres_post else np.nan
            all_pre_win_n[state]  = len(all_pres_pre)
            all_post_win_n[state] = len(all_pres_post)
            _all_pres_pre_by_state[state]  = all_pres_pre
            _all_pres_post_by_state[state] = all_pres_post

        tag = f"{vpn_type}_{xxx_site.replace('.', '_')}"

        print(f"    Generating static_bar...")
        make_fig_a(post_ever, pre_ever, all_ever, cohort_sizes,
                   site_label, vpn_label,
                   os.path.join(OUT_DIRS["static_bar"], f"static_bar_{tag}.png"))

        print(f"    Generating time_series...")
        make_fig_b(post_weekly, all_weekly, cohort_sizes,
                   site_label, vpn_label,
                   os.path.join(OUT_DIRS["time_series"], f"time_series_{tag}.png"))

        print(f"    Generating pre_post...")
        make_fig_c(post_pre_win, post_post_win, all_pre_win, all_post_win,
                   cohort_sizes, all_pre_win_n, all_post_win_n,
                   site_label, vpn_label,
                   os.path.join(OUT_DIRS["pre_post"], f"pre_post_{tag}.png"))

        if xxx_site == "PORNHUB.COM":
            label_5s = vpn_label + " (>5s sessions)"

            print(f"    Generating static_bar (>5s VPN)...")
            post_ever_5s = {s: len(ids & ever_vpn_5s) / cohort_sizes[s]
                            for s, ids in _post_ids_by_state.items()}
            pre_ever_5s  = {s: (len(ids & ever_vpn_5s) / len(ids)) if ids else np.nan
                            for s, ids in _pre_ids_by_state.items()}
            all_ever_5s  = {s: (len(ids & ever_vpn_5s) / len(ids)) if ids else np.nan
                            for s, ids in _all_ids_by_state.items()}
            make_fig_a(
                post_ever_5s, pre_ever_5s, all_ever_5s, cohort_sizes,
                site_label, label_5s,
                os.path.join(OUT_DIRS["static_bar"], f"static_bar_{tag}_vpn5s.png"),
                ylabel=f"Share ever visited {vpn_label} site >5sec",
            )

            print(f"    Generating time_series (>5s VPN)...")
            post_weekly_5s = {}
            all_weekly_5s  = {}
            for state in qualifying:
                if state not in cohort_sizes:
                    continue
                wos_law  = law_wos[state]
                n_post   = cohort_sizes[state]
                post_ids = _post_ids_by_state[state]
                cohort_vpn_5s = vpn_pos_5s[vpn_pos_5s["machine_id"].isin(post_ids)]
                cohort_vpn_5s_by_week = cohort_vpn_5s["week_of_sample"].value_counts().to_dict()
                post_weekly_5s[state] = {}
                all_weekly_5s[state]  = {}
                for t in range(T_MIN, T_MAX + 1):
                    wos_t = wos_law + t
                    post_weekly_5s[state][t] = cohort_vpn_5s_by_week.get(wos_t, 0) / n_post
                    denom_t = denom_dict.get((state, wos_t), 0)
                    num_t   = vpn_sw_5s.get((state, wos_t), 0)
                    all_weekly_5s[state][t] = (num_t / denom_t) if denom_t > 0 else np.nan
            make_fig_b(
                post_weekly_5s, all_weekly_5s, cohort_sizes,
                site_label, label_5s,
                os.path.join(OUT_DIRS["time_series"], f"time_series_{tag}_vpn5s.png"),
                ylabel="Share visited VPN that week >5sec",
            )

            print(f"    Generating pre_post (>5s VPN)...")
            post_pre_win_5s, post_post_win_5s = {}, {}
            all_pre_win_5s,  all_post_win_5s  = {}, {}
            all_pre_win_5s_n, all_post_win_5s_n = {}, {}
            for state in qualifying:
                if state not in cohort_sizes:
                    continue
                wos_law  = law_wos[state]
                n_post   = cohort_sizes[state]
                post_ids = _post_ids_by_state[state]
                pre_weeks  = range(wos_law + T_MIN, wos_law)
                post_weeks = range(wos_law, wos_law + T_MAX + 1)
                cohort_vpn_5s = vpn_pos_5s[vpn_pos_5s["machine_id"].isin(post_ids)]
                post_pre_win_5s[state]  = len(set(
                    cohort_vpn_5s[cohort_vpn_5s["week_of_sample"].isin(pre_weeks)]["machine_id"]
                )) / n_post
                post_post_win_5s[state] = len(set(
                    cohort_vpn_5s[cohort_vpn_5s["week_of_sample"].isin(post_weeks)]["machine_id"]
                )) / n_post
                state_vpn_5s = vpn_pos_5s[vpn_pos_5s["state"] == state]
                all_pres_pre  = _all_pres_pre_by_state[state]
                all_pres_post = _all_pres_post_by_state[state]
                all_pre_win_5s[state]    = (len(set(
                    state_vpn_5s[state_vpn_5s["week_of_sample"].isin(pre_weeks)]["machine_id"]
                )) / len(all_pres_pre))  if all_pres_pre  else np.nan
                all_post_win_5s[state]   = (len(set(
                    state_vpn_5s[state_vpn_5s["week_of_sample"].isin(post_weeks)]["machine_id"]
                )) / len(all_pres_post)) if all_pres_post else np.nan
                all_pre_win_5s_n[state]  = len(all_pres_pre)
                all_post_win_5s_n[state] = len(all_pres_post)
            make_fig_c(
                post_pre_win_5s, post_post_win_5s, all_pre_win_5s, all_post_win_5s,
                cohort_sizes, all_pre_win_5s_n, all_post_win_5s_n,
                site_label, label_5s,
                os.path.join(OUT_DIRS["pre_post"], f"pre_post_{tag}_vpn5s.png"),
                ylabel="Share visited VPN at least once >5sec",
            )

print("\nDone.")
