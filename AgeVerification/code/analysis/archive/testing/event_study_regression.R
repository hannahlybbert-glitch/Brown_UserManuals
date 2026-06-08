# Author: Matt Brown, assisted by Claude
# Created: 02/28/2026
# Purpose: Stacked TWFE event-study regressions — all 8 sites × 2 DVs
#          Full population sample (no XXX-active screening).
#          Texas excluded from pooled specs (EXCLUDE_TREATED).
#
# DVs:
#   over60      — 1 if machine had >60s on site in that week
#   win_min     — weekly minutes on site, winsorized at p95 of nonzero obs
#
# Sites: all_xxx (pooled), PORNHUB, XVIDEOS, XHAMSTER, XNXX,
#        CHATURBATE, other_XXX_sites, all_other_sites
#
# Specification:
#   dv ~ i(rel_week, treated, ref=-1) | machine_cohort + cohort_week
#   SE clustered by state
#
# Usage:
#   Rscript code/analysis/event_study_regression.R
#
# Outputs (output/analysis/event_study/):
#   {slug}_{dv}_coefs.csv   — coefficients + 95% CI
#   {slug}_{dv}.png         — event-study plot

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(fixest)
  library(ggplot2)
  library(here)
})

# ============================================================================
# CONSTANTS
# ============================================================================

project_root <- here::here()
data_dir  <- file.path(project_root, "data", "Aggregation", "machine_panel")
demo_file <- file.path(project_root, "data", "ProcessComscore",
                       "full_demographics", "full_machine_person_demos.parquet")
laws_file <- file.path(project_root, "raw", "statelaws", "statelaws_dates.csv")
agg_csv   <- file.path(project_root, "data", "Aggregation", "aggregated_file", "final_aggregated.csv")
out_dir   <- file.path(project_root, "output", "analysis", "event_study")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

EXCLUDE_STATES  <- c("DC", "XX", "ZZ")
EXCLUDE_TREATED <- "TX"   # TX law was immediately enjoined; excluded from pooled specs
CUTOFF_DATE    <- as.Date("2024-11-24")
T_MIN <- -16L; T_MAX <- 8L
t_range <- T_MIN:T_MAX
MAROON  <- "#8c1515"

XXX_SLUGS <- c("PORNHUB.COM", "CHATURBATE.COM", "XHAMSTER.COM",
                "XNXX.COM",   "XVIDEOS.COM",    "other_XXX_sites")

SITES <- list(
  list(key = "all_xxx",          label = "All XXX (pooled)",  slug = "all_xxx"),
  list(key = "PORNHUB.COM",      label = "Pornhub",           slug = "PORNHUB_COM"),
  list(key = "XVIDEOS.COM",      label = "xVideos",           slug = "XVIDEOS_COM"),
  list(key = "XHAMSTER.COM",     label = "xHamster",          slug = "XHAMSTER_COM"),
  list(key = "XNXX.COM",         label = "XNXX",              slug = "XNXX_COM"),
  list(key = "CHATURBATE.COM",   label = "Chaturbate",        slug = "CHATURBATE_COM"),
  list(key = "other_XXX_sites",  label = "Other XXX",         slug = "other_XXX"),
  list(key = "all_other_sites",  label = "All other sites",   slug = "all_other"),
  list(key = "VPN_clean",       label = "VPN (clean)",        slug = "VPN_clean"),
  list(key = "allVPN",          label = "All VPN",            slug = "allVPN")
)

# ============================================================================
# LOAD SHARED DATA
# ============================================================================

cat("Loading week→date map...\n")
week_dates <- read.csv(agg_csv,
    colClasses = c(week_of_sample = "integer", week_start_date = "character")) |>
  select(week_of_sample, week_start_date) |>
  distinct() |>
  mutate(week_start_date = as.Date(week_start_date))

