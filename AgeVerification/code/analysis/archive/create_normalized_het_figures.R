# Author: Matt Brown, assisted by Claude
# Created: 2026-03-20; Updated: 2026-04-24
# Purpose: Horizontal bar charts of normalized subgroup ATTs, one per site.
#   For each site: subgroups on y-axis, normalized beta as a horizontal bar
#   colored by direction, faceted by period (ST | LT).
#   Normalization: beta / baseline_mean_treat (within-subgroup treatment group
#   mean in periods -4 to -1), matching the main event study framing.
#
# Requires: output/.../intermediate/normalized_het_results.rds
#           (produced by create_normalized_het_regressions.R)
#
# Outputs (output/.../normalized_het/):
#   het_bar_{site_slug}_win_min.png  (one per site)

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
    norm_st = beta_st / baseline_mean_treat,
    norm_lt = beta_lt / baseline_mean_treat
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

theme_house <- function() {
  theme_bw(base_size = 11) +
    theme(
      panel.grid.minor    = element_blank(),
      panel.grid.major.x  = element_line(color = "gray88"),
      panel.grid.major.y  = element_blank(),
      panel.border        = element_blank(),
      axis.line.x         = element_line(color = "black", linewidth = 0.4),
      axis.line.y         = element_line(color = "black", linewidth = 0.4),
      strip.background    = element_rect(fill = "gray95", color = NA),
      strip.text.y.right  = element_text(angle = 0, hjust = 0, size = 9),
      strip.text.x        = element_text(size = 9, face = "bold"),
      plot.title          = element_text(size = 12),
      plot.subtitle       = element_text(size = 8, color = "gray40"),
      legend.position     = "bottom"
    )
}

out_dir <- file.path(out_base, "normalized_het")
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

  pd <- pd_wide |>
    select(group_label, char, norm_st, norm_lt) |>
    pivot_longer(
      cols      = c(norm_st, norm_lt),
      names_to  = "period_key",
      values_to = "beta"
    ) |>
    mutate(
      period    = factor(PERIOD_LABELS[period_key], levels = PERIOD_LABELS),
      direction = factor(ifelse(beta >= 0, "Increase", "Decrease"),
                         levels = c("Increase", "Decrease"))
    )

  p <- ggplot(pd, aes(x = beta, y = group_label, fill = direction)) +
    geom_col(orientation = "y", width = 0.65) +
    geom_vline(xintercept = 0, linewidth = 0.5, color = "gray30") +
    facet_grid(char ~ period, scales = "free_y", space = "free_y") +
    scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    scale_fill_manual(
      values = c("Increase" = NAVY, "Decrease" = MAROON),
      name   = NULL
    ) +
    labs(
      title    = sprintf("Subgroup ATTs — %s (win. min)", site$label),
      subtitle = "Normalized by within-subgroup treatment group mean (τ = −4 to −1).",
      x        = "Change relative to subgroup baseline mean",
      y        = NULL
    ) +
    theme_house()

  path <- file.path(out_dir, sprintf("het_bar_%s_win_min.png", site$slug))
  ggsave(path, p, width = 10, height = 6, dpi = 300)
  cat(sprintf("  %s: %s\n", site$label, path))
}

cat("\nAll done.\n")
