# Author: Matt Brown, assisted by Claude
# Created: 2026-03-06
# Purpose: Load all shared data, build stacked panel and win_min wide table,
#          serialise to data/intermediate/ for downstream analysis scripts.
#
# Run once upfront (~80s). Saves:
#   data/intermediate/stacked_panel.rds  — named list of shared objects
#   data/intermediate/xxx_win_wide.rds   — per-site winsorized minutes (wide)
#
# Usage:
#   Rscript code/analysis/prepare_desktop.R

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

# ============================================================================
# STATE LAWS
# ============================================================================

cat("Loading PH shutdown dates...\n")
laws <- read.csv(ph_shutdown_file, stringsAsFactors = FALSE, na.strings = c("", "NA"))
laws$date_PH_shutdown <- as.Date(laws$date_PH_shutdown)
treated_all <- sort(laws$state)
law_date    <- setNames(laws$date_PH_shutdown, laws$state)
qualifying  <- treated_all[!is.na(law_date[treated_all]) &
                            law_date[treated_all] < CUTOFF_DATE]
cat(sprintf("  Qualifying (%d): %s\n", length(qualifying),
            paste(qualifying, collapse = ", ")))

base_date <- as.Date("2022-01-01")
law_wos <- setNames(
  sapply(qualifying, function(s)
    as.integer(law_date[s] - base_date) %/% 7L + 1L),
  qualifying
)

# ============================================================================
# MACHINE DEMOGRAPHICS  (all columns — for heterogeneous.R subgroups)
# ============================================================================

cat("Loading machine demographics...\n")
demos <- read_parquet(demo_file,
    col_select = c("machine_id", "state", "have_demos", "gender", "hoh_age",
                   "children_present", "hh_income")) |>
  filter(have_demos == 1L) |>
  distinct(machine_id, .keep_all = TRUE) |>
  filter(!state %in% EXCLUDE_STATES)

# ============================================================================
# PRESENCE PANEL
# ============================================================================

cat("Loading presence panel...\n")
t0 <- proc.time()
presence <- read_parquet(file.path(data_dir, "machine_week_presence.parquet")) |>
  inner_join(select(demos, machine_id, state), by = "machine_id") |>
  filter(!is.na(state), !state %in% EXCLUDE_STATES)
cat(sprintf("  %s rows | %s machines  (%.1fs)\n",
    format(nrow(presence), big.mark = ","),
    format(n_distinct(presence$machine_id), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))

control_states <- setdiff(unique(presence$state), treated_all)
cat(sprintf("  Control: %d states\n", length(control_states)))

week_dates <- data.frame(week_of_sample = sort(unique(presence$week_of_sample))) |>
  mutate(week_start_date = as.Date("2022-01-01") + (week_of_sample - 1L) * 7L)

# ============================================================================
# BUILD STACKED PANEL
# ============================================================================

cat("\nBuilding stacked panel...\n")
t0 <- proc.time()

stacked_base <- lapply(qualifying, function(s) {
  wos_0        <- law_wos[[s]]
  window_weeks <- wos_0 + t_range
  presence |>
    filter(week_of_sample %in% window_weeks,
           state == s | state %in% control_states) |>
    mutate(
      cohort   = s,
      rel_week = as.integer(week_of_sample - wos_0),
      treated  = as.integer(state == s)
    ) |>
    select(machine_id, week_of_sample, state, cohort, rel_week, treated)
}) |> bind_rows() |>
  mutate(
    machine_cohort = paste0(machine_id, "__", cohort),
    cohort_week    = paste0(cohort,     "__", week_of_sample)
  )

rm(presence)

# Merge all demographic columns (gender, hoh_age, children_present)
demo_slim    <- demos |> select(machine_id, gender, hoh_age, children_present, hh_income)
stacked_base <- stacked_base |> left_join(demo_slim, by = "machine_id")
rm(demos, demo_slim)

cat(sprintf("Stacked: %s rows | %s machine\u00d7cohort | %s cohort\u00d7week | %d clusters  (%.1fs)\n",
    format(nrow(stacked_base),                           big.mark = ","),
    format(n_distinct(stacked_base$machine_cohort),      big.mark = ","),
    format(n_distinct(stacked_base$cohort_week),         big.mark = ","),
    n_distinct(stacked_base$state),
    (proc.time() - t0)[["elapsed"]]))

needed_weeks    <- sort(unique(as.integer(outer(unname(law_wos), t_range, "+"))))
needed_machines <- unique(stacked_base$machine_id)
n_clusters      <- n_distinct(stacked_base$state)

# ============================================================================
# BALANCED MACHINE×COHORT SET
# ============================================================================

cat("\nBuilding balanced machine×cohort set (all 25 event-window weeks required)...\n")
t0 <- proc.time()
n_weeks_required <- length(t_range)
balanced_mcs <- stacked_base |>
  group_by(machine_cohort) |>
  summarise(n_weeks = n_distinct(week_of_sample), .groups = "drop") |>
  filter(n_weeks == n_weeks_required) |>
  pull(machine_cohort)
cat(sprintf("  Balanced: %s of %s machine×cohort pairs (%.1f%%)  (%.1fs)\n",
    format(length(balanced_mcs),                    big.mark = ","),
    format(n_distinct(stacked_base$machine_cohort), big.mark = ","),
    100 * length(balanced_mcs) / n_distinct(stacked_base$machine_cohort),
    (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# BUILD XXX WIN_MIN WIDE TABLE
# ============================================================================

xxx_win_wide <- build_xxx_win_wide(needed_weeks, needed_machines)

# ============================================================================
# SAVE RDS FILES
# ============================================================================

dir.create(int_dir, recursive = TRUE, showWarnings = FALSE)

panel_path <- file.path(int_dir, "stacked_panel.rds")
saveRDS(
  list(
    stacked_base    = stacked_base,
    week_dates      = week_dates,
    needed_weeks    = needed_weeks,
    needed_machines = needed_machines,
    law_wos         = law_wos,
    law_date        = law_date,
    qualifying      = qualifying,
    n_clusters      = n_clusters,
    control_states  = control_states,
    balanced_mcs    = balanced_mcs
  ),
  panel_path
)
cat(sprintf("\nSaved: %s  (%.1f MB)\n",
    panel_path,
    file.size(panel_path) / 1e6))

win_path <- file.path(int_dir, "xxx_win_wide.rds")
saveRDS(xxx_win_wide, win_path)
cat(sprintf("Saved: %s  (%.1f MB)\n",
    win_path,
    file.size(win_path) / 1e6))

het_path <- file.path(int_dir, "het_covs.rds")
saveRDS(build_het_covariates(stacked_base, xxx_win_wide), het_path)
cat(sprintf("Saved: %s  (%.1f MB)\n",
    het_path,
    file.size(het_path) / 1e6))

cat("\nAll done.\n")
