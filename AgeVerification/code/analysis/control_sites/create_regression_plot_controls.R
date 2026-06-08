# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-28
# Purpose: Dot plot of long-term ATT (beta_LT) for control sites (excl. Amazon).
#   Sites ordered top to bottom by baseline mean (highest at top).
#   beta_LT with 95% CI on x-axis. Vertical reference line at zero. All maroon.
#
# Requires:
#   output/analysis/combined/control_sites/intermediate/regression_results_controls.rds
#
# Output:
#   output/analysis/combined/control_sites/controls_regression_plot.png

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(here)
})

Sys.setenv(ANALYSIS_MODE = "combined")
source(here::here("code", "analysis", "_source", "config.R"))

out_dir      <- file.path(here::here(), "output", "analysis", "combined", "control_sites")
results_path <- file.path(out_dir, "intermediate", "regression_results_controls.rds")

cat("Loading results...\n")
results      <- readRDS(results_path)
if (length(results$pooled) == 0L) stop("results$pooled is empty.")

# ============================================================================
# BUILD PLOT DATA
# ============================================================================

rows <- lapply(results$pooled, function(entry) {
  res <- entry$win_min
  data.frame(
    key           = entry$key,
    label         = entry$label,
    baseline_mean = entry$baseline_mean,
    beta_lt       = res$beta_longterm,
    se_lt         = res$se_longterm,
    stringsAsFactors = FALSE
  )
})

df <- dplyr::bind_rows(rows) |>
  dplyr::filter(key != "Amazon Sites") |>
  dplyr::arrange(dplyr::desc(baseline_mean)) |>
  dplyr::mutate(
    ci_lo   = beta_lt - 1.96 * se_lt,
    ci_hi   = beta_lt + 1.96 * se_lt,
    y_label = sprintf("%s\n(%.2f min)", label, baseline_mean),
    label_f = factor(y_label, levels = rev(y_label))
  )

# ============================================================================
# THEME
# ============================================================================

theme_controls <- function(base_size = 11) {
  theme_bw(base_size = base_size) +
    theme(
      panel.grid.minor   = element_blank(),
      panel.grid.major.y = element_blank(),
      panel.grid.major.x = element_line(color = "gray92"),
      panel.border       = element_blank(),
      axis.line.x        = element_line(color = "black", linewidth = 0.4),
      axis.ticks.y       = element_blank(),
      axis.text.y        = element_text(size = 10, lineheight = 0.85),
      axis.text.x        = element_text(size = 13),
      axis.title.x       = element_text(size = 15, margin = margin(t = 8)),
      legend.position    = "none"
    )
}

# ============================================================================
# PLOT
# ============================================================================

p <- ggplot(df, aes(x = beta_lt, y = label_f)) +
  geom_vline(xintercept = 0, linetype = "dashed",
             linewidth = 0.5, color = "gray40") +
  geom_errorbar(aes(xmin = ci_lo, xmax = ci_hi),
                width = 0, linewidth = 0.55,
                orientation = "y",
                color = MAROON) +
  geom_point(size = 2.5, color = MAROON) +
  scale_x_continuous(
    name = "Change in weekly minutes per machine"
  ) +
  labs(y = NULL) +
  theme_controls()

out_path <- file.path(out_dir, "controls_regression_plot.png")
ggsave(out_path, p, width = 7.5, height = 7, dpi = 300)
cat(sprintf("Wrote: %s\n", out_path))

cat("\nAll done.\n")
