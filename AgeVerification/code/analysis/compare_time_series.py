# Author: Matt Brown, assisted by Claude
# Created: 02/28/2026
# Purpose: Per-state and stacked comparison time series (two DVs)

"""
Comparison Time Series — Treated State vs Control Mean

For each qualifying treated state (law effective before 2024-11-24), plots an
8-panel (2×4) figure comparing the treated state's series to the machine-count-
weighted control mean, with a difference line on a secondary y-axis.

Also produces a stacked event-study figure per DV, pooling all qualifying treated
states in relative time (t = −16 to +8 weeks around the law's effective date),
weighted by machine count.

Two dependent variables:
  DV1 (winsorized_p95): weekly minutes per machine, winsorized at p95 of nonzero obs
  DV2 (share_60s):      share of machines with >60s on site in a given week

Panels (Row 0): All XXX (pooled), PORNHUB.COM, XVIDEOS.COM, XHAMSTER.COM
Panels (Row 1): XNXX.COM, CHATURBATE.COM, other_XXX_sites, all_other_sites

Outputs:
  output/analysis/compare_time_series/winsorized_p95/{STATE}.png
  output/analysis/compare_time_series/winsorized_p95/stacked.png
  output/analysis/compare_time_series/share_60s/{STATE}.png
  output/analysis/compare_time_series/share_60s/stacked.png
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

warnings.filterwarnings('ignore')

file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", ".."))
sys.path.insert(0, os.path.join(project_root, "code"))
from plot_style import apply_plot_style, COLOR_PALETTE

apply_plot_style()

# ============================================================================
# CONSTANTS
# ============================================================================

MOBILE = os.environ.get("ANALYSIS_MODE") == "mobile"

if MOBILE:
    data_dir = os.path.join(project_root, "data", "Aggregation", "mobile_machine_panel")
    out_base = os.path.join(project_root, "output", "analysis", "mobile", "compare_time_series")
else:
    data_dir = os.path.join(project_root, "data", "Aggregation", "machine_panel")
    out_base = os.path.join(project_root, "output", "analysis", "compare_time_series")

SITES = [
    "PORNHUB.COM", "CHATURBATE.COM", "XHAMSTER.COM",
    "XNXX.COM", "XVIDEOS.COM", "other_XXX_sites",
]
ALL_OTHER      = "all_other_sites"
EXCLUDE_STATES  = {"DC", "XX", "ZZ"}
EXCLUDE_TREATED = {"TX"}   # TX law was immediately enjoined; excluded from pooled stacked figures
CUTOFF_DATE     = pd.Timestamp("2024-11-24")
T_MIN, T_MAX   = -16, 8

TREATED_COLOR = COLOR_PALETTE[0]   # maroon
CTRL_COLOR    = COLOR_PALETTE[1]   # contrast
DIFF_COLOR    = COLOR_PALETTE[2]   # difference line

SITE_LABELS = {
    "all_xxx":         "All XXX",
    "PORNHUB.COM":     "Pornhub",
    "XVIDEOS.COM":     "xVideos",
    "XHAMSTER.COM":    "xHamster",
    "XNXX.COM":        "XNXX",
    "CHATURBATE.COM":  "Chaturbate",
    "other_XXX_sites": "Other XXX",
    "all_other_sites": "All other sites",
    "VPNclean":       "VPN (clean)",
    "allVPN":          "All VPN",
}
PANEL_ORDER = [
    "all_xxx", "PORNHUB.COM", "XVIDEOS.COM", "XHAMSTER.COM", "XNXX.COM", 
    "CHATURBATE.COM", "other_XXX_sites", "all_other_sites", "VPNclean", "allVPN",
]


def fmt_date_axis(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", rotation=0)


# ============================================================================
# LOAD SHARED DATA
# ============================================================================

print("Loading week→date map...")
week_dates = (
    pd.read_csv(
        os.path.join(project_root, "data", "Aggregation", "aggregated_file", "final_aggregated.csv"),
        usecols=["week_of_sample", "week_start_date"],
    )
    .drop_duplicates()
    .assign(week_start_date=lambda d: pd.to_datetime(d["week_start_date"]))
    .set_index("week_of_sample")["week_start_date"]
)

print("Loading state laws...")
if MOBILE:
    laws = pd.read_csv(os.path.join(project_root, "raw", "statelaws", "phshutdown_dates.csv"))
    treated_states_all = sorted(laws["state"].tolist())
    law_date = {
        row["state"]: pd.to_datetime(row["date_PH_shutdown"])
        for _, row in laws.iterrows()
        if pd.notna(row.get("date_PH_shutdown"))
    }
else:
    laws = pd.read_csv(os.path.join(project_root, "raw", "statelaws", "statelaws_dates.csv"))
    treated_states_all = sorted(laws.loc[laws["day_passed"].notna(), "state"].tolist())
    law_date = {
        row["state"]: pd.to_datetime(row["day_effective"], format="%d%b%Y")
        for _, row in laws.iterrows()
        if pd.notna(row.get("day_effective"))
    }

qualifying = [s for s in treated_states_all
              if s in law_date and law_date[s] < CUTOFF_DATE]
excluded   = [s for s in treated_states_all if s not in qualifying]
print(f"  Qualifying ({len(qualifying)}): {qualifying}")
print(f"  Excluded:  {excluded}")
# qualifying_pooled drops TX from the stacked event-study figures only;
# TX's individual time-series figure is still produced
qualifying_pooled = [s for s in qualifying if s not in EXCLUDE_TREATED]
print(f"  Qualifying pooled ({len(qualifying_pooled)}): {qualifying_pooled}")

print("Loading machine demographics...")
if MOBILE:
    demos_raw = pd.read_csv(
        os.path.join(project_root, "data", "ProcessComscore", "mobile_characteristics.csv"),
        usecols=["machine_id"],
    ).drop_duplicates(subset="machine_id")
    demos_raw["machine_id"] = demos_raw["machine_id"].astype(str)
    state_lookup = pd.read_parquet(
        os.path.join(project_root, "data", "Aggregation", "mobile_to_state_lookup.parquet"),
        columns=["machine_id", "state"],
    )
    state_lookup["machine_id"] = state_lookup["machine_id"].astype(str)
    demos = demos_raw.merge(state_lookup, on="machine_id", how="left")
    del demos_raw, state_lookup
else:
    demos = pd.read_parquet(
        os.path.join(project_root, "data", "ProcessComscore", "full_demographics",
                     "full_machine_person_demos.parquet"),
        columns=["machine_id", "state"],
    ).drop_duplicates(subset="machine_id")
demos = demos[demos["state"].notna() & ~demos["state"].isin(EXCLUDE_STATES)].copy()

print("Loading machine_week_presence.parquet...")
presence = pd.read_parquet(os.path.join(data_dir, "machine_week_presence.parquet"))
presence = presence.merge(demos[["machine_id", "state"]], on="machine_id", how="left")
presence = presence[presence["state"].notna() & ~presence["state"].isin(EXCLUDE_STATES)].copy()

denom = (
    presence.groupby(["state", "week_of_sample"])
    .size()
    .reset_index(name="machine_count")
)
denom["week_start_date"] = denom["week_of_sample"].map(week_dates)
del presence

all_states     = set(denom["state"].unique())
control_states = all_states - set(treated_states_all)
print(f"  Control states: {len(control_states)}")

# ============================================================================
# BUILD METRICS: DV1 and DV2
# ============================================================================

def make_sw_dv1(panel, p95):
    """Winsorize at p95, aggregate to state-week, join denom → min/machine/week."""
    pw = panel.copy()
    pw["total_duration"] = pw["total_duration"].clip(upper=p95)
    agg = pw.groupby(["state", "week_of_sample"])["total_duration"].sum().reset_index()
    sw = denom.merge(agg, on=["state", "week_of_sample"], how="left")
    sw["total_duration"] = sw["total_duration"].fillna(0)
    sw["min_per_machine"] = sw["total_duration"] / 60 / sw["machine_count"]
    return sw


def make_sw_dv2(panel):
    """Share of machines with >60s on site, aggregate to state-week."""
    p = panel.copy()
    p["over60"] = (p["total_duration"] > 60).astype(int)
    agg = p.groupby(["state", "week_of_sample"])["over60"].sum().reset_index(name="n_over60")
    sw = denom.merge(agg, on=["state", "week_of_sample"], how="left")
    sw["n_over60"]     = sw["n_over60"].fillna(0)
    sw["share_over60"] = sw["n_over60"] / sw["machine_count"]
    return sw


metrics_dv1, metrics_dv2 = {}, {}

# ---- All XXX (pooled) ----
print("Building All XXX (pooled)...")
site_frames = [
    pd.read_parquet(
        os.path.join(data_dir, f"machine_aggregated_{site}.parquet"),
        columns=["machine_id", "week_of_sample", "total_duration"],
    )
    for site in SITES
]
panel_all = pd.concat(site_frames, ignore_index=True)
del site_frames
panel_all = panel_all[panel_all["total_duration"].notna()].copy()
panel_all = (
    panel_all.groupby(["machine_id", "week_of_sample"])["total_duration"]
    .sum().reset_index()
)
panel_all = panel_all.merge(demos[["machine_id", "state"]], on="machine_id", how="left")
panel_all = panel_all[panel_all["state"].notna() & ~panel_all["state"].isin(EXCLUDE_STATES)].copy()

metrics_dv2["all_xxx"] = make_sw_dv2(panel_all)
p95_all = panel_all.loc[panel_all["total_duration"] > 0, "total_duration"].quantile(0.95)
print(f"  Pooled XXX p95: {p95_all:.1f}s ({p95_all/60:.1f} min)")
metrics_dv1["all_xxx"] = make_sw_dv1(panel_all, p95_all)
del panel_all

# ---- Individual sites ----
for site in SITES + [ALL_OTHER, "VPNclean", "allVPN"]:
    print(f"Building metric: {site}...")
    mw = pd.read_parquet(
        os.path.join(data_dir, f"machine_aggregated_{site}.parquet"),
        columns=["machine_id", "week_of_sample", "total_duration"],
    )
    mw = mw[mw["total_duration"].notna()].copy()
    mw = mw.merge(demos[["machine_id", "state"]], on="machine_id", how="left")
    mw = mw[mw["state"].notna() & ~mw["state"].isin(EXCLUDE_STATES)].copy()

    metrics_dv2[site] = make_sw_dv2(mw)

    nonzero   = mw.loc[mw["total_duration"] > 0, "total_duration"]
    p95_site  = nonzero.quantile(0.95) if len(nonzero) > 0 else np.inf
    print(f"  p95: {p95_site:.1f}s ({p95_site/60:.1f} min)")
    metrics_dv1[site] = make_sw_dv1(mw, p95_site)
    del mw

# ============================================================================
# CONTROL AGGREGATES (machine-count weighted across control states, per week)
# ============================================================================

def build_ctrl_dv1(sw):
    ctrl = sw[sw["state"].isin(control_states)]
    agg  = ctrl.groupby("week_of_sample")[["total_duration", "machine_count"]].sum().reset_index()
    agg["ctrl_mean"]      = agg["total_duration"] / 60 / agg["machine_count"]
    agg["week_start_date"] = agg["week_of_sample"].map(week_dates)
    return agg


def build_ctrl_dv2(sw):
    ctrl = sw[sw["state"].isin(control_states)]
    agg  = ctrl.groupby("week_of_sample")[["n_over60", "machine_count"]].sum().reset_index()
    agg["ctrl_mean"]      = agg["n_over60"] / agg["machine_count"]
    agg["week_start_date"] = agg["week_of_sample"].map(week_dates)
    return agg


ctrl_dv1 = {k: build_ctrl_dv1(v) for k, v in metrics_dv1.items()}
ctrl_dv2 = {k: build_ctrl_dv2(v) for k, v in metrics_dv2.items()}

# ============================================================================
# LAW WEEK LOOKUP  (week_of_sample closest to law effective date)
# ============================================================================

_base = pd.Timestamp("2022-01-01")
law_wos = {
    state: int((law_date[state] - _base).days // 7) + 1
    for state in qualifying
}

# ============================================================================
# PLOTTING HELPERS
# ============================================================================

def add_diff_axis(ax, x_vals, treated_arr, ctrl_arr, is_rightmost):
    """
    Overlay difference (treated − control) on a twinx right axis.
    Scale (tick labels + ylabel) shown on every panel; ylabel only on rightmost.
    Returns the Line2D handle for use in legends.
    """
    diff = treated_arr - ctrl_arr          # NaN propagates automatically
    ax2  = ax.twinx()
    (l3,) = ax2.plot(x_vals, diff, color=DIFF_COLOR, linewidth=1.0,
                     linestyle=":", label="Difference")
    ax2.axhline(0, color=DIFF_COLOR, linewidth=0.4, linestyle=":")
    ax2.tick_params(axis="y", labelcolor=DIFF_COLOR, labelsize=7)
    if is_rightmost:
        ax2.set_ylabel("Difference", fontsize=8, color=DIFF_COLOR)
    return l3


# ============================================================================
# PER-STATE FIGURES
# ============================================================================

def make_per_state_figures(metrics, ctrl_dict, value_col, value_label, subdir):
    out_dir = os.path.join(out_base, subdir)
    os.makedirs(out_dir, exist_ok=True)

    for state in qualifying:
        print(f"  {state}...", end=" ", flush=True)
        fig, axes = plt.subplots(2, 5, figsize=(25, 9))
        law_dt = law_date[state]

        for idx, metric_key in enumerate(PANEL_ORDER):
            ax       = axes[idx // 5, idx % 5]
            sw       = metrics[metric_key]
            ctrl_map = ctrl_dict[metric_key].set_index("week_of_sample")["ctrl_mean"]

            td = sw[sw["state"] == state].sort_values("week_start_date")
            x_dates      = td["week_start_date"].values
            treated_arr  = td[value_col].values.astype(float)
            ctrl_arr     = td["week_of_sample"].map(ctrl_map).values.astype(float)

            (l1,) = ax.plot(x_dates, treated_arr, color=TREATED_COLOR,
                            linewidth=1.4, label=state)
            (l2,) = ax.plot(x_dates, ctrl_arr,    color=CTRL_COLOR,
                            linewidth=1.4, label="Control mean")
            ax.axvline(law_dt, color="gray", linestyle="--", linewidth=1)

            if idx % 5 == 0:
                ax.set_ylabel(value_label)

            if idx == 0:
                ax.legend([l1, l2], [state, "Control mean"], fontsize=8)

            ax.set_title(SITE_LABELS[metric_key], fontsize=11)
            fmt_date_axis(ax)

        fig.suptitle(f"{state} — comparison to control states ({subdir})", fontsize=13)
        plt.tight_layout()
        fig.savefig(os.path.join(out_dir, f"{state}.png"), dpi=300, bbox_inches="tight")
        plt.close(fig)
        print("saved")


# ============================================================================
# STACKED EVENT-STUDY FIGURES
# ============================================================================

def make_stacked_figure(metrics, ctrl_dict, value_col, value_label, subdir):
    out_dir = os.path.join(out_base, subdir)
    os.makedirs(out_dir, exist_ok=True)

    t_range = list(range(T_MIN, T_MAX + 1))
    fig, axes = plt.subplots(2, 5, figsize=(25, 9))

    for idx, metric_key in enumerate(PANEL_ORDER):
        ax       = axes[idx // 5, idx % 5]
        sw       = metrics[metric_key]
        ctrl_map = ctrl_dict[metric_key].set_index("week_of_sample")["ctrl_mean"]

        # Gather (t, state) observations for stacking (TX excluded via qualifying_pooled)
        records = []
        for state in qualifying_pooled:
            wos_0 = law_wos[state]
            for t in t_range:
                wos_t = wos_0 + t
                row   = sw[(sw["state"] == state) & (sw["week_of_sample"] == wos_t)]
                if len(row) == 0:
                    continue
                mc_t   = float(row["machine_count"].values[0])
                val_t  = float(row[value_col].values[0])
                ctrl_t = ctrl_map.get(wos_t, np.nan)
                if np.isnan(ctrl_t):
                    continue
                records.append({"t": t, "mc": mc_t, "val": val_t, "ctrl": float(ctrl_t)})

        df_s = pd.DataFrame(records)
        if df_s.empty:
            continue

        # Machine-count weighted average across states at each t
        df_s["val_mc"]  = df_s["val"]  * df_s["mc"]
        df_s["ctrl_mc"] = df_s["ctrl"] * df_s["mc"]
        grp = (
            df_s.groupby("t")
            .agg(val_mc_sum=("val_mc", "sum"), ctrl_mc_sum=("ctrl_mc", "sum"),
                 mc_sum=("mc", "sum"))
            .reset_index()
        )
        grp["treated"] = grp["val_mc_sum"]  / grp["mc_sum"]
        grp["ctrl"]    = grp["ctrl_mc_sum"] / grp["mc_sum"]

        t_vals       = grp["t"].values
        treated_arr  = grp["treated"].values
        ctrl_arr     = grp["ctrl"].values

        (l1,) = ax.plot(t_vals, treated_arr, color=TREATED_COLOR, linewidth=1.4,
                        label="Treated (weighted)")
        (l2,) = ax.plot(t_vals, ctrl_arr,    color=CTRL_COLOR,    linewidth=1.4,
                        label="Control (weighted)")
        ax.axvline(0, color="gray", linestyle="--", linewidth=1)

        if idx % 5 == 0:
            ax.set_ylabel(value_label)
        ax.set_xlabel("Weeks relative to law")

        l3 = add_diff_axis(ax, t_vals, treated_arr, ctrl_arr,
                           is_rightmost=(idx % 5 == 4))

        if idx == 0:
            ax.legend([l1, l2, l3],
                      ["Treated (weighted)", "Control (weighted)", "Difference"],
                      fontsize=8)

        ax.set_title(SITE_LABELS[metric_key], fontsize=11)

    n = len(qualifying_pooled)
    fig.suptitle(
        f"Stacked event study — {n} treated states (excl. TX), t=0: law effective date ({subdir})",
        fontsize=13,
    )
    plt.tight_layout()
    out_path = os.path.join(out_dir, "stacked.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Stacked saved: {out_path}")


# ============================================================================
# MAIN
# ============================================================================

print("\n=== DV1: Winsorized p95 (min / machine / week) ===")
print("Per-state figures...")
make_per_state_figures(metrics_dv1, ctrl_dv1, "min_per_machine",
                       "Min / machine / week", "winsorized_p95")
print("Stacked figure...")
make_stacked_figure(metrics_dv1, ctrl_dv1, "min_per_machine",
                    "Min / machine / week", "winsorized_p95")

print("\n=== DV2: Share with >60s on site ===")
print("Per-state figures...")
make_per_state_figures(metrics_dv2, ctrl_dv2, "share_over60",
                       "Share of machines (>60s)", "share_60s")
print("Stacked figure...")
make_stacked_figure(metrics_dv2, ctrl_dv2, "share_over60",
                    "Share of machines (>60s)", "share_60s")

print("\nDone.")
