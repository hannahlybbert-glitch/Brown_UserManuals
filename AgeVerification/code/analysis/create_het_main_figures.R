# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-04-27; Updated: 2026-05-11
# Purpose: Heterogeneity dot plot — vertical layout, All-XXX level effects.
#   24 subgroups on y-axis (top to bottom), long-term All-XXX change on x-axis.
#   8 groups: Age (3), Gender (4), Device (2), Income (3), Children (2),
#             State (2), XXX Usage Tercile (4), PH Usage Tercile (4).
#   One point per subgroup. Level effects (minutes, not normalized).
#   PH baseline (treatment group, τ = −4 to −1) shown in subgroup label.
#   Horizontal dotted lines separate groups. 95% CI error bars.
#
# Requires: output/.../intermediate/het_multisite_results.rds
#           (produced by create_het_main_regressions.R)
#
# Outputs (output/.../heterogeneity_plots/):
#   het_main.png

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD DATA
# ============================================================================

cat("Loading het_multisite_results...\n")
inp    <- readRDS(file.path(out_int_dir, "het_multisite_results.rds"))
res_df <- inp$res_df

if (nrow(res_df) == 0L) {
  stop("het_multisite_results.rds is empty. Re-run create_het_main_regressions.R.")
}

# Join PH and all-XXX per-subgroup baselines onto every row
ph_baselines <- res_df |>
  dplyr::filter(site == "Pornhub") |>
  dplyr::select(group, ph_baseline = baseline_mean_treat)

allxxx_baselines <- res_df |>
  dplyr::filter(site == "All XXX (pooled)") |>
  dplyr::select(group, allxxx_baseline = baseline_mean_treat)

res_plot <- res_df |>
  dplyr::left_join(ph_baselines,    by = "group") |>
  dplyr::left_join(allxxx_baselines, by = "group") |>
  dplyr::mutate(site = dplyr::recode(site,
    "Other XXX (combined)" = "Other XXX",
    "All XXX (pooled)"     = "All XXX"
  ))

# ============================================================================
# SUBGROUP STRUCTURE  (8 groups × 24 subgroups)
# ============================================================================

ALL_GROUPS <- list(
  "State"             = c("State: Treated",          "State: Non-Treated"),
  "Gender"            = c("Gender: Male",           "Gender: Female",        "Gender: Shared",        "Gender: Unknown"),
  "Age"               = c("Age: 18-24",            "Age: 25-44",            "Age: 45+"),
  "Income"            = c("Income: <$60k",           "Income: $60k-$99k",     "Income: $100k+"),
  "Children in Desktop" = c("Children in Desktop: Yes", "Children in Desktop: No"),
  "Device Type"       = c("Device: Desktop",        "Device: Mobile"),
  "XXX Usage Tercile" = c("XXX Non Visitor",         "XXX Tercile: Light",    "XXX Tercile: Moderate", "XXX Tercile: Heavy"),
  "PH Usage Tercile"  = c("PH Non Visitor",          "PH Tercile: Light",     "PH Tercile: Moderate",  "PH Tercile: Heavy")
)

ALL_LEVELS <- unlist(ALL_GROUPS, use.names = FALSE)

# Short display names for y-axis tick labels (PH baseline appended at plot time)
DISPLAY_LABELS <- c(
  "Age: 18-24"            = "18–24",
  "Age: 25-44"            = "25–44",
  "Age: 45+"              = "45+",
  "Gender: Male"          = "Male",
  "Gender: Female"        = "Female",
  "Gender: Shared"        = "Shared",
  "Gender: Unknown"       = "Unknown",
  "Device: Desktop"       = "Desktop",
  "Device: Mobile"        = "Mobile",
  "Income: <$60k"         = "<$60k",
  "Income: $60k-$99k"     = "$60k–\n$99k",
  "Income: $100k+"        = "$100k+",
  "Children in Desktop: Yes" = "Yes",
  "Children in Desktop: No"  = "No",
  "State: Treated"        = "Treated",
  "State: Non-Treated"    = "Non-Treated",
  "XXX Non Visitor"       = "Non Visitor",
  "XXX Tercile: Light"    = "Light",
  "XXX Tercile: Moderate" = "Moderate",
  "XXX Tercile: Heavy"    = "Heavy",
  "PH Non Visitor"        = "Non Visitor",
  "PH Tercile: Light"     = "Light",
  "PH Tercile: Moderate"  = "Moderate",
  "PH Tercile: Heavy"     = "Heavy"
)

