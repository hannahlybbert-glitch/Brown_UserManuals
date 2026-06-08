# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-22 (updated: 2026-05-28)
# Purpose: Waterfall decomposition of top-25 adult usage into 5 named groups.
#
# Five bars: Pornhub, Other Compliant, XVideos, XNXX, Other Noncompliant.
# LHS stacked bar shows pre-period baseline-minute share of each group.
# Group-specific colors used throughout (maroon family = compliant; navy = noncompliant).
#
# Requires:
#   output/analysis/combined/top_25/intermediate/regression_results_top25.rds
#
# Output:
#   output/analysis/combined/top_25/waterfalls/waterfall_main.png
#
# Usage:
#   ANALYSIS_MODE=combined Rscript code/analysis/create_decomp_plots2.R

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(here)
})

Sys.setenv(ANALYSIS_MODE = "combined")
source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# DATA
# ============================================================================

cat("Loading regression results...\n")
t25_path    <- here::here("output", "analysis", "combined", "top_25",
                          "intermediate", "regression_results_top25.rds")
results_t25 <- readRDS(t25_path)

# ============================================================================
# COLOR PALETTE  (maroon family = compliant; navy family = noncompliant)
# ============================================================================

GROUP_COLORS <- c(
  "Pornhub"            = "#8c1515",  # dark maroon
  "Other Compliant"    = "#c47070",  # light maroon
  "XVideos"            = "#0B3954",  # dark navy
  "XNXX"               = "#1e6e9e",  # medium navy
  "Other Noncompliant" = "#5b9dc8"   # light navy
)
GROUP_LEVELS <- names(GROUP_COLORS)

# ============================================================================
# THEME
# ============================================================================

theme_house <- function(base_size = 13) {
  theme_classic(base_size = base_size) +
    theme(
      panel.background  = element_rect(fill = "white", colour = NA),
      plot.background   = element_rect(fill = "white", colour = NA),
      axis.line         = element_line(colour = "black"),
      axis.ticks        = element_line(colour = "black"),
      panel.grid        = element_blank(),
      legend.background = element_blank(),
      legend.key        = element_blank()
    )
}

fig_dir <- here::here("output", "analysis", "combined", "top_25", "waterfalls")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# WATERFALL — shared builder
# ============================================================================

