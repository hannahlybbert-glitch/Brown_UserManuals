# Author: Hannah Lybbert
# Created: 04/24/2026
# Purpose: Demographic summary table for the exact regression analysis sample.
#          Reads stacked_panel.rds (built by prepare_combined.R) so that the
#          machine set is identical to what enters the regressions.
#
# Columns reported: age (6 bins), HH income (6 bins), children present,
#                   HH size (1/2/3/4/5+), N machines.
# Columns in table: Full sample | Ever-treated | Never-treated
#
# Requires: data/intermediate_combined/stacked_panel.rds
#           (re-run prepare_combined.R after adding hh_size to demo_slim)
#
# Outputs:
#   output/analysis/combined/summary_tables/demo_summary_table.md
#   output/analysis/combined/summary_tables/demo_summary_table.tex
#
# Usage:
#   Rscript code/analysis/create_demo_summary_tables.R

suppressPackageStartupMessages({
  library(dplyr)
  library(knitr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD & DEDUPLICATE TO UNIQUE MACHINES
# ============================================================================

cat("Loading stacked panel...\n")
sp           <- readRDS(file.path(int_dir, "stacked_panel.rds"))
stacked_base <- sp$stacked_base
if (!is.null(MOBILE_FILTER)) stacked_base <- stacked_base[stacked_base$mobile == MOBILE_FILTER, ]

cat(sprintf("  Stacked rows: %s\n", format(nrow(stacked_base), big.mark = ",")))

# Collapse to one row per machine.
# ever_treated: 1 if the machine appears as treated == 1 in any cohort slice
# (i.e. it is from a treated state and observed in its own cohort's window).
machines <- stacked_base |>
  group_by(machine_id) |>
  summarise(
    ever_treated    = as.integer(max(treated) == 1),
    gender          = first(gender),
    hoh_age         = first(hoh_age),
    children_present = first(children_present),
    hh_income       = first(hh_income),
    hh_size         = first(hh_size),
    mobile          = first(mobile),
    .groups = "drop"
  )

n_total  <- nrow(machines)
n_ever   <- sum(machines$ever_treated == 1L)
n_never  <- sum(machines$ever_treated == 0L)

cat(sprintf("  Unique machines: %s\n",    format(n_total, big.mark = ",")))
cat(sprintf("  Ever-treated:    %s\n",    format(n_ever,  big.mark = ",")))
cat(sprintf("  Never-treated:   %s\n\n",  format(n_never, big.mark = ",")))

full  <- machines
ever  <- machines |> filter(ever_treated == 1L)
never <- machines |> filter(ever_treated == 0L)

GROUPS      <- list("Full Sample" = full, "Never-Treated" = never, "Ever-Treated" = ever)
GROUP_NAMES <- names(GROUPS)
GROUP_N     <- c(n_total, n_never, n_ever)

# ============================================================================
# HELPERS
# ============================================================================

# Share of non-NA values matching a level, formatted as "XX.X%"
share <- function(df, col, level) {
  vals <- df[[col]]
  n    <- sum(!is.na(vals))
  if (n == 0L) return("—")
  sprintf("%.1f%%", 100 * sum(vals == level, na.rm = TRUE) / n)
}

# ============================================================================
# DEFINE ROWS
# ============================================================================

AGE_LEVELS    <- c("18-24", "25-34", "35-44", "45-54", "55-64", "65 and Over")
INCOME_LEVELS <- c("HHI:Less than 25k", "HHI:25k-39k", "HHI:40k-59k",
                   "HHI:60k-74k",       "HHI:75k-99k", "HHI:100k+")
INCOME_LABELS <- c("Less than $25k", "$25k–$39k", "$40k–$59k",
                   "$60k–$74k",      "$75k–$99k", "$100k+")
CHILDREN_LEVELS <- c("Yes", "No")
HH_SIZE_LEVELS  <- c("HH Size:1", "HH Size:2", "HH Size:3", "HH Size:4", "HH Size:5 or More")
HH_SIZE_LABELS  <- c("1", "2", "3", "4", "5+")

AGE_DISPLAY       <- c("18-24", "25-34", "35-44", "45-54", "55-64", "65+")
INCOME_LABELS_TEX <- c("$<$ 25k", "$25k-39k$", "$40k-59k$",
                        "$60k-74k$", "$75k-99k$", "$100k+$")

build_section <- function(header, col, levels, labels = levels) {
  rows <- lapply(seq_along(levels), function(i) {
    vals <- sapply(GROUPS, function(g) share(g, col, levels[i]))
    c(labels[i], vals)
  })
  rbind(
    c(header, rep("", length(GROUPS))),
    do.call(rbind, rows)
  )
}

# Children present: single row (share = Yes)
children_row <- c(
  "Children present",
  sapply(GROUPS, function(g) share(g, "children_present", "Children:Yes"))
)

# N row
n_row <- c("N (machines)", format(GROUP_N, big.mark = ","))

# Assemble table body
body <- rbind(
  build_section("Age", "hoh_age", AGE_LEVELS),
  build_section("HH Income", "hh_income", INCOME_LEVELS, INCOME_LABELS),
  children_row,
  build_section("HH Size", "hh_size", HH_SIZE_LEVELS, HH_SIZE_LABELS),
  n_row
)

tbl           <- as.data.frame(body, stringsAsFactors = FALSE)
colnames(tbl) <- c(" ", GROUP_NAMES)
rownames(tbl) <- NULL

# ============================================================================
# CONSOLE PREVIEW
# ============================================================================

cat("=" , strrep("=", 64), "\n", sep = "")
cat("  DEMOGRAPHIC SUMMARY TABLE\n")
cat("=", strrep("=", 64), "\n", sep = "")
print(tbl, row.names = FALSE)

# ============================================================================
# WRITE OUTPUTS
# ============================================================================

out_dir <- file.path(out_base, "summary_tables")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

note <- paste0(
  "Sample: unique machines from stacked_panel.rds (prepare_combined.R). ",
  "Ever-treated = machine appears as treated == 1 in at least one cohort slice. ",
  "Shares exclude missing values from the denominator. ",
  "Age and income bins are harmonised across desktop and mobile."
)

cap <- "Demographic Characteristics of the Analysis Sample"

md_path  <- file.path(out_dir, "demo_summary_table.md")
tex_path <- file.path(out_dir, "demo_summary_table.tex")

writeLines(
  c("# Demographic Summary Table", "", note, "", kable(tbl, format = "markdown")),
  md_path
)
cat(sprintf("Wrote: %s\n", md_path))

tex_pct     <- function(x) gsub("%", "\\\\%", x)
tex_row     <- function(label, vals) paste0(paste(c(label, vals), collapse = " & "), " \\\\")
sec_hdr     <- function(title) sprintf("\\multicolumn{%d}{l}{\\textit{%s}} \\\\", length(GROUPS) + 1L, title)
tex_data_row <- function(display_label, col, level) {
  vals <- tex_pct(sapply(GROUPS, function(g) share(g, col, level)))
  tex_row(paste0("\\quad ", display_label), vals)
}

tex_lines <- c(
  "\\begin{tabular}{lrrr}",
  "\\toprule",
  tex_row("", GROUP_NAMES),
  tex_row("", sprintf("(N = %s)", format(GROUP_N, big.mark = ","))),
  "\\midrule",
  sec_hdr("Age"),
  unname(mapply(tex_data_row, AGE_DISPLAY,       "hoh_age",          AGE_LEVELS)),
  sec_hdr("Household Income"),
  unname(mapply(tex_data_row, INCOME_LABELS_TEX, "hh_income",        INCOME_LEVELS)),
  sec_hdr("Children Present"),
  tex_data_row("Yes", "children_present", "Children:Yes"),
  sec_hdr("Household Size"),
  unname(mapply(tex_data_row, HH_SIZE_LABELS,    "hh_size",          HH_SIZE_LEVELS)),
  "\\bottomrule",
  "\\end{tabular}"
)

writeLines(tex_lines, tex_path)
cat(sprintf("Wrote: %s\n", tex_path))

cat("\nAll done.\n")
