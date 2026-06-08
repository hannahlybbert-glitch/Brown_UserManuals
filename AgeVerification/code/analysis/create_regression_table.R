# Author: Matt Brown, assisted by Claude
# Created: 2026-03-07
# Purpose: Generate regression output table from saved homogeneous pooled ATT
#          results. Builds a manual β/SE/N/R² table without requiring fit objects.
#
# Requires: output/analysis/intermediate/regression_results.rds
#           (produced by run_regressions.R with RUN_HOMOGENEOUS_POOLED = TRUE)
#
# Outputs:
#   output/analysis/full_sample_table.md  — markdown table
#   output/analysis/full_sample_table.tex — LaTeX table (knitr::kable)
#
# Usage:
#   Rscript code/analysis/create_summary_table.R

suppressPackageStartupMessages({
  library(dplyr)
  library(knitr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD RESULTS
# ============================================================================

cat("Loading regression results...\n")
results <- readRDS(file.path(out_int_dir, "regression_results.rds"))

if (length(results$pooled) == 0L) {
  stop("results$pooled is empty. Re-run run_regressions.R with RUN_HOMOGENEOUS_POOLED = TRUE.")
}

cat("Loading stacked panel to count unique machines...\n")
sp <- readRDS(file.path(int_dir, "stacked_panel.rds"))
stacked_tmp <- sp$stacked_base
if (!is.null(MOBILE_FILTER)) stacked_tmp <- stacked_tmp[stacked_tmp$mobile == MOBILE_FILTER, ]
n_unique_machines <- dplyr::n_distinct(stacked_tmp$machine_id)
cat(sprintf("  Unique machines in stacked panel: %s\n",
            format(n_unique_machines, big.mark = ",")))
rm(sp, stacked_tmp)

# SITES_FULL, dvs, DV_METADATA sourced from config.R
# Main table: PH, xVideos, XNXX, Other XXX (combined regression), All XXX.
ACTIVE_SITES <- SITES_FULL[match(
  c("PORNHUB_COM", "XVIDEOS_COM", "XNXX_COM", "other_xxx_combined", "all_xxx"),
  sapply(SITES_FULL, `[[`, "slug")
)]

# ============================================================================
# FORMATTING HELPERS
# ============================================================================

stars <- function(p) {
  if (is.na(p))    return("")
  if (p < 0.01)    return("***")
  if (p < 0.05)    return("**")
  if (p < 0.10)    return("*")
  return("")
}

fmt_est <- function(beta, se, p) {
  if (is.na(beta)) return(c("---", ""))
  c(sprintf("%.4f%s", beta, stars(p)),
    sprintf("(%.4f)", se))
}

# ============================================================================
# BUILD ONE TABLE PER DV
# ============================================================================

# For each DV: rows = (β_pre, SE, β_ST, SE, β_LT, SE, N_obs, N_mc)
#              cols = one per site in SITES_FULL

row_labels <- c("$\\beta_{\\mathrm{pre}}$", "", "$\\beta_{\\mathrm{ST}}$", "",
                "$\\beta_{\\mathrm{LT}}$", "", "Baseline mean", "N (obs)", "N (machines)")

make_dv_table <- function(dv) {
  col_names <- sapply(ACTIVE_SITES, `[[`, "label")

  site_cols <- lapply(ACTIVE_SITES, function(site) {
    res <- results$pooled[[site$slug]][[dv]]
    if (is.null(res)) return(rep(NA_character_, 9))
    pre_fmt <- fmt_est(res$beta_pre,       res$se_pre,       res$p_pre)
    st_fmt  <- fmt_est(res$beta_shortterm, res$se_shortterm, res$p_shortterm)
    lt_fmt  <- fmt_est(res$beta_longterm,  res$se_longterm,  res$p_longterm)
    bm     <- results$event[[site$slug]][[dv]]$baseline_mean
    bm_fmt <- if (!is.null(bm) && !is.na(bm)) sprintf("%.4f", bm) else "\u2014"
    c(pre_fmt[1], pre_fmt[2],
      st_fmt[1],  st_fmt[2],
      lt_fmt[1],  lt_fmt[2],
      bm_fmt,
      format(res$n_obs,         big.mark = ","),
      format(n_unique_machines, big.mark = ","))
  })

  tbl <- as.data.frame(site_cols, stringsAsFactors = FALSE)
  colnames(tbl) <- col_names
  cbind(` ` = row_labels, tbl, stringsAsFactors = FALSE)
}

# ============================================================================
# P-VALUE TABLE
# ============================================================================

pval_row_labels <- c("$p_{\\mathrm{pre}}$", "$p_{\\mathrm{ST}}$",
                     "$p_{\\mathrm{LT}}$", "Baseline mean",
                     "N (obs)", "N (machines)")

fmt_pval <- function(p) if (is.na(p)) "---" else sprintf("%.6f", p)

make_dv_pval_table <- function(dv) {
  col_names <- sapply(ACTIVE_SITES, `[[`, "label")

  site_cols <- lapply(ACTIVE_SITES, function(site) {
    res <- results$pooled[[site$slug]][[dv]]
    if (is.null(res)) return(rep(NA_character_, 6))
    bm     <- results$event[[site$slug]][[dv]]$baseline_mean
    bm_fmt <- if (!is.null(bm) && !is.na(bm)) sprintf("%.4f", bm) else "—"
    c(fmt_pval(res$p_pre),
      fmt_pval(res$p_shortterm),
      fmt_pval(res$p_longterm),
      bm_fmt,
      format(res$n_obs,         big.mark = ","),
      format(n_unique_machines, big.mark = ","))
  })

  tbl <- as.data.frame(site_cols, stringsAsFactors = FALSE)
  colnames(tbl) <- col_names
  cbind(` ` = pval_row_labels, tbl, stringsAsFactors = FALSE)
}

# ============================================================================
# WRITE OUTPUTS
# ============================================================================

out_dir <- file.path(out_base, "full_sample")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

note <- paste0(
  "Stacked TWFE: dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week. ",
  "SE clustered by state. beta_pre: tau in [-16,-5]; beta_ST: tau in [0,3]; beta_LT: tau in [4,8]. ",
  "Baseline mean: treatment group mean in weeks -4 to -1. ",
  "* p<0.10, ** p<0.05, *** p<0.01. SE in parentheses."
)

for (dv in "win_min") {  # change to `dvs` to run both DVs
  tbl       <- make_dv_table(dv)
  dv_label  <- DV_METADATA[[dv]]$short
  cap       <- sprintf("Pooled ATT — stacked TWFE. Outcome: %s", dv_label)

  md_path  <- file.path(out_dir, sprintf("full_sample_table_%s.md",  dv))
  tex_path <- file.path(out_dir, sprintf("full_sample_table_%s.tex", dv))

  # Strip parentheticals from labels; embed column numbers in headers
  clean_labels  <- gsub(" \\(.*\\)", "", sapply(ACTIVE_SITES, `[[`, "label"))
  md_col_names  <- c(" ", paste0(clean_labels, " (", seq_along(ACTIVE_SITES), ")"))
  tex_col_names <- c(" ", paste0("\\shortstack{", clean_labels, "\\\\(",
                                  seq_along(ACTIVE_SITES), ")}"))

  writeLines(
    c(sprintf("# Pooled ATT — %s", dv_label), "", note, "",
      kable(tbl, format = "markdown", col.names = md_col_names)),
    md_path
  )
  cat(sprintf("Wrote: %s\n", md_path))

  # Write LaTeX manually — tabular only, to be \input{}-ed inside a float.
  n_data     <- length(ACTIVE_SITES)
  col_spec   <- paste0("[t]{", paste(rep("l", n_data + 1L), collapse = ""), "}")
  tex_header <- paste(
    c("", paste0("\\shortstack{", clean_labels, "\\\\(", seq_len(n_data), ")}")),
    collapse = " & ")
  body_rows <- vapply(seq_len(nrow(tbl)), function(i)
    paste(as.character(tbl[i, ]), collapse = " & "),
    character(1))
  tex_body <- c(
    paste0(body_rows[1:6], " \\\\"),
    "\\addlinespace",
    "\\addlinespace",
    paste0(body_rows[7:9], " \\\\")
  )
  tex_lines_v <- c(
    sprintf("\\begin{tabular}%s", col_spec),
    "\\toprule",
    paste0(tex_header, " \\\\"),
    "\\midrule",
    tex_body,
    "\\bottomrule",
    "\\end{tabular}"
  )
  writeLines(tex_lines_v, tex_path)
  cat(sprintf("Wrote: %s\n", tex_path))
}


for (dv in "win_min") {
  tbl      <- make_dv_pval_table(dv)
  dv_label <- DV_METADATA[[dv]]$short
  cap      <- sprintf("Pooled ATT p-values — stacked TWFE. Outcome: %s", dv_label)

  md_path  <- file.path(out_dir, sprintf("full_sample_table_%s_pvals.md",  dv))
  tex_path <- file.path(out_dir, sprintf("full_sample_table_%s_pvals.tex", dv))

  clean_labels  <- gsub(" \\(.*\\)", "", sapply(ACTIVE_SITES, `[[`, "label"))
  md_col_names  <- c(" ", paste0(clean_labels, " (", seq_along(ACTIVE_SITES), ")"))
  tex_col_names <- c(" ", paste0("\\shortstack{", clean_labels, "\\\\(",
                                  seq_along(ACTIVE_SITES), ")}"))

  writeLines(
    c(sprintf("# Pooled ATT p-values — %s", dv_label), "", note, "",
      kable(tbl, format = "markdown", col.names = md_col_names)),
    md_path
  )
  cat(sprintf("Wrote: %s\n", md_path))

  n_data     <- length(ACTIVE_SITES)
  col_spec   <- paste0("[t]{", paste(rep("l", n_data + 1L), collapse = ""), "}")
  tex_header <- paste(
    c("", paste0("\\shortstack{", clean_labels, "\\\\(", seq_len(n_data), ")}")),
    collapse = " & ")
  body_rows <- vapply(seq_len(nrow(tbl)), function(i)
    paste(as.character(tbl[i, ]), collapse = " & "),
    character(1))
  tex_body <- c(
    paste0(body_rows[1:3], " \\\\"),
    "\\addlinespace",
    "\\addlinespace",
    paste0(body_rows[4:6], " \\\\")
  )
  tex_lines_v <- c(
    sprintf("\\begin{tabular}%s", col_spec),
    "\\toprule",
    paste0(tex_header, " \\\\"),
    "\\midrule",
    tex_body,
    "\\bottomrule",
    "\\end{tabular}"
  )
  writeLines(tex_lines_v, tex_path)
  cat(sprintf("Wrote: %s\n", tex_path))
}

cat("\nAll done.\n")