make_waterfall <- function(include_rhs = FALSE) {

  bars <- list(
    list(label = "Pornhub",            slug = "PORNHUB_COM"),
    list(label = "Other Compliant",    slug = "other_compliant"),
    list(label = "XVideos",            slug = "XVIDEOS_COM"),
    list(label = "XNXX",               slug = "XNXX_COM"),
    list(label = "Other Noncompliant", slug = "other_noncompliant_top25")
  )
  n_bars <- length(bars)

  betas     <- sapply(bars, function(b)
    results_t25$pooled[[b$slug]][["win_min"]]$beta_longterm)
  ses       <- sapply(bars, function(b)
    results_t25$pooled[[b$slug]][["win_min"]]$se_longterm)
  baselines <- sapply(bars, function(b)
    results_t25$pooled[[b$slug]]$baseline_mean)

  all_top25_baseline <- sum(baselines)
  cat(sprintf("  All-Top25 baseline (sum of subgroups): %.4f min\n", all_top25_baseline))

  # Waterfall bars at x = 2 .. n_bars+1; LHS baseline bar sits at x = 1
  xnum   <- seq_len(n_bars) + 1L
  ystart <- c(0, cumsum(betas[-n_bars]))
  yend_r <- cumsum(betas)

  wf <- data.frame(
    xnum       = xnum,
    ymin       = pmin(ystart, yend_r),
    ymax       = pmax(ystart, yend_r),
    yend_r     = yend_r,
    ci_lo      = yend_r - 1.96 * ses,
    ci_hi      = yend_r + 1.96 * ses,
    label_text = sprintf("%+.2f", betas),
    beta_val   = betas,
    group      = factor(sapply(bars, `[[`, "label"), levels = GROUP_LEVELS),
    stringsAsFactors = FALSE
  )

  # Connectors between consecutive waterfall bars
  conn <- wf |>
    mutate(x_right = xnum + 0.4, x_left = lead(xnum) - 0.4, y = yend_r) |>
    filter(!is.na(x_left))

  # LHS stacked bar: segments stack from 0 down to -all_top25_baseline
  cumbl <- c(0, cumsum(baselines))
  lhs <- data.frame(
    ymax  = -cumbl[-length(cumbl)],
    ymin  = -cumbl[-1],
    group = factor(sapply(bars, `[[`, "label"), levels = GROUP_LEVELS),
    stringsAsFactors = FALSE
  )
  lhs$ymid      <- (lhs$ymax + lhs$ymin) / 2
  lhs$min_label <- sprintf("%.2f", baselines)
  lhs$diag_label <- dplyr::case_when(
    as.character(lhs$group) == "Other Compliant"    ~ "Other\nCompliant",
    as.character(lhs$group) == "Other Noncompliant" ~ "Other\nNoncompliant",
    TRUE                                             ~ as.character(lhs$group)
  )

  # ============================================================================
  # RHS post-treatment bar (V2 only)
  # Stacked from -all_top25_baseline upward: ON, XNXX, XV, OC, PH.
  # Each segment height = baseline_mean + beta_LT for that group.
  # ============================================================================

  rhs       <- NULL
  x_rhs_min <- 7.65
  x_rhs_max <- 8.35

  if (include_rhs) {
    rhs_idx   <- c(5L, 4L, 3L, 2L, 1L)   # ON → PH (bottom to top)
    rhs_h     <- (baselines + betas)[rhs_idx]
    rhs_cumbl <- -all_top25_baseline + c(0, cumsum(rhs_h))
    rhs <- data.frame(
      ymin  = rhs_cumbl[-length(rhs_cumbl)],
      ymax  = rhs_cumbl[-1],
      group = factor(sapply(bars, `[[`, "label")[rhs_idx], levels = GROUP_LEVELS),
      stringsAsFactors = FALSE
    )
    rhs$ymid      <- (rhs$ymin + rhs$ymax) / 2
    rhs$min_label <- sprintf("%.2f", (baselines + betas)[rhs_idx])
    rhs$label <- dplyr::case_when(
      as.character(rhs$group) == "Other Compliant"    ~ "Other\nCompliant",
      as.character(rhs$group) == "Other Noncompliant" ~ "Other\nNoncompliant",
      TRUE                                             ~ as.character(rhs$group)
    )
  }

  # ============================================================================
  # BRACKET ANNOTATIONS
  # ============================================================================

  bk_col <- "gray35"
  bk_lw  <- 0.4
  bk_sz  <- 3.9
  tick_w <- 0.07

  # x positions: NC between LHS bar and PH; Circ between OC and XV;
  # Sub and Cess to the right of the last bar
  x_nc    <- 1.08 + tick_w
  x_circ  <- 3.5
  x_sub   <- 6.5
  x_cess  <- (x_rhs_min + x_rhs_max) / 2

  # y extents (all in data coords; LHS bar sits in negative y territory)
  y_nc_lo   <- -all_top25_baseline      # bottom of LHS bar
  y_nc_hi   <- -cumbl[3]                # top of XVideos segment on LHS = bottom of OC on LHS

  y_circ_lo <- -cumbl[3]                # bottom of OC on LHS bar
  y_circ_hi <- wf$ymin[2]              # bottom of Other Compliant waterfall bar

  y_sub_lo  <- wf$ymin[3]              # bottom of XVideos waterfall bar
  y_sub_hi  <- wf$ymax[5]              # top of Other Noncompliant waterfall bar

  y_cess_lo <- wf$ymax[5]              # top of Other Noncompliant waterfall bar
  y_cess_hi <- 0

  # Percentages (share of all_top25_baseline)
  nc_pct   <- 100 * sum(baselines[3:5]) / all_top25_baseline
  circ_pct <- 100 * ((baselines[1] + betas[1]) + (baselines[2] + betas[2])) / all_top25_baseline
  sub_pct  <- 100 * sum(betas[3:5]) / all_top25_baseline
  cess_pct <- 100 * (-sum(betas)) / all_top25_baseline

  make_bracket <- function(x_pos, y_lo, y_hi, lbl, text_side = "right") {
    txt_x <- if (text_side == "right") x_pos + 0.08 else x_pos - 0.08
    txt_h <- if (text_side == "right") 0 else 1
    list(
      annotate("segment", x = x_pos, xend = x_pos, y = y_lo, yend = y_hi,
               colour = bk_col, linewidth = bk_lw),
      annotate("segment", x = x_pos - tick_w, xend = x_pos + tick_w,
               y = y_lo, yend = y_lo, colour = bk_col, linewidth = bk_lw),
      annotate("segment", x = x_pos - tick_w, xend = x_pos + tick_w,
               y = y_hi, yend = y_hi, colour = bk_col, linewidth = bk_lw),
      annotate("text", x = txt_x, y = (y_lo + y_hi) / 2, label = lbl,
               angle = 0, hjust = txt_h, vjust = 0.5,
               size = bk_sz, colour = bk_col, lineheight = 1.1,
               fontface = "bold")
    )
  }

  all_brackets <- c(
    make_bracket(x_nc,   y_nc_lo,   y_nc_hi,
                 sprintf("Noncompliance\n(%.0f%%)", ceiling(nc_pct))),
    make_bracket(x_circ, y_circ_lo, y_circ_hi,
                 sprintf("Circumvention\n(%.0f%%)", circ_pct)),
    make_bracket(x_sub,  y_sub_lo,  y_sub_hi,
                 sprintf("Substitution\n(%.0f%%)", sub_pct)),
    make_bracket(x_cess, y_cess_lo, y_cess_hi,
                 sprintf("Cessation\n(%.0f%%)", cess_pct))
  )

  y_lower      <- -all_top25_baseline - 0.1
  y_ceil       <- max(0.1, max(wf$ci_hi, na.rm = TRUE) + 0.05)

  # Y-axis: minutes scale — label 0 at the bottom (y = -all_top25_baseline)
  # and the baseline value at the top (y = 0), with clean integers in between.
  k_vals       <- 0:floor(all_top25_baseline)
  y_all_breaks <- sort(unique(c(k_vals - all_top25_baseline, 0)))
  y_all_labels <- sapply(y_all_breaks, function(b) {
    mv <- b + all_top25_baseline
    if (abs(mv - round(mv)) < 1e-6) as.character(as.integer(round(mv)))
    else sprintf("%.2f", mv)
  })

  x_expand_r <- if (include_rhs) 1.3 else 0.2
  r_margin   <- if (include_rhs) 10L else 80L

  ggplot() +
    # LHS stacked baseline bar (narrowed to xmax=1.3 for a visible gap before PH)
    geom_rect(data = lhs,
              aes(xmin = 0.15, xmax = 0.85, ymin = ymin, ymax = ymax, fill = group),
              colour = "white", linewidth = 0.3) +
    geom_text(data = lhs,
              aes(x = 0.50, y = ymid, label = min_label),
              hjust = 0.5, vjust = 0.5, colour = "white",
              size = 4.5, inherit.aes = FALSE) +
    # Diagonal group labels — bottom-left to top-right, right end touching bar left edge.
    # hjust=1 places the right end of each label at x=0.58; text fans out to lower-left.
    geom_text(data = lhs,
              aes(x = 0.10, y = ymid, label = diag_label),
              angle = 0, hjust = 1, vjust = 0.5, colour = "black",
              size = 13 / .pt, lineheight = 0.85, inherit.aes = FALSE) +
    # Waterfall bars
    geom_rect(data = wf,
              aes(xmin = xnum - 0.4, xmax = xnum + 0.4,
                  ymin = ymin, ymax = ymax, fill = group)) +
    # 95% CI error bars
    geom_errorbar(data = wf,
                  aes(x = xnum, ymin = ci_lo, ymax = ci_hi),
                  width = 0.15, linewidth = 0.5, colour = "grey72") +
    # Estimate labels
    geom_text(data = wf,
              aes(x = xnum + 0.4, y = yend_r, label = label_text,
                  vjust = ifelse(beta_val >= 0, -0.4, 1.4)),
              hjust = 1, size = 4.5, colour = "grey20") +
    # Connector dashed lines between waterfall bars
    geom_segment(data = conn,
                 aes(x = x_right, xend = x_left, y = y, yend = y),
                 colour = "grey50", linewidth = 0.3, linetype = "dashed") +
    # Zero line
    geom_hline(yintercept = 0, linewidth = 0.4) +
    # RHS post-treatment bar (V2 only)
    (if (include_rhs)
       geom_rect(data = rhs,
                 aes(xmin = x_rhs_min, xmax = x_rhs_max,
                     ymin = ymin, ymax = ymax, fill = group),
                 colour = "white", linewidth = 0.3)
     else NULL) +
    (if (include_rhs)
       geom_text(data = rhs,
                 aes(x = (x_rhs_min + x_rhs_max) / 2, y = ymid, label = min_label),
                 hjust = 0.5, vjust = 0.5, colour = "white",
                 size = 4.5, inherit.aes = FALSE)
     else NULL) +
    (if (include_rhs)
       geom_text(data = rhs,
                 aes(x = x_rhs_max + 0.08, y = ymid, label = label),
                 hjust = 0, vjust = 0.5, colour = "black",
                 size = 13 / .pt, lineheight = 0.85, inherit.aes = FALSE)
     else NULL) +
    scale_fill_manual(values = GROUP_COLORS, name = NULL) +
    all_brackets +
    scale_x_continuous(
      breaks = if (include_rhs) c(0.50, xnum, (x_rhs_min + x_rhs_max) / 2)
               else              c(0.50, xnum),
      labels = {
        bar_lbls <- gsub("Other (Compliant|Noncompliant)", "Other\n\\1",
                         sapply(bars, `[[`, "label"))
        if (include_rhs)
          c("Pre Law\nMinutes", bar_lbls, "Post Law\nMinutes")
        else
          c("Pre Law\nMinutes", bar_lbls)
      },
      expand = expansion(add = c(1.0, x_expand_r))
    ) +
    scale_y_continuous(
      limits = c(y_lower, y_ceil),
      breaks = y_all_breaks,
      labels = y_all_labels,
      expand = expansion(mult = c(0, 0.01))
    ) +
    labs(x = "Effects of regulation on site category",
         y = "Weekly minutes per machine") +
    theme_house() +
    theme(
      axis.text.x  = element_text(angle = 0, hjust = 0.5, size = 15),
      axis.text.y  = element_text(size = 15),
      axis.title.x = element_text(size = 16, face = "bold",
                                  hjust = 0.5, margin = margin(t = 15)),
      axis.title.y = element_text(size = 17, margin = margin(r = 8)),
      legend.position = "none",
      plot.margin  = margin(5, r_margin, 40, 45, "pt")
    ) +
    coord_cartesian(clip = "off")
}

make_waterfall_main <- function() make_waterfall(include_rhs = TRUE)

# ============================================================================
# GENERATE
# ============================================================================

cat("\n--- waterfall_main ---\n")
path <- file.path(fig_dir, "waterfall_main.png")
ggsave(path, make_waterfall_main(), width = 15.5, height = 6.5)
cat(sprintf("Wrote: %s\n", path))

cat("\nAll done.\n")
