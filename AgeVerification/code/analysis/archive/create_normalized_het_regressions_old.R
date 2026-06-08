# Author: Matt Brown, assisted by Claude
# Created: 2026-03-20
# Purpose: Run site × subgroup TWFE regressions for normalized het table.
#   Saves results to data/intermediate/normalized_het_results.rds for use by
#   create_normalized_het_table.R.
#
# Sites: PH, XVideos, XNXX  (3 sites × 13 subgroups = 39 regressions)

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(fixest)
  library(here)
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

# In device-specific combined modes, restrict to one device type.
if (!is.null(MOBILE_FILTER)) {
  stacked_base <- stacked_base |> filter(mobile == MOBILE_FILTER)
  cat(sprintf("  MOBILE_FILTER=%d applied: %s rows remaining\n",
      MOBILE_FILTER, format(nrow(stacked_base), big.mark = ",")))
}

cat("Loading xxx_win_wide... ")
t0 <- proc.time()
xxx_win_wide <- readRDS(file.path(int_dir, "xxx_win_wide.rds"))
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

cat("Loading het_covs... ")
t0 <- proc.time()
het_covs <- readRDS(file.path(int_dir, "het_covs.rds"))
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# BUILD past_ph_bin: 0 = non-visitor; 1/2/3 = terciles of positive PH users
# ============================================================================

cat("\nBuilding past_ph_bin... ")
t0 <- proc.time()
# Use all machine-cohorts as the spine so that cohorts with no PRE_WINDOW rows
# (machines that joined the panel late) get pre_ph = 0 → bin 0 (non-visitor),
# rather than NA which would drop them from all usage-bin regressions.
all_mc <- distinct(stacked_base, machine_cohort)

ph_prewin <- stacked_base |>
  select(machine_cohort, machine_id, week_of_sample, rel_week) |>
  left_join(
    xxx_win_wide |> select(machine_id, week_of_sample, win_PORNHUB_COM),
    by = c("machine_id", "week_of_sample")
  ) |>
  filter(rel_week %in% PRE_WINDOW) |>
  group_by(machine_cohort) |>
  summarize(pre_ph = mean(coalesce(win_PORNHUB_COM, 0), na.rm = TRUE),
            .groups = "drop")

ph_pre_usage <- all_mc |>
  left_join(ph_prewin, by = "machine_cohort") |>
  mutate(pre_ph = coalesce(pre_ph, 0))

pos_vals <- ph_pre_usage |> filter(pre_ph > 0) |> pull(pre_ph)
t_cuts   <- quantile(pos_vals, probs = c(1/3, 2/3))

ph_pre_usage <- ph_pre_usage |>
  mutate(past_ph_bin = case_when(
    pre_ph == 0           ~ 0L,
    pre_ph <= t_cuts[[1]] ~ 1L,
    pre_ph <= t_cuts[[2]] ~ 2L,
    TRUE                  ~ 3L
  ))
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))
cat(sprintf("  Tercile cuts: %.4f min, %.4f min\n", t_cuts[[1]], t_cuts[[2]]))
cat(sprintf("  PH visitors: %s / %s machine-cohorts (%.1f%%)\n",
            format(sum(ph_pre_usage$pre_ph > 0), big.mark = ","),
            format(nrow(ph_pre_usage), big.mark = ","),
            100 * mean(ph_pre_usage$pre_ph > 0)))

# Build past_xxx_tercile: terciles of pre-period all-XXX win_min
cat("\nBuilding past_xxx_tercile... ")
t0 <- proc.time()
xxx_prewin <- stacked_base |>
  select(machine_cohort, machine_id, week_of_sample, rel_week) |>
  left_join(
    xxx_win_wide |> select(machine_id, week_of_sample, win_min_allxxx),
    by = c("machine_id", "week_of_sample")
  ) |>
  filter(rel_week %in% PRE_WINDOW) |>
  group_by(machine_cohort) |>
  summarize(pre_xxx = mean(coalesce(win_min_allxxx, 0), na.rm = TRUE),
            .groups = "drop")

xxx_pre_usage <- all_mc |>
  left_join(xxx_prewin, by = "machine_cohort") |>
  mutate(pre_xxx = coalesce(pre_xxx, 0))

pos_xxx  <- xxx_pre_usage |> filter(pre_xxx > 0) |> pull(pre_xxx)
xxx_cuts <- quantile(pos_xxx, probs = c(1/3, 2/3))

