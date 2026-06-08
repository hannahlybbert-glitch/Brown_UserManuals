# Author: Matt Brown, assisted by Claude
# Created: 2026-03-06
# Purpose: Stacked TWFE event-study regressions — 10 sites × 2 DVs, full sample.
#          Replaces event_study_regression.R; adds pooled ATT summary table.
#
# Requires: data/intermediate/stacked_panel.rds, data/intermediate/xxx_win_wide.rds
#           (produced by prepare.R)
#
# Outputs (output/analysis/event_study/):
#   {slug}_{dv}_coefs.csv   — coefficients + 95% CI
#   {slug}_{dv}.png         — event-study plot
# output/analysis/full_sample_atts.md   — pooled ATT summary table
#
# Usage:
#   Rscript code/analysis/full_sample.R

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
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
qualifying      <- sp$qualifying
n_clusters      <- sp$n_clusters
control_states  <- sp$control_states
rm(sp)

xxx_win_wide <- readRDS(file.path(int_dir, "xxx_win_wide.rds"))

cat(sprintf("  Stacked: %s rows | %d clusters | %d cohorts\n",
    format(nrow(stacked_base), big.mark = ","), n_clusters, length(qualifying)))

# ============================================================================
# SITES
# ============================================================================

SITES <- list(
  list(key = "all_xxx",         label = "All XXX (pooled)", slug = "all_xxx"),
  list(key = "PORNHUB.COM",     label = "Pornhub",          slug = "PORNHUB_COM"),
  list(key = "XVIDEOS.COM",     label = "xVideos",          slug = "XVIDEOS_COM"),
  list(key = "XHAMSTER.COM",    label = "xHamster",         slug = "XHAMSTER_COM"),
  list(key = "XNXX.COM",        label = "XNXX",             slug = "XNXX_COM"),
  list(key = "CHATURBATE.COM",  label = "Chaturbate",       slug = "CHATURBATE_COM"),
  list(key = "other_XXX_sites", label = "Other XXX",        slug = "other_XXX"),
  list(key = "all_other_sites", label = "All other sites",  slug = "all_other")
  # list(key = "VPN_clean",    label = "VPN (clean)",       slug = "VPN_clean"),  # parquet not on this machine
  # list(key = "allVPN",       label = "All VPN",           slug = "allVPN")       # parquet not on this machine
)

# ============================================================================
# OUTPUT DIRS
# ============================================================================

out_dir    <- file.path(project_root, "output", "analysis", "event_study")
out_tables <- file.path(project_root, "output", "analysis")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# RESULT STORAGE (for ATT table)
# ============================================================================

dvs         <- c("over60", "win_min")
site_labels <- sapply(SITES, `[[`, "label")

atts <- lapply(dvs, function(dv) {
  make_mat <- function()
    matrix(NA_character_, nrow = 3L, ncol = length(SITES),
           dimnames = list(c("\u03b2_ST", "\u03b2_LT", "\u03b2_pre"), site_labels))
  list(ST = make_mat()[1, , drop = FALSE],
       LT = make_mat()[2, , drop = FALSE],
       PRE= make_mat()[3, , drop = FALSE])
})
names(atts) <- dvs

# ============================================================================
# MAIN LOOP — 10 sites × 2 DVs
# ============================================================================

cat("\n", strrep("=", 60), "\n", sep = "")
cat("Running regressions: 10 sites × 2 DVs\n")
cat(strrep("=", 60), "\n\n", sep = "")

