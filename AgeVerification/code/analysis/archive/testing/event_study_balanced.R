# Author: Matt Brown, assisted by Claude
# Created: 2026-03-06
# Purpose: Compare unbalanced (baseline) vs balanced panel event-study results
#
# "Balanced" = machine×cohort pairs that appear in ALL 25 event-window weeks (τ ∈ [-16,+8]).
# Unbalanced coefficients are read from existing CSVs (output/analysis/event_study/)
# to avoid re-running those regressions.
#
# Sites: All XXX, Pornhub, xVideos
# DVs:   over60, win_min
#
# Usage:
#   Rscript code/analysis/event_study_balanced.R
#
# Outputs:
#   output/analysis/event_study_balanced/{slug}_{dv}_balanced_comparison.png  (6 plots)
#   output/analysis/balanced_comparison_over60.md
#   output/analysis/balanced_comparison_win_min.md

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

project_root  <- here::here()
data_dir      <- file.path(project_root, "data", "Aggregation", "machine_panel")
demo_file     <- file.path(project_root, "data", "ProcessComscore",
                           "full_demographics", "full_machine_person_demos.parquet")
laws_file     <- file.path(project_root, "raw", "statelaws", "statelaws_dates.csv")
agg_csv       <- file.path(project_root, "data", "Aggregation", "final_aggregated.csv")
unbal_dir     <- file.path(project_root, "output", "analysis", "event_study")
out_dir       <- file.path(project_root, "output", "analysis", "event_study_balanced")
out_tables    <- file.path(project_root, "output", "analysis")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

EXCLUDE_STATES  <- c("DC", "XX", "ZZ")
EXCLUDE_TREATED <- "TX"
CUTOFF_DATE    <- as.Date("2024-11-24")
T_MIN <- -16L; T_MAX <- 8L
t_range <- T_MIN:T_MAX
MAROON <- "#8c1515"
NAVY   <- "#0B3954"

XXX_SLUGS <- c("PORNHUB.COM", "CHATURBATE.COM", "XHAMSTER.COM",
                "XNXX.COM",   "XVIDEOS.COM",    "other_XXX_sites")