# Map each subgroup name → its group panel label
GROUP_MAP <- setNames(
  rep(names(ALL_GROUPS), lengths(ALL_GROUPS)),
  ALL_LEVELS
)

# ============================================================================
# BUILD PLOT DATA
# ============================================================================

df_allxxx <- res_plot |>
  dplyr::filter(site == "All XXX") |>
  dplyr::mutate(
    norm  = beta_lt,
    ci_lo = beta_lt - 1.96 * se_lt,
    ci_hi = beta_lt + 1.96 * se_lt
  )

present <- intersect(ALL_LEVELS, unique(df_allxxx$group))

ph_bl <- df_allxxx |>
  dplyr::filter(group %in% present) |>
  dplyr::select(group, ph_baseline) |>
  dplyr::distinct() |>
  (\(x) setNames(x$ph_baseline, x$group))()

# Y-axis labels: short name on first line, PH baseline on second line
y_labels <- setNames(
  sprintf("%s\n(%.2f min)", DISPLAY_LABELS[present], ph_bl[present]),
  present
)

df_plot <- df_allxxx |>
  dplyr::filter(group %in% present) |>
  dplyr::mutate(
    # rev(ALL_LEVELS): level 1 = last subgroup (PH Heavy, bottom of plot)
    #                  level N = first subgroup (State Treated, top of plot)
    group_f     = factor(group, levels = rev(ALL_LEVELS)),
    # rev(names(ALL_GROUPS)): highest level = "State" → top panel in facet_grid
    group_panel = factor(GROUP_MAP[group], levels = rev(names(ALL_GROUPS)))
  )

STRIP_LABELS <- c(
  "State"             = "State",
  "Gender"            = "Gender",
  "Age"               = "Age",
  "Income"            = "Household\nIncome",
  "Children Present (Desktop)" = "Children\nPresent\n(Desktop)",
  "Device Type"       = "Device\nType",
  "XXX Usage Tercile" = "XXX\nUsage\nTercile",
  "PH Usage Tercile"  = "Pornhub\nUsage\nTercile"
)

# ============================================================================
# THEME
# ============================================================================

theme_het <- function(base_size = 11) {
  theme_bw(base_size = base_size) +
    theme(
      panel.grid.minor    = element_blank(),
      panel.grid.major.y  = element_blank(),
      panel.grid.major.x  = element_blank(),
      panel.border        = element_blank(),
      axis.line.x         = element_line(color = "black", linewidth = 0.4),
      axis.ticks.y        = element_blank(),
      axis.text.y         = element_text(size = 10, lineheight = 0.85, margin = margin(r = -2)),
      axis.text.x         = element_text(size = 13),
      axis.title.x        = element_text(size = 15, margin = margin(t = 8)),
      plot.title          = element_text(size = 12),
      plot.subtitle       = element_text(size = 7.5, color = "gray40"),
      legend.position     = "none",
      panel.spacing.y     = unit(4, "pt"),
      strip.background    = element_rect(fill = "gray95", color = NA),
      strip.text.y.left   = element_text(size = 10, face = "bold",
                                         angle = 0, hjust = 1, lineheight = 0.85),
      strip.placement     = "outside",
      plot.caption        = element_text(size = 7.5, color = "gray40", hjust = 0),
      plot.margin         = margin(5, 15, 5, 5, "pt")
    )
}

# ============================================================================
# PLOT
# ============================================================================

out_dir <- file.path(out_base, "heterogeneity_plots")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

save_fig <- function(p, name, w, h) {
  path <- file.path(out_dir, name)
  ggsave(path, p, width = w, height = h, dpi = 300)
  cat(sprintf("  Wrote: %s\n", path))
}

