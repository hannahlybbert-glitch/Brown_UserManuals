# Author: Matt Brown, assisted by Claude
# Created: 2026-03-07
# Purpose: Waterfall and dot-plot decompositions of the All XXX pooled ATT.
#          Sites 2-7 sum to col 1 (All XXX); drop pre-period, drop All other.
#
# Requires: output/analysis/intermediate/regression_results.rds
#
# Outputs (per DV):
#   output/analysis/figures/decomp_waterfall_{over60,win_min}.png
#   output/analysis/figures/decomp_dotplot_{over60,win_min}.png
#
# Usage:
#   Rscript code/analysis/create_decomposition_plots.R

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# DATA
# ============================================================================

cat("Loading regression results...\n")
results <- readRDS(file.path(out_int_dir, "regression_results.rds"))

DECOMP_SITES   <- SITES_FULL[sapply(SITES_FULL, `[[`, "key") %in%
                   c("PORNHUB.COM", "XVIDEOS.COM", "XNXX.COM",
                     "XHAMSTER.COM", "CHATURBATE.COM", "other_XXX_sites")]
SITE_LABELS    <- sapply(DECOMP_SITES, `[[`, "label")
PERIOD_SLUGS   <- c("beta_shortterm", "beta_longterm")
PERIOD_LABELS  <- c("Short-term", "Long-term")

# Helper: extract beta/se for one site×period
get_est <- function(slug, dv, period_slug) {
  res <- results$pooled[[slug]][[dv]]
  list(beta = res[[period_slug]],
       se   = res[[sub("beta_", "se_", period_slug)]])
}

# Build long data frame: site × period → beta, se
build_long <- function(dv, include_total = TRUE) {
  rows <- lapply(DECOMP_SITES, function(site) {
    lapply(seq_along(PERIOD_SLUGS), function(i) {
      est <- get_est(site$slug, dv, PERIOD_SLUGS[i])
      data.frame(site = site$label, period = PERIOD_LABELS[i],
                 beta = est$beta, se = est$se, is_total = FALSE,
                 stringsAsFactors = FALSE)
    })
  }) |> unlist(recursive = FALSE) |> bind_rows()

  if (include_total) {
    total_rows <- lapply(seq_along(PERIOD_SLUGS), function(i) {
      est <- get_est("all_xxx", dv, PERIOD_SLUGS[i])
      data.frame(site = "All XXX", period = PERIOD_LABELS[i],
                 beta = est$beta, se = est$se, is_total = TRUE,
                 stringsAsFactors = FALSE)
    }) |> bind_rows()
    rows <- bind_rows(rows, total_rows)
  }
  rows
}

# ============================================================================
# HOUSE STYLE
# ============================================================================

PALETTE_SITES <- c("#8c1515", "#0B3954", "#9a8873", "#b4adea", "#aceb98", "#e8a838")
COL_ST    <- "#8c1515"
COL_LT    <- "#0B3954"
COL_POS   <- "#0B3954"
COL_NEG   <- "#8c1515"
COL_TOTAL <- "grey30"

theme_house <- function(base_size = 11) {
  theme_classic(base_size = base_size) +
    theme(
      panel.background  = element_rect(fill = "white", colour = NA),
      plot.background   = element_rect(fill = "white", colour = NA),
      axis.line         = element_line(colour = "black"),
      axis.ticks        = element_line(colour = "black"),
      panel.grid        = element_blank(),
      legend.background = element_blank(),
      legend.key        = element_blank(),
      strip.background  = element_blank(),
      strip.text        = element_text(face = "bold")
    )
}

fig_dir <- file.path(out_base, "full_sample")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

save_plot <- function(p, name, w = 7, h = 4.5) {
  path <- file.path(fig_dir, name)
  ggsave(path, p, width = w, height = h)
  cat(sprintf("Wrote: %s\n", path))
}

# ============================================================================
# B. WATERFALL (running cumulative bar per period, faceted ST | LT)
# ============================================================================

make_waterfall_df <- function(dv, period_slug, period_label) {
  site_betas <- sapply(DECOMP_SITES, function(s)
    results$pooled[[s$slug]][[dv]][[period_slug]])
  total <- results$pooled[["all_xxx"]][[dv]][[period_slug]]

  n      <- length(site_betas)
  ystart <- c(0, cumsum(site_betas[-n]))
  yend   <- cumsum(site_betas)

  all_labels <- c(SITE_LABELS, "All XXX")
  data.frame(
    x          = factor(all_labels, levels = all_labels),
    xnum       = seq_along(all_labels),
    ymin       = c(pmin(ystart, yend), min(0, total)),
    ymax       = c(pmax(ystart, yend), max(0, total)),
    yend_r     = c(yend, total),         # right edge of bar (for connectors)
    type       = c(ifelse(site_betas >= 0, "Increase", "Decrease"), "Total"),
    label_text = sprintf("%+.3f", c(site_betas, total)),
    beta_val   = c(site_betas, total),
    period     = period_label,
    stringsAsFactors = FALSE
  )
}

