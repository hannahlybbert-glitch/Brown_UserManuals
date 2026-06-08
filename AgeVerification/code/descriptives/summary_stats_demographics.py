# Author: Emily Davis
# Created: 2026-03-24
# Purpose: Demographic summary statistics table for desktop and mobile analysis samples

"""
Produces a tidy CSV of demographic shares for:
  (1) The full analysis sample (machines with have_demos==1)
  (2) The subset that ever visited any XXX Adult site

Variables reported:
  Desktop + Mobile: age, hh_income, hh_size, children_present, gender
  Mobile only:      race, hispanic

NOTE on mobile race/hispanic: these columns appear to have data quality issues
(race values contain ethnicity strings and vice versa). The script extracts
the interpretable values only; investigate raw data before reporting.

Inputs:
  data/ProcessComscore/full_demographics/full_machine_person_demos.parquet  (desktop)
  data/ProcessComscore/full_demographics/full_mobile_demos.parquet          (mobile)
  data/Aggregation/machine_panel/machine_aggregated_*.parquet               (desktop XXX)
  data/Aggregation/mobile_machine_panel/machine_aggregated_*.parquet        (mobile XXX)

Output:
  data/descriptives/demographic_summary_stats.csv
  Columns: device_type, variable, category, n_full, share_full, n_xxx, share_xxx

Usage: python code/descriptives/summary_stats_demographics.py
"""

import pandas as pd
import numpy as np
import os
import pyarrow.parquet as pq

project_root = os.getcwd()

# ==============================================================================
# PATHS
# ==============================================================================
desktop_demos_path = os.path.join(
    project_root, "data", "ProcessComscore", "full_demographics",
    "full_machine_person_demos.parquet"
)
mobile_demos_path = os.path.join(
    project_root, "data", "ProcessComscore", "full_demographics",
    "full_mobile_demos.parquet"
)

desktop_panel_dir = os.path.join(project_root, "data", "Aggregation", "machine_panel")
mobile_panel_dir  = os.path.join(project_root, "data", "Aggregation", "mobile_machine_panel")

output_dir  = os.path.join(project_root, "output", "descriptives", "summarystats")
output_path = os.path.join(output_dir, "demographic_summary_stats.csv")
os.makedirs(output_dir, exist_ok=True)

XXX_CATEGORIES = [
    "PORNHUB.COM", "XVIDEOS.COM", "XHAMSTER.COM",
    "XNXX.COM", "CHATURBATE.COM", "other_XXX_sites"
]

# ==============================================================================
# HELPER: build XXX visitor roster
# Reads only rows with total_duration > 0 from each XXX category file.
# ==============================================================================
def build_xxx_roster(panel_dir):
    machine_ids = set()
    for cat in XXX_CATEGORIES:
        fpath = os.path.join(panel_dir, f"machine_aggregated_{cat}.parquet")
        if not os.path.exists(fpath):
            print(f"  WARNING: {fpath} not found — skipping")
            continue
        table = pq.read_table(
            fpath,
            columns=["machine_id"],
            filters=[("total_duration", ">", 0)]
        )
        machine_ids.update(table["machine_id"].to_pylist())
    return machine_ids


# ==============================================================================
# HELPER: standardize demographic values to clean display labels
# ==============================================================================
def standardize_desktop(df):
    """Rename and recode desktop demographic columns to clean labels."""
    df = df.copy()

    # Age
    df["age"] = df["hoh_age"].replace({"65 and Over": "65+", "Unknown": np.nan})

    # HH income — strip prefix, keep original bucketing
    df["hh_income_clean"] = (
        df["hh_income"]
        .str.replace("HHI US: ", "", regex=False)
        .str.replace(".999k", "k", regex=False)
    )

    # HH size — strip prefix, standardize top bucket
    df["hh_size_clean"] = (
        df["hh_size"]
        .str.replace("HH Size:", "", regex=False)
        .str.strip()
        .replace({"5 or More": "5+", "Unknown": np.nan})
    )

    # Children
    df["children_clean"] = (
        df["children_present"]
        .str.replace("Children:", "", regex=False)
        .str.strip()
    )

    # Gender — keep as-is; "Shared" and "Unknown" are informative for desktop
    df["gender_clean"] = df["gender"]

    return df


