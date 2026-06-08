# Author: Matt Brown, assisted by Claude
# Created: 2026-03-03
# Purpose: Pre-period substitute-share diagnostics for xxx-active treated machines
#          Breakdowns by children-in-home status.
#
# Produces:
#   output/analysis/portfolio_diagnostics/scatter_ph_vs_sub.png          (pooled)
#   output/analysis/portfolio_diagnostics/scatter_ph_vs_sub_children.png (faceted)
#   output/analysis/portfolio_diagnostics/cdf_sub_share.png              (pooled)
#   output/analysis/portfolio_diagnostics/cdf_sub_share_children.png     (by children)
#
# Run before event_study_demographics.R to confirm 50% bin threshold is sensible.
#
# Usage:
#   Rscript code/analysis/portfolio_diagnostics.R

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(here)
})

# ============================================================================
# CONSTANTS  (mirror event_study_demographics.R)
# ============================================================================

project_root <- here::here()
data_dir  <- file.path(project_root, "data", "Aggregation", "machine_panel")
laws_file <- file.path(project_root, "raw", "statelaws", "statelaws_dates.csv")
agg_csv   <- file.path(project_root, "data", "Aggregation", "final_aggregated.csv")
demo_file <- file.path(project_root, "data", "ProcessComscore",
                       "full_demographics", "full_machine_person_demos.parquet")
out_dir   <- file.path(project_root, "output", "analysis", "portfolio_diagnostics")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

EXCLUDE_STATES  <- c("DC", "XX", "ZZ")
EXCLUDE_TREATED <- "TX"
CUTOFF_DATE    <- as.Date("2024-11-24")
T_MIN <- -16L; T_MAX <- 8L
t_range <- T_MIN:T_MAX
MAROON <- "#8c1515"
NAVY   <- "#0B3954"

