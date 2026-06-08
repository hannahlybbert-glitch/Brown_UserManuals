# winsorization_robustness.R
# Pooled TWFE regressions for Pornhub under alternative winsorization choices.
#
# Machine-week thresholds: P95 (main), P96, P97, P98, P99, P99.5
# Session-level threshold: P95 from control-state sessions
#
# Saves: output/descriptives/pages_assessment/winsorization_robustness.csv

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(fixest)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

OUTDIR <- here::here("output", "descriptives", "pages_assessment")
dir.create(OUTDIR, recursive = TRUE, showWarnings = FALSE)

SITE_KEY <- "PORNHUB.COM"   # key used in machine_aggregated parquet filenames
BASE_DATE <- as.Date("2022-01-01")

# ── load stacked panel ────────────────────────────────────────────────────────
cat("Loading stacked panel...\n")
panel_obj    <- readRDS(file.path(int_dir, "stacked_panel.rds"))
stacked_base <- panel_obj$stacked_base
needed_weeks    <- panel_obj$needed_weeks
needed_machines <- panel_obj$needed_machines

cat(sprintf("  %s rows | %d cohorts | %d clusters\n",
    format(nrow(stacked_base), big.mark = ","),
    length(panel_obj$qualifying), panel_obj$n_clusters))

# ── machine-week duration data ────────────────────────────────────────────────
cat("Loading machine-week duration data...\n")
mw_data <- open_dataset(
    file.path(data_dir, paste0("machine_aggregated_", SITE_KEY, ".parquet"))
  ) |>
  filter(week_of_sample %in% needed_weeks,
         machine_id     %in% needed_machines) |>
  select(machine_id, week_of_sample, total_duration) |>
  collect()

cat(sprintf("  %s machine-week rows\n", format(nrow(mw_data), big.mark = ",")))

# Baseline distribution for threshold computation (2022 only, positive values)
baseline_dur <- mw_data |>
  filter(week_of_sample %in% 1:52, total_duration > 0) |>
  pull(total_duration)

cat(sprintf("  Baseline N = %s  (P50=%.0fs  P95=%.0fs  P99=%.0fs)\n",
    format(length(baseline_dur), big.mark = ","),
    quantile(baseline_dur, 0.50),
    quantile(baseline_dur, 0.95),
    quantile(baseline_dur, 0.99)))

# ── helper: build DV, join, run pooled, return row ───────────────────────────
run_one <- function(label, type, percentile, thresh_sec) {
  cat(sprintf("\n  [%s]  threshold = %.0fs (%.1f min)\n",
              label, thresh_sec, thresh_sec / 60))

  dv_data <- mw_data |>
    mutate(win_min = pmin(total_duration, thresh_sec) / 60) |>
    select(machine_id, week_of_sample, win_min)

  df <- stacked_base |>
    left_join(dv_data, by = c("machine_id", "week_of_sample")) |>
    mutate(win_min = coalesce(win_min, 0))

  res <- run_pooled(df, "win_min")

  baseline_short <- mean(df$win_min[df$treated == 0 & df$rel_week %in% SHORT_WINDOW],
                         na.rm = TRUE)
  baseline_long  <- mean(df$win_min[df$treated == 0 & df$rel_week %in% LONG_WINDOW],
                         na.rm = TRUE)

  cat(sprintf("    short: β=%.4f (SE=%.4f)  long: β=%.4f (SE=%.4f)\n",
              res$beta_shortterm, res$se_shortterm,
              res$beta_longterm,  res$se_longterm))

  data.frame(
    label          = label,
    type           = type,
    percentile     = percentile,
    threshold_sec  = thresh_sec,
    beta_short     = res$beta_shortterm,
    se_short       = res$se_shortterm,
    ci_lo_short    = res$beta_shortterm - 1.96 * res$se_shortterm,
    ci_hi_short    = res$beta_shortterm + 1.96 * res$se_shortterm,
    beta_long      = res$beta_longterm,
    se_long        = res$se_longterm,
    ci_lo_long     = res$beta_longterm - 1.96 * res$se_longterm,
    ci_hi_long     = res$beta_longterm + 1.96 * res$se_longterm,
    baseline_short = baseline_short,
    baseline_long  = baseline_long,
    stringsAsFactors = FALSE
  )
}

# ── machine-week threshold loop ───────────────────────────────────────────────
cat("\n── Machine-week thresholds ──────────────────────────────────────────────\n")

mw_percentiles <- c(
  mw_p95   = 0.95,
  mw_p96   = 0.96,
  mw_p97   = 0.97,
  mw_p98   = 0.98,
  mw_p99   = 0.99,
  mw_p99_5 = 0.995
)

