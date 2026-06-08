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
  library(patchwork)
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
# FIXED Y-AXIS FOR win_min: All XXX, Pornhub, xVideos, XNXX
# All four plots share the same scale so effect sizes are directly comparable.
# Lower bound -1.5 ensures the Pornhub baseline mean (~-1.4) is fully visible;
# ticks every 0.25 min match the natural scale of this outcome.
# ============================================================================

FIXED_Y_SLUGS <- c("all_xxx", "PORNHUB_COM", "XVIDEOS_COM", "XNXX_COM")
FIXED_Y_LIM   <- c(-1.5, 0.75)
FIXED_Y_BRK   <- seq(-1.5, 0.75, by = 0.25)

# ============================================================================
# ACTIVE SITES / DVs — restrict output for final draft
# To run all sites and both DVs, comment out the two ACTIVE_* lines below
# and uncomment the "all" lines.
# ============================================================================

ACTIVE_SLUGS <- c("PORNHUB_COM", "XVIDEOS_COM", "XNXX_COM", "all_xxx")
ACTIVE_SITES <- lapply(ACTIVE_SLUGS, function(slug) {
  SITES_FULL[[which(sapply(SITES_FULL, `[[`, "slug") == slug)]]
})
PANEL_LABELS <- c("PORNHUB_COM" = "A", "XVIDEOS_COM" = "B", "XNXX_COM" = "C", "all_xxx" = "D")
ACTIVE_DVS   <- "win_min"
# ACTIVE_SITES <- SITES_FULL  # uncomment to run all sites
# ACTIVE_DVS   <- dvs          # uncomment to run all DVs

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

panel_plots <- list()

for (site in ACTIVE_SITES) {
  if (!site$slug %in% names(results$event)) {
    cat(sprintf("Skipping %s (not in results)\n", site$label))
    next
  }
  cat(sprintf("--- %s ---\n", site$label))

  for (dv in ACTIVE_DVS) {
    if (!dv %in% names(results$event[[site$slug]])) next

    res  <- results$event[[site$slug]][[dv]]
    coefs         <- res$coefs
    baseline_mean <- res$baseline_mean

    csv_path <- file.path(out_dir, sprintf("%s_%s_coefs.csv", site$slug, dv))
    write.csv(coefs, csv_path, row.names = FALSE)

    use_fixed_y <- site$slug %in% FIXED_Y_SLUGS && dv == "win_min"
    p_es <- save_event_study_plot(
      coefs, site$label, DV_METADATA[[dv]]$short, DV_METADATA[[dv]]$y_label,
      site$slug, dv, out_dir,
      baseline_mean = baseline_mean,
      y_limits = if (use_fixed_y) FIXED_Y_LIM else NULL,
      y_breaks = if (use_fixed_y) FIXED_Y_BRK else ggplot2::waiver(),
      panel_label = PANEL_LABELS[site$slug])

    fig_path <- file.path(out_dir, sprintf("%s_%s.png", site$slug, dv))
    cat(sprintf("  %s: → %s\n       → %s\n", dv, csv_path, fig_path))

    panel_plots[[paste(site$slug, dv, sep = "_")]] <- p_es
  }
}

# ============================================================================
# 2×2 COMBINED PANEL
# ============================================================================

if (length(panel_plots) == 4L) {
  panel <- patchwork::wrap_plots(panel_plots, ncol = 2) &
    theme(plot.subtitle = element_blank())

  panel_path <- file.path(out_dir, "event_study_main.png")
  ggsave(panel_path, panel, width = 16, height = 9, dpi = 300)
  cat(sprintf("\nWrote 2×2 panel: %s\n", panel_path))
} else {
  cat(sprintf("\nSkipping panel (expected 4 plots, got %d)\n", length(panel_plots)))
}

cat("\nAll done.\n")
