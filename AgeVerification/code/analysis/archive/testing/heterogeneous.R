# Author: Matt Brown, assisted by Claude
# Created: 2026-03-06
# Purpose: Demographic and past-usage heterogeneity in stacked TWFE event study.
#          Merges event_study_demographics.R + event_study_past_usage.R.
#
# Requires: data/intermediate/stacked_panel.rds, data/intermediate/xxx_win_wide.rds
#           stacked_base already contains gender, hoh_age, children_present.
#
# Subgroups (demographic):
#   all / male / female / young_hoh (18-34) / older_hoh (35+) /
#   children_yes / children_no / xxx_active
# Subgroups (past-usage):
#   sub_users (any XV or XNXX in pre) / no_sub (XXX-active, no subs) /
#   no_xxx (no pre-period XXX)
#
# Sites: all_xxx + 6 individual XXX + 2 VPN (9 total)
#
# Usage:
#   Rscript code/analysis/heterogeneous.R
#
# Outputs:
#   output/analysis/event_study_subgroups/{slug}_{sg}_over60.png
#   output/analysis/event_study_subgroups/past_usage/{slug}_{sg}_win_min.png
#   output/analysis/heterogeneity_table_over60.md
#   output/analysis/heterogeneity_table_win_min.md
#   output/analysis/heterogeneity_table_past_usage_over60.md
#   output/analysis/heterogeneity_table_past_usage_win_min.md

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

cat(sprintf("  Stacked: %s rows | %d clusters | %d cohorts | demo cols: %s\n",
    format(nrow(stacked_base), big.mark = ","), n_clusters, length(qualifying),
    paste(intersect(c("gender", "hoh_age", "children_present"), names(stacked_base)),
          collapse = ", ")))

# ============================================================================
# OUTPUT DIRS
# ============================================================================

