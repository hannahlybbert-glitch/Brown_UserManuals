# Author: Matt Brown, assisted by Claude
# Created: 2026-03-07
# Purpose: Generate spec-3 heterogeneity forest plots from saved regression results.
#          For each DV, produces one plot showing all interaction coefficients from
#          the fully interacted model (run_interacted on all_xxx), grouped by
#          covariate type, with ST and LT as separate series.
#
# Requires: output/analysis/intermediate/regression_results.rds
#           (produced by run_regressions.R with RUN_HETEROGENEOUS = TRUE)
#
# Outputs (output/analysis/heterogeneity_plots/):
#   heterogeneity_interacted_over60.png
#   heterogeneity_interacted_win_min.png
#
# Usage:
#   Rscript code/analysis/create_heterogeneity_plots.R

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD RESULTS
# ============================================================================

cat("Loading regression results...\n")
results <- readRDS(file.path(out_int_dir, "regression_results.rds"))

if (length(results$interacted) == 0L) {
  stop("results$interacted is empty. Re-run run_regressions.R with RUN_HETEROGENEOUS = TRUE.")
}

# ============================================================================
# HELPERS: classify and label terms
# ============================================================================

# Identify which period a term belongs to (shortterm or longterm only)
classify_period <- function(term) {
  dplyr::case_when(
    grepl("shortterm", term) ~ "Short-term (\u03c4\u22080\u20133)",
    grepl("longterm",  term) ~ "Long-term (\u03c4\u22084\u20138)",
    TRUE ~ NA_character_
  )
}

# Identify the covariate group
classify_group <- function(term) {
  dplyr::case_when(
    grepl("past_xxx_bin",  term) ~ "Past XXX activity",
    grepl("kids",          term) ~ "Kids",
    grepl("inc_tercile",   term) ~ "Income tercile",
    grepl("age_bin",       term) ~ "Age bin",
    term %in% c("treated:shortterm", "treated:longterm") ~ "Baseline",
    TRUE ~ NA_character_
  )
}

# Clean term into a human-readable y-axis label
make_label <- function(term) {
  lbl <- sub("^treated:(shortterm|longterm):?", "", term)
  lbl <- sub("^treated:(shortterm|longterm)$", "Baseline (ref group)", lbl)
  lbl <- sub("past_xxx_bin(\\d+)", "XXX activity bin \\1", lbl)
  lbl <- sub("^past_visitor_([A-Z0-9]+)_COM$", "\\1", lbl)
  lbl <- sub("^past_visitor_", "", lbl)
  lbl <- sub("inc_tercile(\\w+)",  "Income: \\1",          lbl)
  lbl <- sub("age_bin([^:]+)",     "Age \\1",              lbl)
  lbl <- gsub("_", " ", lbl)
  tolower(lbl)
}

GROUP_ORDER <- c(
  "Past XXX activity",
  "Kids",
  "Income tercile",
  "Age bin"
)

# ============================================================================
# OUTPUT DIR
# ============================================================================

