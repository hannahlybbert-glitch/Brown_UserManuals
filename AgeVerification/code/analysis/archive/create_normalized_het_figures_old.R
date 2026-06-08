# Author: Matt Brown, assisted by Claude
# Created: 2026-03-20
# Purpose: Figures for normalized heterogeneity analysis.
#   Two versions of Figure 1 (stacked decomposition bar):
#     - PH-tercile version: pre-period usage bins based on Pornhub specifically
#     - XXX-tercile version: pre-period usage bins based on all XXX
#   XV and XNXX combined into one "Substitutes to XV or XNXX" segment.
#
# Reads: data/intermediate/normalized_het_results.rds
# Writes: output/analysis/normalized_het/fig1_{ph,xxx}_tercile_{st,lt}.png

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

PALETTE <- c("#8c1515", "#0B3954", "#9a8873", "#b4adea", "#d0d0d0")
names(PALETTE) <- c("maroon", "navy", "tan", "lavender", "gray")

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
      strip.text.y.right  = element_text(angle = 0, hjust = 0, size = 10),
      legend.position     = "bottom",
      legend.key.size     = unit(0.45, "cm"),
      legend.text         = element_text(size = 10)
    )
}

# ============================================================================
# LOAD AND NORMALIZE
# ============================================================================

inp    <- readRDS(file.path(out_int_dir, "normalized_het_results.rds"))
res_df <- inp$res_df

out_dir <- file.path(out_base, "normalized_het")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

ph_res <- res_df |>
  filter(site == "PH") |>
  transmute(group,
            ey0_st = ybar_st - beta_st,
            ey0_lt = ybar_lt - beta_lt)

norm_df <- res_df |>
  left_join(ph_res, by = "group") |>
  mutate(norm_st = beta_st / ey0_st,
         norm_lt = beta_lt / ey0_lt)

wide <- norm_df |>
  select(site, group, norm_st, norm_lt) |>
  pivot_wider(names_from = site, values_from = c(norm_st, norm_lt)) |>
  left_join(ph_res, by = "group") |>
  mutate(
    frac_st  = 1 + norm_st_PH,
    frac_lt  = 1 + norm_lt_PH,
    sub_st   = norm_st_XV + norm_st_XNXX,   # combined substitution
    sub_lt   = norm_lt_XV + norm_lt_XNXX,
    gone_st  = -norm_st_PH - sub_st,
    gone_lt  = -norm_lt_PH - sub_lt
  )

# ============================================================================
# GROUP METADATA
# ============================================================================

# Clean labels for y-axis
LABELS <- c(
  "Full sample"      = "Full sample",
  "PH bin 0"         = "Non-visitor",
  "PH bin 1 (low)"   = "Low (bin 1)",
  "PH bin 2 (mid)"   = "Mid (bin 2)",
  "PH bin 3 (high)"  = "High (bin 3)",
  "XXX bin 0"        = "Non-visitor",
  "XXX bin 1 (low)"  = "Low (bin 1)",
  "XXX bin 2 (mid)"  = "Mid (bin 2)",
  "XXX bin 3 (high)" = "High (bin 3)",
  "Age 18-34"        = "18\u201334",
  "Age 35-54"        = "35\u201354",
  "Age 55+"          = "55+",
  "Income: low"      = "Low",
  "Income: mid"      = "Mid",
  "Income: high"     = "High",
  "Kids: no"         = "No",
  "Kids: yes"        = "Yes",
  "VPN user: no"     = "No",
  "VPN user: yes"    = "Yes",
  "allVPN user: no"  = "No",
  "allVPN user: yes" = "Yes"
)

# Characteristic grouping (strip labels) — two versions
CHAR_PH <- c(
  "Full sample"      = "All",
  "PH bin 0"         = "PH usage (pre-law)",
  "PH bin 1 (low)"   = "PH usage (pre-law)",
  "PH bin 2 (mid)"   = "PH usage (pre-law)",
  "PH bin 3 (high)"  = "PH usage (pre-law)",
  "Age 18-34"        = "Age",
  "Age 35-54"        = "Age",
  "Age 55+"          = "Age",
  "Income: low"      = "Income",
  "Income: mid"      = "Income",
  "Income: high"     = "Income",
  "Kids: no"         = "Children",
  "Kids: yes"        = "Children",
  "VPN user: no"     = "VPNclean",
  "VPN user: yes"    = "VPNclean",
  "allVPN user: no"  = "allVPN",
  "allVPN user: yes" = "allVPN"
)