cat("Loading state laws...\n")
laws <- read.csv(laws_file, stringsAsFactors = FALSE, na.strings = c("", "NA"))
laws$day_effective <- as.Date(laws$day_effective, format = "%d%b%Y")
treated_all <- sort(laws$state[!is.na(laws$day_passed)])
law_date    <- setNames(laws$day_effective, laws$state)
qualifying  <- treated_all[!is.na(law_date[treated_all]) &
                            law_date[treated_all] < CUTOFF_DATE &
                            !treated_all %in% EXCLUDE_TREATED]
cat(sprintf("  Qualifying (%d): %s\n", length(qualifying),
            paste(qualifying, collapse = ", ")))

base_date <- as.Date("2022-01-01")
law_wos <- setNames(
  sapply(qualifying, function(s)
    as.integer(law_date[s] - base_date) %/% 7L + 1L),
  qualifying
)

cat("Loading machine demographics...\n")
demos <- read_parquet(demo_file, col_select = c("machine_id", "state")) |>
  distinct(machine_id, .keep_all = TRUE) |>
  filter(!state %in% EXCLUDE_STATES)

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

# ============================================================================
# BUILD STACKED PANEL  (once, shared across all sites)
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
cat(sprintf("Stacked: %s rows | %s machine×cohort | %s cohort×week | %d clusters  (%.1fs)\n",
    format(nrow(stacked_base),                           big.mark = ","),
    format(n_distinct(stacked_base$machine_cohort),      big.mark = ","),
    format(n_distinct(stacked_base$cohort_week),         big.mark = ","),
    n_distinct(stacked_base$state),
    (proc.time() - t0)[["elapsed"]]))

needed_weeks    <- sort(unique(as.integer(outer(unname(law_wos), t_range, "+"))))
needed_machines <- unique(stacked_base$machine_id)
n_clusters      <- n_distinct(stacked_base$state)

# ============================================================================
# HELPERS
# ============================================================================

load_site_duration <- function(site_key) {
  if (site_key == "all_xxx") {
    # Sum total_duration across all 6 XXX site parquets
    lapply(XXX_SLUGS, function(s) {
      open_dataset(file.path(data_dir,
                             paste0("machine_aggregated_", s, ".parquet"))) |>
        filter(week_of_sample %in% needed_weeks,
               machine_id     %in% needed_machines) |>
        select(machine_id, week_of_sample, total_duration) |>
        collect()
    }) |>
      bind_rows() |>
      group_by(machine_id, week_of_sample) |>
      summarise(total_duration = sum(total_duration, na.rm = TRUE),
                .groups = "drop")
  } else {
    open_dataset(file.path(data_dir,
                           paste0("machine_aggregated_", site_key, ".parquet"))) |>
      filter(week_of_sample %in% needed_weeks,
             machine_id     %in% needed_machines) |>
      select(machine_id, week_of_sample, total_duration) |>
      collect()
  }
}

# p95 winsorization threshold from 2022 baseline (weeks 1-52) only,
# avoiding secular trends in session duration contaminating the cap.
compute_p95_2022 <- function(site_key) {
  dur <- if (site_key == "all_xxx") {
    lapply(XXX_SLUGS, function(s) {
      open_dataset(file.path(data_dir,
                             paste0("machine_aggregated_", s, ".parquet"))) |>
        filter(week_of_sample %in% 1:52, machine_id %in% needed_machines) |>
        select(machine_id, week_of_sample, total_duration) |>
        collect()
    }) |>
      bind_rows() |>
      group_by(machine_id, week_of_sample) |>
      summarise(total_duration = sum(total_duration, na.rm = TRUE), .groups = "drop")
  } else {
    open_dataset(file.path(data_dir,
                           paste0("machine_aggregated_", site_key, ".parquet"))) |>
      filter(week_of_sample %in% 1:52, machine_id %in% needed_machines) |>
      select(total_duration) |>
      collect()
  }
  quantile(dur$total_duration[dur$total_duration > 0], 0.95, na.rm = TRUE)
}

