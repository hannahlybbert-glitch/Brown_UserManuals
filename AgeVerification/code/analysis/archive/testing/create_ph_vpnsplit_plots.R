# Author: Matt Brown, assisted by Claude
# Created: 2026-03-27
# Purpose: Generate event-study plots and pooled ATT summary table for
#          Pornhub split by pre-period CleanVPN status.
#
# Requires: output/analysis/intermediate/regression_results.rds
#           (produced by run_regressions.R with RUN_PH_VPNSPLIT = TRUE)
#
# Outputs (output/analysis/event_study/):
#   PORNHUB_COM_vpn_{dv}_coefs.csv    — event coefficients, VPN group
#   PORNHUB_COM_novpn_{dv}_coefs.csv  — event coefficients, no-VPN group
#   ph_vpnsplit_{dv}.png              — overlaid two-series event study plot
#
# Outputs (output/analysis/full_sample/):
#   ph_vpnsplit_table_{dv}.md         — pooled ATT summary table (markdown)
#   ph_vpnsplit_table_{dv}.tex        — pooled ATT summary table (LaTeX)
#
# Usage:
#   Rscript code/analysis/create_ph_vpnsplit_plots.R

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(knitr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

# ============================================================================
# LOAD RESULTS
# ============================================================================

cat("Loading regression results...\n")
results <- readRDS(file.path(out_int_dir, "regression_results.rds"))

SLUGS <- c("PORNHUB_COM_vpn", "PORNHUB_COM_novpn")
if (!any(SLUGS %in% names(results$event))) {
  stop("ph_vpnsplit results not found. Re-run run_regressions.R with ph_vpnsplit arg.")
}

qualifying <- results$meta$qualifying
n_clusters <- results$meta$n_clusters
n_cohorts  <- length(qualifying)

# ============================================================================
# OUTPUT DIRS
# ============================================================================

es_dir  <- file.path(out_base, "event_study")
tbl_dir <- file.path(out_base, "full_sample")
dir.create(es_dir,  recursive = TRUE, showWarnings = FALSE)
dir.create(tbl_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# OVERLAID TWO-SERIES EVENT STUDY PLOTS
# ============================================================================

cat("\n", strrep("=", 60), "\n", sep = "")
cat("Writing Pornhub VPN-split event-study plots\n")
cat(strrep("=", 60), "\n\n", sep = "")

SUBSETS <- list(
  list(slug = "PORNHUB_COM_vpn",   label = "Pre-period VPN users",  color = NAVY),
  list(slug = "PORNHUB_COM_novpn", label = "No pre-period VPN",     color = MAROON)
)

for (dv in dvs) {
  dv_meta <- DV_METADATA[[dv]]

  # Write individual coefficient CSVs
  for (sub in SUBSETS) {
    if (!sub$slug %in% names(results$event)) next
    res <- results$event[[sub$slug]][[dv]]
    if (is.null(res)) next
    csv_path <- file.path(es_dir, sprintf("%s_%s_coefs.csv", sub$slug, dv))
    write.csv(res$coefs, csv_path, row.names = FALSE)
    cat(sprintf("  %s %s coefs → %s\n", sub$slug, dv, csv_path))
  }

  # Build combined data frame for the overlaid plot
  plot_data <- lapply(SUBSETS, function(sub) {
    if (!sub$slug %in% names(results$event)) return(NULL)
    res <- results$event[[sub$slug]][[dv]]
    if (is.null(res)) return(NULL)
    res$coefs |> mutate(group = sub$label, color = sub$color)
  })
  plot_data <- Filter(Negate(is.null), plot_data)
  if (length(plot_data) == 0L) next
  plot_df <- bind_rows(plot_data)

  group_colors <- setNames(
    sapply(SUBSETS, `[[`, "color"),
    sapply(SUBSETS, `[[`, "label")
  )

  # Sample sizes for subtitle
  n_vpn   <- results$event[["PORNHUB_COM_vpn"]][[dv]]$n_obs
  n_novpn <- results$event[["PORNHUB_COM_novpn"]][[dv]]$n_obs

  p <- ggplot(plot_df, aes(x = rel_week, color = group, fill = group)) +
    geom_ribbon(aes(ymin = ci_lo, ymax = ci_hi), alpha = 0.12, color = NA) +
    geom_line(aes(y = beta), linewidth = 0.9) +
    geom_point(aes(y = beta), size = 1.8) +
    geom_hline(yintercept = 0, linetype = "dashed", linewidth = 0.5) +
    geom_vline(xintercept = 0, linetype = "dashed", color = "gray50", linewidth = 0.5) +
    scale_color_manual(values = group_colors, name = NULL) +
    scale_fill_manual( values = group_colors, name = NULL) +
    scale_x_continuous(breaks = seq(T_MIN, T_MAX, by = 4)) +
    labs(
      x        = "Weeks relative to law effective date",
      y        = dv_meta$y_label,
      title    = sprintf("Pornhub — by pre-period CleanVPN status  (%s)", dv_meta$short),
      subtitle = sprintf(
        "Machine\u00d7cohort + cohort\u00d7week FE  |  SE clustered by state (%d clusters, %d cohorts)  |  N: VPN=%s, No-VPN=%s",
        n_clusters, n_cohorts,
        format(n_vpn,   big.mark = ","),
        format(n_novpn, big.mark = ","))
    ) +
    theme_bw() +
    theme(
      panel.grid.minor = element_blank(),
      panel.border     = element_blank(),
      axis.line        = element_line(color = "black", linewidth = 0.4),
      plot.title       = element_text(size = 12),
      plot.subtitle    = element_text(size = 7.5, color = "gray40"),
      axis.title       = element_text(size = 10),
      axis.text        = element_text(size = 9),
      legend.position  = "bottom",
      legend.text      = element_text(size = 9)
    )

  fig_path <- file.path(es_dir, sprintf("ph_vpnsplit_%s.png", dv))
  ggsave(fig_path, p, width = 9, height = 5, dpi = 300)
  cat(sprintf("  Overlaid plot (%s) → %s\n", dv, fig_path))
}

# ============================================================================
# POOLED ATT SUMMARY TABLES
# ============================================================================

cat("\n", strrep("=", 60), "\n", sep = "")
cat("Writing Pornhub VPN-split pooled ATT tables\n")
cat(strrep("=", 60), "\n\n", sep = "")

stars <- function(p) {
  if (is.na(p))  return("")
  if (p < 0.01)  return("***")
  if (p < 0.05)  return("**")
  if (p < 0.10)  return("*")
  return("")
}

fmt_est <- function(beta, se, p) {
  if (is.na(beta)) return(c("\u2014", ""))
  c(sprintf("%.4f%s", beta, stars(p)),
    sprintf("(%.4f)", se))
}

col_labels <- c("Pornhub (VPN users)", "Pornhub (no VPN)")
row_labels <- c("\u03b2_pre", "", "\u03b2_ST", "", "\u03b2_LT", "", "N (obs)", "N (machine\u00d7cohort)")

for (dv in dvs) {
  site_cols <- lapply(SUBSETS, function(sub) {
    res <- results$pooled[[sub$slug]][[dv]]
    if (is.null(res)) return(rep(NA_character_, 8))
    pre_fmt <- fmt_est(res$beta_pre,       res$se_pre,       res$p_pre)
    st_fmt  <- fmt_est(res$beta_shortterm, res$se_shortterm, res$p_shortterm)
    lt_fmt  <- fmt_est(res$beta_longterm,  res$se_longterm,  res$p_longterm)
    c(pre_fmt[1], pre_fmt[2],
      st_fmt[1],  st_fmt[2],
      lt_fmt[1],  lt_fmt[2],
      format(res$n_obs, big.mark = ","),
      format(res$n_mc,  big.mark = ","))
  })

  tbl <- as.data.frame(site_cols, stringsAsFactors = FALSE)
  colnames(tbl) <- col_labels
  rownames(tbl) <- row_labels

  header <- sprintf(
    "Pornhub — pooled ATT by pre-period CleanVPN status  |  DV: %s  |  SE clustered by state (%d clusters)",
    DV_METADATA[[dv]]$short, n_clusters
  )

  md_path  <- file.path(tbl_dir, sprintf("ph_vpnsplit_table_%s.md",  dv))
  tex_path <- file.path(tbl_dir, sprintf("ph_vpnsplit_table_%s.tex", dv))

  writeLines(c(header, "", kable(tbl, format = "markdown")), md_path)
  writeLines(c(
    "% Auto-generated by create_ph_vpnsplit_plots.R",
    kable(tbl, format = "latex", booktabs = TRUE, caption = header)
  ), tex_path)

  cat(sprintf("  %s → %s\n       → %s\n", dv, md_path, tex_path))
}

cat("\nAll done.\n")