CHAR_XXX <- c(
  "Full sample"      = "All",
  "XXX bin 0"        = "XXX usage (pre-law)",
  "XXX bin 1 (low)"  = "XXX usage (pre-law)",
  "XXX bin 2 (mid)"  = "XXX usage (pre-law)",
  "XXX bin 3 (high)" = "XXX usage (pre-law)",
  "Age 18-34"        = "Age",
  "Age 35-54"        = "Age",
  "Age 55+"          = "Age",
  "Income: low"      = "Income",
  "Income: mid"      = "Income",
  "Income: high"     = "Income",
  "Kids: no"         = "Children",
  "Kids: yes"        = "Children",
  "VPN user: no"     = "VPNclean",
  "VPN user: yes"    = "VPNclean",
  "allVPN user: no"  = "allVPN",
  "allVPN user: yes" = "allVPN"
)

CHAR_LEVELS_PH  <- c("All", "PH usage (pre-law)",  "Age", "Income", "Children", "VPNclean", "allVPN")
CHAR_LEVELS_XXX <- c("All", "XXX usage (pre-law)", "Age", "Income", "Children", "VPNclean", "allVPN")

seg_colors <- c(
  "Remains on PH"          = PALETTE[["maroon"]],
  "Substitutes to XV or XNXX" = PALETTE[["navy"]],
  "Disappears"             = PALETTE[["gray"]]
)

# ============================================================================
# FIGURE 1: stacked decomposition bar
# ============================================================================

make_fig1 <- function(period = "ST", usage_var = "PH") {
  sfx      <- tolower(period)
  char_map <- if (usage_var == "PH") CHAR_PH else CHAR_XXX
  char_lvl <- if (usage_var == "PH") CHAR_LEVELS_PH else CHAR_LEVELS_XXX

  # Groups shown in this version
  usage_groups <- if (usage_var == "PH") {
    c("Full sample", "PH bin 0", "PH bin 1 (low)", "PH bin 2 (mid)", "PH bin 3 (high)",
      "Age 18-34", "Age 35-54", "Age 55+",
      "Income: low", "Income: mid", "Income: high",
      "Kids: no", "Kids: yes",
      "VPN user: no", "VPN user: yes",
      "allVPN user: no", "allVPN user: yes")
  } else {
    c("Full sample", "XXX bin 0", "XXX bin 1 (low)", "XXX bin 2 (mid)", "XXX bin 3 (high)",
      "Age 18-34", "Age 35-54", "Age 55+",
      "Income: low", "Income: mid", "Income: high",
      "Kids: no", "Kids: yes",
      "VPN user: no", "VPN user: yes",
      "allVPN user: no", "allVPN user: yes")
  }

  decomp <- wide |>
    filter(group %in% usage_groups) |>
    transmute(
      group,
      `Remains on PH`             = if (sfx == "st") frac_st else frac_lt,
      `Substitutes to XV or XNXX` = if (sfx == "st") sub_st  else sub_lt,
      `Disappears`                = pmax(0, if (sfx == "st") gone_st else gone_lt)
    ) |>
    pivot_longer(-group, names_to = "component", values_to = "value") |>
    mutate(
      component   = factor(component,
                           levels = c("Remains on PH",
                                      "Substitutes to XV or XNXX",
                                      "Disappears")),
      group_label = factor(LABELS[group],
                           levels = rev(unique(LABELS[usage_groups]))),
      char        = factor(char_map[group], levels = char_lvl)
    )

  period_label <- if (period == "ST") "Short-run (\u03c4\u2009=\u20090\u20133 weeks)" else
                                       "Long-run (\u03c4\u2009=\u20094\u20138 weeks)"

  ggplot(decomp, aes(x = value, y = group_label, fill = component)) +
    geom_col(orientation = "y", width = 0.65) +
    geom_vline(xintercept = 0, linewidth = 0.5, color = "gray30") +
    facet_grid(char ~ ., scales = "free_y", space = "free_y") +
    scale_x_continuous(
      labels = scales::percent_format(accuracy = 1),
      breaks = seq(-0.25, 1.25, 0.25)
    ) +
    scale_y_discrete() +
    scale_fill_manual(values = seg_colors, name = NULL) +
    labs(
      title = sprintf("What Happens to Pornhub Minutes After A Shock \u2014 %s",
                      period_label),
      x = "Fraction of counterfactual non-treated consumption",
      y = NULL
    ) +
    theme_house()
}

for (usage_var in c("PH", "XXX")) {
  for (period in c("ST", "LT")) {
    p    <- make_fig1(period, usage_var)
    slug <- tolower(sprintf("fig1_%s_tercile_%s", usage_var, period))
    path <- file.path(out_dir, paste0(slug, ".png"))
    ggsave(path, p, width = 9, height = 7, dpi = 300)
    cat(sprintf("Fig 1 (%s tercile, %s): %s\n", usage_var, period, path))
  }
}

cat("\nAll figures done.\n")
