# Author: Matt Brown, assisted by Claude
# Created: 2026-03-07
# Purpose: Diverging stacked bar chart decomposing "All XXX" pooled ATT
#          into site-level contributions (cols 2-7 sum to col 1).
#
# Requires: output/analysis/intermediate/regression_results.rds
#
# Outputs:
#   output/analysis/figures/decomposition_over60.pdf
#   output/analysis/figures/decomposition_win_min.pdf
#
# Usage:
#   Rscript code/analysis/create_decomposition_plot.R

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD RESULTS
# ============================================================================

cat("Loading regression results...\n")
results <- readRDS(file.path(out_int_dir, "regression_results.rds"))

# ============================================================================
# HOUSE STYLE
# ============================================================================

PALETTE <- c("#8c1515", "#0B3954", "#9a8873", "#b4adea", "#aceb98", "#e8a838")

theme_house <- function() {
  theme_classic(base_size = 11) +
    theme(
      panel.background  = element_rect(fill = "white", colour = NA),
      plot.background   = element_rect(fill = "white", colour = NA),
      axis.line         = element_line(colour = "black"),
      axis.ticks        = element_line(colour = "black"),
      axis.ticks.length = unit(4, "pt"),
      panel.grid        = element_blank(),
      legend.background = element_blank(),
      legend.key        = element_blank()
    )
}

# ============================================================================
# PLOTTING FUNCTION
# ============================================================================

# Sites that decompose the aggregate (cols 2-7 in the table)
DECOMP_SITES <- SITES_FULL[2:7]   # excludes all_xxx and all_other

PERIOD_LEVELS <- c("beta_pre", "beta_shortterm", "beta_longterm")
PERIOD_LABELS <- c("Pre", "Short-term", "Long-term")

make_decomp_plot <- function(dv) {
  dv_label <- DV_METADATA[[dv]]$short

  # --- site contributions ---
  long <- lapply(DECOMP_SITES, function(site) {
    res <- results$pooled[[site$slug]][[dv]]
    if (is.null(res)) return(NULL)
    data.frame(
      site   = site$label,
      period = PERIOD_LEVELS,
      beta   = c(res$beta_pre, res$beta_shortterm, res$beta_longterm),
      stringsAsFactors = FALSE
    )
  }) |> bind_rows()

  long$period <- factor(long$period, levels = PERIOD_LEVELS, labels = PERIOD_LABELS)
  long$site   <- factor(long$site,   levels = sapply(DECOMP_SITES, `[[`, "label"))

  # --- All XXX aggregate ---
  agg_res <- results$pooled[["all_xxx"]][[dv]]
  totals <- data.frame(
    period = factor(PERIOD_LABELS, levels = PERIOD_LABELS),
    total  = c(agg_res$beta_pre, agg_res$beta_shortterm, agg_res$beta_longterm)
  )

  ggplot(long, aes(x = period, y = beta, fill = site)) +
    geom_col(position = "stack", width = 0.6, colour = "white", linewidth = 0.3) +
    geom_point(
      data = totals, aes(x = period, y = total),
      inherit.aes = FALSE,
      shape = 18, size = 4, colour = "black"
    ) +
    geom_hline(yintercept = 0, linewidth = 0.4, colour = "black") +
    scale_fill_manual(values = PALETTE, name = NULL) +
    labs(
      title   = sprintf("Decomposition of All XXX effect: %s", dv_label),
      x       = NULL,
      y       = sprintf("Change in %s", dv_label),
      caption = "Bars = site contributions; diamond = All XXX pooled ATT. Stacked TWFE. SE clustered by state."
    ) +
    theme_house() +
    theme(legend.position = "bottom") +
    guides(fill = guide_legend(nrow = 2))
}

# ============================================================================
# WRITE OUTPUTS
# ============================================================================

fig_dir <- file.path(project_root, "output", "analysis", "figures")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

for (dv in dvs) {
  p        <- make_decomp_plot(dv)
  out_path <- file.path(fig_dir, sprintf("decomposition_%s.pdf", dv))
  ggsave(out_path, p, width = 6, height = 4.5)
  cat(sprintf("Wrote: %s\n", out_path))
}

cat("\nAll done.\n")
