# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21 (updated: 2026-05-28)
# Purpose: Run pooled three-period TWFE regressions for top-25 adult sites
#          plus two combined groups. Combined mode only. No event study.
#
#          Memory-efficient structure — only one wide table in memory at a time:
#            1. Load other_compliant_win_wide → run other-compliant site
#               regressions + other_compliant combined → release
#            2. Load individual parquets for PORNHUB, XVIDEOS, XNXX, other_adult
#               one at a time
#            3. Load other_noncompliant_win_wide → run other-noncompliant site
#               regressions + other_noncompliant_top25 combined → release
#
# Requires:
#   data/intermediate_combined/stacked_panel.rds
#   data/intermediate_combined/top25_other_compliant_win_wide.rds     [prepare_top25.R]
#   data/intermediate_combined/top25_other_noncompliant_win_wide.rds  [prepare_top25.R]
#   data/Aggregation/top25/desktop_mobile_machine_panel/
#       machine_aggregated_{PORNHUB,XVIDEOS,XNXX,other_adult}.parquet
#   output/ProcessComscore/data_structure_validation/top25_adult_sites.csv
#   raw/compliance/top_25_compliance.csv
#
# Output:
#   output/analysis/combined/top_25/intermediate/regression_results_top25.rds
#
# Usage:
#   Rscript code/analysis/top25/run_regressions_top25.R

