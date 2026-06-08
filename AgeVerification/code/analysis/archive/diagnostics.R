# Author: Matt Brown, assisted by Claude
# Created: 2026-03-06
# Purpose: Diagnostic analyses.
#          Merges event_study_balanced.R + portfolio_diagnostics.R + se_diagnostics.R.
#
# Requires: data/intermediate/stacked_panel.rds, data/intermediate/xxx_win_wide.rds
#           data/intermediate/regression_results.rds (from run_regressions.R)
#
# Section A — Balanced panel comparison
# Section B — Portfolio diagnostics (substitute-share, scatter + CDF)
# Section C — SE diagnostics (Moulton, ICC, forest plots, diversion ratio)
#
# Usage:
#   Rscript code/analysis/diagnostics.R

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(tidyr)
  library(fixest)
  library(ggplot2)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

# ============================================================================
# LOAD SHARED DATA
# ============================================================================

cat("Loading stacked panel from RDS...\n")
sp <- readRDS(file.path(int_dir, "stacked_panel.rds"))
stacked_base    <- sp$stacked_base
week_dates      <- sp$week_dates
needed_weeks    <- sp$needed_weeks
needed_machines <- sp$needed_machines
law_wos         <- sp$law_wos
law_date        <- sp$law_date
qualifying      <- sp$qualifying
n_clusters      <- sp$n_clusters
control_states  <- if (!is.null(sp$control_states)) sp$control_states else sp$never_treated_states
balanced_mcs    <- sp$balanced_mcs
rm(sp)

if (!is.null(MOBILE_FILTER)) {
  stacked_base <- stacked_base |> filter(mobile == MOBILE_FILTER)
  cat(sprintf("  MOBILE_FILTER=%d applied: %s rows remaining\n",
      MOBILE_FILTER, format(nrow(stacked_base), big.mark = ",")))
}

xxx_win_wide <- readRDS(file.path(int_dir, "xxx_win_wide.rds"))

cat(sprintf("  Stacked: %s rows | %d clusters | %d cohorts\n",
    format(nrow(stacked_base), big.mark = ","), n_clusters, length(qualifying)))
cat(sprintf("  Balanced m×c: %s\n", format(length(balanced_mcs), big.mark = ",")))

# ============================================================================
# SECTION A — BALANCED PANEL COMPARISON
# ============================================================================

cat("\n", strrep("=", 60), "\n", sep = "")
cat("Section A — Balanced panel comparison\n")
cat(strrep("=", 60), "\n\n", sep = "")

out_dir_balanced <- file.path(out_base, "diagnostics", "event_study_balanced")
out_tables_dir   <- out_dir_balanced
dir.create(out_dir_balanced, recursive = TRUE, showWarnings = FALSE)

# BAL_SITES, dvs sourced from config.R
dv_labels  <- c(over60 = "Change in Pr(>60s)", win_min = "Change in winsorized min/week")
col_names  <- as.vector(outer(sapply(BAL_SITES, `[[`, "label"),
                               c("(Unbal)", "(Bal)"), paste))
bal_results <- lapply(dvs, function(dv) {
  matrix(NA_character_, nrow = 4L, ncol = length(col_names),
         dimnames = list(c("\u03b2_pre", "\u03b2_ST", "\u03b2_LT", "N (obs) / N (m\u00d7c)"),
                         col_names))
}) |> setNames(dvs)

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
      title    = sprintf("Balanced vs unbalanced panel \u2014 %s", site_label),
      subtitle = sprintf(
        "Unbalanced: %s machine\u00d7cohort pairs  |  Balanced: %s (%d cohorts, %d state clusters)",
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

  path <- file.path(out_dir_balanced, sprintf("%s_%s_balanced_comparison.png", slug, dv_slug))
  ggsave(path, p, width = 9, height = 4.5, dpi = 300)
  cat(sprintf("    \u2192 %s\n", path))
  invisible(p)
}

write_comparison_table <- function(mat, dv_label, filepath) {
  cols     <- colnames(mat)
  header   <- paste0("| Estimate | ", paste(cols, collapse = " | "), " |")
  sep_line <- paste0("|", paste(rep(":---|", length(cols) + 1L), collapse = ""))
  content <- c(
    sprintf("# Balanced vs Unbalanced Panel \u2014 %s\n", dv_label),
    "Pooled three-period TWFE: `dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week`. SE clustered by state.  ",
    "\u03b2_ST: \u03c4 \u2208 [0,3]. \u03b2_LT: \u03c4 \u2208 [4,8]. \u03b2_pre: \u03c4 \u2208 [\u221216,\u22125].  ",
    sprintf("**Balanced** = machine\u00d7cohort pairs present in all %d event-window weeks. Format: \u03b2 (SE).\n",
            length(t_range)),
    header, sep_line
  )
  for (row_nm in rownames(mat)) {
    vals <- mat[row_nm, ]
    vals[is.na(vals)] <- "\u2014"
    content <- c(content,
      paste0("| **", row_nm, "** | ", paste(vals, collapse = " | "), " |"))
  }
  writeLines(content, filepath)
  cat(sprintf("Wrote: %s\n", filepath))
}