def bin_mobile_age(age_series):
    """Bin raw integer age into age-range strings matching desktop."""
    bins   = [17, 24, 34, 44, 54, 64, 150]
    labels = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
    return pd.cut(age_series, bins=bins, labels=labels).astype("object")


def standardize_mobile(df):
    """Rename and recode mobile demographic columns to clean labels."""
    df = df.copy()

    # Age — bin raw integer
    df["age"] = bin_mobile_age(df["age"])

    # HH income — strip prefix
    df["hh_income_clean"] = (
        df["hh_income"]
        .str.replace("HHI USD:", "", regex=False)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("  ", " ", regex=False)
    )

    # HH size — strip prefix, standardize top bucket
    df["hh_size_clean"] = (
        df["hh_size"]
        .str.replace("HH Size:", "", regex=False)
        .str.strip()
    )

    # Children
    df["children_clean"] = (
        df["children_present"]
        .str.replace("Children:", "", regex=False)
        .str.strip()
    )

    # Gender
    df["gender_clean"] = df["gender"]

    # Race — extract only values that are clearly race labels
    df["race_clean"] = df["race"].where(
        df["race"].isin(["Race:Black", "Race:Non-Black", "Not Reportable"]),
        other=np.nan
    ).str.replace("Race:", "", regex=False)

    # Hispanic — extract only clearly ethnicity labels
    df["hispanic_clean"] = df["hispanic"].where(
        df["hispanic"].isin(["Hispanic", "Non-Hispanic", "Not Reportable"]),
        other=np.nan
    )

    return df


# ==============================================================================
# HELPER: compute shares for one variable
# ==============================================================================
def compute_shares(series_full, series_xxx, var_name):
    """
    Given a column for the full sample and the XXX subsample,
    return a DataFrame with columns:
      variable, category, n_full, share_full, n_xxx, share_xxx
    """
    rows = []

    counts_full = series_full.dropna().value_counts()
    counts_xxx  = series_xxx.dropna().value_counts()

    total_full = counts_full.sum()
    total_xxx  = counts_xxx.sum()

    all_cats = counts_full.index.union(counts_xxx.index)

    # Income-specific sort order (low to high); all other variables sort alphabetically
    income_order = [
        "Less than 25k", "Less than 25000",
        "25k-39k", "25000 - 39999",
        "40k-59k", "40000 - 59999",
        "60k-74k", "60000 - 74999",
        "75k-99k", "75000 - 99999",
        "100k-149k", "100000 or more",
        "150k-199k",
        "200k+",
    ]
    if var_name == "hh_income":
        all_cats = sorted(all_cats, key=lambda x: income_order.index(x) if x in income_order else 99)
    else:
        all_cats = sorted(all_cats, key=str)

    for cat in all_cats:
        n_full = counts_full.get(cat, 0)
        n_xxx  = counts_xxx.get(cat, 0)
        rows.append({
            "variable":    var_name,
            "category":    cat,
            "n_full":      n_full,
            "share_full":  n_full / total_full if total_full > 0 else np.nan,
            "n_xxx":       n_xxx,
            "share_xxx":   n_xxx / total_xxx  if total_xxx  > 0 else np.nan,
        })

    return pd.DataFrame(rows)


# ==============================================================================
# MAIN
# ==============================================================================
print("=" * 80)
print("DEMOGRAPHIC SUMMARY STATISTICS")
print("=" * 80)

all_results = []

# ---- DESKTOP ----------------------------------------------------------------
print("\n[DESKTOP]")

