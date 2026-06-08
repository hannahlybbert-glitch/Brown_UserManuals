# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-04-27; Updated: 2026-05-04
# Purpose: Run regressions for multi-site heterogeneity combined dot plot.
#   Sites: Pornhub, xVideos, XNXX, Other XXX (combined), All XXX (5 sites).
#   Subgroups: 3 age, 4 gender, 2 device, 3 income, 2 children, 2 state,
#              4 XXX tercile, 4 PH tercile = 24 subgroups, 120 regressions.
#   Normalization: beta / baseline_mean_treat (treatment group, τ = −4 to −1).
#
# Requires: data/intermediate.../stacked_panel.rds
#           data/intermediate.../xxx_win_wide.rds
#
# Saves: output/.../intermediate/het_multisite_results.rds

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(fixest)
  library(here)
  library(knitr)
  library(tidyr)
})

source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

t_global <- proc.time()

# ============================================================================
# LOAD SHARED DATA
# ============================================================================

cat("Loading stacked panel... ")
t0 <- proc.time()
sp              <- readRDS(file.path(int_dir, "stacked_panel.rds"))
stacked_base    <- sp$stacked_base
needed_weeks    <- sp$needed_weeks
needed_machines <- sp$needed_machines
qualifying      <- sp$qualifying
n_clusters      <- sp$n_clusters
rm(sp)
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

if (!is.null(MOBILE_FILTER)) {
  stacked_base <- stacked_base |> filter(mobile == MOBILE_FILTER)
  cat(sprintf("  MOBILE_FILTER=%d applied: %s rows remaining\n",
      MOBILE_FILTER, format(nrow(stacked_base), big.mark = ",")))
}

laws           <- read.csv(ph_shutdown_file, stringsAsFactors = FALSE, na.strings = c("", "NA"))
treated_states <- unique(laws$state[!is.na(laws$state)])

cat("Loading xxx_win_wide... ")
t0 <- proc.time()
xxx_win_wide <- readRDS(file.path(int_dir, "xxx_win_wide.rds"))
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# BUILD SUBGROUP COVARIATES
# ============================================================================

cat("\nBuilding subgroup covariates... ")
t0 <- proc.time()

base_covs <- stacked_base |>
  mutate(
    age_bin3 = case_when(
      hoh_age == "18-24"                                ~ "18-24",
      hoh_age %in% c("25-34", "35-44")                 ~ "25-44",
      hoh_age %in% c("45-54", "55-64", "65 and Over")  ~ "45+",
      TRUE                                              ~ NA_character_
    ),
    inc_bin3 = case_when(
      hh_income %in% c("HHI:Less than 25k", "HHI:25k-39k", "HHI:40k-59k") ~ "<$60k",
      hh_income %in% c("HHI:60k-74k", "HHI:75k-99k")                      ~ "$60k-$99k",
      hh_income == "HHI:100k+"                                              ~ "$100k+",
      TRUE                                                                  ~ NA_character_
    ),
    treated_state = if_else(state %in% treated_states, "Treated", "Non-Treated"),
    kids          = as.integer(children_present == "Children:Yes")
  )

cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# PRE-PERIOD USAGE TERCILES  (τ = −16 to −1)
# ============================================================================

TERCILE_WINDOW <- -16:-1

cat("Computing pre-period usage terciles... ")
t0 <- proc.time()

preperiod_mw <- stacked_base |>
  dplyr::filter(rel_week %in% TERCILE_WINDOW) |>
  dplyr::distinct(machine_id, week_of_sample)

tercile_stats <- xxx_win_wide |>
  dplyr::semi_join(preperiod_mw, by = c("machine_id", "week_of_sample")) |>
  dplyr::group_by(machine_id) |>
  dplyr::summarise(
    ph_pre_avg  = mean(win_PORNHUB_COM, na.rm = TRUE),
    xxx_pre_avg = mean(win_min_allxxx,  na.rm = TRUE),
    .groups = "drop"
  )

# Machines absent from xxx_win_wide during pre-period get 0
tercile_data <- dplyr::distinct(stacked_base, machine_id) |>
  dplyr::left_join(tercile_stats, by = "machine_id") |>
  dplyr::mutate(
    ph_pre_avg  = dplyr::coalesce(ph_pre_avg,  0),
    xxx_pre_avg = dplyr::coalesce(xxx_pre_avg, 0),
    ph_tercile  = c("PH Tercile: Light", "PH Tercile: Moderate", "PH Tercile: Heavy")[
                    dplyr::ntile(dplyr::if_else(ph_pre_avg > 0, ph_pre_avg, NA_real_), 3)],
    xxx_tercile = c("XXX Tercile: Light", "XXX Tercile: Moderate", "XXX Tercile: Heavy")[
                    dplyr::ntile(dplyr::if_else(xxx_pre_avg > 0, xxx_pre_avg, NA_real_), 3)]
  )

