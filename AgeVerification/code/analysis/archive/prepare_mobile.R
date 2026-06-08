# Author: Emily Davis, assisted by Claude
# Created: 2026-03-11
# Purpose: Mobile equivalent of prepare.R. Loads mobile aggregation outputs,
#          remaps demographic columns to match the desktop schema, builds the
#          stacked panel and win_min wide table, and serialises to
#          data/intermediate_mobile/ for downstream analysis scripts.
#
# Differences from prepare.R:
#   1. Sources config_mobile.R (overrides data_dir, demo_file, int_dir).
#   2. Demographics loaded from mobile_characteristics.csv (not parquet);
#      numeric age binned to hoh_age strings; state joined from
#      mobile_to_state_lookup.parquet (not in the demo file).
#   3. All other logic (stacked panel, balanced set, xxx_win_wide) is identical.
#
# Run once upfront. Saves:
#   data/intermediate_mobile/stacked_panel.rds
#   data/intermediate_mobile/xxx_win_wide.rds
#
# Usage:
#   Rscript code/analysis/prepare_mobile.R

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

# ============================================================================
# WEEK→DATE MAP
# ============================================================================

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
# MOBILE DEMOGRAPHICS
# Mobile-specific: load CSV, bin numeric age → hoh_age, join state from lookup.
# After remapping, the demos data frame has the same columns as the desktop:
#   machine_id, state, gender, hoh_age, children_present, hh_income
# ============================================================================

cat("Loading mobile demographics...\n")

demos_raw <- read.csv(demo_file, stringsAsFactors = FALSE) |>
  distinct(machine_id, .keep_all = TRUE) |>
  mutate(
    hoh_age = dplyr::case_when(
      age >= 18 & age <= 24 ~ "18-24",
      age >= 25 & age <= 34 ~ "25-34",
      age >= 35 & age <= 44 ~ "35-44",
      age >= 45 & age <= 54 ~ "45-54",
      age >= 55 & age <= 64 ~ "55-64",
      age >= 65              ~ "65 and Over",
      TRUE                   ~ NA_character_
    )
  ) |>
  select(machine_id, gender, hoh_age, children_present, hh_income)

cat(sprintf("  %s machines in demographics file\n",
            format(nrow(demos_raw), big.mark = ",")))

cat("Loading mobile state lookup...\n")
state_lookup <- read_parquet(state_lookup_file) |>
  select(machine_id, state) |>
  mutate(machine_id = as.character(machine_id))

demos <- demos_raw |>
  mutate(machine_id = as.character(machine_id)) |>
  left_join(state_lookup, by = "machine_id") |>
  filter(!is.na(state), !state %in% EXCLUDE_STATES)

cat(sprintf("  %s machines after state join and exclusions\n",
            format(nrow(demos), big.mark = ",")))

# ============================================================================
# PRESENCE PANEL
# ============================================================================

cat("Loading presence panel...\n")
t0 <- proc.time()
presence <- read_parquet(file.path(data_dir, "machine_week_presence.parquet")) |>
  mutate(machine_id = as.character(machine_id)) |>
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

# Merge all demographic columns (gender, hoh_age, children_present, hh_income)
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