make_B <- function(dv) {
  dv_label <- DV_METADATA[[dv]]$short
  df <- bind_rows(
    make_waterfall_df(dv, "beta_shortterm", "Short-term"),
    make_waterfall_df(dv, "beta_longterm",  "Long-term")
  )
  df$period <- factor(df$period, levels = PERIOD_LABELS)
  df$type   <- factor(df$type, levels = c("Increase", "Decrease", "Total"))

  # connector segments (between adjacent bars within each period)
  conn <- df |>
    filter(type != "Total") |>
    group_by(period) |>
    mutate(x_right = xnum + 0.4, x_left = lead(xnum) - 0.4, y = yend_r) |>
    filter(!is.na(x_left))

  ggplot(df) +
    geom_rect(aes(xmin = xnum - 0.4, xmax = xnum + 0.4,
                  ymin = ymin, ymax = ymax, fill = type)) +
    geom_text(aes(x = xnum, y = yend_r, label = label_text,
                  vjust = ifelse(beta_val >= 0, -0.4, 1.4)),
              size = 2.6, colour = "grey20") +
    geom_segment(data = conn,
                 aes(x = x_right, xend = x_left, y = y, yend = y),
                 colour = "grey50", linewidth = 0.3, linetype = "dashed") +
    geom_hline(yintercept = 0, linewidth = 0.4) +
    facet_wrap(~period) +
    scale_x_continuous(
      breaks = seq_along(c(SITE_LABELS, "All XXX")),
      labels = c(SITE_LABELS, "All XXX")
    ) +
    scale_y_continuous(expand = expansion(mult = c(0.12, 0.08))) +
    scale_fill_manual(
      values = c("Increase" = COL_POS, "Decrease" = COL_NEG, "Total" = COL_TOTAL),
      name = NULL
    ) +
    labs(title = sprintf("B. Waterfall: %s", dv_label),
         x = NULL, y = DV_METADATA[[dv]]$y_label,
         caption = "Each bar starts where the previous ended. 'All XXX' bar runs from 0 to total ATT.") +
    theme_house() +
    theme(axis.text.x = element_text(angle = 30, hjust = 1),
          legend.position = "top",
          panel.spacing = unit(1.5, "cm"))
}

# ============================================================================
# C. DOT PLOT / FOREST PLOT (sites on y-axis, faceted by period, with SEs)
# ============================================================================

make_C <- function(dv) {
  dv_label <- DV_METADATA[[dv]]$short
  df <- build_long(dv, include_total = TRUE)

  site_order <- c(rev(SITE_LABELS), "All XXX")
  df$site   <- factor(df$site,   levels = site_order)
  df$period <- factor(df$period, levels = PERIOD_LABELS)
  df$is_total <- df$site == "All XXX"

  ggplot(df, aes(x = beta, y = site, colour = is_total, shape = is_total)) +
    geom_vline(xintercept = 0, linewidth = 0.4, colour = "grey50") +
    geom_errorbar(aes(xmin = beta - 1.96 * se, xmax = beta + 1.96 * se),
                  width = 0.25, linewidth = 0.5, orientation = "y") +
    geom_point(size = 2.5) +
    geom_hline(yintercept = length(SITE_LABELS) + 0.5,
               linetype = "dashed", colour = "grey60", linewidth = 0.4) +
    facet_wrap(~period) +
    scale_colour_manual(values = c("FALSE" = COL_ST, "TRUE" = COL_TOTAL), guide = "none") +
    scale_shape_manual(values  = c("FALSE" = 16,     "TRUE" = 18),         guide = "none") +
    labs(title = sprintf("C. Dot plot (95%% CI): %s", dv_label),
         x = sprintf("Change in %s", dv_label), y = NULL,
         caption = "Error bars = 95% CI (SE clustered by state). Diamond = All XXX total.") +
    theme_house() +
    theme(panel.spacing = unit(1.5, "cm"))
}

# ============================================================================
# GENERATE ALL
# ============================================================================

for (dv in dvs) {
  cat(sprintf("\n--- %s ---\n", dv))
  save_plot(make_B(dv), sprintf("decomp_waterfall_%s.png", dv), w = 8,   h = 4.5)
  save_plot(make_C(dv), sprintf("decomp_dotplot_%s.png",   dv), w = 7.5, h = 4)
}

cat("\nAll done.\n")
