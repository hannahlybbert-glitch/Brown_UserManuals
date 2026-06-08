# Author: Matt Brown, assisted by Claude
# Created: 2026-03-07
# Purpose: Generate event-study plots and coefficient CSVs from saved regression
#          results.  Reads data/intermediate/regression_results.rds.
#
# Requires: data/intermediate/regression_results.rds
#           (produced by run_regressions.R with RUN_HOMOGENEOUS_EVENT_STUDY = TRUE)
#
# Outputs (output/analysis/event_study/):
#   {slug}_{dv}_coefs.csv   — event-study coefficients + 95% CI
#   {slug}_{dv}.png         — event-study plot
#
# Usage:
#   Rscript code/analysis/create_event_study_plots.R

suppressPackageStartupMessages({
  library(ggplot2)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

# ============================================================================
# LOAD RESULTS
# ============================================================================

cat("Loading regression results...\n")
results <- readRDS(file.path(out_int_dir, "regression_results.rds"))

if (length(results$event) == 0L) {
  stop("results$event is empty. Re-run run_regressions.R with RUN_HOMOGENEOUS_EVENT_STUDY = TRUE.")
}

# qualifying + n_clusters for plot subtitles (stored in results$meta by run_regressions.R)
qualifying <- results$meta$qualifying
n_clusters <- results$meta$n_clusters

# SITES_FULL, dvs, DV_METADATA sourced from config.R

# ============================================================================
# OUTPUT DIR
# ============================================================================

out_dir <- file.path(out_base, "event_study")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# WRITE PLOTS + CSVs
# ============================================================================

cat("\n", strrep("=", 60), "\n", sep = "")
cat("Writing event-study plots and CSVs\n")
cat(strrep("=", 60), "\n\n", sep = "")

for (site in SITES_FULL) {
  if (!site$slug %in% names(results$event)) {
    cat(sprintf("Skipping %s (not in results)\n", site$label))
    next
  }
  cat(sprintf("--- %s ---\n", site$label))

  for (dv in dvs) {
    if (!dv %in% names(results$event[[site$slug]])) next

    res  <- results$event[[site$slug]][[dv]]
    coefs         <- res$coefs
    baseline_mean <- res$baseline_mean

    csv_path <- file.path(out_dir, sprintf("%s_%s_coefs.csv", site$slug, dv))
    write.csv(coefs, csv_path, row.names = FALSE)

    fig_path <- save_event_study_plot(
      coefs, site$label, DV_METADATA[[dv]]$short, DV_METADATA[[dv]]$y_label,
      site$slug, dv, out_dir,
      baseline_mean = baseline_mean)

    cat(sprintf("  %s: → %s\n       → %s\n", dv, csv_path, fig_path))
  }
}

# ============================================================================
# VPN — XXX VISITORS ONLY PLOTS
# ============================================================================

VPN_XXX_SITES <- list(
  list(slug = "VPNclean_xxx", label = "VPN (clean) — XXX visitors only"),
  list(slug = "allVPN_xxx",   label = "All VPN — XXX visitors only")
)

vpn_xxx_present <- any(sapply(VPN_XXX_SITES, function(s) s$slug %in% names(results$event)))

if (vpn_xxx_present) {
  cat("\n", strrep("=", 60), "\n", sep = "")
  cat("Writing VPN XXX-visitor event-study plots and CSVs\n")
  cat(strrep("=", 60), "\n\n", sep = "")

  for (site in VPN_XXX_SITES) {
    if (!site$slug %in% names(results$event)) {
      cat(sprintf("Skipping %s (not in results)\n", site$label))
      next
    }
    cat(sprintf("--- %s ---\n", site$label))

    for (dv in dvs) {
      if (!dv %in% names(results$event[[site$slug]])) next

      res           <- results$event[[site$slug]][[dv]]
      coefs         <- res$coefs
      baseline_mean <- res$baseline_mean

      csv_path <- file.path(out_dir, sprintf("%s_%s_coefs.csv", site$slug, dv))
      write.csv(coefs, csv_path, row.names = FALSE)

      fig_path <- save_event_study_plot(
        coefs, site$label, DV_METADATA[[dv]]$short, DV_METADATA[[dv]]$y_label,
        site$slug, dv, out_dir,
        baseline_mean = baseline_mean)

      cat(sprintf("  %s: → %s\n       → %s\n", dv, csv_path, fig_path))
    }
  }
}

# ============================================================================
# VPN — NEVER-XXX MACHINES PLOTS
# ============================================================================

VPN_NOXXX_SITES <- list(
  list(slug = "VPNclean_noxxx", label = "VPN (clean) — never-XXX machines"),
  list(slug = "allVPN_noxxx",   label = "All VPN — never-XXX machines")
)

vpn_noxxx_present <- any(sapply(VPN_NOXXX_SITES, function(s) s$slug %in% names(results$event)))

if (vpn_noxxx_present) {
  cat("\n", strrep("=", 60), "\n", sep = "")
  cat("Writing VPN never-XXX event-study plots and CSVs\n")
  cat(strrep("=", 60), "\n\n", sep = "")

  for (site in VPN_NOXXX_SITES) {
    if (!site$slug %in% names(results$event)) {
      cat(sprintf("Skipping %s (not in results)\n", site$label))
      next
    }
    cat(sprintf("--- %s ---\n", site$label))

    for (dv in dvs) {
      if (!dv %in% names(results$event[[site$slug]])) next

      res           <- results$event[[site$slug]][[dv]]
      coefs         <- res$coefs
      baseline_mean <- res$baseline_mean

      csv_path <- file.path(out_dir, sprintf("%s_%s_coefs.csv", site$slug, dv))
      write.csv(coefs, csv_path, row.names = FALSE)

      fig_path <- save_event_study_plot(
        coefs, site$label, DV_METADATA[[dv]]$short, DV_METADATA[[dv]]$y_label,
        site$slug, dv, out_dir,
        baseline_mean = baseline_mean)

      cat(sprintf("  %s: → %s\n       → %s\n", dv, csv_path, fig_path))
    }
  }
}

cat("\nAll done.\n")