xxx_pre_usage <- xxx_pre_usage |>
  mutate(past_xxx_tercile = case_when(
    pre_xxx == 0             ~ 0L,
    pre_xxx <= xxx_cuts[[1]] ~ 1L,
    pre_xxx <= xxx_cuts[[2]] ~ 2L,
    TRUE                     ~ 3L
  ))
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))
cat(sprintf("  XXX tercile cuts: %.4f min, %.4f min\n", xxx_cuts[[1]], xxx_cuts[[2]]))
cat(sprintf("  XXX visitors: %s / %s machine-cohorts (%.1f%%)\n",
            format(sum(xxx_pre_usage$pre_xxx > 0), big.mark = ","),
            format(nrow(xxx_pre_usage), big.mark = ","),
            100 * mean(xxx_pre_usage$pre_xxx > 0)))

# ============================================================================
# BUILD vpn_pre_* binaries: 1 if machine visited VPN site at least once in PRE_WINDOW
# To add allVPN: copy this block, replace "VPNclean" → "allVPN" and
#   "vpn_pre_clean" → "vpn_pre_all", then join below and add subgroups.
# ============================================================================

build_vpn_pre_binary <- function(vpn_site_key, var_name) {
  cat(sprintf("\nBuilding %s (%s)... ", var_name, vpn_site_key))
  t0 <- proc.time()
  vpn_dur <- load_site_duration(vpn_site_key)
  result <- stacked_base |>
    select(machine_cohort, machine_id, week_of_sample, rel_week) |>
    filter(rel_week %in% PRE_WINDOW) |>
    left_join(vpn_dur, by = c("machine_id", "week_of_sample")) |>
    group_by(machine_cohort) |>
    summarize(
      !!var_name := as.integer(any(!is.na(total_duration) & total_duration > 0)),
      .groups = "drop"
    )
  # Coerce non-visitors (no pre-period rows at all) to 0
  result <- all_mc |>
    left_join(result, by = "machine_cohort") |>
    mutate(!!var_name := coalesce(.data[[var_name]], 0L))
  cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))
  cat(sprintf("  %s visitors: %s / %s machine-cohorts (%.1f%%)\n",
              vpn_site_key,
              format(sum(result[[var_name]] == 1L), big.mark = ","),
              format(nrow(result), big.mark = ","),
              100 * mean(result[[var_name]] == 1L)))
  result
}

vpn_pre_clean_df <- build_vpn_pre_binary("VPNclean", "vpn_pre_clean")
vpn_pre_all_df  <- build_vpn_pre_binary("allVPN",    "vpn_pre_all")

# Attach group covariates to stacked_base (keyed by machine_cohort)
base_covs <- stacked_base |>
  left_join(
    het_covs |> select(machine_cohort, age_bin, inc_tercile, kids),
    by = "machine_cohort"
  ) |>
  left_join(
    ph_pre_usage |> select(machine_cohort, past_ph_bin),
    by = "machine_cohort"
  ) |>
  left_join(
    xxx_pre_usage |> select(machine_cohort, past_xxx_tercile),
    by = "machine_cohort"
  ) |>
  left_join(
    vpn_pre_clean_df |> select(machine_cohort, vpn_pre_clean),
    by = "machine_cohort"
  ) |>
  left_join(
    vpn_pre_all_df |> select(machine_cohort, vpn_pre_all),
    by = "machine_cohort"
  )
# ============================================================================
# DIAGNOSE MISSING COVARIATES
# ============================================================================

miss <- base_covs |>
  filter(treated == 1L) |>
  distinct(machine_cohort, age_bin, inc_tercile, kids) |>
  summarize(
    n_total    = n(),
    n_miss_age = sum(is.na(age_bin)),
    n_miss_inc = sum(is.na(inc_tercile)),
    n_miss_kids = sum(is.na(kids)),
    n_miss_any = sum(is.na(age_bin) | is.na(inc_tercile) | is.na(kids))
  )
cat("\nMissing covariate summary (treated machine-cohorts):\n")
print(miss)

cat("\nMissing rate by state:\n")
base_covs |>
  filter(treated == 1L) |>
  distinct(machine_cohort, state, age_bin) |>
  group_by(state) |>
  summarize(n = n(), n_miss = sum(is.na(age_bin)),
            pct_miss = round(100 * mean(is.na(age_bin)), 1),
            .groups = "drop") |>
  arrange(desc(pct_miss)) |>
  print()

# Restrict to machines with complete demographic covariates.
# This ensures the full-sample row and demographic subgroup rows use the same
# sample, and matches the effective sample of run_interacted() (feols listwise
# deletion drops the same machines).
base_covs <- base_covs |>
  filter(!is.na(age_bin), !is.na(inc_tercile), !is.na(kids))

