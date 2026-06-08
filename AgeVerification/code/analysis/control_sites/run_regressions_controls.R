# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-28
# Purpose: Run pooled three-period TWFE regressions for 12 control (non-adult) sites.
#          Combined mode only. No event study.
#
#          Mirrors run_regressions_top25.R: loads pre-built stacked_panel.rds
#          and controls_win_wide.rds (produced by prepare_control_sites.R), then
#          loops over sites joining win_{slug} columns and running run_pooled().
#
# Sites: Netflix, Reddit, Twitter, OnlyFans, Facebook, Instructure, Wikimedia,
#        eBay, Amazon, DuckDuckGo, Enthusiast Gaming, Bytedance (TikTok).
#
# Requires:
#   data/intermediate_combined/stacked_panel.rds      [from prepare_combined.R]
#   data/intermediate_combined/controls_win_wide.rds  [from prepare_control_sites.R]
#
# Output:
#   output/analysis/combined/control_sites/intermediate/
#       regression_results_controls.rds
#
# Usage:
#   Rscript code/analysis/control_sites/run_regressions_controls.R

suppressPackageStartupMessages({
  library(dplyr)
  library(fixest)
  library(here)
})

# ============================================================================
# SETUP
# ============================================================================

Sys.setenv(ANALYSIS_MODE = "combined")
source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

out_base    <- file.path(here::here(), "output", "analysis", "combined", "control_sites")
out_int_dir <- file.path(out_base, "intermediate")
dir.create(out_int_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# CONTROL SITE LIST
# ============================================================================

CONTROL_SITES <- list(
  list(key = "Netflix Inc.",               label = "Netflix",            slug = "Netflix_Inc"),
  list(key = "Reddit",                     label = "Reddit",             slug = "Reddit"),
  list(key = "Twitter",                    label = "Twitter",            slug = "Twitter"),
  list(key = "ONLYFANS.COM",               label = "OnlyFans",           slug = "ONLYFANS_COM"),
  list(key = "Facebook",                   label = "Facebook",           slug = "Facebook"),
  list(key = "INSTRUCTURE.COM",            label = "Instructure",        slug = "INSTRUCTURE_COM"),
  list(key = "Wikimedia Foundation Sites", label = "Wikimedia",          slug = "Wikimedia_Foundation_Sites"),
  list(key = "eBay",                       label = "eBay",               slug = "eBay"),
  list(key = "Amazon Sites",               label = "Amazon",             slug = "Amazon_Sites"),
  list(key = "DUCKDUCKGO.COM",             label = "DuckDuckGo",         slug = "DUCKDUCKGO_COM"),
  list(key = "Enthusiast Gaming",          label = "Enthusiast Gaming",  slug = "Enthusiast_Gaming"),
  list(key = "Bytedance Inc.",             label = "Bytedance (TikTok)", slug = "Bytedance_Inc")
)

cat(sprintf("Control sites to regress: %d\n\n", length(CONTROL_SITES)))

# ============================================================================
# LOAD STACKED PANEL
# ============================================================================

cat("Loading stacked panel...\n")
t0 <- proc.time()
sp           <- readRDS(file.path(here::here(), "data", "intermediate_combined",
                                  "stacked_panel.rds"))
stacked_base <- sp$stacked_base
qualifying   <- sp$qualifying
n_clusters   <- sp$n_clusters
rm(sp)
cat(sprintf("  %s rows | %d clusters | %d cohorts  (%.1fs)\n\n",
    format(nrow(stacked_base), big.mark = ","),
    n_clusters, length(qualifying),
    (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# LOAD CONTROLS_WIN_WIDE
# ============================================================================

cat("Loading controls_win_wide...\n")
t0                <- proc.time()
controls_win_wide <- readRDS(file.path(here::here(), "data", "intermediate_combined",
                                       "controls_win_wide.rds"))
cat(sprintf("  %s rows, %d cols  (%.1fs)\n\n",
    format(nrow(controls_win_wide), big.mark = ","),
    ncol(controls_win_wide),
    (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# RESULTS STORAGE
# ============================================================================

results_path <- file.path(out_int_dir, "regression_results_controls.rds")

if (file.exists(results_path)) {
  cat(sprintf("Resuming from existing checkpoint (%.1f MB)...\n",
              file.size(results_path) / 1e6))
  results <- readRDS(results_path)
} else {
  results <- list(pooled = list())
}

results$meta <- list(
  n_clusters = n_clusters,
  n_cohorts  = length(qualifying),
  qualifying = qualifying
)

# ============================================================================
# POOLED REGRESSIONS  (one per control site)
# ============================================================================

cat(strrep("=", 60), "\n")
cat(sprintf("Pooled regressions: %d control sites\n", length(CONTROL_SITES)))
cat(strrep("=", 60), "\n\n")

t_global <- proc.time()
n_sites  <- length(CONTROL_SITES)

for (i in seq_along(CONTROL_SITES)) {
  site <- CONTROL_SITES[[i]]

  if (!is.null(results$pooled[[site$slug]])) {
    cat(sprintf("--- [%d/%d] %s — already done, skipping\n\n", i, n_sites, site$key))
    next
  }

  cat(sprintf("--- [%d/%d] %s ---\n", i, n_sites, site$key))

  win_col <- paste0("win_", site$slug)

  df <- stacked_base |>
    left_join(
      select(controls_win_wide, machine_id, week_of_sample, win_min = all_of(win_col)),
      by = c("machine_id", "week_of_sample")
    ) |>
    mutate(win_min = coalesce(win_min, 0))

  baseline_mean <- mean(df$win_min[df$treated == 1L & df$rel_week == -1L],
                        na.rm = TRUE)

  t0  <- proc.time()
  res <- run_pooled(df, "win_min")
  cat(sprintf("  [PL] N=%s  base=%.4f  beta_LT=%+.4f  (%.1fs)\n",
      format(res$n_obs, big.mark = ","),
      baseline_mean,
      coalesce(res$beta_longterm, NA_real_),
      (proc.time() - t0)[["elapsed"]]))

  results$pooled[[site$slug]] <- list(
    win_min       = res,
    baseline_mean = baseline_mean,
    label         = site$label,
    key           = site$key
  )

  rm(df); gc()
  saveRDS(results, results_path)
  cat(sprintf("  [checkpoint saved]\n\n"))
}

cat(strrep("=", 60), "\n")
cat(sprintf("Total elapsed: %.1fs\n", (proc.time() - t_global)[["elapsed"]]))
cat(sprintf("Saved: %s\n", results_path))
cat(strrep("=", 60), "\n")
