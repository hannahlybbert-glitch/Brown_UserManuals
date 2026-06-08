# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-12
# Purpose: Build a 25-row table of states where Pornhub shut down,
#          with their law effective date and PH shutdown date.
#
# Requires:
#   raw/statelaws/phshutdown_dates.csv
#   raw/statelaws/statelaws_dates.csv
#
# Outputs:
#   output/ProcessAuxiliary/shutdown_dates_states.tex
#   output/ProcessAuxiliary/shutdown_dates_states.md
#
# Usage:
#   python code/ProcessAuxiliary/shutdown_dates_states.py

import os
import pandas as pd
from datetime import datetime

# ============================================================================
# PATHS
# ============================================================================

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ph_path   = os.path.join(ROOT, "raw", "statelaws", "phshutdown_dates.csv")
laws_path = os.path.join(ROOT, "raw", "statelaws", "statelaws_dates.csv")
out_dir   = os.path.join(ROOT, "output", "ProcessAuxiliary")
os.makedirs(out_dir, exist_ok=True)

# ============================================================================
# STATE NAMES
# ============================================================================

STATE_NAMES = {
    "AL": "Alabama",       "AK": "Alaska",         "AZ": "Arizona",
    "AR": "Arkansas",      "CA": "California",      "CO": "Colorado",
    "CT": "Connecticut",   "DE": "Delaware",        "FL": "Florida",
    "GA": "Georgia",       "HI": "Hawaii",          "ID": "Idaho",
    "IL": "Illinois",      "IN": "Indiana",         "IA": "Iowa",
    "KS": "Kansas",        "KY": "Kentucky",        "LA": "Louisiana",
    "ME": "Maine",         "MD": "Maryland",        "MA": "Massachusetts",
    "MI": "Michigan",      "MN": "Minnesota",       "MS": "Mississippi",
    "MO": "Missouri",      "MT": "Montana",         "NE": "Nebraska",
    "NV": "Nevada",        "NH": "New Hampshire",   "NJ": "New Jersey",
    "NM": "New Mexico",    "NY": "New York",        "NC": "North Carolina",
    "ND": "North Dakota",  "OH": "Ohio",            "OK": "Oklahoma",
    "OR": "Oregon",        "PA": "Pennsylvania",    "RI": "Rhode Island",
    "SC": "South Carolina","SD": "South Dakota",    "TN": "Tennessee",
    "TX": "Texas",         "UT": "Utah",            "VT": "Vermont",
    "VA": "Virginia",      "WA": "Washington",      "WV": "West Virginia",
    "WI": "Wisconsin",     "WY": "Wyoming",
}

# ============================================================================
# DATE HELPERS
# ============================================================================

def parse_date(val):
    if pd.isna(val) or str(val).strip() == "":
        return None
    s = str(val).strip()
    for fmt in ("%d%b%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {val!r}")

def fmt_date(dt):
    """Format datetime as 'Month D, YYYY' (no leading zero on day)."""
    if dt is None:
        return ""
    return dt.strftime(f"%B {dt.day}, %Y")

# ============================================================================
# LOAD & MERGE
# ============================================================================

ph   = pd.read_csv(ph_path)
laws = pd.read_csv(laws_path, na_values=["", "NA"])

df = ph.merge(laws[["state", "day_effective"]], on="state", how="left")

df["_ph_dt"]  = df["date_PH_shutdown"].apply(parse_date)
df["_law_dt"] = df["day_effective"].apply(parse_date)

df = df.sort_values("_ph_dt").reset_index(drop=True)

rows = []
for _, r in df.iterrows():
    rows.append({
        "State":            STATE_NAMES.get(r["state"], r["state"]),
        "Date Effective":   fmt_date(r["_law_dt"]),
        "Date Pornhub Shutdown": fmt_date(r["_ph_dt"]),
    })

# ============================================================================
# MARKDOWN
# ============================================================================

md_lines = [
    "| State | Date Effective | Date Pornhub Shutdown |",
    "| --- | --- | --- |",
]
for r in rows:
    md_lines.append(f"| {r['State']} | {r['Date Effective']} | {r['Date Pornhub Shutdown']} |")

md_path = os.path.join(out_dir, "shutdown_dates_states.md")
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines) + "\n")
print(f"Wrote: {md_path}")

# ============================================================================
# LATEX
# ============================================================================

def esc(s):
    """Escape LaTeX special characters in a plain string."""
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")

tex_rows = []
for r in rows:
    tex_rows.append(
        f"  {esc(r['State'])} & {esc(r['Date Effective'])} & {esc(r['Date Pornhub Shutdown'])} \\\\"
    )

tex_lines = [
    r"\begin{tabular}{lll}",
    r"\toprule",
    r"  State & Date Effective & Date Pornhub Shutdown \\",
    r"\midrule",
] + tex_rows + [
    r"\bottomrule",
    r"\end{tabular}",
]

tex_path = os.path.join(out_dir, "shutdown_dates_states.tex")
with open(tex_path, "w", encoding="utf-8") as f:
    f.write("\n".join(tex_lines) + "\n")
print(f"Wrote: {tex_path}")