# Regressions for balanced panel comparison are run in run_regressions.R
# (Section D, RUN_DIAGNOSTICS = TRUE) and stored in regression_results.rds.
cat("Loading regression results from RDS...\n")
reg_results <- readRDS(file.path(out_int_dir, "regression_results.rds"))

if (length(reg_results$balanced) == 0L) {
  stop("reg_results$balanced is empty. Re-run run_regressions.R with RUN_DIAGNOSTICS = TRUE.")
}

for (s_idx in seq_along(BAL_SITES)) {
  site <- BAL_SITES[[s_idx]]
  cat(sprintf("--- %s ---\n", site$label))

  if (!site$slug %in% names(reg_results$balanced)) {
    cat("  (not in regression_results; skipping)\n\n"); next
  }

  for (dv in dvs) {
    if (!dv %in% names(reg_results$balanced[[site$slug]])) next

    br         <- reg_results$balanced[[site$slug]][[dv]]
    full_coefs <- br$full_coefs
    bal_coefs  <- br$bal_coefs
    res_u      <- br$res_full
    res_b      <- br$res_bal
    n_unbal_mc <- br$n_unbal_mc
    n_bal_mc   <- br$n_bal_mc

    cat(sprintf("  DV: %s  (unbal %s | bal %s m\u00d7c)\n",
        dv, format(n_unbal_mc, big.mark = ","), format(n_bal_mc, big.mark = ",")))

    save_comparison_plot(full_coefs, bal_coefs,
      site_label = site$label, dv_label = dv_labels[[dv]],
      slug = site$slug, dv_slug = dv,
      n_unbal = n_unbal_mc, n_bal = n_bal_mc)

    col_u <- paste0(site$label, " (Unbal)")
    col_b <- paste0(site$label, " (Bal)")
    bal_results[[dv]]["\u03b2_pre",             col_u] <- fmt_coef(res_u$beta_pre,       res_u$se_pre)
    bal_results[[dv]]["\u03b2_ST",              col_u] <- fmt_coef(res_u$beta_shortterm, res_u$se_shortterm)
    bal_results[[dv]]["\u03b2_LT",              col_u] <- fmt_coef(res_u$beta_longterm,  res_u$se_longterm)
    bal_results[[dv]]["N (obs) / N (m\u00d7c)", col_u] <- sprintf("%s / %s",
        format(res_u$n_obs, big.mark = ","), format(res_u$n_mc, big.mark = ","))
    bal_results[[dv]]["\u03b2_pre",             col_b] <- fmt_coef(res_b$beta_pre,       res_b$se_pre)
    bal_results[[dv]]["\u03b2_ST",              col_b] <- fmt_coef(res_b$beta_shortterm, res_b$se_shortterm)
    bal_results[[dv]]["\u03b2_LT",              col_b] <- fmt_coef(res_b$beta_longterm,  res_b$se_longterm)
    bal_results[[dv]]["N (obs) / N (m\u00d7c)", col_b] <- sprintf("%s / %s",
        format(res_b$n_obs, big.mark = ","), format(res_b$n_mc, big.mark = ","))
  }
  cat("\n")
}
rm(reg_results)

write_comparison_table(bal_results[["over60"]],
  "Pr(>60s on site) \u2014 over60",
  file.path(out_tables_dir, "balanced_comparison_over60.md"))
write_comparison_table(bal_results[["win_min"]],
  "Winsorized min/machine/week \u2014 win_min",
  file.path(out_tables_dir, "balanced_comparison_win_min.md"))

# ============================================================================
# SECTION B — PORTFOLIO DIAGNOSTICS
# ============================================================================

cat("\n", strrep("=", 60), "\n", sep = "")
cat("Section B \u2014 Portfolio diagnostics\n")
cat(strrep("=", 60), "\n\n", sep = "")

out_dir_portfolio <- file.path(out_base, "diagnostics", "portfolio_diagnostics")
dir.create(out_dir_portfolio, recursive = TRUE, showWarnings = FALSE)