mw_rows <- bind_rows(lapply(names(mw_percentiles), function(nm) {
  p      <- mw_percentiles[[nm]]
  thresh <- unname(quantile(baseline_dur, p))
  run_one(nm, "machine-week", p, thresh)
}))

# ── session-level thresholds (P95–P99.5) ─────────────────────────────────────
cat("\n── Session-level winsorization ─────────────────────────────────────────\n")

sess_file <- here::here("data", "ProcessComscore", "merged_cat_session_files",
                        "pornhub_sessions.parquet")

# Compute all session-level thresholds at once from control-state sessions
cat("  Computing session thresholds from control-state sessions...\n")
sess_ctrl_dur <- read_parquet(sess_file, col_select = c("treated", "duration")) |>
  filter(treated == 0, !is.na(duration)) |>
  pull(duration)

sess_percentiles <- c(
  sess_p95   = 0.95,
  sess_p96   = 0.96,
  sess_p97   = 0.97,
  sess_p98   = 0.98,
  sess_p99   = 0.99,
  sess_p99_5 = 0.995
)
sess_thresholds <- sapply(sess_percentiles, function(p) unname(quantile(sess_ctrl_dur, p)))
for (nm in names(sess_thresholds)) {
  cat(sprintf("  %s = %.0fs (%.1f min)\n", nm, sess_thresholds[nm], sess_thresholds[nm] / 60))
}

# Read full session data once, compute week_of_sample
cat("  Reading full session data...\n")
sess_raw <- read_parquet(
    sess_file,
    col_select = c("machine_id", "date", "duration")
  ) |>
  filter(!is.na(duration)) |>
  mutate(
    week_of_sample = as.integer(
      as.numeric(difftime(as.Date(date), BASE_DATE, units = "days")) %/% 7
    ) + 1L
  )

# Loop over session-level percentiles
sess_rows <- bind_rows(lapply(names(sess_percentiles), function(nm) {
  p      <- sess_percentiles[[nm]]
  thresh <- sess_thresholds[[nm]]
  cat(sprintf("\n  [%s]  threshold = %.0fs (%.1f min)\n", nm, thresh, thresh / 60))

  sess_mw <- sess_raw |>
    mutate(win_sec = pmin(duration, thresh)) |>
    group_by(machine_id, week_of_sample) |>
    summarise(win_min = sum(win_sec) / 60, .groups = "drop")

  df_s <- stacked_base |>
    left_join(sess_mw |> filter(week_of_sample %in% needed_weeks,
                                machine_id     %in% needed_machines),
              by = c("machine_id", "week_of_sample")) |>
    mutate(win_min = coalesce(win_min, 0))

  res <- run_pooled(df_s, "win_min")

  baseline_short <- mean(df_s$win_min[df_s$treated == 0 & df_s$rel_week %in% SHORT_WINDOW], na.rm = TRUE)
  baseline_long  <- mean(df_s$win_min[df_s$treated == 0 & df_s$rel_week %in% LONG_WINDOW],  na.rm = TRUE)

  cat(sprintf("    short: β=%.4f (SE=%.4f)  long: β=%.4f (SE=%.4f)\n",
              res$beta_shortterm, res$se_shortterm,
              res$beta_longterm,  res$se_longterm))

  data.frame(
    label          = nm,
    type           = "session",
    percentile     = p,
    threshold_sec  = thresh,
    beta_short     = res$beta_shortterm,
    se_short       = res$se_shortterm,
    ci_lo_short    = res$beta_shortterm - 1.96 * res$se_shortterm,
    ci_hi_short    = res$beta_shortterm + 1.96 * res$se_shortterm,
    beta_long      = res$beta_longterm,
    se_long        = res$se_longterm,
    ci_lo_long     = res$beta_longterm - 1.96 * res$se_longterm,
    ci_hi_long     = res$beta_longterm + 1.96 * res$se_longterm,
    baseline_short = baseline_short,
    baseline_long  = baseline_long,
    stringsAsFactors = FALSE
  )
}))

# ── save ──────────────────────────────────────────────────────────────────────
all_results <- bind_rows(mw_rows, sess_rows)
out_path    <- file.path(OUTDIR, "winsorization_robustness.csv")
write.csv(all_results, out_path, row.names = FALSE)
cat(sprintf("\nSaved → %s\n", out_path))
print(all_results[, c("label", "beta_short", "se_short", "beta_long", "se_long",
                      "baseline_short", "threshold_sec")])