base_covs <- base_covs |>
  dplyr::left_join(
    dplyr::select(tercile_data, machine_id, ph_tercile, xxx_tercile, ph_pre_avg, xxx_pre_avg),
    by = "machine_id"
  )
rm(preperiod_mw, tercile_stats, tercile_data)

cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# SUBGROUP DEFINITIONS
# ============================================================================

subgroups <- list(
  # Age (3)
  "Age: 18-24"            = quote(age_bin3 == "18-24"),
  "Age: 25-44"            = quote(age_bin3 == "25-44"),
  "Age: 45+"              = quote(age_bin3 == "45+"),
  # Gender (4)
  "Gender: Male"          = quote(gender == "Male"),
  "Gender: Female"        = quote(gender == "Female"),
  "Gender: Shared"        = quote(gender == "Shared"),
  "Gender: Unknown"       = quote(gender == "Unknown"),
  # Device type (2)
  "Device: Desktop"       = quote(mobile == 0L),
  "Device: Mobile"        = quote(mobile == 1L),
  # Income (3)
  "Income: <$60k"         = quote(inc_bin3 == "<$60k"),
  "Income: $60k-$99k"     = quote(inc_bin3 == "$60k-$99k"),
  "Income: $100k+"        = quote(inc_bin3 == "$100k+"),
  # Children in Desktop (2)
  "Children in Desktop: Yes" = quote(mobile == 0L & kids == 1L),
  "Children in Desktop: No"  = quote(mobile == 0L & kids == 0L),
  # State (2)
  "State: Treated"        = quote(treated_state == "Treated"),
  "State: Non-Treated"    = quote(treated_state == "Non-Treated"),
  # All-XXX pre-period usage terciles (τ = −16 to −1)
  "XXX Non Visitor"       = quote(xxx_pre_avg == 0),
  "XXX Tercile: Light"    = quote(xxx_tercile == "XXX Tercile: Light"),
  "XXX Tercile: Moderate" = quote(xxx_tercile == "XXX Tercile: Moderate"),
  "XXX Tercile: Heavy"    = quote(xxx_tercile == "XXX Tercile: Heavy"),
  # PH pre-period usage terciles (τ = −16 to −1)
  "PH Non Visitor"        = quote(ph_pre_avg == 0),
  "PH Tercile: Light"     = quote(ph_tercile == "PH Tercile: Light"),
  "PH Tercile: Moderate"  = quote(ph_tercile == "PH Tercile: Moderate"),
  "PH Tercile: Heavy"     = quote(ph_tercile == "PH Tercile: Heavy")
)

BASELINE_WINDOW <- -4:-1

TARGET_KEYS <- c("PORNHUB.COM", "XVIDEOS.COM", "XNXX.COM",
                 "other_xxx_combined", "all_xxx")
TARGET_SITES <- SITES_FULL[sapply(SITES_FULL, `[[`, "key") %in% TARGET_KEYS]

# ============================================================================
# MAIN LOOP: site × subgroup
# ============================================================================

results <- list()
n_total <- length(TARGET_SITES) * length(subgroups)
n_done  <- 0L

for (site in TARGET_SITES) {
  cat(sprintf("\n%s  [%s]\n", strrep("=", 50), site$label))

  cat(sprintf("  Loading duration data... "))
  t0       <- proc.time()
  dur_data <- load_site_duration(site$key)
  cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

  cat(sprintf("  Attaching DVs... "))
  t0      <- proc.time()
  df_site <- base_covs |>
    left_join(dur_data, by = c("machine_id", "week_of_sample")) |>
    attach_dvs(site$key, xxx_win_wide)
  rm(dur_data)
  cat(sprintf("%.1fs  (%s rows)\n",
              (proc.time() - t0)[["elapsed"]],
              format(nrow(df_site), big.mark = ",")))

  for (sg_name in names(subgroups)) {
    n_done <- n_done + 1L
    cat(sprintf("  [%d/%d] %-22s ", n_done, n_total, sg_name))

    expr <- subgroups[[sg_name]]
    df_g <- df_site |> filter(!!expr)

    n_treated <- n_distinct(df_g$machine_id[df_g$treated == 1L])

    if (n_treated < 10L) {
      cat(sprintf("SKIPPED (n_treated=%d too small)\n", n_treated))
      next
    }

    baseline_mean_treat <- mean(
      df_g$win_min[df_g$treated == 1L & df_g$rel_week %in% BASELINE_WINDOW],
      na.rm = TRUE
    )

    t0      <- proc.time()
    res     <- run_pooled(df_g, "win_min")
    elapsed <- (proc.time() - t0)[["elapsed"]]

    cat(sprintf("n=%s  beta_ST=%+.4f  beta_LT=%+.4f  base=%.4f  (%.1fs)\n",
                format(n_treated, big.mark = ","),
                coalesce(res$beta_shortterm, NA_real_),
                coalesce(res$beta_longterm,  NA_real_),
                baseline_mean_treat,
                elapsed))

    results[[paste(site$slug, sg_name, sep = "|||")]] <- list(
      site                = site$label,
      site_slug           = site$slug,
      group               = sg_name,
      n_mach              = n_treated,
      beta_st             = res$beta_shortterm,
      se_st               = res$se_shortterm,
      beta_lt             = res$beta_longterm,
      se_lt               = res$se_longterm,
      p_lt                = res$p_longterm,
      baseline_mean_treat = baseline_mean_treat
    )
  }

  rm(df_site); gc()
}