THEME_BASE <- theme_bw() + theme(
  panel.grid.minor = element_blank(),
  panel.border     = element_blank(),
  axis.line        = element_line(color = "black", linewidth = 0.4),
  plot.title       = element_text(size = 12),
  plot.subtitle    = element_text(size = 8, color = "gray40"),
  axis.title       = element_text(size = 10),
  axis.text        = element_text(size = 9)
)

# machine→children lookup from stacked_base demo columns
machine_children <- stacked_base |>
  distinct(machine_id, children_present) |>
  mutate(children_label = case_when(
    children_present == "Children:Yes" ~ "Children present",
    children_present == "Children:No"  ~ "No children",
    TRUE                               ~ NA_character_
  )) |>
  select(machine_id, children_label)

# Pre-period treated rows
pre_rows <- stacked_base |>
  filter(rel_week < 0L, treated == 1L) |>
  select(machine_id, week_of_sample, machine_cohort)

cat(sprintf("  Pre-period treated rows: %s machine\u00d7week | %s machines\n",
    format(nrow(pre_rows), big.mark = ","),
    format(n_distinct(pre_rows$machine_id), big.mark = ",")))

cat("Loading site durations (PH, XV, XNXX)...\n")
t0 <- proc.time()
ph_dur   <- load_site_duration("PORNHUB.COM")
xv_dur   <- load_site_duration("XVIDEOS.COM")
xnxx_dur <- load_site_duration("XNXX.COM")
cat(sprintf("  Loaded  (%.1fs)\n", (proc.time() - t0)[["elapsed"]]))

cat("Computing substitute share per machine\u00d7cohort...\n")
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

cat(sprintf("  %s any-active machine\u00d7cohort pairs  (%.1fs)\n",
    format(nrow(sub_share_tbl), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))
rm(pre_rows, ph_dur, xv_dur, xnxx_dur)

share_0    <- sub_share_tbl |> filter(sub_share == 0)
share_low  <- sub_share_tbl |> filter(sub_share > 0, sub_share <= 0.5)
share_high <- sub_share_tbl |> filter(sub_share > 0.5, sub_share < 1)
share_1    <- sub_share_tbl |> filter(sub_share == 1)

cat(sprintf("  Bins: share=0 %s | (0,0.5] %s | (0.5,1) %s | share=1 %s\n",
    format(nrow(share_0), big.mark = ","), format(nrow(share_low), big.mark = ","),
    format(nrow(share_high), big.mark = ","), format(nrow(share_1), big.mark = ",")))

# Plot A — scatter PH vs substitute (pooled)
p_scatter <- ggplot(sub_share_tbl, aes(x = log(ph_tot + 1), y = log(sub_tot + 1))) +
  geom_point(alpha = 0.15, size = 0.6, color = MAROON) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed",
              color = "gray50", linewidth = 0.5) +
  labs(x = "log(PH minutes + 1)", y = "log(XV + XNXX minutes + 1)",
       title = "Pre-period PH vs substitute site usage (treated machine\u00d7cohort pairs)",
       subtitle = sprintf("n = %s any-active pairs  |  dashed line = equal usage",
                          format(nrow(sub_share_tbl), big.mark = ","))) +
  THEME_BASE
path_a <- file.path(out_dir_portfolio, "scatter_ph_vs_sub.png")
ggsave(path_a, p_scatter, width = 6, height = 6, dpi = 300)
cat(sprintf("  \u2192 %s\n", path_a))

# Plot A2 — scatter faceted by children
sub_known <- sub_share_tbl |> filter(!is.na(children_label))
n_by_ch   <- sub_known |> count(children_label)
p_scatter_ch <- ggplot(sub_known, aes(x = log(ph_tot + 1), y = log(sub_tot + 1))) +
  geom_point(alpha = 0.15, size = 0.5, color = MAROON) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed",
              color = "gray50", linewidth = 0.5) +
  facet_wrap(~children_label) +
  labs(x = "log(PH minutes + 1)", y = "log(XV + XNXX minutes + 1)",
       title = "Pre-period PH vs substitute site usage by children-in-home status",
       subtitle = sprintf("Children present: n=%s  |  No children: n=%s  |  dashed = equal usage",
         format(n_by_ch$n[n_by_ch$children_label == "Children present"], big.mark = ","),
         format(n_by_ch$n[n_by_ch$children_label == "No children"],      big.mark = ","))) +
  THEME_BASE
path_a2 <- file.path(out_dir_portfolio, "scatter_ph_vs_sub_children.png")
ggsave(path_a2, p_scatter_ch, width = 10, height = 5, dpi = 300)
cat(sprintf("  \u2192 %s\n", path_a2))