for (s_idx in seq_along(SITES)) {
  site <- SITES[[s_idx]]
  cat(sprintf("--- %s (%s) ---\n", site$label, site$key))

  t0       <- proc.time()
  dur_data <- load_site_duration(site$key)
  cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
      format(nrow(dur_data), big.mark = ","),
      (proc.time() - t0)[["elapsed"]]))

  df <- stacked_base |>
    left_join(dur_data, by = c("machine_id", "week_of_sample"))
  rm(dur_data)

  df <- attach_dvs(df, site$key, xxx_win_wide)

  for (dv in dvs) {
    dv_label <- if (dv == "over60") ">60s binary" else "Win. min/machine (p95)"
    y_label  <- if (dv == "over60") "Change in Pr(>60s)" else
                                    "Change in min/machine/week (p95-win.)"

    t1  <- proc.time()
    fit <- feols(as.formula(sprintf(
      "%s ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week", dv)),
      data = df, cluster = ~state, warn = FALSE, notes = FALSE)
    cat(sprintf("    %s: N=%s, R2_within=%.4f  (%.1fs)\n",
        dv_label,
        format(fit$nobs, big.mark = ","),
        fit$r2["r2_within"],
        (proc.time() - t1)[["elapsed"]]))

    coefs    <- extract_coefs(fit)
    csv_path <- file.path(out_dir, sprintf("%s_%s_coefs.csv", site$slug, dv))
    write.csv(coefs, csv_path, row.names = FALSE)

    baseline_mean <- mean(df[[dv]][df$treated == 1L & df$rel_week == -1L], na.rm = TRUE)
    fig_path <- save_event_study_plot(coefs, site$label, dv_label, y_label,
                                      site$slug, dv, out_dir,
                                      baseline_mean = baseline_mean)
    cat(sprintf("    → %s\n    → %s\n", csv_path, fig_path))

    res <- run_pooled(df, dv)
    if (!is.na(res$beta_shortterm)) {
      atts[[dv]][["ST"]] [1, s_idx] <- fmt_coef(res$beta_shortterm, res$se_shortterm)
      atts[[dv]][["LT"]] [1, s_idx] <- fmt_coef(res$beta_longterm,  res$se_longterm)
      atts[[dv]][["PRE"]][1, s_idx] <- fmt_coef(res$beta_pre,       res$se_pre)
    }
  }

  rm(df)
  cat("\n")
}

# ============================================================================
# WRITE POOLED ATT TABLE
# ============================================================================

write_atts_table <- function(mat_list, dv_label, filepath) {
  cols     <- site_labels
  header   <- paste0("| Estimate | ", paste(cols, collapse = " | "), " |")
  sep_line <- paste0("|", paste(rep(":---|", length(cols) + 1L), collapse = ""))
  make_row <- function(label, row) {
    vals <- row
    vals[is.na(vals)] <- "\u2014"
    paste0("| **", label, "** | ", paste(vals, collapse = " | "), " |")
  }
  content <- c(
    sprintf("# Full Sample ATT Summary \u2014 %s\n", dv_label),
    "Pooled three-period TWFE: `dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week`. SE clustered by state.  ",
    "\u03b2_ST: \u03c4 \u2208 [0,3]. \u03b2_LT: \u03c4 \u2208 [4,8]. \u03b2_pre: \u03c4 \u2208 [\u221216,\u22125]. Reference: \u03c4 \u2208 {\u22124,...,\u22121}. Format: \u03b2 (SE).\n",
    header, sep_line,
    make_row("\u03b2_ST",  mat_list[["ST"]] [1, ]),
    make_row("\u03b2_LT",  mat_list[["LT"]] [1, ]),
    make_row("\u03b2_pre", mat_list[["PRE"]][1, ]),
    ""
  )
  writeLines(content, filepath)
  cat(sprintf("Wrote: %s\n", filepath))
}

cat(strrep("=", 60), "\n", sep = "")
cat("Writing ATT tables\n")
cat(strrep("=", 60), "\n\n", sep = "")

# Write combined table (both DVs in one file)
atts_path <- file.path(out_tables, "full_sample_atts.md")
lines_all <- c()
for (dv in dvs) {
  dv_label <- if (dv == "over60") "Pr(>60s) \u2014 over60" else
                                  "Winsorized min/machine/week (p95) \u2014 win_min"
  cols     <- site_labels
  header   <- paste0("| Estimate | ", paste(cols, collapse = " | "), " |")
  sep_line <- paste0("|", paste(rep(":---|", length(cols) + 1L), collapse = ""))
  make_row <- function(label, row) {
    vals <- row; vals[is.na(vals)] <- "\u2014"
    paste0("| **", label, "** | ", paste(vals, collapse = " | "), " |")
  }
  lines_all <- c(lines_all,
    sprintf("## %s\n", dv_label),
    "Pooled three-period TWFE: `dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week`. SE clustered by state.  ",
    "\u03b2_ST: \u03c4 \u2208 [0,3]. \u03b2_LT: \u03c4 \u2208 [4,8]. \u03b2_pre: \u03c4 \u2208 [\u221216,\u22125]. Format: \u03b2 (SE).\n",
    header, sep_line,
    make_row("\u03b2_ST",  atts[[dv]][["ST"]] [1, ]),
    make_row("\u03b2_LT",  atts[[dv]][["LT"]] [1, ]),
    make_row("\u03b2_pre", atts[[dv]][["PRE"]][1, ]),
    ""
  )
}
writeLines(c("# Full Sample ATT Summary\n", lines_all), atts_path)
cat(sprintf("Wrote: %s\n", atts_path))

cat("\nAll done.\n")