# p_het <- ggplot(df_plot, aes(x = norm, y = group_f)) +
#   # Reference line at zero
#   geom_vline(xintercept = 0, linetype = "dashed",
#              linewidth = 0.5, color = "gray40") +
#   # Dotted separator at the bottom of each facet panel (between groups)
#   geom_hline(yintercept = 0.5, linetype = "dotted",
#              linewidth = 0.4, color = "gray55") +
#   # 95% CI error bars (horizontal)
#   geom_errorbarh(aes(xmin = ci_lo, xmax = ci_hi),
#                  height = 0, linewidth = 0.55, color = MAROON) +
#   # Point estimate
#   geom_point(size = 2.5, color = MAROON) +
#   # One panel per group, strips on the left
#   facet_grid(group_panel ~ ., scales = "free_y", space = "free_y", switch = "y",
#              labeller = labeller(group_panel = STRIP_LABELS)) +
#   scale_y_discrete(labels = y_labels) +
#   scale_x_continuous(
#     name = "Change in avg. weekly winsorized minutes (All XXX)"
#   ) +
#   labs(
#     title   = "Heterogeneity in All-XXX usage — Long-term (τ = 4–8 weeks)",
#     caption = "All XXX level effect. Label shows PH baseline usage in subgroup.",
#     y       = NULL
#   ) +
#   theme_het()
#
# cat("\nHeterogeneity dot plot — vertical layout, All XXX, long-term\n")
# save_fig(p_het, "het_main.png", w = 9, h = 10)

# ============================================================================
# PCT PLOT — same layout but estimate / subgroup PH baseline
# Non-visitors excluded from both tercile groups (baseline = 0 → undefined)
# ============================================================================

# ALL_GROUPS_PCT <- list(
#   "State"             = c("State: Treated",          "State: Non-Treated"),
#   "Gender"            = c("Gender: Male",            "Gender: Female",        "Gender: Shared",        "Gender: Unknown"),
#   "Age"               = c("Age: 18-24",              "Age: 25-44",            "Age: 45+"),
#   "Income"            = c("Income: <$60k",            "Income: $60k-$99k",     "Income: $100k+"),
#   "Children"          = c("Children: Yes",            "Children: No"),
#   "Device Type"       = c("Device: Desktop",         "Device: Mobile"),
#   "XXX Usage Tercile" = c("XXX Tercile: Light",       "XXX Tercile: Moderate", "XXX Tercile: Heavy"),
#   "PH Usage Tercile"  = c("PH Tercile: Light",        "PH Tercile: Moderate",  "PH Tercile: Heavy")
# )
#
# ALL_LEVELS_PCT <- unlist(ALL_GROUPS_PCT, use.names = FALSE)
# GROUP_MAP_PCT  <- setNames(
#   rep(names(ALL_GROUPS_PCT), lengths(ALL_GROUPS_PCT)),
#   ALL_LEVELS_PCT
# )
#
# present_pct <- intersect(ALL_LEVELS_PCT, unique(df_allxxx$group))
#
# y_labels_pct <- setNames(DISPLAY_LABELS[present_pct], present_pct)
#
# df_pct <- df_allxxx |>
#   dplyr::filter(group %in% present_pct) |>
#   dplyr::mutate(
#     norm  =  beta_lt              / allxxx_baseline,
#     ci_lo = (beta_lt - 1.96 * se_lt) / allxxx_baseline,
#     ci_hi = (beta_lt + 1.96 * se_lt) / allxxx_baseline,
#     group_f     = factor(group, levels = rev(ALL_LEVELS_PCT)),
#     group_panel = factor(GROUP_MAP_PCT[group], levels = rev(names(ALL_GROUPS_PCT)))
#   )
#
# p_het_pct <- ggplot(df_pct, aes(x = norm, y = group_f)) +
#   geom_vline(xintercept = 0, linetype = "dashed",
#              linewidth = 0.5, color = "gray40") +
#   geom_hline(yintercept = 0.5, linetype = "dotted",
#              linewidth = 0.4, color = "gray55") +
#   geom_errorbarh(aes(xmin = ci_lo, xmax = ci_hi),
#                  height = 0, linewidth = 0.55, color = MAROON) +
#   geom_point(size = 2.5, color = MAROON) +
#   facet_grid(group_panel ~ ., scales = "free_y", space = "free_y", switch = "y",
#              labeller = labeller(group_panel = STRIP_LABELS)) +
#   scale_y_discrete(labels = y_labels_pct) +
#   scale_x_continuous(
#     name   = "% change in avg. weekly winsorized minutes (All XXX)",
#     labels = scales::percent
#   ) +
#   labs(
#     title   = "Heterogeneity in All-XXX usage — Long-term (τ = 4–8 weeks)",
#     caption = "All XXX percentage effect. Each subgroup divided by its baseline PH minutes per week.",
#     y       = NULL
#   ) +
#   theme_het()
#
# cat("\nHeterogeneity dot plot — pct normalized, vertical layout, All XXX, long-term\n")
# save_fig(p_het_pct, "het_main_pct.png", w = 9, h = 10)