# Plot B — CDF substitute share (pooled)
cdf_data <- sub_share_tbl |> arrange(sub_share) |>
  mutate(ecdf_val = seq_len(n()) / n())
p_cdf <- ggplot(cdf_data, aes(x = sub_share, y = ecdf_val)) +
  geom_line(color = MAROON, linewidth = 0.9) +
  geom_vline(xintercept = 0.5, linetype = "dashed", color = NAVY, linewidth = 0.5) +
  annotate("text", x = 0.52, y = 0.15, label = "50%", hjust = 0,
           color = NAVY, size = 3.2) +
  scale_x_continuous(breaks = seq(0, 1, 0.25), limits = c(0, 1)) +
  scale_y_continuous(breaks = seq(0, 1, 0.25), labels = scales::percent) +
  labs(x = "Substitute share  [XV + XNXX] / [PH + XV + XNXX]",
       y = "Cumulative fraction of machine\u00d7cohort pairs",
       title = "CDF of pre-period substitute share (treated, any-active)",
       subtitle = sprintf("share=0: %s  |  (0,0.5]: %s  |  (0.5,1): %s  |  share=1: %s",
         format(nrow(share_0), big.mark = ","), format(nrow(share_low), big.mark = ","),
         format(nrow(share_high), big.mark = ","), format(nrow(share_1), big.mark = ","))) +
  THEME_BASE
path_b <- file.path(out_dir_portfolio, "cdf_sub_share.png")
ggsave(path_b, p_cdf, width = 7, height = 4.5, dpi = 300)
cat(sprintf("  \u2192 %s\n", path_b))

# Plot B2 — CDF substitute share by children
cdf_children <- sub_known |>
  group_by(children_label) |>
  arrange(sub_share, .by_group = TRUE) |>
  mutate(ecdf_val = seq_len(n()) / n()) |>
  ungroup()
p_cdf_ch <- ggplot(cdf_children,
    aes(x = sub_share, y = ecdf_val, color = children_label, linetype = children_label)) +
  geom_line(linewidth = 0.9) +
  geom_vline(xintercept = 0.5, linetype = "dashed", color = "gray50", linewidth = 0.4) +
  scale_color_manual(values = c("Children present" = MAROON, "No children" = NAVY), name = NULL) +
  scale_linetype_manual(values = c("Children present" = "solid", "No children" = "solid"), name = NULL) +
  scale_x_continuous(breaks = seq(0, 1, 0.25), limits = c(0, 1)) +
  scale_y_continuous(breaks = seq(0, 1, 0.25), labels = scales::percent) +
  labs(x = "Substitute share  [XV + XNXX] / [PH + XV + XNXX]",
       y = "Cumulative fraction of machine\u00d7cohort pairs",
       title = "CDF of pre-period substitute share by children-in-home status",
       subtitle = sprintf("Treated any-active pairs  |  Children present: n=%s  |  No children: n=%s",
         format(n_by_ch$n[n_by_ch$children_label == "Children present"], big.mark = ","),
         format(n_by_ch$n[n_by_ch$children_label == "No children"],      big.mark = ","))) +
  THEME_BASE + theme(legend.position = "bottom")
path_b2 <- file.path(out_dir_portfolio, "cdf_sub_share_children.png")
ggsave(path_b2, p_cdf_ch, width = 7, height = 4.5, dpi = 300)
cat(sprintf("  \u2192 %s\n", path_b2))

# ============================================================================
# SECTION C — SE DIAGNOSTICS
# ============================================================================

cat("\n", strrep("=", 60), "\n", sep = "")
cat("Section C \u2014 SE diagnostics\n")
cat(strrep("=", 60), "\n\n", sep = "")

out_dir_se <- file.path(out_base, "diagnostics", "se_diagnostics")
dir.create(out_dir_se, recursive = TRUE, showWarnings = FALSE)

n_rows_stack <- nrow(stacked_base)
n_mc_pairs   <- n_distinct(stacked_base$machine_cohort)

# Load Pornhub duration
cat("Loading Pornhub duration...\n")
t0 <- proc.time()
dur_ph <- open_dataset(file.path(data_dir, "machine_aggregated_PORNHUB.COM.parquet")) |>
  filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
  select(machine_id, week_of_sample, total_duration) |>
  collect()
cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
    format(nrow(dur_ph), big.mark = ","), (proc.time() - t0)[["elapsed"]]))

p95_ph <- compute_p95_2022("PORNHUB.COM")
cat(sprintf("  p95 Pornhub = %.1fs (%.1f min)\n", p95_ph, p95_ph / 60))