desktop_raw = pd.read_parquet(desktop_demos_path)
desktop = desktop_raw[desktop_raw["have_demos"] == 1].copy()
print(f"  Analysis sample (have_demos==1): {len(desktop):,} machines")
print(f"  Total in file (incl. no demos):  {len(desktop_raw):,} machines")

print("  Building XXX visitor roster...")
desktop_xxx_ids = build_xxx_roster(desktop_panel_dir)
desktop["ever_xxx"] = desktop["machine_id"].isin(desktop_xxx_ids)
n_xxx_desktop = desktop["ever_xxx"].sum()
print(f"  XXX visitors: {n_xxx_desktop:,} ({n_xxx_desktop / len(desktop) * 100:.1f}% of analysis sample)")

desktop = standardize_desktop(desktop)
desktop_xxx = desktop[desktop["ever_xxx"]]

desktop_vars = {
    "age":      "age",
    "hh_income":"hh_income_clean",
    "hh_size":  "hh_size_clean",
    "children": "children_clean",
    "gender":   "gender_clean",
}

for var_label, col in desktop_vars.items():
    result = compute_shares(desktop[col], desktop_xxx[col], var_label)
    result.insert(0, "device_type", "desktop")
    all_results.append(result)

# ---- MOBILE -----------------------------------------------------------------
print("\n[MOBILE]")

if not os.path.exists(mobile_demos_path):
    print(f"  WARNING: {mobile_demos_path} not found.")
    print("  Run create_full_mobile_demographics.py first. Skipping mobile.")
else:
    mobile_raw = pd.read_parquet(mobile_demos_path)
    mobile = mobile_raw[mobile_raw["have_demos"] == 1].copy()
    print(f"  Analysis sample (have_demos==1): {len(mobile):,} machines")
    print(f"  Total in file (incl. no demos):  {len(mobile_raw):,} machines")

    print("  Building XXX visitor roster...")
    mobile_xxx_ids = build_xxx_roster(mobile_panel_dir)
    mobile["ever_xxx"] = mobile["machine_id"].isin(mobile_xxx_ids)
    n_xxx_mobile = mobile["ever_xxx"].sum()
    print(f"  XXX visitors: {n_xxx_mobile:,} ({n_xxx_mobile / len(mobile) * 100:.1f}% of analysis sample)")

    mobile = standardize_mobile(mobile)
    mobile_xxx = mobile[mobile["ever_xxx"]]

    mobile_vars = {
        "age":      "age",
        "hh_income":"hh_income_clean",
        "hh_size":  "hh_size_clean",
        "children": "children_clean",
        "gender":   "gender_clean",
        "race":     "race_clean",
        "hispanic": "hispanic_clean",
    }

    for var_label, col in mobile_vars.items():
        result = compute_shares(mobile[col], mobile_xxx[col], var_label)
        result.insert(0, "device_type", "mobile")
        all_results.append(result)

# ---- SAVE CSV ---------------------------------------------------------------
print("\n" + "=" * 80)
print("SAVING OUTPUT")
print("=" * 80)

output = pd.concat(all_results, ignore_index=True)
output = output[["device_type", "variable", "category",
                 "n_full", "share_full", "n_xxx", "share_xxx"]]

output.to_csv(output_path, index=False)
print(f"  Saved: {output_path}")

# ==============================================================================
# EXPORT HELPERS
# ==============================================================================

DESKTOP_VARS = ["age", "hh_income", "hh_size", "children"]
MOBILE_VARS  = ["age", "hh_income", "hh_size", "children", "gender", "race", "hispanic"]
VAR_LABELS   = {
    "age":      "Age",
    "hh_income":"Household Income",
    "hh_size":  "Household Size",
    "children": "Children Present",
    "gender":   "Gender",
    "race":     "Race",
    "hispanic": "Ethnicity",
}