extract_coefs <- function(fit) {
  idx   <- grep("treated", names(coef(fit)))
  betas <- coef(fit)[idx]
  se_v  <- sqrt(diag(vcov(fit)))[idx]
  ci    <- confint(fit, level = 0.95)[idx, , drop = FALSE]
  coefs <- data.frame(
    rel_week = as.integer(regmatches(names(betas), regexpr("-?\\d+", names(betas)))),
    beta     = as.numeric(betas),
    se       = as.numeric(se_v),
    ci_lo    = ci[, 1],
    ci_hi    = ci[, 2],
    stringsAsFactors = FALSE
  )
  ref_row <- data.frame(rel_week = -1L, beta = 0, se = NA_real_, ci_lo = 0, ci_hi = 0)
  bind_rows(coefs, ref_row) |> arrange(rel_week)
}

save_plot <- function(coefs, site_label, dv_label, y_label, slug, dv_slug, baseline_mean) {
  p <- ggplot(coefs, aes(x = rel_week)) +
    geom_errorbar(aes(ymin = ci_lo, ymax = ci_hi), width = 0.3, color = MAROON, linewidth = 0.6) +
    geom_line(aes(y = beta),  color = MAROON, linewidth = 0.9) +
    geom_point(aes(y = beta), color = MAROON, size = 2) +
    geom_hline(yintercept = 0, linetype = "dashed", linewidth = 0.5) +
    geom_vline(xintercept = 0, linetype = "dashed", color = "gray50", linewidth = 0.5) +
    annotate("text", x = 0.25, y = 0,
             label = sprintf("(mean = %.3f)", baseline_mean),
             hjust = 0, vjust = 1.6, size = 2.8, color = "gray40") +
    scale_x_continuous(breaks = seq(T_MIN, T_MAX, by = 4)) +
    labs(
      x        = "Weeks relative to law effective date",
      y        = y_label,
      title    = sprintf("Stacked TWFE — %s  (%s)", site_label, dv_label),
      subtitle = sprintf(
        "Machine×cohort + cohort×week FE  |  SE clustered by state (%d clusters, %d cohorts)",
        n_clusters, length(qualifying))
    ) +
    theme_bw() +
    theme(
      panel.grid.minor = element_blank(),
      panel.border     = element_blank(),
      axis.line        = element_line(color = "black", linewidth = 0.4),
      plot.title       = element_text(size = 12),
      plot.subtitle    = element_text(size = 8, color = "gray40"),
      axis.title       = element_text(size = 10),
      axis.text        = element_text(size = 9)
    )
  path <- file.path(out_dir, sprintf("%s_%s.png", slug, dv_slug))
  ggsave(path, p, width = 9, height = 4.5, dpi = 300)
  path
}

run_one <- function(df, formula_str, site_label, dv_label, y_label, slug, dv_slug) {
  t0  <- proc.time()
  fit <- feols(as.formula(formula_str),
               data = df, cluster = ~state, warn = FALSE, notes = FALSE)
  elapsed <- (proc.time() - t0)[["elapsed"]]
  cat(sprintf("    %s: N=%s, R2_within=%.4f, time=%.1fs\n",
      dv_label,
      format(fit$nobs, big.mark = ","),
      fit$r2["r2_within"],
      elapsed))

  coefs    <- extract_coefs(fit)
  csv_path <- file.path(out_dir, sprintf("%s_%s_coefs.csv", slug, dv_slug))
  write.csv(coefs, csv_path, row.names = FALSE)

  baseline_mean <- mean(df[[dv_slug]][df$treated == 1L & df$rel_week == -1L], na.rm = TRUE)
  fig_path <- save_plot(coefs, site_label, dv_label, y_label, slug, dv_slug, baseline_mean)
  cat(sprintf("    → %s\n    → %s\n", csv_path, fig_path))
  invisible(fit)
}

# ============================================================================
# PRE-BUILD XXX SITE WIN_MINS (used for all_xxx and individual XXX sites)
# ============================================================================
cat("\nPre-building per-site XXX win_min (for all_xxx additive construction)...\n")
t0_prebuilt <- proc.time()