out_subgroups     <- file.path(project_root, "output", "analysis", "event_study_subgroups")
out_past_usage    <- file.path(out_subgroups, "past_usage")
out_tables        <- file.path(project_root, "output", "analysis")
dir.create(out_subgroups,  recursive = TRUE, showWarnings = FALSE)
dir.create(out_past_usage, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# BUILD SUBGROUP MEMBERSHIP SETS (once, from xxx_win_wide + stacked_base)
# ============================================================================

cat("\nBuilding subgroup membership sets...\n")
t0 <- proc.time()

pre_mc <- stacked_base |>
  filter(rel_week < 0L) |>
  select(machine_id, week_of_sample, machine_cohort)

# xxx_active: any XXX visit (win_min_allxxx > 0) in pre-period
xxx_active_mcs <- pre_mc |>
  left_join(select(xxx_win_wide, machine_id, week_of_sample, win_min_allxxx),
            by = c("machine_id", "week_of_sample")) |>
  group_by(machine_cohort) |>
  summarise(any_xxx = any(!is.na(win_min_allxxx) & win_min_allxxx > 0),
            .groups = "drop") |>
  filter(any_xxx) |>
  pull(machine_cohort)

# sub_users: any XV or XNXX minutes > 0 in pre-period
sub_users_mcs <- pre_mc |>
  left_join(select(xxx_win_wide, machine_id, week_of_sample,
                   win_XVIDEOS_COM, win_XNXX_COM),
            by = c("machine_id", "week_of_sample")) |>
  group_by(machine_cohort) |>
  summarise(
    sub_tot = sum(coalesce(win_XVIDEOS_COM, 0) + coalesce(win_XNXX_COM, 0)),
    .groups = "drop"
  ) |>
  filter(sub_tot > 0) |>
  pull(machine_cohort)

no_sub_mcs <- setdiff(xxx_active_mcs, sub_users_mcs)
no_xxx_mcs <- setdiff(unique(stacked_base$machine_cohort), xxx_active_mcs)
rm(pre_mc)

cat(sprintf("  xxx-active:              %s machine×cohort\n",
    format(length(xxx_active_mcs), big.mark = ",")))
cat(sprintf("  Sub-users (XV/XNXX>0):   %s\n",
    format(length(sub_users_mcs), big.mark = ",")))
cat(sprintf("  XXX-active, no subs:     %s\n",
    format(length(no_sub_mcs), big.mark = ",")))
cat(sprintf("  No XXX at all:           %s  (%.1fs)\n",
    format(length(no_xxx_mcs), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# SUBGROUP DEFINITIONS
# ============================================================================

DEMO_SUBGROUPS <- list(
  list(id = "all",          label = "All machines",
       fn = function(df) df),
  list(id = "male",         label = "Male",
       fn = function(df) filter(df, gender == "Male")),
  list(id = "female",       label = "Female",
       fn = function(df) filter(df, gender == "Female")),
  list(id = "young_hoh",    label = "Young HoH (18-34)",
       fn = function(df) filter(df, hoh_age %in% c("18-24", "25-34"))),
  list(id = "older_hoh",    label = "Older HoH (35+)",
       fn = function(df) filter(df, hoh_age %in%
                                  c("35-44", "45-54", "55-64", "65 and Over"))),
  list(id = "children_yes", label = "Children present",
       fn = function(df) filter(df, children_present == "Children:Yes")),
  list(id = "children_no",  label = "No children",
       fn = function(df) filter(df, children_present == "Children:No")),
  list(id = "xxx_active",   label = "XXX-active (pre-period)",
       fn = function(df) filter(df, machine_cohort %in% xxx_active_mcs))
)

PAST_SUBGROUPS <- list(
  list(id = "sub",    label = "Any substitute usage (XV or XNXX)",
       fn = function(df) filter(df, machine_cohort %in% sub_users_mcs)),
  list(id = "no_sub", label = "XXX-active, no substitute usage",
       fn = function(df) filter(df, machine_cohort %in% no_sub_mcs)),
  list(id = "no_xxx", label = "No past XXX usage",
       fn = function(df) filter(df, machine_cohort %in% no_xxx_mcs))
)

# Part A event-study plots: demographic subgroups (male/female/xxx_active) + past-usage (all 3)
DEMO_PLOT_SUBGROUPS <- DEMO_SUBGROUPS[sapply(DEMO_SUBGROUPS, `[[`, "id") %in%
                                        c("male", "female", "xxx_active")]

# ============================================================================
# SITES  (7 XXX + 2 VPN)
# ============================================================================

SITES <- list(
  list(key = "all_xxx",         label = "All XXX",    slug = "all_xxx"),
  list(key = "PORNHUB.COM",     label = "Pornhub",    slug = "PORNHUB_COM"),
  list(key = "XVIDEOS.COM",     label = "xVideos",    slug = "XVIDEOS_COM"),
  list(key = "XHAMSTER.COM",    label = "xHamster",   slug = "XHAMSTER_COM"),
  list(key = "XNXX.COM",        label = "XNXX",       slug = "XNXX_COM"),
  list(key = "CHATURBATE.COM",  label = "Chaturbate", slug = "CHATURBATE_COM"),
  list(key = "other_XXX_sites", label = "Other XXX",  slug = "other_XXX")
  # list(key = "VPN_clean",    label = "VPN (clean)", slug = "VPN_clean"),  # parquet not on this machine
  # list(key = "allVPN",       label = "All VPN",     slug = "allVPN")       # parquet not on this machine
)

# ============================================================================
# RESULT STORAGE
# ============================================================================

dvs         <- c("over60", "win_min")
site_labels <- sapply(SITES, `[[`, "label")

make_results_mat <- function(subgroups) {
  sg_labels <- sapply(subgroups, `[[`, "label")
  lapply(dvs, function(dv) {
    make_mat <- function()
      matrix(NA_character_, nrow = length(subgroups), ncol = length(SITES),
             dimnames = list(sg_labels, site_labels))
    list(ST = make_mat(), LT = make_mat(), PRE = make_mat())
  }) |> setNames(dvs)
}

demo_results <- make_results_mat(DEMO_SUBGROUPS)
past_results <- make_results_mat(PAST_SUBGROUPS)

# ============================================================================
# MAIN LOOP — 9 sites
# ============================================================================

cat("\n", strrep("=", 60), "\n", sep = "")
cat("Running regressions: 9 sites\n")
cat(strrep("=", 60), "\n\n", sep = "")

for (s_idx in seq_along(SITES)) {
  site <- SITES[[s_idx]]
  cat(sprintf("--- %s (%s) ---\n", site$label, site$key))

  t0       <- proc.time()
  dur_data <- load_site_duration(site$key)
  cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
      format(nrow(dur_data), big.mark = ","),
      (proc.time() - t0)[["elapsed"]]))

  df_site <- stacked_base |>
    left_join(dur_data, by = c("machine_id", "week_of_sample"))
  rm(dur_data)
  df_site <- attach_dvs(df_site, site$key, xxx_win_wide)

  # ---- Part A: Demographic event-study plots (over60) ----
  cat("  Part A — demographic event studies (over60)\n")
  for (sg in DEMO_PLOT_SUBGROUPS) {
    df_g  <- sg$fn(df_site)
    n_cl  <- n_distinct(df_g$state)
    b_mean <- mean(df_g$over60[df_g$treated == 1L & df_g$rel_week == -1L], na.rm = TRUE)
    cat(sprintf("    %s: N=%s, %d clusters\n",
        sg$label, format(nrow(df_g), big.mark = ","), n_cl))
    tryCatch({
      fit   <- feols(over60 ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week,
                     data = df_g, cluster = ~state, warn = FALSE, notes = FALSE)
      coefs <- extract_coefs(fit)
      path  <- save_event_study_plot(
        coefs, site$label, sg$label, "Change in Pr(>60s)",
        site$slug, paste0(sg$id, "_over60"), out_subgroups,
        baseline_mean = b_mean, n_clusters = n_cl)
      cat(sprintf("      → %s\n", path))
    }, error = function(e) {
      cat(sprintf("    ERROR (%s): %s\n", sg$label, conditionMessage(e)))
    })
  }

  # ---- Part A: Past-usage event-study plots (win_min) ----
  cat("  Part A — past-usage event studies (win_min)\n")
  for (sg in PAST_SUBGROUPS) {
    df_g  <- sg$fn(df_site)
    n_cl  <- n_distinct(df_g$state)
    b_mean <- mean(df_g$win_min[df_g$treated == 1L & df_g$rel_week == -1L], na.rm = TRUE)
    cat(sprintf("    %s: N=%s, %d clusters\n",
        sg$label, format(nrow(df_g), big.mark = ","), n_cl))
    tryCatch({
      fit   <- feols(win_min ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week,
                     data = df_g, cluster = ~state, warn = FALSE, notes = FALSE)
      coefs <- extract_coefs(fit)
      path  <- save_event_study_plot(
        coefs, site$label, sg$label, "Change in winsorized min/week",
        site$slug, paste0(sg$id, "_win_min"), out_past_usage,
        baseline_mean = b_mean, n_clusters = n_cl)
      cat(sprintf("      → %s\n", path))
    }, error = function(e) {
      cat(sprintf("    ERROR (%s): %s\n", sg$label, conditionMessage(e)))
    })
  }

  # ---- Part B: Pooled ATTs — demographic subgroups ----
  cat("  Part B — pooled ATTs (demographic)\n")
  for (dv in dvs) {
    for (sg_idx in seq_along(DEMO_SUBGROUPS)) {
      sg    <- DEMO_SUBGROUPS[[sg_idx]]
      df_sg <- sg$fn(df_site)
      cat(sprintf("    %s / %-28s N=%s\n",
          dv, sg$label, format(nrow(df_sg), big.mark = ",")))
      res <- run_pooled(df_sg, dv)
      if (!is.na(res$beta_shortterm)) {
        demo_results[[dv]][["ST"]] [sg_idx, s_idx] <-
          fmt_coef(res$beta_shortterm, res$se_shortterm)
        demo_results[[dv]][["LT"]] [sg_idx, s_idx] <-
          fmt_coef(res$beta_longterm,  res$se_longterm)
        demo_results[[dv]][["PRE"]][sg_idx, s_idx] <-
          fmt_coef(res$beta_pre,       res$se_pre)
      }
    }
  }

  # ---- Part B: Pooled ATTs — past-usage subgroups ----
  cat("  Part B — pooled ATTs (past-usage)\n")
  for (dv in dvs) {
    for (sg_idx in seq_along(PAST_SUBGROUPS)) {
      sg    <- PAST_SUBGROUPS[[sg_idx]]
      df_sg <- sg$fn(df_site)
      cat(sprintf("    %s / %-40s N=%s\n",
          dv, sg$label, format(nrow(df_sg), big.mark = ",")))
      res <- run_pooled(df_sg, dv)
      if (!is.na(res$beta_shortterm)) {
        past_results[[dv]][["ST"]] [sg_idx, s_idx] <-
          fmt_coef(res$beta_shortterm, res$se_shortterm)
        past_results[[dv]][["LT"]] [sg_idx, s_idx] <-
          fmt_coef(res$beta_longterm,  res$se_longterm)
        past_results[[dv]][["PRE"]][sg_idx, s_idx] <-
          fmt_coef(res$beta_pre,       res$se_pre)
      }
    }
  }

  rm(df_site)
  cat("\n")
}

# ============================================================================
# WRITE MARKDOWN TABLES
# ============================================================================

write_md_table <- function(res_mats, title_line, header_line, filepath) {
  sl       <- colnames(res_mats[["ST"]])
  sg       <- rownames(res_mats[["ST"]])
  header   <- paste0("| Estimate | ", paste(sl, collapse = " | "), " |")
  sep_line <- paste0("|", paste(rep(":---|", length(sl) + 1L), collapse = ""))

  make_row <- function(label, mat, sg_name) {
    vals <- mat[sg_name, ]
    vals[is.na(vals)] <- "\u2014"
    paste0("| **", label, "** | ", paste(vals, collapse = " | "), " |")
  }

  content <- c(title_line, "", header_line, "")
  for (s in sg) {
    content <- c(content,
      sprintf("## %s\n", s),
      header, sep_line,
      make_row("\u03b2_ST",  res_mats[["ST"]],  s),
      make_row("\u03b2_LT",  res_mats[["LT"]],  s),
      make_row("\u03b2_pre", res_mats[["PRE"]], s),
      "")
  }
  writeLines(content, filepath)
  cat(sprintf("Wrote: %s\n", filepath))
}

pooled_footer <- paste0(
  "Pooled three-period TWFE: `dv ~ treated:pre + treated:shortterm + treated:longterm",
  " | machine_cohort + cohort_week`. SE clustered by state.  \n",
  "\u03b2_ST: \u03c4 \u2208 [0,3]. \u03b2_LT: \u03c4 \u2208 [4,8].",
  " \u03b2_pre: \u03c4 \u2208 [\u221216,\u22125]. Format: \u03b2 (SE)."
)

past_footer <- paste0(pooled_footer, "  \n",
  "Subgroups: **sub_users** = any XV or XNXX > 0; **no_sub** = any XXX but no XV/XNXX;",
  " **no_xxx** = no XXX at all.")

cat(strrep("=", 60), "\n", sep = "")
cat("Writing tables\n")
cat(strrep("=", 60), "\n\n", sep = "")

write_md_table(
  demo_results[["over60"]],
  "# Heterogeneity Table \u2014 Pr(>60s on site) \u2014 over60",
  pooled_footer,
  file.path(out_tables, "heterogeneity_table_over60.md")
)
write_md_table(
  demo_results[["win_min"]],
  "# Heterogeneity Table \u2014 Winsorized min/machine/week (p95) \u2014 win_min",
  pooled_footer,
  file.path(out_tables, "heterogeneity_table_win_min.md")
)
write_md_table(
  past_results[["over60"]],
  "# Heterogeneity by Past Usage \u2014 Pr(>60s on site) \u2014 over60",
  past_footer,
  file.path(out_tables, "heterogeneity_table_past_usage_over60.md")
)
write_md_table(
  past_results[["win_min"]],
  "# Heterogeneity by Past Usage \u2014 Winsorized min/machine/week (p95) \u2014 win_min",
  past_footer,
  file.path(out_tables, "heterogeneity_table_past_usage_win_min.md")
)

cat("\nAll done.\n")