df <- stacked_base |>
  left_join(dur_ph, by = c("machine_id", "week_of_sample")) |>
  mutate(
    over60  = as.integer(!is.na(total_duration) & total_duration > 60),
    win_min = pmin(replace(total_duration, is.na(total_duration), 0), p95_ph) / 60
  )
rm(dur_ph)
cat(sprintf("Full panel: %s rows\n", format(nrow(df), big.mark = ",")))

# --- Diagnostic 1: State-level baseline statistics ---
cat("\nComputing state-level baseline statistics...\n")
treated_pre <- df |>
  filter(treated == 1L, rel_week < 0L) |>
  group_by(state, cohort) |>
  summarise(n_obs_pre = n(), n_machines_pre = n_distinct(machine_id),
            mean_over60_pre = mean(over60, na.rm = TRUE), .groups = "drop")
treated_post <- df |>
  filter(treated == 1L, rel_week >= 0L) |>
  group_by(state, cohort) |>
  summarise(n_obs_post = n(), mean_over60_post = mean(over60, na.rm = TRUE),
            .groups = "drop")
control_means <- df |>
  filter(treated == 0L) |>
  group_by(cohort) |>
  summarise(ctrl_pre  = mean(over60[rel_week < 0L],  na.rm = TRUE),
            ctrl_post = mean(over60[rel_week >= 0L], na.rm = TRUE),
            .groups = "drop")
state_stats <- treated_pre |>
  inner_join(treated_post, by = c("state", "cohort")) |>
  inner_join(control_means, by = "cohort") |>
  mutate(did_naive = (mean_over60_post - mean_over60_pre) - (ctrl_post - ctrl_pre),
         law_date_str = format(law_date[state], "%b %Y")) |>
  arrange(law_date[state])

cat(sprintf("  %-6s %-10s %10s %10s %8s %8s %10s\n",
    "State", "Law Date", "N_mach_pre", "mean_pre", "mean_post",
    "ctrl_pre", "DiD_naive"))
for (i in seq_len(nrow(state_stats))) {
  r <- state_stats[i, ]
  cat(sprintf("  %-6s %-10s %10s %10.4f %8.4f %8.4f %10.4f\n",
      r$state, r$law_date_str, format(r$n_machines_pre, big.mark = ","),
      r$mean_over60_pre, r$mean_over60_post, r$ctrl_pre, r$did_naive))
}

# --- Diagnostic 2: Robust vs clustered SE ---
cat("\nRunning pooled regression (robust vs clustered)...\n")
df_ph3 <- df |> mutate(
  pre       = as.integer(rel_week %in% PRE_WINDOW),
  shortterm = as.integer(rel_week %in% SHORT_WINDOW),
  longterm  = as.integer(rel_week %in% LONG_WINDOW)
)
fit_clustered <- feols(
  over60 ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week,
  data = df_ph3, cluster = ~state, warn = FALSE, notes = FALSE)
fit_robust <- feols(
  over60 ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week,
  data = df_ph3, vcov = "hetero", warn = FALSE, notes = FALSE)

se_cl  <- sqrt(diag(vcov(fit_clustered)))["treated:longterm"]
se_rob <- sqrt(diag(vcov(fit_robust)))   ["treated:longterm"]
moulton_factor <- se_cl / se_rob
n_bar <- n_rows_stack / n_clusters
icc_implied <- (moulton_factor^2 - 1) / (n_bar - 1)
n_eff <- n_rows_stack / (1 + icc_implied * (n_bar - 1))

cat(sprintf("\n  SE (clustered by state):  %.6f\n", se_cl))
cat(sprintf("  SE (heteroskedastic):     %.6f\n", se_rob))
cat(sprintf("  Moulton factor:           %.2f\n", moulton_factor))
cat(sprintf("  Implied ICC:              %.6f\n", icc_implied))
cat(sprintf("  Average cluster size:     %.0f observations\n", n_bar))
cat(sprintf("  Effective N (approx):     %.0f\n", n_eff))

se_df <- data.frame(
  estimator       = c("Clustered (state)", "Heteroskedastic-robust"),
  beta_longterm   = rep(coef(fit_clustered)["treated:longterm"], 2),
  se              = c(se_cl, se_rob),
  moulton_factor  = c(moulton_factor, 1.0),
  n_clusters      = c(n_clusters, NA_integer_),
  n_obs           = rep(n_rows_stack, 2),
  n_eff           = c(round(n_eff), round(n_rows_stack)),
  icc_implied     = c(icc_implied, NA_real_)
)
write.csv(se_df, file.path(out_dir_se, "se_comparison.csv"), row.names = FALSE)