# ============================================================================
# LEVEL PLOT (no-heavy) — excludes Heavy tercile from XXX and PH usage groups
# ============================================================================

# ALL_GROUPS_NOHEAVY <- list(
#   "State"             = c("State: Treated",          "State: Non-Treated"),
#   "Gender"            = c("Gender: Male",            "Gender: Female",        "Gender: Shared",        "Gender: Unknown"),
#   "Age"               = c("Age: 18-24",              "Age: 25-44",            "Age: 45+"),
#   "Income"            = c("Income: <$60k",            "Income: $60k-$99k",     "Income: $100k+"),
#   "Children"          = c("Children: Yes",            "Children: No"),
#   "Device Type"       = c("Device: Desktop",         "Device: Mobile"),
#   "XXX Usage Tercile" = c("XXX Non Visitor",          "XXX Tercile: Light",    "XXX Tercile: Moderate"),
#   "PH Usage Tercile"  = c("PH Non Visitor",           "PH Tercile: Light",     "PH Tercile: Moderate")
# )
#
# ALL_LEVELS_NOHEAVY <- unlist(ALL_GROUPS_NOHEAVY, use.names = FALSE)
# GROUP_MAP_NOHEAVY  <- setNames(
#   rep(names(ALL_GROUPS_NOHEAVY), lengths(ALL_GROUPS_NOHEAVY)),
#   ALL_LEVELS_NOHEAVY
# )
#
# present_noheavy <- intersect(ALL_LEVELS_NOHEAVY, unique(df_allxxx$group))
#
# ph_bl_noheavy <- df_allxxx |>
#   dplyr::filter(group %in% present_noheavy) |>
#   dplyr::select(group, ph_baseline) |>
#   dplyr::distinct() |>
#   (\(x) setNames(x$ph_baseline, x$group))()
#
# y_labels_noheavy <- setNames(
#   sprintf("%s\n(%.2f min)", DISPLAY_LABELS[present_noheavy], ph_bl_noheavy[present_noheavy]),
#   present_noheavy
# )
#
# df_noheavy <- df_allxxx |>
#   dplyr::filter(group %in% present_noheavy) |>
#   dplyr::mutate(
#     norm  = beta_lt,
#     ci_lo = beta_lt - 1.96 * se_lt,
#     ci_hi = beta_lt + 1.96 * se_lt,
#     group_f     = factor(group, levels = rev(ALL_LEVELS_NOHEAVY)),
#     group_panel = factor(GROUP_MAP_NOHEAVY[group], levels = rev(names(ALL_GROUPS_NOHEAVY)))
#   )
#
# p_het_noheavy <- ggplot(df_noheavy, aes(x = norm, y = group_f)) +
#   geom_vline(xintercept = 0, linetype = "dashed",
#              linewidth = 0.5, color = "gray40") +
#   geom_hline(yintercept = 0.5, linetype = "dotted",
#              linewidth = 0.4, color = "gray55") +
#   geom_errorbarh(aes(xmin = ci_lo, xmax = ci_hi),
#                  height = 0, linewidth = 0.55, color = MAROON) +
#   geom_point(size = 2.5, color = MAROON) +
#   facet_grid(group_panel ~ ., scales = "free_y", space = "free_y", switch = "y",
#              labeller = labeller(group_panel = STRIP_LABELS)) +
#   scale_y_discrete(labels = y_labels_noheavy) +
#   scale_x_continuous(
#     name = "Change in avg. weekly winsorized minutes (All XXX)"
#   ) +
#   labs(
#     title   = "Heterogeneity in All-XXX usage — Long-term (τ = 4–8 weeks)",
#     caption = "All XXX level effect. Label shows PH baseline usage in subgroup.",
#     y       = NULL
#   ) +
#   theme_het()
#
# cat("\nHeterogeneity dot plot — no-heavy, vertical layout, All XXX, long-term\n")
# save_fig(p_het_noheavy, "het_main_noheavy.png", w = 9, h = 10)

