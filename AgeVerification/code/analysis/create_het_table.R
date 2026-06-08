# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-15
# Purpose: Heterogeneity regression table — long-term ATT by subgroup × site.
#   Rows:    18 subgroups organised into 7 groups (Gender, Age, Income,
#            Children Present (Desktop), Device Type, XXX Usage Tercile,
#            PH Usage Tercile). Mirrors ALL_GROUPS_PCT_NOLIGHT in figures.
#   Columns: Pornhub | xVideos | XNXX | Other XXX | All XXX
#   Cells:   beta_LT with significance stars / SE in parentheses below.
#
# Requires: output/.../intermediate/het_multisite_results.rds
#           (produced by create_het_main_regressions.R)
#
# Outputs (output/.../heterogeneity_tables/):
#   het_table.md
#   het_table.tex

suppressPackageStartupMessages({
  library(dplyr)
  library(knitr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD
# ============================================================================

cat("Loading het_multisite_results...\n")
inp     <- readRDS(file.path(out_int_dir, "het_multisite_results.rds"))
res_df  <- inp$res_df
diff_df <- inp$diff_df

if (nrow(res_df) == 0L) stop("het_multisite_results.rds is empty.")

# ============================================================================
# STRUCTURE DEFINITIONS  (mirrors create_het_main_figures.R)
# ============================================================================

SITES_TABLE <- list(
  list(slug = "PORNHUB_COM",       label = "Pornhub"),
  list(slug = "XVIDEOS_COM",       label = "xVideos"),
  list(slug = "XNXX_COM",          label = "XNXX"),
  list(slug = "other_xxx_combined",label = "Other XXX"),
  list(slug = "all_xxx",           label = "All XXX")
)
SITE_LABELS <- sapply(SITES_TABLE, `[[`, "label")

ALL_GROUPS <- list(
  "Gender"                     = c("Gender: Male",              "Gender: Female",     "Gender: Shared",     "Gender: Unknown"),
  "Age"                        = c("Age: 18-24",                "Age: 25-44",         "Age: 45+"),
  "Income"                     = c("Income: <$60k",             "Income: $60k-$99k",  "Income: $100k+"),
  "Children Present (Desktop)" = c("Children in Desktop: Yes",  "Children in Desktop: No"),
  "Device Type"                = c("Device: Desktop",           "Device: Mobile"),
  "XXX Usage Tercile"          = c("XXX Tercile: Moderate",     "XXX Tercile: Heavy"),
  "PH Usage Tercile"           = c("PH Tercile: Moderate",      "PH Tercile: Heavy")
)

DISPLAY_LABELS <- c(
  "Gender: Male"               = "Male",
  "Gender: Female"             = "Female",
  "Gender: Shared"             = "Shared",
  "Gender: Unknown"            = "Unknown",
  "Age: 18-24"                 = "18–24",
  "Age: 25-44"                 = "25–44",
  "Age: 45+"                   = "45+",
  "Income: <$60k"              = "<$60k",
  "Income: $60k-$99k"          = "$60k–$99k",
  "Income: $100k+"             = "$100k+",
  "Children in Desktop: Yes"   = "Yes",
  "Children in Desktop: No"    = "No",
  "Device: Desktop"            = "Desktop",
  "Device: Mobile"             = "Mobile",
  "XXX Tercile: Moderate"      = "XXX Moderate",
  "XXX Tercile: Heavy"         = "XXX Heavy",
  "PH Tercile: Moderate"       = "PH Moderate",
  "PH Tercile: Heavy"          = "PH Heavy"
)

# ============================================================================
# FORMATTING HELPERS
# ============================================================================

stars <- function(p) {
  dplyr::case_when(
    is.na(p)  ~ "",
    p < 0.01  ~ "***",
    p < 0.05  ~ "**",
    p < 0.10  ~ "*",
    TRUE      ~ ""
  )
}

# Normalise site labels to match SITE_LABELS
res_df <- res_df |>
  mutate(site_label = dplyr::recode(site,
    "Pornhub"              = "Pornhub",
    "xVideos"              = "xVideos",
    "XNXX"                 = "XNXX",
    "Other XXX (combined)" = "Other XXX",
    "All XXX (pooled)"     = "All XXX"
  ),
  est_str  = ifelse(is.na(beta_lt), "—",
                    sprintf("%.3f%s", beta_lt, stars(p_lt))),
  se_str   = ifelse(is.na(se_lt),   "",
                    sprintf("(%.3f)", se_lt)),
  pval_str = ifelse(is.na(p_lt), "—", sprintf("%.6f", p_lt))
  )

# Lookup helpers: group × site → est or SE string
lookup <- function(sg, sl, col) {
  d <- res_df[res_df$group == sg & res_df$site_label == sl, col, drop = TRUE]
  if (length(d) == 0L) return(if (col == "est_str") "—" else "")
  d[[1L]]
}

# ============================================================================
# BUILD TABLE ROWS
# ============================================================================
# Each group gets:  one header row (label only)
# Each subgroup gets: one estimate row + one SE row

make_blank  <- function() setNames(rep("", length(SITE_LABELS) + 1L), c("Subgroup", SITE_LABELS))
make_header <- function(grp) {
  r <- make_blank()
  r[["Subgroup"]] <- grp
  r
}
make_est <- function(sg) {
  r <- make_blank()
  r[["Subgroup"]] <- paste0("  ", DISPLAY_LABELS[[sg]])
  for (sl in SITE_LABELS) r[[sl]] <- lookup(sg, sl, "est_str")
  r
}
make_se <- function(sg) {
  r <- make_blank()
  for (sl in SITE_LABELS) r[[sl]] <- lookup(sg, sl, "se_str")
  r
}

rows <- list()
for (grp in names(ALL_GROUPS)) {
  rows <- c(rows, list(make_header(grp)))
  for (sg in ALL_GROUPS[[grp]]) {
    rows <- c(rows, list(make_est(sg)), list(make_se(sg)))
  }
}

tbl <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)

# ============================================================================
# BUILD P-VALUE TABLE
# ============================================================================

make_pval <- function(sg) {
  r <- make_blank()
  r[["Subgroup"]] <- paste0("  ", DISPLAY_LABELS[[sg]])
  for (sl in SITE_LABELS) r[[sl]] <- lookup(sg, sl, "pval_str")
  r
}

pval_rows <- list()
for (grp in names(ALL_GROUPS)) {
  pval_rows <- c(pval_rows, list(make_header(grp)))
  for (sg in ALL_GROUPS[[grp]]) {
    pval_rows <- c(pval_rows, list(make_pval(sg)))
  }
}

pval_tbl <- as.data.frame(do.call(rbind, pval_rows), stringsAsFactors = FALSE)

# ============================================================================
# WRITE OUTPUTS
# ============================================================================

out_dir <- file.path(out_base, "heterogeneity_plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

note <- paste0(
  "Long-term ATT (tau = 4 to 8 weeks). ",
  "Stacked TWFE: dv ~ treated:longterm | machine_cohort + cohort_week. ",
  "SE clustered by state. Outcome: winsorized minutes per machine per week. ",
  "* p<0.10, ** p<0.05, *** p<0.01. SE in parentheses."
)

md_path  <- file.path(out_dir, "het_table.md")
tex_path <- file.path(out_dir, "het_table.tex")

writeLines(
  c("# Heterogeneity — Long-term ATT by Subgroup and Site", "", note, "",
    kable(tbl, format = "markdown", row.names = FALSE)),
  md_path
)
cat(sprintf("Wrote: %s\n", md_path))

writeLines(
  kable(tbl, format = "latex", booktabs = TRUE, row.names = FALSE),
  tex_path
)
cat(sprintf("Wrote: %s\n", tex_path))

pval_md_path  <- file.path(out_dir, "het_table_pvals.md")
pval_tex_path <- file.path(out_dir, "het_table_pvals.tex")

pval_note <- paste0(
  "Long-term ATT p-values (tau = 4 to 8 weeks). ",
  "Stacked TWFE: dv ~ treated:longterm | machine_cohort + cohort_week. ",
  "SE clustered by state. Outcome: winsorized minutes per machine per week. ",
  "p = 2 * (1 - pnorm(|beta / SE|))."
)

writeLines(
  c("# Heterogeneity — Long-term ATT p-values by Subgroup and Site", "",
    pval_note, "",
    kable(pval_tbl, format = "markdown", row.names = FALSE)),
  pval_md_path
)
cat(sprintf("Wrote: %s\n", pval_md_path))

writeLines(
  kable(pval_tbl, format = "latex", booktabs = TRUE, row.names = FALSE),
  pval_tex_path
)
cat(sprintf("Wrote: %s\n", pval_tex_path))

diff_csv_path <- file.path(out_dir, "het_diff_pvals.csv")
write.csv(diff_df, diff_csv_path, row.names = FALSE)
cat(sprintf("Wrote: %s\n", diff_csv_path))

cat("\nAll done.\n")