res_df <- dplyr::bind_rows(lapply(results, as.data.frame))

# ============================================================================
# TOP-25 COMBINED GROUP HET REGRESSIONS
# other_compliant and other_noncompliant_top25 from prepare_top25.R wide tables.
# These results feed the circumvention and substitution het figures.
# ============================================================================

TOP25_COMBINED <- list(
  list(
    slug     = "other_compliant",
    label    = "Other Compliant",
    rds_path = file.path(here::here(), "data", "intermediate_combined",
                         "top25_other_compliant_win_wide.rds"),
    win_col  = "win_other_compliant"
  ),
  list(
    slug     = "other_noncompliant_top25",
    label    = "Other Noncompliant Top 25",
    rds_path = file.path(here::here(), "data", "intermediate_combined",
                         "top25_other_noncompliant_win_wide.rds"),
    win_col  = "win_other_noncompliant_top25"
  )
)

top25_results <- list()
n_total_top25 <- length(TOP25_COMBINED) * length(subgroups)
n_done_top25  <- 0L

for (tc in TOP25_COMBINED) {
  cat(sprintf("\n%s  [%s]\n", strrep("=", 50), tc$label))

  cat("  Loading top25 wide table... ")
  t0       <- proc.time()
  win_wide <- readRDS(tc$rds_path)
  cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

  cat("  Building df_site... ")
  t0      <- proc.time()
  df_site <- base_covs |>
    left_join(
      select(win_wide, machine_id, week_of_sample, win_min = all_of(tc$win_col)),
      by = c("machine_id", "week_of_sample")
    ) |>
    mutate(win_min = coalesce(win_min, 0))
  rm(win_wide); gc()
  cat(sprintf("%.1fs  (%s rows)\n",
              (proc.time() - t0)[["elapsed"]],
              format(nrow(df_site), big.mark = ",")))

  for (sg_name in names(subgroups)) {
    n_done_top25 <- n_done_top25 + 1L
    cat(sprintf("  [%d/%d] %-22s ", n_done_top25, n_total_top25, sg_name))

    expr <- subgroups[[sg_name]]
    df_g <- df_site |> filter(!!expr)

    n_treated <- n_distinct(df_g$machine_id[df_g$treated == 1L])

    if (n_treated < 10L) {
      cat(sprintf("SKIPPED (n_treated=%d too small)\n", n_treated))
      next
    }

    baseline_mean_treat <- mean(
      df_g$win_min[df_g$treated == 1L & df_g$rel_week %in% BASELINE_WINDOW],
      na.rm = TRUE
    )

    t0      <- proc.time()
    res     <- run_pooled(df_g, "win_min")
    elapsed <- (proc.time() - t0)[["elapsed"]]

    cat(sprintf("n=%s  beta_ST=%+.4f  beta_LT=%+.4f  base=%.4f  (%.1fs)\n",
                format(n_treated, big.mark = ","),
                coalesce(res$beta_shortterm, NA_real_),
                coalesce(res$beta_longterm,  NA_real_),
                baseline_mean_treat,
                elapsed))

    top25_results[[paste(tc$slug, sg_name, sep = "|||")]] <- list(
      site                = tc$label,
      site_slug           = tc$slug,
      group               = sg_name,
      n_mach              = n_treated,
      beta_st             = res$beta_shortterm,
      se_st               = res$se_shortterm,
      beta_lt             = res$beta_longterm,
      se_lt               = res$se_longterm,
      p_lt                = res$p_longterm,
      baseline_mean_treat = baseline_mean_treat
    )
  }

  rm(df_site); gc()
}

top25_res_df <- dplyr::bind_rows(lapply(top25_results, as.data.frame))
res_df       <- dplyr::bind_rows(res_df, top25_res_df)