# ============================================================================
# PCT PLOT (no-light) — excludes Light tercile from XXX and PH usage groups
# ============================================================================

# All-XXX reference line: long-term ATT / baseline mean from pooled regression
# baseline_mean is stored under $event, not $pooled, in regression_results.rds
results_main  <- readRDS(file.path(out_int_dir, "regression_results.rds"))
allxxx_beta   <- results_main$pooled[["all_xxx"]][["win_min"]]$beta_longterm
allxxx_bl     <- results_main$event[["all_xxx"]][["win_min"]]$baseline_mean
allxxx_ref    <- allxxx_beta / allxxx_bl
rm(results_main, allxxx_beta, allxxx_bl)
cat(sprintf("All-XXX reference line: %.1f%%\n", 100 * allxxx_ref))

# Circumvention and substitution reference lines from pooled top-25 regression
t25_slugs <- list(
  list(slug = "PORNHUB_COM"),
  list(slug = "other_compliant"),
  list(slug = "XVIDEOS_COM"),
  list(slug = "XNXX_COM"),
  list(slug = "other_noncompliant_top25")
)
t25_path  <- here::here("output", "analysis", "combined", "top_25",
                         "intermediate", "regression_results_top25.rds")
res_t25   <- readRDS(t25_path)
t25_betas <- sapply(t25_slugs, function(b)
  res_t25$pooled[[b$slug]][["win_min"]]$beta_longterm)
t25_bls   <- sapply(t25_slugs, function(b)
  res_t25$pooled[[b$slug]]$baseline_mean)
t25_denom <- sum(t25_bls)
circ_ref  <- ((t25_bls[1] + t25_betas[1]) + (t25_bls[2] + t25_betas[2])) / t25_denom
sub_ref   <- sum(t25_betas[3:5]) / t25_denom
rm(res_t25, t25_betas, t25_bls, t25_denom)
cat(sprintf("Circumvention reference line: %.1f%%\n", 100 * circ_ref))
cat(sprintf("Substitution  reference line: %.1f%%\n", 100 * sub_ref))

ALL_GROUPS_PCT_NOLIGHT <- list(
  "Gender"            = c("Gender: Male",            "Gender: Female",        "Gender: Shared",        "Gender: Unknown"),
  "Age"               = c("Age: 18-24",              "Age: 25-44",            "Age: 45+"),
  "Income"            = c("Income: <$60k",            "Income: $60k-$99k",     "Income: $100k+"),
  "Children Present (Desktop)" = c("Children in Desktop: Yes", "Children in Desktop: No"),
  "Device Type"       = c("Device: Desktop",         "Device: Mobile"),
  "XXX Usage Tercile" = c("XXX Tercile: Moderate",   "XXX Tercile: Heavy"),
  "PH Usage Tercile"  = c("PH Tercile: Moderate",    "PH Tercile: Heavy")
)

ALL_LEVELS_PCT_NOLIGHT <- unlist(ALL_GROUPS_PCT_NOLIGHT, use.names = FALSE)
GROUP_MAP_PCT_NOLIGHT  <- setNames(
  rep(names(ALL_GROUPS_PCT_NOLIGHT), lengths(ALL_GROUPS_PCT_NOLIGHT)),
  ALL_LEVELS_PCT_NOLIGHT
)

present_pct_nolight <- intersect(ALL_LEVELS_PCT_NOLIGHT, unique(df_allxxx$group))

y_labels_pct_nolight <- setNames(DISPLAY_LABELS[present_pct_nolight], present_pct_nolight)