# --- Diagnostic 3: State-level ATTs ---
cat("\nEstimating state-level ATTs (one regression per treated state)...\n")
state_atts <- lapply(qualifying, function(s) {
  df_s <- df_ph3 |> filter(cohort == s)
  tryCatch({
    fit_s <- feols(
      over60 ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week,
      data = df_s, cluster = ~state, warn = FALSE, notes = FALSE)
    cf <- coef(fit_s); se_s <- sqrt(diag(vcov(fit_s)))
    data.frame(
      state    = s,
      beta_lt  = unname(cf["treated:longterm"]),
      se_lt    = unname(se_s["treated:longterm"]),
      beta_pre = unname(cf["treated:pre"]),
      se_pre   = unname(se_s["treated:pre"]),
      n_obs    = fit_s$nobs,
      n_machines_pre = state_stats$n_machines_pre[state_stats$state == s],
      mean_pre = state_stats$mean_over60_pre[state_stats$state == s],
      law_date = law_date[s], stringsAsFactors = FALSE)
  }, error = function(e) { cat(sprintf("  ERROR %s: %s\n", s, conditionMessage(e))); NULL })
}) |> bind_rows() |> arrange(law_date)

state_atts$ci_lo <- state_atts$beta_lt - 1.96 * state_atts$se_lt
state_atts$ci_hi <- state_atts$beta_lt + 1.96 * state_atts$se_lt
state_atts$label <- sprintf("%s (%s, N=%s)", state_atts$state,
    format(state_atts$law_date, "%b'%y"),
    format(state_atts$n_machines_pre, big.mark = ","))

write.csv(state_atts, file.path(out_dir_se, "pornhub_state_level.csv"), row.names = FALSE)

sd_att <- sd(state_atts$beta_lt, na.rm = TRUE)
cat(sprintf("  Cross-state SD of ATT: %.4f\n", sd_att))

# Forest plot
pooled_row <- data.frame(
  state = "POOLED",
  beta_lt  = coef(fit_clustered)["treated:longterm"],
  se_lt    = se_cl,
  ci_lo    = coef(fit_clustered)["treated:longterm"] - 1.96 * se_cl,
  ci_hi    = coef(fit_clustered)["treated:longterm"] + 1.96 * se_cl,
  label    = sprintf("Pooled (N=%s)", format(sum(state_atts$n_machines_pre), big.mark = ",")),
  n_machines_pre = sum(state_atts$n_machines_pre), mean_pre = NA_real_,
  stringsAsFactors = FALSE)
forest_df <- bind_rows(state_atts, pooled_row)
forest_df$label     <- factor(forest_df$label, levels = rev(forest_df$label))
forest_df$is_pooled <- forest_df$state == "POOLED"

p_forest <- ggplot(forest_df, aes(x = beta_lt, y = label,
                                   color = is_pooled, size = is_pooled)) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "gray60", linewidth = 0.5) +
  geom_errorbarh(aes(xmin = ci_lo, xmax = ci_hi), height = 0.3, linewidth = 0.6) +
  geom_point() +
  scale_color_manual(values = c("FALSE" = MAROON, "TRUE" = NAVY), guide = "none") +
  scale_size_manual(values  = c("FALSE" = 2,      "TRUE" = 3),    guide = "none") +
  scale_x_continuous(labels = function(x) sprintf("%.1f pp", x * 100),
                     breaks = seq(-0.06, 0.04, by = 0.02)) +
  labs(x = "ATT (\u03b2_LT, \u03c4 \u2208 [4,8])  [95% CI, SE clustered by state within cohort]",
       y = NULL,
       title = "Pornhub \u2014 state-level ATT on Pr(>60s), stacked TWFE",
       subtitle = sprintf("Each row: one treated-state cohort.  Blue = pooled \u03b2_LT (%.4f, SE=%.4f).",
                          coef(fit_clustered)["treated:longterm"], se_cl)) +
  theme_bw() +
  theme(panel.grid.minor = element_blank(), panel.border = element_blank(),
        axis.line = element_line(color = "black", linewidth = 0.4),
        plot.title = element_text(size = 12),
        plot.subtitle = element_text(size = 8, color = "gray40"),
        axis.text.y = element_text(size = 8), axis.text.x = element_text(size = 9),
        axis.title.x = element_text(size = 9))
path_forest <- file.path(out_dir_se, "forest_state_atts.png")
ggsave(path_forest, p_forest, width = 9, height = 6, dpi = 300)
cat(sprintf("  \u2192 %s\n", path_forest))

# --- XNXX state-level ATTs ---
cat("\nXNXX \u2014 state-level ATTs\n")
dur_xnxx <- open_dataset(file.path(data_dir, "machine_aggregated_XNXX.COM.parquet")) |>
  filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
  select(machine_id, week_of_sample, total_duration) |>
  collect()