suppressPackageStartupMessages({
  library(arrow)
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

data_dir    <- file.path(here::here(), "data", "Aggregation", "top25",
                         "desktop_mobile_machine_panel")
out_base    <- file.path(here::here(), "output", "analysis", "combined", "top_25")
out_int_dir <- file.path(out_base, "intermediate")
dir.create(out_int_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# SITE LIST  (top 25 from CSV + other_adult)
# ============================================================================

top25_csv <- read.csv(
  here::here("output", "ProcessComscore", "data_structure_validation",
             "top25_adult_sites.csv"),
  stringsAsFactors = FALSE
)

TOP25_SITES <- c(
  lapply(seq_len(nrow(top25_csv)), function(i) {
    nm <- top25_csv$top_web_name[i]
    list(
      key   = nm,
      label = sprintf("%d. %s", top25_csv$rank[i], nm),
      slug  = gsub("[^A-Za-z0-9]", "_", nm),
      rank  = top25_csv$rank[i]
    )
  }),
  list(list(
    key   = "other_adult",
    label = "26. Other Adult",
    slug  = "other_adult",
    rank  = 26L
  ))
)

# ============================================================================
# COMPLIANCE — site group membership
# ============================================================================

compliance_raw <- read.csv(
  here::here("raw", "compliance", "top_25_compliance.csv"),
  stringsAsFactors = FALSE
)
names(compliance_raw) <- gsub("[^a-z]", "", tolower(names(compliance_raw)))

compliant_sites    <- compliance_raw$site[tolower(trimws(compliance_raw$compliant)) == "yes"]
noncompliant_sites <- setdiff(compliance_raw$site, compliant_sites)

other_compliant_keys    <- setdiff(compliant_sites, "PORNHUB.COM")
other_noncompliant_keys <- setdiff(noncompliant_sites, c("XVIDEOS.COM", "XNXX.COM"))

# Loaded individually — not in either wide table
individual_keys <- c("PORNHUB.COM", "XVIDEOS.COM", "XNXX.COM", "other_adult")

cat(sprintf("other_compliant sites (%d):    %s\n",
    length(other_compliant_keys), paste(other_compliant_keys, collapse = ", ")))
cat(sprintf("other_noncompliant sites (%d): %s\n",
    length(other_noncompliant_keys), paste(other_noncompliant_keys, collapse = ", ")))
cat(sprintf("individual sites (%d):         %s\n\n",
    length(individual_keys), paste(individual_keys, collapse = ", ")))

# ============================================================================
# LOAD STACKED PANEL
# ============================================================================

cat("Loading stacked panel...\n")
t0 <- proc.time()
sp              <- readRDS(file.path(here::here(), "data", "intermediate_combined",
                                     "stacked_panel.rds"))
stacked_base    <- sp$stacked_base
needed_weeks    <- sp$needed_weeks
needed_machines <- sp$needed_machines
qualifying      <- sp$qualifying
n_clusters      <- sp$n_clusters
rm(sp)
cat(sprintf("  %s rows | %d clusters | %d cohorts  (%.1fs)\n\n",
    format(nrow(stacked_base), big.mark = ","),
    n_clusters, length(qualifying),
    (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# HELPERS
# ============================================================================

# Run one pooled regression from a wide-table column and save checkpoint.
run_one <- function(site_slug, win_col, win_wide, rank = NULL, label, key) {
  df <- stacked_base |>
    left_join(
      select(win_wide, machine_id, week_of_sample, win_min = all_of(win_col)),
      by = c("machine_id", "week_of_sample")
    ) |>
    mutate(win_min = coalesce(win_min, 0))

  baseline_mean <- mean(df$win_min[df$treated == 1L & df$rel_week == -1L], na.rm = TRUE)

  t0  <- proc.time()
  res <- run_pooled(df, "win_min")
  cat(sprintf("  [PL] N=%s  base=%.4f  beta_LT=%+.4f  (%.1fs)\n",
      format(res$n_obs, big.mark = ","), baseline_mean,
      coalesce(res$beta_longterm, NA_real_),
      (proc.time() - t0)[["elapsed"]]))
  rm(df); gc()

  entry <- list(win_min = res, baseline_mean = baseline_mean, label = label, key = key)
  if (!is.null(rank)) entry$rank <- rank
  entry
}

# Run one pooled regression from an individually loaded parquet.
run_one_individual <- function(site) {
  t_load <- proc.time()
  dur    <- load_site_duration(site$key)
  cat(sprintf("  loaded: %s rows  (%.1fs)\n",
      format(nrow(dur), big.mark = ","),
      (proc.time() - t_load)[["elapsed"]]))

  df <- stacked_base |>
    left_join(dur, by = c("machine_id", "week_of_sample")) |>
    mutate(win_min = coalesce(total_duration / 60, 0))
  rm(dur)

  baseline_mean <- mean(df$win_min[df$treated == 1L & df$rel_week == -1L], na.rm = TRUE)

  t0  <- proc.time()
  res <- run_pooled(df, "win_min")
  cat(sprintf("  [PL] N=%s  base=%.4f  beta_LT=%+.4f  (%.1fs)\n",
      format(res$n_obs, big.mark = ","), baseline_mean,
      coalesce(res$beta_longterm, NA_real_),
      (proc.time() - t0)[["elapsed"]]))
  rm(df); gc()

  list(win_min = res, baseline_mean = baseline_mean,
       rank = site$rank, label = site$label, key = site$key)
}

# ============================================================================
# RESULTS STORAGE
# ============================================================================

results_path <- file.path(out_int_dir, "regression_results_top25.rds")

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

t_global <- proc.time()

# ============================================================================
# SECTION 1: OTHER COMPLIANT SITES + other_compliant COMBINED
# Load the compliant wide table, run all regressions that use it, then release.
# ============================================================================

cat(strrep("=", 60), "\n")
cat(sprintf("Section 1: other-compliant sites (%d) + combined\n", length(other_compliant_keys)))
cat(strrep("=", 60), "\n\n")

cat("Loading other_compliant_win_wide...\n")
t0                       <- proc.time()
other_compliant_win_wide <- readRDS(file.path(here::here(), "data", "intermediate_combined",
                                              "top25_other_compliant_win_wide.rds"))
cat(sprintf("  %s rows, %d cols  (%.1fs)\n\n",
    format(nrow(other_compliant_win_wide), big.mark = ","),
    ncol(other_compliant_win_wide),
    (proc.time() - t0)[["elapsed"]]))

for (site in TOP25_SITES) {
  if (!site$key %in% other_compliant_keys) next

  if (!is.null(results$pooled[[site$slug]])) {
    cat(sprintf("--- [%d/26] %s — already done, skipping\n\n", site$rank, site$key))
    next
  }
  cat(sprintf("--- [%d/26] %s ---\n", site$rank, site$key))

  results$pooled[[site$slug]] <- run_one(
    site_slug = site$slug,
    win_col   = paste0("win_", site$slug),
    win_wide  = other_compliant_win_wide,
    rank      = site$rank, label = site$label, key = site$key
  )
  saveRDS(results, results_path)
  cat(sprintf("  [checkpoint saved]\n\n"))
}

# other_compliant combined regression
if (is.null(results$pooled[["other_compliant"]])) {
  cat("--- other_compliant (combined) ---\n")
  results$pooled[["other_compliant"]] <- run_one(
    site_slug = "other_compliant",
    win_col   = "win_other_compliant",
    win_wide  = other_compliant_win_wide,
    label = "Other Compliant", key = "other_compliant"
  )
  saveRDS(results, results_path)
  cat(sprintf("  [checkpoint saved]\n\n"))
} else {
  cat("--- other_compliant — already done, skipping\n\n")
}

rm(other_compliant_win_wide); gc()
cat("Released other_compliant_win_wide.\n\n")

# ============================================================================
# SECTION 2: INDIVIDUAL SITES  (PORNHUB, XVIDEOS, XNXX, other_adult)
# Each parquet is loaded and freed one at a time.
# ============================================================================

cat(strrep("=", 60), "\n")
cat(sprintf("Section 2: individual sites (%d)\n", length(individual_keys)))
cat(strrep("=", 60), "\n\n")

for (site in TOP25_SITES) {
  if (!site$key %in% individual_keys) next

  if (!is.null(results$pooled[[site$slug]])) {
    cat(sprintf("--- [%d/26] %s — already done, skipping\n\n", site$rank, site$key))
    next
  }
  cat(sprintf("--- [%d/26] %s ---\n", site$rank, site$key))

  results$pooled[[site$slug]] <- run_one_individual(site)
  saveRDS(results, results_path)
  cat(sprintf("  [checkpoint saved]\n\n"))
}

# ============================================================================
# SECTION 3: OTHER NONCOMPLIANT SITES + other_noncompliant_top25 COMBINED
# Load the noncompliant wide table, run all regressions that use it, then release.
# ============================================================================

cat(strrep("=", 60), "\n")
cat(sprintf("Section 3: other-noncompliant sites (%d) + combined\n", length(other_noncompliant_keys)))
cat(strrep("=", 60), "\n\n")

cat("Loading other_noncompliant_win_wide...\n")
t0                          <- proc.time()
other_noncompliant_win_wide <- readRDS(file.path(here::here(), "data", "intermediate_combined",
                                                 "top25_other_noncompliant_win_wide.rds"))
cat(sprintf("  %s rows, %d cols  (%.1fs)\n\n",
    format(nrow(other_noncompliant_win_wide), big.mark = ","),
    ncol(other_noncompliant_win_wide),
    (proc.time() - t0)[["elapsed"]]))

for (site in TOP25_SITES) {
  if (!site$key %in% other_noncompliant_keys) next

  if (!is.null(results$pooled[[site$slug]])) {
    cat(sprintf("--- [%d/26] %s — already done, skipping\n\n", site$rank, site$key))
    next
  }
  cat(sprintf("--- [%d/26] %s ---\n", site$rank, site$key))

  results$pooled[[site$slug]] <- run_one(
    site_slug = site$slug,
    win_col   = paste0("win_", site$slug),
    win_wide  = other_noncompliant_win_wide,
    rank      = site$rank, label = site$label, key = site$key
  )
  saveRDS(results, results_path)
  cat(sprintf("  [checkpoint saved]\n\n"))
}

# other_noncompliant_top25 combined regression
if (is.null(results$pooled[["other_noncompliant_top25"]])) {
  cat("--- other_noncompliant_top25 (combined) ---\n")
  results$pooled[["other_noncompliant_top25"]] <- run_one(
    site_slug = "other_noncompliant_top25",
    win_col   = "win_other_noncompliant_top25",
    win_wide  = other_noncompliant_win_wide,
    label = "Other Noncompliant Top 25", key = "other_noncompliant_top25"
  )
  saveRDS(results, results_path)
  cat(sprintf("  [checkpoint saved]\n\n"))
} else {
  cat("--- other_noncompliant_top25 — already done, skipping\n\n")
}

rm(other_noncompliant_win_wide); gc()
cat("Released other_noncompliant_win_wide.\n\n")

cat(strrep("=", 60), "\n")
cat(sprintf("Total elapsed: %.1fs\n", (proc.time() - t_global)[["elapsed"]]))
cat(sprintf("Saved: %s\n", results_path))
cat(strrep("=", 60), "\n")
