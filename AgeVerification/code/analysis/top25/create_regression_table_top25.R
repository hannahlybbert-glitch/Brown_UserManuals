# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Build regression table for top-25 adult sites.
#          Sites as rows; columns show long-term ATT, SE, baseline mean, N.
#
# Requires:
#   output/analysis/combined/top_25/intermediate/regression_results_top25.rds
#
# Output:
#   output/analysis/combined/top_25/top25_regression_table.md
#   output/analysis/combined/top_25/top25_regression_table.tex
#
# Usage:
#   Rscript code/analysis/top25/create_regression_table_top25.R

suppressPackageStartupMessages({
  library(dplyr)
  library(knitr)
  library(here)
})

Sys.setenv(ANALYSIS_MODE = "combined")
source(here::here("code", "analysis", "_source", "config.R"))

out_dir      <- file.path(here::here(), "output", "analysis", "combined", "top_25")
results_path <- file.path(out_dir, "intermediate", "regression_results_top25.rds")

cat("Loading results...\n")
results <- readRDS(results_path)
if (length(results$pooled) == 0L) stop("results$pooled is empty.")

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

esc_latex <- function(s) {
  s <- as.character(s)
  s <- gsub("&",  "\\\\&",  s)
  s <- gsub("%",  "\\\\%",  s)
  s <- gsub("_",  "\\\\_",  s)
  s <- gsub("#",  "\\\\#",  s)
  s <- gsub("\\$", "\\\\$", s)
  s
}

# ============================================================================
# BUILD TABLE DATA
# ============================================================================

rows <- lapply(results$pooled, function(entry) {
  if (is.null(entry$rank)) return(NULL)  # skip combined virtual sites
  res <- entry$win_min
  data.frame(
    rank          = entry$rank,
    site          = entry$key,
    beta_lt       = res$beta_longterm,
    se_lt         = res$se_longterm,
    p_lt          = res$p_longterm,
    baseline_mean = entry$baseline_mean,
    n_obs         = res$n_obs,
    stringsAsFactors = FALSE
  )
})

tbl_raw <- dplyr::bind_rows(rows) |> dplyr::arrange(rank)

# ============================================================================
# MARKDOWN TABLE
# ============================================================================

tbl_md <- tbl_raw |>
  mutate(
    `beta_LT`      = ifelse(is.na(beta_lt), "—",
                            sprintf("%.4f%s", beta_lt, stars(p_lt))),
    `(SE)`         = ifelse(is.na(se_lt), "",
                            sprintf("(%.4f)", se_lt)),
    `Baseline Mean`= sprintf("%.4f", baseline_mean),
    `N (obs)`      = format(n_obs, big.mark = ",")
  ) |>
  select(Rank = rank, Site = site, `beta_LT`, `(SE)`, `Baseline Mean`, `N (obs)`)

note <- paste0(
  "Stacked TWFE: win_min ~ treated:pre + treated:shortterm + treated:longterm | ",
  "machine_cohort + cohort_week. SE clustered by state. ",
  "beta_LT: tau in [4,8]. Baseline mean: treatment group week -1. ",
  "* p<0.10, ** p<0.05, *** p<0.01. Combined (desktop + mobile)."
)

md_path <- file.path(out_dir, "top25_regression_table.md")
writeLines(
  c("# Top-25 Adult Sites — Long-term ATT (win_min)", "", note, "",
    kable(tbl_md, format = "markdown", row.names = FALSE)),
  md_path
)
cat(sprintf("Wrote: %s\n", md_path))

# ============================================================================
# LATEX TABLE
# One data row + one SE row per site, no tabular wrapper artifacts.
# ============================================================================

tex_data_rows <- unlist(lapply(seq_len(nrow(tbl_raw)), function(i) {
  r   <- tbl_raw[i, ]
  est <- if (is.na(r$beta_lt)) "---" else
         sprintf("%.4f%s", r$beta_lt, stars(r$p_lt))
  se  <- if (is.na(r$se_lt)) "" else sprintf("(%.4f)", r$se_lt)
  bm  <- sprintf("%.4f", r$baseline_mean)
  n   <- format(r$n_obs, big.mark = ",")
  site_esc <- esc_latex(r$site)
  c(
    sprintf("  %d & %s & %s & %s & %s \\\\", r$rank, site_esc, est, bm, n),
    sprintf("    &   & %s &   &   \\\\", se)
  )
}))

tex_lines <- c(
  "\\begin{tabular}{rlrrl}",
  "\\toprule",
  "  Rank & Site & $\\hat{\\beta}_{\\mathrm{LT}}$ & Baseline Mean & N (obs) \\\\",
  "\\midrule",
  tex_data_rows,
  "\\bottomrule",
  "\\end{tabular}"
)

tex_path <- file.path(out_dir, "top25_regression_table.tex")
writeLines(tex_lines, tex_path)
cat(sprintf("Wrote: %s\n", tex_path))

cat("\nAll done.\n")