df_xnxx <- stacked_base |>
  left_join(dur_xnxx, by = c("machine_id", "week_of_sample")) |>
  mutate(over60 = as.integer(!is.na(total_duration) & total_duration > 60))
rm(dur_xnxx)
p95_xnxx <- compute_p95_2022("XNXX.COM")
cat(sprintf("  p95 XNXX = %.1fs (%.1f min)\n", p95_xnxx, p95_xnxx / 60))
df_xnxx <- df_xnxx |>
  mutate(win_min = pmin(replace(total_duration, is.na(total_duration), 0), p95_xnxx) / 60)

for (dv_name in c("over60", "win_min")) {
  cat(sprintf("\n--- DV: %s ---\n", dv_name))
  fml_pool <- as.formula(sprintf(
    "%s ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week",
    dv_name))
  df_xnxx_3p <- df_xnxx |> mutate(
    pre       = as.integer(rel_week %in% PRE_WINDOW),
    shortterm = as.integer(rel_week %in% SHORT_WINDOW),
    longterm  = as.integer(rel_week %in% LONG_WINDOW))
  fit_pool <- feols(fml_pool, data = df_xnxx_3p, cluster = ~state, warn = FALSE, notes = FALSE)
  se_pool  <- sqrt(diag(vcov(fit_pool)))["treated:longterm"]
  cat(sprintf("  Pooled \u03b2_ST: %.4f  \u03b2_LT: %.4f (SE=%.4f)\n",
              coef(fit_pool)["treated:shortterm"],
              coef(fit_pool)["treated:longterm"], se_pool))

  xnxx_atts <- lapply(qualifying, function(s) {
    df_s <- df_xnxx_3p |> filter(cohort == s)
    tryCatch({
      fit_s <- feols(fml_pool, data = df_s, cluster = ~state, warn = FALSE, notes = FALSE)
      cf <- coef(fit_s); se_s <- sqrt(diag(vcov(fit_s)))
      data.frame(state = s, beta_lt = unname(cf["treated:longterm"]),
                 se_lt = unname(se_s["treated:longterm"]),
                 beta_pre = unname(cf["treated:pre"]),
                 se_pre   = unname(se_s["treated:pre"]),
                 law_date = law_date[s], stringsAsFactors = FALSE)
    }, error = function(e) { cat(sprintf("  ERROR %s: %s\n", s, conditionMessage(e))); NULL })
  }) |> bind_rows() |> arrange(law_date)
  xnxx_atts$ci_lo <- xnxx_atts$beta_lt - 1.96 * xnxx_atts$se_lt
  xnxx_atts$ci_hi <- xnxx_atts$beta_lt + 1.96 * xnxx_atts$se_lt
  xnxx_atts$label <- sprintf("%s (%s)", xnxx_atts$state,
                             format(xnxx_atts$law_date, "%b'%y"))
  csv_path <- file.path(out_dir_se, sprintf("xnxx_state_level_%s.csv", dv_name))
  write.csv(xnxx_atts, csv_path, row.names = FALSE)

  pooled_xnxx <- data.frame(state = "POOLED",
    beta_lt = coef(fit_pool)["treated:longterm"], se_lt = se_pool,
    ci_lo = coef(fit_pool)["treated:longterm"] - 1.96 * se_pool,
    ci_hi = coef(fit_pool)["treated:longterm"] + 1.96 * se_pool,
    label = "Pooled", stringsAsFactors = FALSE)
  forest_xnxx <- bind_rows(xnxx_atts, pooled_xnxx)
  forest_xnxx$label     <- factor(forest_xnxx$label, levels = rev(forest_xnxx$label))
  forest_xnxx$is_pooled <- forest_xnxx$state == "POOLED"
  dv_label_x <- if (dv_name == "win_min") "win. min/machine/week (p95)" else "Pr(>60s)"
  p_fx <- ggplot(forest_xnxx, aes(x = beta_lt, y = label, color = is_pooled, size = is_pooled)) +
    geom_vline(xintercept = 0, linetype = "dashed", color = "gray60", linewidth = 0.5) +
    geom_errorbarh(aes(xmin = ci_lo, xmax = ci_hi), height = 0.3, linewidth = 0.6) +
    geom_point() +
    scale_color_manual(values = c("FALSE" = MAROON, "TRUE" = NAVY), guide = "none") +
    scale_size_manual(values  = c("FALSE" = 2,      "TRUE" = 3),    guide = "none") +
    labs(x = "ATT (\u03b2_LT, \u03c4 \u2208 [4,8])  [95% CI, SE clustered by state within cohort]",
         y = NULL,
         title = sprintf("XNXX \u2014 state-level ATT on %s, stacked TWFE", dv_label_x),
         subtitle = sprintf("Blue = pooled \u03b2_LT (%.4f, SE=%.4f).",
                            coef(fit_pool)["treated:longterm"], se_pool)) +
    theme_bw() +
    theme(panel.grid.minor = element_blank(), panel.border = element_blank(),
          axis.line = element_line(color = "black", linewidth = 0.4),
          plot.title = element_text(size = 12),
          plot.subtitle = element_text(size = 8, color = "gray40"),
          axis.text.y = element_text(size = 8), axis.text.x = element_text(size = 9),
          axis.title.x = element_text(size = 9))
  png_path <- file.path(out_dir_se, sprintf("forest_state_atts_xnxx_%s.png", dv_name))
  ggsave(png_path, p_fx, width = 8, height = 6, dpi = 300)
  cat(sprintf("  \u2192 %s\n", png_path))
}