SITES <- list(
  list(key = "all_xxx",     label = "All XXX", slug = "all_xxx"),
  list(key = "PORNHUB.COM", label = "Pornhub", slug = "PORNHUB_COM"),
  list(key = "XVIDEOS.COM", label = "xVideos", slug = "XVIDEOS_COM")
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
rm(demos)
cat(sprintf("  %s rows | %s machines  (%.1fs)\n",
    format(nrow(presence), big.mark = ","),
    format(n_distinct(presence$machine_id), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))

control_states <- setdiff(unique(presence$state), treated_all)

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
cat(sprintf("Stacked: %s rows | %s machine×cohort  (%.1fs)\n",
    format(nrow(stacked_base),                      big.mark = ","),
    format(n_distinct(stacked_base$machine_cohort), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))

needed_weeks    <- sort(unique(as.integer(outer(unname(law_wos), t_range, "+"))))
needed_machines <- unique(stacked_base$machine_id)

# ============================================================================
# BUILD BALANCED MACHINE×COHORT SET
# ============================================================================

cat("\nBuilding balanced machine×cohort set (all 25 event-window weeks required)...\n")
t0 <- proc.time()

n_weeks_required <- length(t_range)   # 25

balanced_mcs <- stacked_base |>
  group_by(machine_cohort) |>
  summarise(n_weeks = n_distinct(week_of_sample), .groups = "drop") |>
  filter(n_weeks == n_weeks_required) |>
  pull(machine_cohort)

n_total <- n_distinct(stacked_base$machine_cohort)
n_bal   <- length(balanced_mcs)
cat(sprintf("  Balanced: %s of %s machine×cohort pairs retained (%.1f%%)  (%.1fs)\n",
    format(n_bal,   big.mark = ","),
    format(n_total, big.mark = ","),
    100 * n_bal / n_total,
    (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# HELPERS
# ============================================================================

load_site_duration <- function(site_key) {
  if (site_key == "all_xxx") {
    lapply(XXX_SLUGS, function(s) {
      open_dataset(file.path(data_dir, paste0("machine_aggregated_", s, ".parquet"))) |>
        filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
        select(machine_id, week_of_sample, total_duration) |>
        collect()
    }) |>
      bind_rows() |>
      group_by(machine_id, week_of_sample) |>
      summarise(total_duration = sum(total_duration, na.rm = TRUE), .groups = "drop")
  } else {
    open_dataset(file.path(data_dir, paste0("machine_aggregated_", site_key, ".parquet"))) |>
      filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
      select(machine_id, week_of_sample, total_duration) |>
      collect()
  }
}

compute_p95_2022 <- function(site_key) {
  dur <- if (site_key == "all_xxx") {
    lapply(XXX_SLUGS, function(s) {
      open_dataset(file.path(data_dir, paste0("machine_aggregated_", s, ".parquet"))) |>
        filter(week_of_sample %in% 1:52, machine_id %in% needed_machines) |>
        select(machine_id, week_of_sample, total_duration) |>
        collect()
    }) |>
      bind_rows() |>
      group_by(machine_id, week_of_sample) |>
      summarise(total_duration = sum(total_duration, na.rm = TRUE), .groups = "drop")
  } else {
    open_dataset(file.path(data_dir, paste0("machine_aggregated_", site_key, ".parquet"))) |>
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

save_comparison_plot <- function(unbal_coefs, bal_coefs, site_label, dv_label,
                                  slug, dv_slug, n_unbal, n_bal) {
  unbal_coefs$spec <- "Unbalanced"
  bal_coefs$spec   <- "Balanced (all 25 weeks)"
  plot_data <- bind_rows(unbal_coefs, bal_coefs) |>
    mutate(spec = factor(spec, levels = c("Unbalanced", "Balanced (all 25 weeks)")))

  p <- ggplot(plot_data, aes(x = rel_week, color = spec, fill = spec)) +
    geom_ribbon(aes(ymin = ci_lo, ymax = ci_hi), alpha = 0.15, color = NA) +
    geom_line(aes(y = beta), linewidth = 0.9) +
    geom_point(aes(y = beta), size = 1.8) +
    geom_hline(yintercept = 0, linetype = "dashed", linewidth = 0.4, color = "gray40") +
    geom_vline(xintercept = 0, linetype = "dashed", linewidth = 0.4, color = "gray50") +
    scale_color_manual(values = c("Unbalanced" = MAROON,
                                  "Balanced (all 25 weeks)" = NAVY)) +
    scale_fill_manual( values = c("Unbalanced" = MAROON,
                                  "Balanced (all 25 weeks)" = NAVY)) +
    scale_x_continuous(breaks = seq(T_MIN, T_MAX, by = 4)) +
    labs(
      x        = "Weeks relative to law effective date",
      y        = dv_label,
      color    = NULL, fill = NULL,
      title    = sprintf("Balanced vs unbalanced panel — %s", site_label),
      subtitle = sprintf(
        "Unbalanced: %s machine×cohort pairs  |  Balanced: %s (%d cohorts, %d state clusters)",
        format(n_unbal, big.mark = ","),
        format(n_bal,   big.mark = ","),
        length(qualifying),
        n_distinct(stacked_base$state))
    ) +
    theme_bw() +
    theme(
      panel.grid.minor  = element_blank(),
      panel.border      = element_blank(),
      axis.line         = element_line(color = "black", linewidth = 0.4),
      plot.title        = element_text(size = 12),
      plot.subtitle     = element_text(size = 8, color = "gray40"),
      axis.title        = element_text(size = 10),
      axis.text         = element_text(size = 9),
      legend.position   = "bottom",
      legend.text       = element_text(size = 9)
    )

  path <- file.path(out_dir, sprintf("%s_%s_balanced_comparison.png", slug, dv_slug))
  ggsave(path, p, width = 9, height = 4.5, dpi = 300)
  cat(sprintf("    → %s\n", path))
  invisible(p)
}

run_pooled <- function(df, dv) {
  df2 <- df |>
    mutate(
      pre       = as.integer(rel_week %in% -16:-5),
      shortterm = as.integer(rel_week %in% 0:3),
      longterm  = as.integer(rel_week %in% 4:8)
    )
  fml <- as.formula(
    sprintf("%s ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week", dv)
  )
  tryCatch({
    fit  <- feols(fml, data = df2, cluster = ~state, warn = FALSE, notes = FALSE)
    cf   <- coef(fit)
    se_v <- sqrt(diag(vcov(fit)))
    list(
      beta_pre       = unname(cf["treated:pre"]),
      se_pre         = unname(se_v["treated:pre"]),
      beta_shortterm = unname(cf["treated:shortterm"]),
      se_shortterm   = unname(se_v["treated:shortterm"]),
      beta_longterm  = unname(cf["treated:longterm"]),
      se_longterm    = unname(se_v["treated:longterm"]),
      n_obs          = fit$nobs,
      n_mc           = n_distinct(df2$machine_cohort)
    )
  }, error = function(e) {
    cat(sprintf("      ERROR: %s\n", conditionMessage(e)))
    list(beta_pre = NA_real_, se_pre = NA_real_,
         beta_shortterm = NA_real_, se_shortterm = NA_real_,
         beta_longterm  = NA_real_, se_longterm  = NA_real_,
         n_obs = 0L, n_mc = 0L)
  })
}

fmt_coef <- function(beta, se) {
  if (is.na(beta)) return("—")
  sprintf("%.4f (%.4f)", beta, se)
}

# ============================================================================
# RESULT STORAGE
# ============================================================================

dvs     <- c("over60", "win_min")
dv_labels <- c(over60 = "Change in Pr(>60s)", win_min = "Change in winsorized min/week")
specs   <- c("Unbalanced", "Balanced")
# Results: list[dv][metric][site_label × spec_label]
site_labels <- sapply(SITES, `[[`, "label")
col_names   <- as.vector(outer(site_labels,
                                c("(Unbal)", "(Bal)"),
                                paste))
results <- lapply(dvs, function(dv) {
  m <- matrix(NA_character_, nrow = 4L, ncol = length(col_names),
              dimnames = list(c("β_pre", "β_ST", "β_LT", "N (obs) / N (m×c)"),
                              col_names))
  m
})
names(results) <- dvs

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
# MAIN LOOP
# ============================================================================
cat("\n", strrep("=", 60), "\n", sep = "")
cat("Running regressions: 3 sites\n")
cat(strrep("=", 60), "\n\n", sep = "")

for (s_idx in seq_along(SITES)) {
  site <- SITES[[s_idx]]
  cat(sprintf("--- %s (%s) ---\n", site$label, site$key))

  t0       <- proc.time()
  dur_data <- load_site_duration(site$key)
  cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
      format(nrow(dur_data), big.mark = ","),
      (proc.time() - t0)[["elapsed"]]))

  df_site <- stacked_base |>
    left_join(dur_data, by = c("machine_id", "week_of_sample"))
  rm(dur_data)

  if (site$key == "all_xxx") {
    p95 <- compute_p95_2022(site$key)
    cat(sprintf("  p95 (summed, ref only) = %.1fs (%.1f min)\n", p95, p95 / 60))
    df_site <- df_site |>
      mutate(over60 = as.integer(!is.na(total_duration) & total_duration > 60)) |>
      left_join(select(xxx_win_wide, machine_id, week_of_sample, win_min_allxxx),
                by = c("machine_id", "week_of_sample")) |>
      mutate(win_min = coalesce(win_min_allxxx, 0)) |>
      select(-win_min_allxxx)

  } else if (site$key %in% XXX_SLUGS) {
    win_col <- paste0("win_", gsub("[^A-Za-z0-9]", "_", site$key))
    df_site <- df_site |>
      mutate(over60 = as.integer(!is.na(total_duration) & total_duration > 60)) |>
      left_join(select(xxx_win_wide, machine_id, week_of_sample, all_of(win_col)),
                by = c("machine_id", "week_of_sample")) |>
      rename(win_min = all_of(win_col)) |>
      mutate(win_min = coalesce(win_min, 0))

  } else {
    p95 <- compute_p95_2022(site$key)
    cat(sprintf("  p95 = %.1fs (%.1f min)\n", p95, p95 / 60))
    df_site <- df_site |>
      mutate(
        over60  = as.integer(!is.na(total_duration) & total_duration > 60),
        win_min = pmin(replace(total_duration, is.na(total_duration), 0), p95) / 60
      )
  }

  df_bal <- df_site |> filter(machine_cohort %in% balanced_mcs)
  n_unbal_mc <- n_distinct(df_site$machine_cohort)
  n_bal_mc   <- n_distinct(df_bal$machine_cohort)
  cat(sprintf("  machine×cohort: unbalanced %s | balanced %s\n",
      format(n_unbal_mc, big.mark = ","),
      format(n_bal_mc,   big.mark = ",")))

  for (dv in dvs) {
    cat(sprintf("  DV: %s\n", dv))

    # ---- Event study plots ----
    unbal_csv <- file.path(unbal_dir, sprintf("%s_%s_coefs.csv", site$slug, dv))
    if (file.exists(unbal_csv)) {
      unbal_coefs <- read.csv(unbal_csv)
      cat(sprintf("    Unbalanced coefs: read from %s\n", basename(unbal_csv)))
    } else {
      cat(sprintf("    WARNING: %s not found; running unbalanced regression\n", unbal_csv))
      t1  <- proc.time()
      fit <- feols(as.formula(sprintf(
        "%s ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week", dv)),
        data = df_site, cluster = ~state, warn = FALSE, notes = FALSE)
      unbal_coefs <- extract_coefs(fit)
      cat(sprintf("    Unbalanced fit  (%.1fs)\n", (proc.time() - t1)[["elapsed"]]))
    }

    cat("    Balanced event study... ")
    t1  <- proc.time()
    fit_bal <- feols(as.formula(sprintf(
      "%s ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week", dv)),
      data = df_bal, cluster = ~state, warn = FALSE, notes = FALSE)
    bal_coefs <- extract_coefs(fit_bal)
    cat(sprintf("(%.1fs)\n", (proc.time() - t1)[["elapsed"]]))

    save_comparison_plot(
      unbal_coefs, bal_coefs,
      site_label = site$label,
      dv_label   = dv_labels[[dv]],
      slug       = site$slug,
      dv_slug    = dv,
      n_unbal    = n_unbal_mc,
      n_bal      = n_bal_mc
    )

    # ---- Pooled pre/ST/LT ----
    cat("    Pooled unbalanced... ")
    t1 <- proc.time()
    res_u <- run_pooled(df_site, dv)
    cat(sprintf("(%.1fs)\n", (proc.time() - t1)[["elapsed"]]))

    cat("    Pooled balanced... ")
    t1 <- proc.time()
    res_b <- run_pooled(df_bal, dv)
    cat(sprintf("(%.1fs)\n", (proc.time() - t1)[["elapsed"]]))

    col_u <- paste0(site$label, " (Unbal)")
    col_b <- paste0(site$label, " (Bal)")
    results[[dv]]["β_pre",              col_u] <- fmt_coef(res_u$beta_pre,       res_u$se_pre)
    results[[dv]]["β_ST",               col_u] <- fmt_coef(res_u$beta_shortterm, res_u$se_shortterm)
    results[[dv]]["β_LT",               col_u] <- fmt_coef(res_u$beta_longterm,  res_u$se_longterm)
    results[[dv]]["N (obs) / N (m×c)",  col_u] <- sprintf("%s / %s",
        format(res_u$n_obs, big.mark = ","), format(res_u$n_mc, big.mark = ","))
    results[[dv]]["β_pre",              col_b] <- fmt_coef(res_b$beta_pre,       res_b$se_pre)
    results[[dv]]["β_ST",               col_b] <- fmt_coef(res_b$beta_shortterm, res_b$se_shortterm)
    results[[dv]]["β_LT",               col_b] <- fmt_coef(res_b$beta_longterm,  res_b$se_longterm)
    results[[dv]]["N (obs) / N (m×c)",  col_b] <- sprintf("%s / %s",
        format(res_b$n_obs, big.mark = ","), format(res_b$n_mc, big.mark = ","))
  }

  rm(df_site, df_bal)
  cat("\n")
}

# ============================================================================
# WRITE MARKDOWN TABLES
# ============================================================================

write_comparison_table <- function(mat, dv_label, filepath) {
  cols     <- colnames(mat)
  header   <- paste0("| Estimate | ", paste(cols, collapse = " | "), " |")
  sep_line <- paste0("|", paste(rep(":---|", length(cols) + 1L), collapse = ""))

  content <- c(
    sprintf("# Balanced vs Unbalanced Panel — %s\n", dv_label),
    sprintf("Pooled three-period TWFE: `dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week`. SE clustered by state.  "),
    sprintf("Reference period: τ ∈ {−4,...,−1}. β_ST: τ ∈ [0,3]. β_LT: τ ∈ [4,8]. β_pre: τ ∈ [−16,−5].  "),
    sprintf("**Balanced** = machine×cohort pairs present in all %d event-window weeks. Format: β (SE).\n",
            length(t_range)),
    header, sep_line
  )
  for (row_nm in rownames(mat)) {
    vals <- mat[row_nm, ]
    vals[is.na(vals)] <- "—"
    content <- c(content,
      paste0("| **", row_nm, "** | ", paste(vals, collapse = " | "), " |"))
  }
  writeLines(content, filepath)
  cat(sprintf("Wrote: %s\n", filepath))
}

cat(strrep("=", 60), "\n", sep = "")
cat("Writing tables\n")
cat(strrep("=", 60), "\n\n", sep = "")

write_comparison_table(
  results[["over60"]],
  "Pr(>60s on site) — over60",
  file.path(out_tables, "balanced_comparison_over60.md")
)

write_comparison_table(
  results[["win_min"]],
  "Winsorized min/machine/week — win_min",
  file.path(out_tables, "balanced_comparison_win_min.md")
)

cat("\nAll done.\n")