cat(sprintf("\nAfter complete-covariates filter: %s treated machine-cohorts remain\n",
            format(n_distinct(base_covs$machine_cohort[base_covs$treated == 1L]),
                   big.mark = ",")))

rm(stacked_base, het_covs, ph_pre_usage, xxx_pre_usage, vpn_pre_clean_df, vpn_pre_all_df)

# ============================================================================
# SUBGROUP DEFINITIONS
# ============================================================================

subgroups <- list(
  "Full sample"      = TRUE,
  # PH-specific terciles
  "PH bin 0"         = quote(past_ph_bin == 0L),
  "PH bin 1 (low)"   = quote(past_ph_bin == 1L),
  "PH bin 2 (mid)"   = quote(past_ph_bin == 2L),
  "PH bin 3 (high)"  = quote(past_ph_bin == 3L),
  # All-XXX terciles
  "XXX bin 0"        = quote(past_xxx_tercile == 0L),
  "XXX bin 1 (low)"  = quote(past_xxx_tercile == 1L),
  "XXX bin 2 (mid)"  = quote(past_xxx_tercile == 2L),
  "XXX bin 3 (high)" = quote(past_xxx_tercile == 3L),
  # Demographics
  "Age 18-34"        = quote(age_bin == "18-34"),
  "Age 35-54"        = quote(age_bin == "35-54"),
  "Age 55+"          = quote(age_bin == "55+"),
  "Income: low"      = quote(inc_tercile == "low"),
  "Income: mid"      = quote(inc_tercile == "mid"),
  "Income: high"     = quote(inc_tercile == "high"),
  "Kids: no"         = quote(kids == 0),
  "Kids: yes"        = quote(kids == 1),
  # VPN history splits (VPNclean definition)
  "VPN user: no"     = quote(vpn_pre_clean == 0L),
  "VPN user: yes"    = quote(vpn_pre_clean == 1L),
  "allVPN user: no"  = quote(vpn_pre_all == 0L),
  "allVPN user: yes" = quote(vpn_pre_all == 1L)
)

TARGET_SITES <- list(
  list(key = "PORNHUB.COM",  label = "PH"),
  list(key = "XVIDEOS.COM",  label = "XV"),
  list(key = "XNXX.COM",     label = "XNXX")
)

# ============================================================================
# MAIN LOOP: site × subgroup
# ============================================================================

results <- list()
n_total  <- length(TARGET_SITES) * length(subgroups)
n_done   <- 0L

for (site in TARGET_SITES) {
  cat(sprintf("\n%s  [%s]\n", strrep("=", 50), site$label))

  cat(sprintf("  Loading %s duration... ", site$key))
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
    cat(sprintf("  [%d/%d] %-20s ", n_done, n_total, sg_name))

    expr <- subgroups[[sg_name]]
    df_g <- if (isTRUE(expr)) df_site else df_site |> filter(!!expr)

    n_treated <- n_distinct(df_g$machine_id[df_g$treated == 1L])

    ybar_st <- mean(df_g$win_min[df_g$treated == 1L &
                                 df_g$rel_week %in% SHORT_WINDOW], na.rm = TRUE)
    ybar_lt <- mean(df_g$win_min[df_g$treated == 1L &
                                 df_g$rel_week %in% LONG_WINDOW],  na.rm = TRUE)

    t0  <- proc.time()
    res <- run_pooled(df_g, "win_min")
    elapsed <- (proc.time() - t0)[["elapsed"]]

    cat(sprintf("n=%s  beta_ST=%+.4f  beta_LT=%+.4f  (%.1fs)\n",
                format(n_treated, big.mark = ","),
                coalesce(res$beta_shortterm, NA_real_),
                coalesce(res$beta_longterm,  NA_real_),
                elapsed))

    results[[paste(site$label, sg_name, sep = "|||")]] <- list(
      site    = site$label,
      group   = sg_name,
      n_mach  = n_treated,
      beta_st = res$beta_shortterm,
      beta_lt = res$beta_longterm,
      ybar_st = ybar_st,
      ybar_lt = ybar_lt
    )
  }

  rm(df_site); gc()
}

res_df <- dplyr::bind_rows(lapply(results, as.data.frame))

# ============================================================================
# SAVE
# ============================================================================

out <- list(
  res_df    = res_df,
  subgroups = names(subgroups)   # preserve ordering for table script
)

out_path <- file.path(out_int_dir, "normalized_het_results.rds")
saveRDS(out, out_path)

cat(sprintf("\nSaved: %s\n", out_path))
cat(sprintf("Total elapsed: %.1fs\n", (proc.time() - t_global)[["elapsed"]]))