# --- SE memo ---
cat("\nWriting SE memo...\n")
beta    <- round(coef(fit_clustered)["treated:longterm"] * 100, 2)
ci_lo_m <- round((coef(fit_clustered)["treated:longterm"] - 1.96 * se_cl) * 100, 2)
ci_hi_m <- round((coef(fit_clustered)["treated:longterm"] + 1.96 * se_cl) * 100, 2)
se_m    <- round(se_cl * 100, 2)
se_r_m  <- round(se_rob * 100, 2)
mf      <- round(moulton_factor, 1)
n_eff_k <- round(n_eff / 1000)
n_total_m <- round(n_rows_stack / 1e6, 1)
avg_pre_rate <- round(mean(state_atts$mean_pre, na.rm = TRUE) * 100, 1)
sd_att_pp <- round(sd_att * 100, 2)

memo_lines <- c(
  "# What Drives the SE on the Pornhub Estimate?",
  "", sprintf("Generated by `code/analysis/diagnostics.R`"), "",  "---", "",
  "## The Number", "",
  sprintf("The pooled Pornhub `over60` estimate is **%.2f pp** (SE = %.2f pp),", beta, se_m),
  sprintf("giving a 95%% CI of [%.2f pp, %.2f pp].", ci_lo_m, ci_hi_m), "",
  "---", "", "## 1. Most Machines Never Visit Pornhub", "",
  sprintf("In the pre-period, the mean of `over60` on Pornhub is roughly **%.1f%%** of machines per week.", avg_pre_rate),
  "The effective numerator is the difference in Pornhub-visitor rates before vs. after the law.", "",
  "---", "", "## 2. The Moulton Problem", "",
  "| Estimator | SE on \u03b2_LT | Implied precision |",
  "|-----------|-------------|-------------------|",
  sprintf("| Heteroskedastic robust | **%.2f pp** | treats obs as independent |", se_r_m),
  sprintf("| Clustered by state | **%.2f pp** | accounts for within-cluster correlation |", se_m),
  sprintf("| **Moulton factor** | **%.1f\u00d7** | how much clustering inflates SE |", mf),
  "",
  sprintf("Average cluster size: %.0f. Effective N \u2248 **%d thousand observations**.", n_bar, n_eff_k),
  "", "---", "", "## 3. Cross-State Heterogeneity", "",
  "| State | Law date | Pre-rate | N machines (pre) | \u03b2_LT | SE | \u03b2_pre |",
  "|-------|----------|----------|-----------------|-------|----|-------|"
)
for (i in seq_len(nrow(state_atts))) {
  r <- state_atts[i, ]
  memo_lines <- c(memo_lines,
    sprintf("| %s | %s | %.1f%% | %s | %.4f | %.4f | %.4f |",
            r$state, format(r$law_date, "%b %Y"), r$mean_pre * 100,
            format(r$n_machines_pre, big.mark = ","), r$beta_lt, r$se_lt, r$beta_pre))
}
memo_lines <- c(memo_lines, "",
  sprintf("Cross-state SD of ATT: **%.2f pp**.", sd_att_pp), "",
  "---", "", "## 4. Summary", "",
  "**Bottom line**: The SE reflects 15 treated states, not 15 million machines.",
  "Each additional law enactment contributes ~as much to precision as millions of additional panel observations.", "")
writeLines(memo_lines, file.path(out_dir_se, "memo_se_drivers.md"))
cat(sprintf("Wrote: %s\n", file.path(out_dir_se, "memo_se_drivers.md")))

cat("\nAll done.\n")