df_pct_nolight <- df_allxxx |>
  dplyr::filter(group %in% present_pct_nolight) |>
  dplyr::mutate(
    norm  =  beta_lt              / allxxx_baseline,
    ci_lo = (beta_lt - 1.96 * se_lt) / allxxx_baseline,
    ci_hi = (beta_lt + 1.96 * se_lt) / allxxx_baseline,
    group_f     = factor(group, levels = rev(ALL_LEVELS_PCT_NOLIGHT)),
    group_panel = factor(GROUP_MAP_PCT_NOLIGHT[group], levels = rev(names(ALL_GROUPS_PCT_NOLIGHT)))
  )

p_het_pct_nolight <- ggplot(df_pct_nolight, aes(x = norm, y = group_f)) +
  geom_vline(xintercept = 0, linetype = "dashed",
             linewidth = 0.5, color = "gray40") +
  geom_vline(xintercept = allxxx_ref, linetype = "dashed",
             linewidth = 0.35, color = "gray70") +
  geom_errorbar(aes(xmin = ci_lo, xmax = ci_hi),
                width = 0, linewidth = 0.55, color = MAROON,
                orientation = "y") +
  geom_point(size = 2.5, color = MAROON) +
  facet_grid(group_panel ~ ., scales = "free_y", space = "free_y", switch = "y",
             labeller = labeller(group_panel = STRIP_LABELS)) +
  scale_y_discrete(labels = y_labels_pct_nolight) +
  scale_x_continuous(
    name   = "Percent change in weekly minutes per machine (all XXX)",
    labels = scales::percent
  ) +
  labs(
    y = NULL
  ) +
  theme_het()

cat("\nHeterogeneity dot plot — cessation (All XXX, pct no-light)\n")
save_fig(p_het_pct_nolight, "het_main_cessation.png", w = 9, h = 10)

# ============================================================================
# CIRCUMVENTION + SUBSTITUTION PLOTS
#
# Denominator (per subgroup) = sum of baseline means across all top-25 sites:
#   baseline_PH + baseline_other_compliant + baseline_XV + baseline_XNXX
#   + baseline_other_noncompliant_top25
#
# Circumvention numerator = remaining minutes on compliant sites (PH + other_compliant):
#   (baseline_PH - |beta_lt_PH|) + (baseline_other_compliant - |beta_lt_other_compliant|)
#   = (baseline_PH + beta_lt_PH) + (baseline_other_compliant + beta_lt_other_compliant)
#
# Substitution numerator = increase in minutes on noncompliant sites:
#   beta_lt_XV + beta_lt_XNXX + beta_lt_other_noncompliant_top25
# ============================================================================

# Pull per-subgroup values for each component site/group
pull_site <- function(site_label) {
  res_plot |>
    dplyr::filter(site == site_label) |>
    dplyr::select(group,
                  baseline = baseline_mean_treat,
                  beta_lt,
                  se_lt)
}

by_group_ph      <- pull_site("Pornhub")
by_group_xv      <- pull_site("XVideos")
by_group_xnxx    <- pull_site("XNXX")
by_group_comp    <- pull_site("Other Compliant")
by_group_noncomp <- pull_site("Other Noncompliant Top 25")

