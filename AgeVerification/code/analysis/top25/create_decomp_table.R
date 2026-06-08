# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-29
# Purpose: Regression table for the five decomposition groups used in the
#          waterfall figure (Pornhub, Other Compliant, XVideos, XNXX,
#          Other Noncompliant).  Shows pre, short-term, and long-term ATT.
#
# Requires:
#   output/analysis/combined/top_25/intermediate/regression_results_top25.rds
#
# Output:
#   output/analysis/combined/top_25/decomp_regression_table.md
#   output/analysis/combined/top_25/decomp_regression_table.tex
#
# Usage:
#   Rscript code/analysis/top25/create_decomp_table.R

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
# GROUPS
# ============================================================================

groups <- list(
  list(label = "Pornhub",            slug = "PORNHUB_COM"),
  list(label = "Other Compliant",    slug = "other_compliant"),
  list(label = "XVideos",            slug = "XVIDEOS_COM"),
  list(label = "XNXX",               slug = "XNXX_COM"),
  list(label = "Other Noncompliant", slug = "other_noncompliant_top25")
)

# ============================================================================
# FORMATTING HELPERS
# ============================================================================

stars <- function(p) {
  dplyr::case_when(
    is.na(p) ~ "",
    p < 0.01 ~ "***",
    p < 0.05 ~ "**",
    p < 0.10 ~ "*",
    TRUE     ~ ""
  )
}

esc_latex <- function(s) {
  s <- as.character(s)
  s <- gsub("&",   "\\\\&",  s)
  s <- gsub("%",   "\\\\%",  s)
  s <- gsub("_",   "\\\\_",  s)
  s <- gsub("#",   "\\\\#",  s)
  s <- gsub("\\$", "\\\\$",  s)
  s
}

# ============================================================================
# BUILD TABLE DATA
# ============================================================================

tbl_raw <- lapply(groups, function(g) {
  entry <- results$pooled[[g$slug]]
  if (is.null(entry)) stop(sprintf("Slug not found: %s", g$slug))
  res <- entry$win_min
  data.frame(
    group         = g$label,
    beta_pre      = res$beta_pre,
    se_pre        = res$se_pre,
    p_pre         = res$p_pre,
    beta_st       = res$beta_shortterm,
    se_st         = res$se_shortterm,
    p_st          = res$p_shortterm,
    beta_lt       = res$beta_longterm,
    se_lt         = res$se_longterm,
    p_lt          = res$p_longterm,
    baseline_mean = entry$baseline_mean,
    n_obs         = res$n_obs,
    stringsAsFactors = FALSE
  )
}) |> dplyr::bind_rows()

# ============================================================================
# MARKDOWN TABLE
# ============================================================================

fmt_est <- function(b, p) sprintf("%.4f%s", b, stars(p))
fmt_se  <- function(s)    sprintf("(%.4f)", s)

tbl_md <- tbl_raw |>
  mutate(
    Group            = group,
    `beta_pre`       = fmt_est(beta_pre, p_pre),
    `(SE) pre`       = fmt_se(se_pre),
    `beta_ST`        = fmt_est(beta_st,  p_st),
    `(SE) ST`        = fmt_se(se_st),
    `beta_LT`        = fmt_est(beta_lt,  p_lt),
    `(SE) LT`        = fmt_se(se_lt),
    `Baseline Mean`  = sprintf("%.4f", baseline_mean),
    `N (obs)`        = format(n_obs, big.mark = ",")
  ) |>
  select(Group, `beta_pre`, `(SE) pre`, `beta_ST`, `(SE) ST`,
         `beta_LT`, `(SE) LT`, `Baseline Mean`, `N (obs)`)

note <- paste0(
  "Stacked TWFE: win_min ~ treated:pre + treated:shortterm + treated:longterm | ",
  "machine_cohort + cohort_week. SE clustered by state. ",
  "Pre: tau in [-4,-1]; ST: tau in [0,3]; LT: tau in [4,8]. ",
  "Baseline mean: treatment group week -1. ",
  "* p<0.10, ** p<0.05, *** p<0.01. Combined (desktop + mobile)."
)

md_path <- file.path(out_dir, "decomp_regression_table.md")
writeLines(
  c("# Decomposition Groups — Regression Results (win_min)", "", note, "",
    kable(tbl_md, format = "markdown", row.names = FALSE)),
  md_path
)
cat(sprintf("Wrote: %s\n", md_path))

# ============================================================================
# LATEX TABLE
# Coefficient row + SE row per group.
# ============================================================================

tex_data_rows <- unlist(lapply(seq_len(nrow(tbl_raw)), function(i) {
  r <- tbl_raw[i, ]
  coef_row <- sprintf(
    "  %s & %s & %s & %s & %s & %s \\\\",
    esc_latex(r$group),
    sprintf("%.4f%s", r$beta_pre, stars(r$p_pre)),
    sprintf("%.4f%s", r$beta_st,  stars(r$p_st)),
    sprintf("%.4f%s", r$beta_lt,  stars(r$p_lt)),
    sprintf("%.4f",   r$baseline_mean),
    format(r$n_obs, big.mark = ",")
  )
  se_row <- sprintf(
    "    & %s & %s & %s &  &  \\\\",
    sprintf("(%.4f)", r$se_pre),
    sprintf("(%.4f)", r$se_st),
    sprintf("(%.4f)", r$se_lt)
  )
  c(coef_row, se_row)
}))

tex_lines <- c(
  "\\begin{tabular}{lrrrrl}",
  "\\toprule",
  paste0("  Group & $\\hat{\\beta}_{\\mathrm{pre}}$ & ",
         "$\\hat{\\beta}_{\\mathrm{ST}}$ & ",
         "$\\hat{\\beta}_{\\mathrm{LT}}$ & ",
         "Baseline Mean & N (obs) \\\\"),
  "\\midrule",
  tex_data_rows,
  "\\bottomrule",
  "\\end{tabular}"
)

tex_path <- file.path(out_dir, "decomp_regression_table.tex")
writeLines(tex_lines, tex_path)
cat(sprintf("Wrote: %s\n", tex_path))

cat("\nAll done.\n")