def get_table_rows(df, device):
    vars_to_show = DESKTOP_VARS if device == "desktop" else MOBILE_VARS
    sub = df[(df["device_type"] == device) & (df["variable"].isin(vars_to_show))].copy()
    sub["var_order"] = sub["variable"].map({v: i for i, v in enumerate(vars_to_show)})
    sub = sub.sort_values("var_order", kind="stable").reset_index(drop=True)
    total_full = int(sub[sub["variable"] == "age"]["n_full"].sum())
    total_xxx  = int(sub[sub["variable"] == "age"]["n_xxx"].sum())
    return sub, total_full, total_xxx


# ---- LATEX ------------------------------------------------------------------
def export_latex(df, device, tex_path):
    sub, total_full, total_xxx = get_table_rows(df, device)
    title = device.capitalize()

    lines = []
    lines.append(r"\begin{table}[h]")
    lines.append(r"\centering")
    lines.append(rf"\caption{{{title} Sample Demographics}}")
    lines.append(r"\begin{tabular}{lrrrr}")
    lines.append(r"\toprule")
    lines.append(
        r" & \multicolumn{2}{c}{Full Sample} & \multicolumn{2}{c}{XXX Visitors} \\"
    )
    lines.append(
        rf" & \multicolumn{{2}}{{c}}{{(N = {total_full:,})}} "
        rf"& \multicolumn{{2}}{{c}}{{(N = {total_xxx:,})}} \\"
    )
    lines.append(r" & N & Share & N & Share \\")
    lines.append(r"\midrule")

    cur_var = None
    for _, row in sub.iterrows():
        if row["variable"] != cur_var:
            if cur_var is not None:
                lines.append(r"\\[-4pt]")
            label = VAR_LABELS[row["variable"]]
            lines.append(rf"\multicolumn{{5}}{{l}}{{\textit{{{label}}}}} \\")
            cur_var = row["variable"]
        n_f = int(row["n_full"]);  s_f = row["share_full"] * 100
        n_x = int(row["n_xxx"]);   s_x = row["share_xxx"]  * 100
        cat  = str(row["category"]).replace("%", r"\%").replace("&", r"\&")
        lines.append(
            rf"\quad {cat} & {n_f:,} & {s_f:.1f}\% & {n_x:,} & {s_x:.1f}\% \\"
        )

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    with open(tex_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {tex_path}")


# ---- MARKDOWN ---------------------------------------------------------------
def export_markdown(df, device, md_path):
    sub, total_full, total_xxx = get_table_rows(df, device)
    title = device.capitalize()

    lines = []
    lines.append(f"## {title} Sample Demographics")
    lines.append(f"N full sample = {total_full:,} | N XXX visitors = {total_xxx:,}")
    lines.append("")
    lines.append(f"| | Full sample N | Full sample % | XXX visitors N | XXX visitors % |")
    lines.append(f"|---|---:|---:|---:|---:|")

    cur_var = None
    for _, row in sub.iterrows():
        if row["variable"] != cur_var:
            label = VAR_LABELS[row["variable"]]
            lines.append(f"| **{label}** | | | | |")
            cur_var = row["variable"]
        n_f = int(row["n_full"]);  s_f = row["share_full"] * 100
        n_x = int(row["n_xxx"]);   s_x = row["share_xxx"]  * 100
        lines.append(
            f"| &nbsp;&nbsp;&nbsp;{row['category']} | {n_f:,} | {s_f:.1f}% | {n_x:,} | {s_x:.1f}% |"
        )

    with open(md_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved: {md_path}")


# ---- RUN EXPORTS ------------------------------------------------------------
for device in ["desktop", "mobile"]:
    if output["device_type"].eq(device).any():
        export_latex(output, device,
                     os.path.join(output_dir, f"demographic_summary_stats_{device}.tex"))
        export_markdown(output, device,
                        os.path.join(output_dir, f"demographic_summary_stats_{device}.md"))

print("\nPreview:")
print(output.head(20).to_string(index=False))
print("=" * 80)
print("COMPLETE")
print("=" * 80)