# ============================================================================
# DIFFERENCE TESTS  (interacted TWFE, fully saturated FEs)
# ============================================================================

diff_pairs <- list(
  list(label = "Age: 18-24 vs 25-44",
       g1    = quote(age_bin3 == "18-24"),
       g0    = quote(age_bin3 == "25-44")),
  list(label = "Age: 18-24 vs 45+",
       g1    = quote(age_bin3 == "18-24"),
       g0    = quote(age_bin3 == "45+")),
  list(label = "Children in Desktop: Yes vs No",
       g1    = quote(mobile == 0L & kids == 1L),
       g0    = quote(mobile == 0L & kids == 0L))
)

diff_results <- list()

for (site in TARGET_SITES) {
  cat(sprintf("\nDiff tests — %s\n", site$label))

  dur_data <- load_site_duration(site$key)
  df_site  <- base_covs |>
    left_join(dur_data, by = c("machine_id", "week_of_sample")) |>
    attach_dvs(site$key, xxx_win_wide)
  rm(dur_data)

  for (pair in diff_pairs) {
    cat(sprintf("  %s ... ", pair$label))
    t0  <- proc.time()
    res <- run_diff_test(df_site, "win_min", pair$g1, pair$g0)
    cat(sprintf("diff_LT=%+.4f  p_LT=%.3f  (%.1fs)\n",
                coalesce(res$beta_diff_lt, NA_real_),
                coalesce(res$p_diff_lt,    NA_real_),
                (proc.time() - t0)[["elapsed"]]))

    diff_results[[paste(site$slug, pair$label, sep = "|||")]] <- c(
      list(site = site$label, site_slug = site$slug, comparison = pair$label),
      res
    )
  }

  rm(df_site); gc()
}

diff_df <- dplyr::bind_rows(lapply(diff_results, as.data.frame))

# ============================================================================
# DIFF TEST P-VALUE TABLES
# ============================================================================

stars <- function(p) dplyr::case_when(
  is.na(p) ~ "", p < 0.01 ~ "***", p < 0.05 ~ "**", p < 0.10 ~ "*", TRUE ~ ""
)

SITE_LABELS <- c("Pornhub", "xVideos", "XNXX", "Other XXX", "All XXX")
site_recode <- c(
  "Pornhub"              = "Pornhub",
  "xVideos"              = "xVideos",
  "XNXX"                 = "XNXX",
  "Other XXX (combined)" = "Other XXX",
  "All XXX (pooled)"     = "All XXX"
)

diff_wide <- diff_df |>
  dplyr::mutate(
    site_label = dplyr::recode(site, !!!site_recode),
    cell = ifelse(is.na(p_diff_lt), "—",
                  sprintf("%.4f%s\n(%.4f)", beta_diff_lt, stars(p_diff_lt), p_diff_lt))
  ) |>
  dplyr::select(comparison, site_label, cell) |>
  tidyr::pivot_wider(names_from = site_label, values_from = cell, values_fill = "—") |>
  dplyr::select(Comparison = comparison, dplyr::any_of(SITE_LABELS))

out_dir_tables <- file.path(out_base, "heterogeneity_plots")
dir.create(out_dir_tables, recursive = TRUE, showWarnings = FALSE)

diff_note <- paste0(
  "Interacted TWFE difference test. Each group's outcome normalized by its own baseline mean ",
  "(treatment group, tau = -4 to -1). ",
  "Cell: beta_diff_LT / p-value. SE clustered by state. * p<0.10, ** p<0.05, *** p<0.01."
)

diff_md_path  <- file.path(out_dir_tables, "het_diff_pvals.md")
diff_tex_path <- file.path(out_dir_tables, "het_diff_pvals.tex")

writeLines(
  c("# Heterogeneity Difference Tests — Long-term ATT", "", diff_note, "",
    kable(diff_wide, format = "markdown", row.names = FALSE)),
  diff_md_path
)
cat(sprintf("Wrote: %s\n", diff_md_path))

writeLines(
  kable(diff_wide, format = "latex", booktabs = TRUE, row.names = FALSE),
  diff_tex_path
)
cat(sprintf("Wrote: %s\n", diff_tex_path))

# ============================================================================
# SAVE
# ============================================================================

out <- list(
  res_df    = res_df,
  diff_df   = diff_df,
  subgroups = names(subgroups),
  sites     = TARGET_SITES
)

out_path <- file.path(out_int_dir, "het_multisite_results.rds")
saveRDS(out, out_path)

cat(sprintf("\nSaved: %s\n", out_path))
cat(sprintf("Total elapsed: %.1fs\n", (proc.time() - t_global)[["elapsed"]]))
