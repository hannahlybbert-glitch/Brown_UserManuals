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

# SITES_FULL, dvs, DV_METADATA sourced from config.R
# VPN and comparison sites are excluded from the main table.
MAIN_SITES <- SITES_FULL[!sapply(SITES_FULL, `[[`, "key") %in%
                c("VPNclean", "allVPN", COMPARISON_SITE_KEYS)]

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
  if (is.na(beta)) return(c("\u2014", ""))
  c(sprintf("%.4f%s", beta, stars(p)),
    sprintf("(%.4f)", se))
}

# ============================================================================
# BUILD ONE TABLE PER DV
# ============================================================================

# For each DV: rows = (β_pre, SE, β_ST, SE, β_LT, SE, N_obs, N_mc)
#              cols = one per site in SITES_FULL

row_labels <- c("\u03b2_pre", "", "\u03b2_ST", "", "\u03b2_LT", "", "N (obs)", "N (machines)")

make_dv_table <- function(dv) {
  site_cols <- lapply(MAIN_SITES, function(site) {
    res <- results$pooled[[site$slug]][[dv]]
    if (is.null(res)) return(rep(NA_character_, 8))
    pre_fmt <- fmt_est(res$beta_pre,       res$se_pre,       res$p_pre)
    st_fmt  <- fmt_est(res$beta_shortterm, res$se_shortterm, res$p_shortterm)
    lt_fmt  <- fmt_est(res$beta_longterm,  res$se_longterm,  res$p_longterm)
    c(pre_fmt[1], pre_fmt[2],
      st_fmt[1],  st_fmt[2],
      lt_fmt[1],  lt_fmt[2],
      format(res$n_obs, big.mark = ","),
      format(res$n_mc,  big.mark = ","))
  })
  tbl <- as.data.frame(site_cols, stringsAsFactors = FALSE)
  colnames(tbl) <- sapply(MAIN_SITES, `[[`, "label")
  cbind(` ` = row_labels, tbl, stringsAsFactors = FALSE)
}

# ============================================================================
# WRITE OUTPUTS
# ============================================================================

out_dir <- file.path(out_base, "full_sample")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

note <- paste0(
  "Stacked TWFE: dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week. ",
  "SE clustered by state. beta_pre: tau in [-16,-5]; beta_ST: tau in [0,3]; beta_LT: tau in [4,8]. ",
  "* p<0.10, ** p<0.05, *** p<0.01. SE in parentheses."
)

for (dv in dvs) {
  tbl       <- make_dv_table(dv)
  dv_label  <- DV_METADATA[[dv]]$short
  cap       <- sprintf("Pooled ATT — stacked TWFE. Outcome: %s", dv_label)

  md_path  <- file.path(out_dir, sprintf("full_sample_table_%s.md",  dv))
  tex_path <- file.path(out_dir, sprintf("full_sample_table_%s.tex", dv))

  writeLines(
    c(sprintf("# Pooled ATT — %s", dv_label), "", note, "", kable(tbl, format = "markdown")),
    md_path
  )
  cat(sprintf("Wrote: %s\n", md_path))

  writeLines(
    kable(tbl, format = "latex", booktabs = TRUE, caption = cap),
    tex_path
  )
  cat(sprintf("Wrote: %s\n", tex_path))
}

# ============================================================================
# VPN SUBGROUP TABLE (XXX visitors vs. never XXX)
# ============================================================================

VPN_SUBGROUP_SITES <- list(
  list(slug = "VPNclean_xxx",   label = "VPN clean — XXX visitors"),
  list(slug = "VPNclean_noxxx", label = "VPN clean — never XXX"),
  list(slug = "allVPN_xxx",     label = "All VPN — XXX visitors"),
  list(slug = "allVPN_noxxx",   label = "All VPN — never XXX")
)

vpn_present <- any(sapply(VPN_SUBGROUP_SITES,
                          function(s) !is.null(results$pooled[[s$slug]])))

if (vpn_present) {
  make_vpn_table <- function(dv) {
    site_cols <- lapply(VPN_SUBGROUP_SITES, function(site) {
      res <- results$pooled[[site$slug]][[dv]]
      if (is.null(res)) return(rep(NA_character_, 8))
      pre_fmt <- fmt_est(res$beta_pre,       res$se_pre,       res$p_pre)
      st_fmt  <- fmt_est(res$beta_shortterm, res$se_shortterm, res$p_shortterm)
      lt_fmt  <- fmt_est(res$beta_longterm,  res$se_longterm,  res$p_longterm)
      c(pre_fmt[1], pre_fmt[2],
        st_fmt[1],  st_fmt[2],
        lt_fmt[1],  lt_fmt[2],
        format(res$n_obs, big.mark = ","),
        format(res$n_mc,  big.mark = ","))
    })
    tbl <- as.data.frame(site_cols, stringsAsFactors = FALSE)
    colnames(tbl) <- sapply(VPN_SUBGROUP_SITES, `[[`, "label")
    cbind(` ` = row_labels, tbl, stringsAsFactors = FALSE)
  }

  for (dv in dvs) {
    tbl      <- make_vpn_table(dv)
    dv_label <- DV_METADATA[[dv]]$short
    cap      <- sprintf("VPN pooled ATT by XXX-visitor status — stacked TWFE. Outcome: %s", dv_label)

    md_path  <- file.path(out_dir, sprintf("full_sample_table_vpn_%s.md",  dv))
    tex_path <- file.path(out_dir, sprintf("full_sample_table_vpn_%s.tex", dv))

    writeLines(
      c(sprintf("# VPN Pooled ATT by XXX-visitor status — %s", dv_label), "", note, "",
        kable(tbl, format = "markdown")),
      md_path
    )
    cat(sprintf("Wrote: %s\n", md_path))

    writeLines(
      kable(tbl, format = "latex", booktabs = TRUE, caption = cap),
      tex_path
    )
    cat(sprintf("Wrote: %s\n", tex_path))
  }
} else {
  cat("VPN subgroup results not found in RDS — skipping VPN table.\n")
  cat("Run: Rscript code/analysis/run_regressions.R vpn_xxx vpn_noxxx\n")
}

cat("\nAll done.\n")
