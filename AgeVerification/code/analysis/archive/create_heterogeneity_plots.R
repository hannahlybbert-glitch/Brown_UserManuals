# Author: Matt Brown, assisted by Claude
# Created: 2026-03-07; Updated: 2026-04-24
# Purpose: Normalized subgroup ATT forest plots, one per site.
#   For each site: subgroups on y-axis, normalized beta + 95% CI on x-axis,
#   faceted by period (ST | LT).
#   Normalization: beta / baseline_mean_treat, where baseline_mean_treat is the
#   treatment group mean in periods -4 to -1 within that subgroup.
#   SE / baseline_mean_treat gives correct CI width (baseline is observed, not estimated).
#
# Requires: output/.../intermediate/normalized_het_results.rds
#           (produced by create_normalized_het_regressions.R)
#
# Outputs (output/.../heterogeneity_plots/):
#   het_forest_{site_slug}_win_min.png  (one per site)

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD AND NORMALIZE
# ============================================================================

cat("Loading normalized het results...\n")
inp      <- readRDS(file.path(out_int_dir, "normalized_het_results.rds"))
res_df   <- inp$res_df
sg_order <- inp$subgroups
sites    <- inp$sites

if (nrow(res_df) == 0L) {
  stop("normalized_het_results.rds is empty. Re-run create_normalized_het_regressions.R.")
}

plot_df <- res_df |>
  mutate(
    norm_st    = beta_st / baseline_mean_treat,
    norm_lt    = beta_lt / baseline_mean_treat,
    se_norm_st = se_st   / baseline_mean_treat,
    se_norm_lt = se_lt   / baseline_mean_treat,
    ci_lo_st   = norm_st - 1.96 * se_norm_st,
    ci_hi_st   = norm_st + 1.96 * se_norm_st,
    ci_lo_lt   = norm_lt - 1.96 * se_norm_lt,
    ci_hi_lt   = norm_lt + 1.96 * se_norm_lt
  )

# ============================================================================
# SUBGROUP GROUPING
# ============================================================================

CHAR_MAP <- c(
  "Full sample"     = "All",
  "Age: 18-24"      = "Age",
  "Age: 25-34"      = "Age",
  "Age: 35-44"      = "Age",
  "Age: 45-54"      = "Age",
  "Age: 55-64"      = "Age",
  "Age: 65+"        = "Age",
  "Device: desktop" = "Device",
  "Device: mobile"  = "Device",
  "Kids: no"        = "Children",
  "Kids: yes"       = "Children"
)

CHAR_LEVELS <- c("All", "Age", "Device", "Children")

Y_LABELS <- c(
  "Full sample"     = "Full sample",
  "Age: 18-24"      = "18–24",
  "Age: 25-34"      = "25–34",
  "Age: 35-44"      = "35–44",
  "Age: 45-54"      = "45–54",
  "Age: 55-64"      = "55–64",
  "Age: 65+"        = "65+",
  "Device: desktop" = "Desktop",
  "Device: mobile"  = "Mobile",
  "Kids: no"        = "No",
  "Kids: yes"       = "Yes"
)

PERIOD_LABELS <- c(
  norm_st = "Short-term (τ = 0–3 weeks)",
  norm_lt = "Long-term (τ = 4–8 weeks)"
)

# ============================================================================
# HOUSE STYLE
# ============================================================================

theme_house <- function(base_size = 11) {
  theme_bw(base_size = base_size) +
    theme(
      panel.grid.minor   = element_blank(),
      panel.grid.major.y = element_line(color = "gray92"),
      panel.border       = element_blank(),
      axis.line.x        = element_line(color = "black", linewidth = 0.4),
      axis.line.y        = element_blank(),
      axis.ticks.y       = element_blank(),
      strip.background   = element_rect(fill = "gray95", color = NA),
      strip.text         = element_text(size = 9, face = "bold"),
      plot.title         = element_text(size = 12),
      plot.subtitle      = element_text(size = 8, color = "gray40"),
      axis.title         = element_text(size = 10),
      axis.text          = element_text(size = 8)
    )
}

out_dir <- file.path(out_base, "heterogeneity_plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# ONE PLOT PER SITE
# ============================================================================

for (site in sites) {
  pd_wide <- plot_df |>
    filter(site_slug == site$slug) |>
    mutate(
      char        = factor(CHAR_MAP[group], levels = CHAR_LEVELS),
      group_label = factor(Y_LABELS[group], levels = rev(Y_LABELS[sg_order]))
    )

  if (nrow(pd_wide) == 0L) {
    cat(sprintf("  Skipping %s (no results)\n", site$label)); next
  }

  # Pivot to long by period
  pd <- pd_wide |>
    select(group_label, char, norm_st, norm_lt, ci_lo_st, ci_hi_st, ci_lo_lt, ci_hi_lt) |>
    pivot_longer(
      cols      = c(norm_st, norm_lt),
      names_to  = "period_key",
      values_to = "beta"
    ) |>
    mutate(
      ci_lo  = ifelse(period_key == "norm_st", ci_lo_st, ci_lo_lt),
      ci_hi  = ifelse(period_key == "norm_st", ci_hi_st, ci_hi_lt),
      period = factor(PERIOD_LABELS[period_key], levels = PERIOD_LABELS)
    )

  p <- ggplot(pd, aes(x = beta, y = group_label)) +
    geom_vline(xintercept = 0, linetype = "dashed", linewidth = 0.5, color = "gray40") +
    geom_errorbar(aes(xmin = ci_lo, xmax = ci_hi),
                  width = 0.3, linewidth = 0.6, color = MAROON,
                  orientation = "y") +
    geom_point(size = 2.5, color = MAROON) +
    facet_grid(char ~ period, scales = "free_y", space = "free_y") +
    scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    labs(
      title    = sprintf("Subgroup ATTs — %s (win. min)", site$label),
      subtitle = paste0("Normalized by within-subgroup treatment group mean (τ = −4 to −1). ",
                        "Error bars = 95% CI."),
      x = "Change relative to subgroup baseline mean",
      y = NULL
    ) +
    theme_house()

  path <- file.path(out_dir, sprintf("het_forest_%s_win_min.png", site$slug))
  ggsave(path, p, width = 10, height = 6, dpi = 300)
  cat(sprintf("  %s: %s\n", site$label, path))
}

cat("\nAll done.\n")