out_dir <- file.path(out_base, "heterogeneity_plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# MAKE PLOTS
# ============================================================================

cat("\n", strrep("=", 60), "\n", sep = "")
cat("Writing spec-3 heterogeneity forest plots\n")
cat(strrep("=", 60), "\n\n", sep = "")

PERIOD_SPECS <- list(
  ST = list(period_val = "Short-term (\u03c4\u22080\u20133)", title_sfx = "Short-term (\u03c4 \u22080\u20133)"),
  LT = list(period_val = "Long-term (\u03c4\u22084\u20138)",  title_sfx = "Long-term (\u03c4 \u22084\u20138)")
)

for (site in SITES_FULL) {
  res <- results$interacted[[site$slug]][["win_min"]]
  if (is.null(res)) {
    cat(sprintf("Skipping %s (not in results$interacted)\n", site$label)); next
  }

  coefs <- res$coefs

  pd_all <- coefs |>
    mutate(
      period = classify_period(term),
      group  = classify_group(term),
      label  = make_label(term)
    ) |>
    filter(!is.na(period), !is.na(group)) |>
    mutate(
      ci_lo = estimate - 1.96 * std.error,
      ci_hi = estimate + 1.96 * std.error,
      group = factor(group, levels = c("Baseline", GROUP_ORDER))
    )

  if (nrow(pd_all) == 0L) {
    cat(sprintf("  %s: no plottable terms\n", site$label)); next
  }

  # Extract baseline (reference group) estimates before filtering
  baseline_ests <- pd_all |>
    filter(group == "Baseline") |>
    select(period, estimate, std.error)

  pd_all <- pd_all |> filter(group != "Baseline") |>
    mutate(group = factor(group, levels = GROUP_ORDER))

  for (key in names(PERIOD_SPECS)) {
    spec <- PERIOD_SPECS[[key]]
    pd <- pd_all |>
      filter(period == spec$period_val) |>
      mutate(label = factor(label, levels = rev(unique(label[order(group, label)]))))

    if (nrow(pd) == 0L) next

    ref_row <- baseline_ests |> filter(period == spec$period_val)
    ref_est <- if (nrow(ref_row) > 0) ref_row$estimate[1] else NA_real_
    ref_se  <- if (nrow(ref_row) > 0) ref_row$std.error[1] else NA_real_

    x_lab <- if (!is.na(ref_est)) {
      sprintf("marginal impact of characteristic on TE\n(ref. group: \u03b2 = %.3f, SE = %.3f)",
              ref_est, ref_se)
    } else {
      "marginal impact of characteristic on TE"
    }

    subtitle_text <- if (!is.null(res$r2_within)) {
      sprintf("Win. min/machine/week | Fully interacted pooled TWFE | 95%% CI  (N=%s, R\u00b2_within=%.4f)",
              format(res$n_obs, big.mark = ","),
              res$r2_within)
    } else {
      sprintf("Win. min/machine/week | Fully interacted pooled TWFE | 95%% CI  (N=%s)",
              format(res$n_obs, big.mark = ","))
    }

    p <- ggplot(pd, aes(x = estimate, y = label)) +
      geom_vline(xintercept = 0, linetype = "dashed", linewidth = 0.5,
                 color = "gray40") +
      geom_errorbarh(aes(xmin = ci_lo, xmax = ci_hi),
                     height = 0.3, linewidth = 0.6, color = MAROON) +
      geom_point(size = 2.5, color = MAROON) +
      facet_grid(group ~ ., scales = "free_y", space = "free_y") +
      scale_x_continuous(
        breaks = function(lims) {
          br <- scales::extended_breaks()(lims)
          sort(unique(c(br, 0)))
        },
        labels = function(br) {
          sapply(br, function(b) {
            if (!is.na(b) && abs(b) < 1e-10 && !is.na(ref_est)) sprintf("0\n(%.3f)", ref_est) else as.character(b)
          })
        }
      ) +
      labs(
        x        = x_lab,
        y        = NULL,
        title    = sprintf("Spec-3 interacted effects \u2014 %s \u2014 %s",
                           site$label, spec$title_sfx),
        subtitle = subtitle_text
      ) +
      theme_bw() +
      theme(
        panel.grid.minor   = element_blank(),
        panel.grid.major.y = element_line(color = "gray92"),
        panel.border       = element_blank(),
        axis.line.x        = element_line(color = "black", linewidth = 0.4),
        axis.line.y        = element_blank(),
        axis.ticks.y       = element_blank(),
        strip.background   = element_rect(fill = "gray95", color = NA),
        strip.text         = element_text(size = 8, face = "bold"),
        plot.title         = element_text(size = 12),
        plot.subtitle      = element_text(size = 8, color = "gray40"),
        axis.title         = element_text(size = 10),
        axis.text          = element_text(size = 8)
      )

    path <- file.path(out_dir, sprintf("heterogeneity_interacted_%s_%s.png", site$slug, key))
    ggsave(path, p, width = 9, height = 10, dpi = 300)
    cat(sprintf("  %s [%s]: \u2192 %s\n", site$label, key, path))
  }
}

cat("\nAll done.\n")