# Build per-subgroup denominator and numerators
circ_sub_df <- by_group_ph |>
  dplyr::inner_join(by_group_xv,      by = "group", suffix = c("_ph",    "_xv")) |>
  dplyr::inner_join(by_group_xnxx,    by = "group", suffix = c("",       "_xnxx")) |>
  dplyr::rename(baseline_xnxx = baseline, beta_lt_xnxx = beta_lt, se_lt_xnxx = se_lt) |>
  dplyr::inner_join(by_group_comp,    by = "group", suffix = c("",       "_comp")) |>
  dplyr::rename(baseline_comp = baseline, beta_lt_comp = beta_lt, se_lt_comp = se_lt) |>
  dplyr::inner_join(by_group_noncomp, by = "group", suffix = c("",       "_noncomp")) |>
  dplyr::rename(baseline_noncomp = baseline, beta_lt_noncomp = beta_lt, se_lt_noncomp = se_lt) |>
  dplyr::mutate(
    denom = baseline_ph + baseline_xv + baseline_xnxx + baseline_comp + baseline_noncomp,

    # Circumvention: remaining level on compliant sites / all-top25 baseline
    circ_norm  = (baseline_ph   + beta_lt_ph   +
                  baseline_comp + beta_lt_comp) / denom,
    circ_se    = sqrt(se_lt_ph^2 + se_lt_comp^2) / denom,
    circ_ci_lo = circ_norm - 1.96 * circ_se,
    circ_ci_hi = circ_norm + 1.96 * circ_se,

    # Substitution: increase in noncompliant minutes / all-top25 baseline
    sub_beta   = beta_lt_xv + beta_lt_xnxx + beta_lt_noncomp,
    sub_se     = sqrt(se_lt_xv^2 + se_lt_xnxx^2 + se_lt_noncomp^2),
    sub_norm   =  sub_beta               / denom,
    sub_ci_lo  = (sub_beta - 1.96 * sub_se) / denom,
    sub_ci_hi  = (sub_beta + 1.96 * sub_se) / denom
  )

present_cs    <- intersect(ALL_LEVELS_PCT_NOLIGHT, unique(circ_sub_df$group))
y_labels_cs   <- setNames(DISPLAY_LABELS[present_cs], present_cs)

df_cs <- circ_sub_df |>
  dplyr::filter(group %in% present_cs) |>
  dplyr::mutate(
    group_f     = factor(group, levels = rev(ALL_LEVELS_PCT_NOLIGHT)),
    group_panel = factor(GROUP_MAP_PCT_NOLIGHT[group], levels = rev(names(ALL_GROUPS_PCT_NOLIGHT)))
  )

# --- Circumvention ---
p_circ <- ggplot(df_cs, aes(x = circ_norm, y = group_f)) +
  geom_vline(xintercept = 0, linetype = "dashed",
             linewidth = 0.5, color = "gray40") +
  geom_vline(xintercept = circ_ref, linetype = "dashed",
             linewidth = 0.35, color = "gray70") +
  geom_errorbar(aes(xmin = circ_ci_lo, xmax = circ_ci_hi),
                width = 0, linewidth = 0.55, color = MAROON,
                orientation = "y") +
  geom_point(size = 2.5, color = MAROON) +
  facet_grid(group_panel ~ ., scales = "free_y", space = "free_y", switch = "y",
             labeller = labeller(group_panel = STRIP_LABELS)) +
  scale_y_discrete(labels = y_labels_cs) +
  scale_x_continuous(
    name   = "Weekly minutes per machine persisting on compliant sites after restrictions\n(as percent of top 25 baseline)",
    labels = scales::percent
  ) +
  labs(y = NULL) +
  theme_het()

cat("\nHeterogeneity dot plot — circumvention\n")
save_fig(p_circ, "het_circumvention.png", w = 9, h = 10)

# --- Substitution ---
p_sub <- ggplot(df_cs, aes(x = sub_norm, y = group_f)) +
  geom_vline(xintercept = 0, linetype = "dashed",
             linewidth = 0.5, color = "gray40") +
  geom_vline(xintercept = sub_ref, linetype = "dashed",
             linewidth = 0.35, color = "gray70") +
  geom_errorbar(aes(xmin = sub_ci_lo, xmax = sub_ci_hi),
                width = 0, linewidth = 0.55, color = MAROON,
                orientation = "y") +
  geom_point(size = 2.5, color = MAROON) +
  facet_grid(group_panel ~ ., scales = "free_y", space = "free_y", switch = "y",
             labeller = labeller(group_panel = STRIP_LABELS)) +
  scale_y_discrete(labels = y_labels_cs) +
  scale_x_continuous(
    name   = "Change in weekly minutes per machine at noncompliant sites\n(as percent of top 25 baseline)",
    labels = scales::percent
  ) +
  labs(y = NULL) +
  theme_het()

cat("\nHeterogeneity dot plot — substitution\n")
save_fig(p_sub, "het_substitution.png", w = 9, h = 10)

cat("\nAll done.\n")