xxx_win_prebuilt <- lapply(XXX_SLUGS, function(s) {
  t1 <- proc.time()
  p95_s <- compute_p95_2022(s)
  dur_s <- open_dataset(file.path(data_dir, paste0("machine_aggregated_", s, ".parquet"))) |>
    filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
    select(machine_id, week_of_sample, total_duration) |>
    collect()
  result <- dur_s |>
    mutate(win_min_s = pmin(total_duration, p95_s) / 60) |>
    select(machine_id, week_of_sample, win_min_s)
  names(result)[3] <- paste0("win_", gsub("[^A-Za-z0-9]", "_", s))
  cat(sprintf("  %s: p95 = %.1f min  (%.1fs)\n", s, p95_s / 60,
              (proc.time() - t1)[["elapsed"]]))
  result
})

xxx_win_wide <- Reduce(
  function(a, b) full_join(a, b, by = c("machine_id", "week_of_sample")),
  xxx_win_prebuilt
) |>
  mutate(win_min_allxxx = rowSums(across(starts_with("win_")), na.rm = TRUE))

rm(xxx_win_prebuilt)
cat(sprintf("Pre-build complete: %s rows  (%.1fs total)\n",
    format(nrow(xxx_win_wide), big.mark = ","),
    (proc.time() - t0_prebuilt)[["elapsed"]]))

# ============================================================================
# MAIN LOOP — all 8 sites
# ============================================================================
cat("\n", strrep("=", 60), "\n", sep = "")
cat("Running regressions: 8 sites × 2 DVs\n")
cat(strrep("=", 60), "\n\n", sep = "")

for (site in SITES) {
  cat(sprintf("--- %s (%s) ---\n", site$label, site$key))

  # Load site-specific duration data
  t0       <- proc.time()
  dur_data <- load_site_duration(site$key)
  cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
      format(nrow(dur_data), big.mark = ","),
      (proc.time() - t0)[["elapsed"]]))

  # Join to stacked panel
  df <- stacked_base |>
    left_join(dur_data, by = c("machine_id", "week_of_sample"))
  rm(dur_data)

  if (site$key == "all_xxx") {
    p95 <- compute_p95_2022(site$key)
    cat(sprintf("  p95 (summed, ref only) = %.1fs (%.1f min)\n", p95, p95 / 60))
    df <- df |>
      mutate(over60 = as.integer(!is.na(total_duration) & total_duration > 60)) |>
      left_join(select(xxx_win_wide, machine_id, week_of_sample, win_min_allxxx),
                by = c("machine_id", "week_of_sample")) |>
      mutate(win_min = coalesce(win_min_allxxx, 0)) |>
      select(-win_min_allxxx)

  } else if (site$key %in% XXX_SLUGS) {
    win_col <- paste0("win_", gsub("[^A-Za-z0-9]", "_", site$key))
    df <- df |>
      mutate(over60 = as.integer(!is.na(total_duration) & total_duration > 60)) |>
      left_join(select(xxx_win_wide, machine_id, week_of_sample, all_of(win_col)),
                by = c("machine_id", "week_of_sample")) |>
      rename(win_min = all_of(win_col)) |>
      mutate(win_min = coalesce(win_min, 0))

  } else {
    p95 <- compute_p95_2022(site$key)
    cat(sprintf("  p95 = %.1fs (%.1f min)\n", p95, p95 / 60))
    df <- df |>
      mutate(
        over60  = as.integer(!is.na(total_duration) & total_duration > 60),
        win_min = pmin(replace(total_duration, is.na(total_duration), 0), p95) / 60
      )
  }

  # Regression 1: over60
  run_one(df,
    "over60 ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week",
    site$label, ">60s binary", "Change in Pr(>60s)", site$slug, "over60")

  # Regression 2: winsorized minutes
  run_one(df,
    "win_min ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week",
    site$label, "Win. min/machine (p95)", "Change in min/machine/week (p95-win.)",
    site$slug, "win_min")

  rm(df)
  cat("\n")
}

cat("All done.\n")