THEME_BASE <- theme_bw() + theme(
  panel.grid.minor = element_blank(),
  panel.border     = element_blank(),
  axis.line        = element_line(color = "black", linewidth = 0.4),
  plot.title       = element_text(size = 12),
  plot.subtitle    = element_text(size = 8, color = "gray40"),
  axis.title       = element_text(size = 10),
  axis.text        = element_text(size = 9)
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
demos <- read_parquet(demo_file,
    col_select = c("machine_id", "state", "children_present")) |>
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

# Stash machine→children lookup before demos is released
machine_children <- demos |>
  select(machine_id, children_present) |>
  mutate(children_label = case_when(
    children_present == "Children:Yes" ~ "Children present",
    children_present == "Children:No"  ~ "No children",
    TRUE                               ~ NA_character_
  )) |>
  select(machine_id, children_label)

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
  mutate(machine_cohort = paste0(machine_id, "__", cohort))

rm(presence, demos)
cat(sprintf("Stacked: %s rows | %s machine×cohort  (%.1fs)\n",
    format(nrow(stacked_base),                      big.mark = ","),
    format(n_distinct(stacked_base$machine_cohort), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))

needed_weeks    <- sort(unique(as.integer(outer(unname(law_wos), t_range, "+"))))
needed_machines <- unique(stacked_base$machine_id)

# ============================================================================
# PRE-PERIOD ROWS (treated only)
# ============================================================================

cat("\nExtracting treated pre-period rows...\n")
pre_rows <- stacked_base |>
  filter(rel_week < 0L, treated == 1L) |>
  select(machine_id, week_of_sample, machine_cohort)

cat(sprintf("  %s machine×week rows | %s machines\n",
    format(nrow(pre_rows), big.mark = ","),
    format(n_distinct(pre_rows$machine_id), big.mark = ",")))

# ============================================================================
# LOAD PH / XV / XNXX DURATIONS
# ============================================================================

load_site_min <- function(site_slug) {
  open_dataset(file.path(data_dir,
      paste0("machine_aggregated_", site_slug, ".parquet"))) |>
    filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
    select(machine_id, week_of_sample, total_duration) |>
    collect()
}

cat("Loading site durations (PH, XV, XNXX)...\n")
t0 <- proc.time()
ph_dur   <- load_site_min("PORNHUB.COM")
xv_dur   <- load_site_min("XVIDEOS.COM")
xnxx_dur <- load_site_min("XNXX.COM")
cat(sprintf("  Loaded  (%.1fs)\n", (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# COMPUTE SUBSTITUTE SHARE PER MACHINE×COHORT
# ============================================================================

cat("\nComputing substitute share per machine×cohort...\n")
t0 <- proc.time()

sub_share_tbl <- pre_rows |>
  left_join(rename(ph_dur,   ph_min   = total_duration), by = c("machine_id", "week_of_sample")) |>
  left_join(rename(xv_dur,   xv_min   = total_duration), by = c("machine_id", "week_of_sample")) |>
  left_join(rename(xnxx_dur, xnxx_min = total_duration), by = c("machine_id", "week_of_sample")) |>
  replace_na(list(ph_min = 0, xv_min = 0, xnxx_min = 0)) |>
  group_by(machine_id, machine_cohort) |>
  summarise(
    ph_tot  = sum(ph_min),
    sub_tot = sum(xv_min + xnxx_min),
    .groups = "drop"
  ) |>
  filter(ph_tot > 0 | sub_tot > 0) |>
  mutate(sub_share = sub_tot / (ph_tot + sub_tot)) |>
  left_join(machine_children, by = "machine_id")

cat(sprintf("  %s any-active machine×cohort pairs  (%.1fs)\n",
    format(nrow(sub_share_tbl), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))

rm(pre_rows, ph_dur, xv_dur, xnxx_dur)

# Bin counts (pooled)
share_0    <- sub_share_tbl |> filter(sub_share == 0)
share_low  <- sub_share_tbl |> filter(sub_share > 0, sub_share <= 0.5)
share_high <- sub_share_tbl |> filter(sub_share > 0.5, sub_share < 1)
share_1    <- sub_share_tbl |> filter(sub_share == 1)

cat(sprintf("  Bin counts: share=0 %s | low(0-50%%) %s | high(50-99%%) %s | share=1 %s\n",
    format(nrow(share_0),    big.mark = ","),
    format(nrow(share_low),  big.mark = ","),
    format(nrow(share_high), big.mark = ","),
    format(nrow(share_1),    big.mark = ",")))

# Bin counts by children status
cat("  By children status:\n")
sub_share_tbl |>
  filter(!is.na(children_label)) |>
  mutate(bin = case_when(
    sub_share == 0                        ~ "share=0",
    sub_share > 0 & sub_share <= 0.5     ~ "low (0-50%)",
    sub_share > 0.5 & sub_share < 1      ~ "high (50-99%)",
    sub_share == 1                        ~ "share=1"
  )) |>
  count(children_label, bin) |>
  arrange(children_label, bin) |>
  with(cat(sprintf("    %-20s %-18s %s\n", children_label, bin,
                   format(n, big.mark = ","))))

# ============================================================================
# PLOT A — Scatter: PH vs substitute minutes (pooled)
# ============================================================================

cat("\nPlot A — Scatter (pooled)...\n")

p_scatter <- ggplot(sub_share_tbl,
    aes(x = log(ph_tot + 1), y = log(sub_tot + 1))) +
  geom_point(alpha = 0.15, size = 0.6, color = MAROON) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed",
              color = "gray50", linewidth = 0.5) +
  labs(
    x        = "log(PH minutes + 1)",
    y        = "log(XV + XNXX minutes + 1)",
    title    = "Pre-period PH vs substitute site usage (treated machine×cohort pairs)",
    subtitle = sprintf("n = %s any-active pairs  |  dashed line = equal usage",
                       format(nrow(sub_share_tbl), big.mark = ","))
  ) +
  THEME_BASE

path_a <- file.path(out_dir, "scatter_ph_vs_sub.png")
ggsave(path_a, p_scatter, width = 6, height = 6, dpi = 300)
cat(sprintf("  → %s\n", path_a))

# ============================================================================
# PLOT A2 — Scatter: faceted by children status
# ============================================================================

cat("Plot A2 — Scatter (by children)...\n")

sub_known <- sub_share_tbl |> filter(!is.na(children_label))
n_by_ch   <- sub_known |> count(children_label)

p_scatter_ch <- ggplot(sub_known,
    aes(x = log(ph_tot + 1), y = log(sub_tot + 1))) +
  geom_point(alpha = 0.15, size = 0.5, color = MAROON) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed",
              color = "gray50", linewidth = 0.5) +
  facet_wrap(~children_label) +
  labs(
    x        = "log(PH minutes + 1)",
    y        = "log(XV + XNXX minutes + 1)",
    title    = "Pre-period PH vs substitute site usage by children-in-home status",
    subtitle = sprintf("Children present: n=%s  |  No children: n=%s  |  dashed = equal usage",
      format(n_by_ch$n[n_by_ch$children_label == "Children present"], big.mark = ","),
      format(n_by_ch$n[n_by_ch$children_label == "No children"],      big.mark = ","))
  ) +
  THEME_BASE

path_a2 <- file.path(out_dir, "scatter_ph_vs_sub_children.png")
ggsave(path_a2, p_scatter_ch, width = 10, height = 5, dpi = 300)
cat(sprintf("  → %s\n", path_a2))

# ============================================================================
# PLOT B — CDF of substitute share (pooled)
# ============================================================================

cat("Plot B — CDF (pooled)...\n")

cdf_data <- sub_share_tbl |>
  arrange(sub_share) |>
  mutate(ecdf_val = seq_len(n()) / n())

p_cdf <- ggplot(cdf_data, aes(x = sub_share, y = ecdf_val)) +
  geom_line(color = MAROON, linewidth = 0.9) +
  geom_vline(xintercept = 0.5, linetype = "dashed", color = NAVY, linewidth = 0.5) +
  annotate("text", x = 0.52, y = 0.15, label = "50%", hjust = 0,
           color = NAVY, size = 3.2) +
  scale_x_continuous(breaks = seq(0, 1, 0.25), limits = c(0, 1)) +
  scale_y_continuous(breaks = seq(0, 1, 0.25), labels = scales::percent) +
  labs(
    x        = "Substitute share  [XV + XNXX] / [PH + XV + XNXX]",
    y        = "Cumulative fraction of machine×cohort pairs",
    title    = "CDF of pre-period substitute share (treated, any-active)",
    subtitle = sprintf(
      "share=0: %s  |  (0,0.5]: %s  |  (0.5,1): %s  |  share=1: %s",
      format(nrow(share_0),    big.mark = ","),
      format(nrow(share_low),  big.mark = ","),
      format(nrow(share_high), big.mark = ","),
      format(nrow(share_1),    big.mark = ","))
  ) +
  THEME_BASE

path_b <- file.path(out_dir, "cdf_sub_share.png")
ggsave(path_b, p_cdf, width = 7, height = 4.5, dpi = 300)
cat(sprintf("  → %s\n", path_b))

# ============================================================================
# PLOT B2 — CDF of substitute share by children status
# ============================================================================

cat("Plot B2 — CDF (by children)...\n")

cdf_children <- sub_known |>
  group_by(children_label) |>
  arrange(sub_share, .by_group = TRUE) |>
  mutate(ecdf_val = seq_len(n()) / n()) |>
  ungroup()

p_cdf_ch <- ggplot(cdf_children, aes(x = sub_share, y = ecdf_val,
                                      color = children_label,
                                      linetype = children_label)) +
  geom_line(linewidth = 0.9) +
  geom_vline(xintercept = 0.5, linetype = "dashed", color = "gray50", linewidth = 0.4) +
  scale_color_manual(values = c("Children present" = MAROON, "No children" = NAVY),
                     name = NULL) +
  scale_linetype_manual(values = c("Children present" = "solid", "No children" = "solid"),
                        name = NULL) +
  scale_x_continuous(breaks = seq(0, 1, 0.25), limits = c(0, 1)) +
  scale_y_continuous(breaks = seq(0, 1, 0.25), labels = scales::percent) +
  labs(
    x        = "Substitute share  [XV + XNXX] / [PH + XV + XNXX]",
    y        = "Cumulative fraction of machine×cohort pairs",
    title    = "CDF of pre-period substitute share by children-in-home status",
    subtitle = sprintf("Treated any-active pairs  |  Children present: n=%s  |  No children: n=%s",
      format(n_by_ch$n[n_by_ch$children_label == "Children present"], big.mark = ","),
      format(n_by_ch$n[n_by_ch$children_label == "No children"],      big.mark = ","))
  ) +
  THEME_BASE +
  theme(legend.position = "bottom")

path_b2 <- file.path(out_dir, "cdf_sub_share_children.png")
ggsave(path_b2, p_cdf_ch, width = 7, height = 4.5, dpi = 300)
cat(sprintf("  → %s\n", path_b2))

cat("\nAll done.\n")
