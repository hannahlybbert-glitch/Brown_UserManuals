# Author: Matt Brown, assisted by Claude
# Created: 2026-03-20
# Purpose: Cluster bootstrap SEs for Chen-Roth normalized het table.
#   Resamples 13 treatment states B times with replacement (mclapply, parallel).
#   Each draw: rebuild treated sample, run 51 regressions, compute normalized stats.
#   Bootstrap SE = SD of normalized statistic across draws.
#
# Reads:
#   data/intermediate/stacked_panel.rds
#   data/intermediate/xxx_win_wide.rds
#   data/intermediate/het_covs.rds
#   data/intermediate/normalized_het_results.rds  (point estimates; stored in output)
# Writes:
#   data/intermediate/normalized_het_bootstrap.rds

suppressPackageStartupMessages({
  library(dplyr)
  library(fixest)
  library(parallel)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

B        <- 100L
CORES    <- max(1L, parallel::detectCores() - 1L)
SEED     <- 42L
DRY_RUN  <- TRUE    # TRUE: run once on full data (no resampling) to verify output

cat(sprintf("Bootstrap: B=%d, CORES=%d, DRY_RUN=%s\n", B, CORES, DRY_RUN))

# ============================================================================
# LOAD AND BUILD base_wide
#   Pre-load ALL data once; child processes inherit via fork (copy-on-write).
# ============================================================================

cat("\nLoading stacked panel... ")
t0 <- proc.time()
sp              <- readRDS(file.path(int_dir, "stacked_panel.rds"))
stacked_base    <- sp$stacked_base
needed_weeks    <- sp$needed_weeks
needed_machines <- sp$needed_machines
rm(sp)
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

cat("Loading xxx_win_wide... ")
t0 <- proc.time()
xxx_win_wide <- readRDS(file.path(int_dir, "xxx_win_wide.rds"))
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

cat("Loading het_covs... ")
t0 <- proc.time()
het_covs <- readRDS(file.path(int_dir, "het_covs.rds"))
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

# Build past_ph_bin (same logic as create_normalized_het_regressions.R)
cat("\nBuilding past_ph_bin... ")
t0 <- proc.time()
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

# Build past_xxx_tercile
cat("Building past_xxx_tercile... ")
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

# Join covariates; add win_min columns for all 3 target sites from xxx_win_wide
# (avoid reloading parquet files — all 3 sites are already in xxx_win_wide)
cat("Building base_wide (joining covariates + 3-site win_min)... ")
t0 <- proc.time()

base_wide <- stacked_base |>
  left_join(het_covs     |> select(machine_cohort, age_bin, inc_tercile, kids),
            by = "machine_cohort") |>
  left_join(ph_pre_usage  |> select(machine_cohort, past_ph_bin),
            by = "machine_cohort") |>
  left_join(xxx_pre_usage |> select(machine_cohort, past_xxx_tercile),
            by = "machine_cohort") |>
  left_join(
    xxx_win_wide |> select(machine_id, week_of_sample,
                           win_PORNHUB_COM, win_XVIDEOS_COM, win_XNXX_COM),
    by = c("machine_id", "week_of_sample")
  ) |>
  mutate(
    win_min_PH   = coalesce(win_PORNHUB_COM,  0),
    win_min_XV   = coalesce(win_XVIDEOS_COM,  0),
    win_min_XNXX = coalesce(win_XNXX_COM,     0),
    pre           = as.integer(rel_week %in% PRE_WINDOW),
    shortterm     = as.integer(rel_week %in% SHORT_WINDOW),
    longterm      = as.integer(rel_week %in% LONG_WINDOW)
  ) |>
  select(-win_PORNHUB_COM, -win_XVIDEOS_COM, -win_XNXX_COM)

# Restrict to complete-covariate machines (mirrors create_normalized_het_regressions.R)
base_covs <- base_covs |>
  filter(!is.na(age_bin), !is.na(inc_tercile), !is.na(kids))
cat(sprintf("After complete-covariates filter: %s treated machine-cohorts\n",
            format(n_distinct(base_covs$machine_cohort[base_covs$treated == 1L]),
                   big.mark = ",")))

rm(stacked_base, het_covs, ph_pre_usage, xxx_pre_usage, xxx_win_wide)
gc()
cat(sprintf("%.1fs  (%s rows)\n",
            (proc.time() - t0)[["elapsed"]],
            format(nrow(base_wide), big.mark = ",")))

# ============================================================================
# SUBGROUP DEFINITIONS (must match create_normalized_het_regressions.R exactly)
# ============================================================================

SUBGROUPS <- list(
  "Full sample"      = TRUE,
  "PH bin 0"         = quote(past_ph_bin == 0L),
  "PH bin 1 (low)"   = quote(past_ph_bin == 1L),
  "PH bin 2 (mid)"   = quote(past_ph_bin == 2L),
  "PH bin 3 (high)"  = quote(past_ph_bin == 3L),
  "XXX bin 0"        = quote(past_xxx_tercile == 0L),
  "XXX bin 1 (low)"  = quote(past_xxx_tercile == 1L),
  "XXX bin 2 (mid)"  = quote(past_xxx_tercile == 2L),
  "XXX bin 3 (high)" = quote(past_xxx_tercile == 3L),
  "Age 18-34"        = quote(age_bin == "18-34"),
  "Age 35-54"        = quote(age_bin == "35-54"),
  "Age 55+"          = quote(age_bin == "55+"),
  "Income: low"      = quote(inc_tercile == "low"),
  "Income: mid"      = quote(inc_tercile == "mid"),
  "Income: high"     = quote(inc_tercile == "high"),
  "Kids: no"         = quote(kids == 0),
  "Kids: yes"        = quote(kids == 1)
)

TARGET_SITES <- c("PH" = "win_min_PH", "XV" = "win_min_XV", "XNXX" = "win_min_XNXX")

# ============================================================================
# HELPER: run 51 regressions on (possibly bootstrapped) df, return normalized stats
#
# Returns a named numeric vector with one entry per (group × site × period) cell:
#   "{group}|||norm_{period}_{site}"  — normalized beta
#   "{group}|||ey0_{period}"          — E[Y^PH(0)] for that period
#   "{group}|||frac_{period}"         — fraction remaining on PH
# ============================================================================

run_one_draw <- function(df) {
  cells <- numeric(0)

  for (sg_name in names(SUBGROUPS)) {
    expr <- SUBGROUPS[[sg_name]]
    df_g <- if (isTRUE(expr)) df else df[eval(expr, df), , drop = FALSE]

    # Observed post-law mean for PH (treated units, by period)
    post_tx    <- df_g[df_g$treated == 1L, ]
    ybar_st_PH <- mean(post_tx$win_min_PH[post_tx$rel_week %in% SHORT_WINDOW], na.rm = TRUE)
    ybar_lt_PH <- mean(post_tx$win_min_PH[post_tx$rel_week %in% LONG_WINDOW],  na.rm = TRUE)

    # Regression for each site
    betas <- list()
    for (site_label in names(TARGET_SITES)) {
      dv  <- TARGET_SITES[[site_label]]
      fml <- as.formula(sprintf(
        "%s ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week",
        dv
      ))
      res <- tryCatch({
        fit <- feols(fml, data = df_g, cluster = ~state, warn = FALSE, notes = FALSE)
        cf  <- coef(fit)
        list(beta_st = unname(cf["treated:shortterm"]),
             beta_lt = unname(cf["treated:longterm"]))
      }, error = function(e) list(beta_st = NA_real_, beta_lt = NA_real_))

      betas[[site_label]] <- res
    }

    # Compute normalized stats for ST and LT
    for (period in c("st", "lt")) {
      ybar_PH <- if (period == "st") ybar_st_PH else ybar_lt_PH
      beta_PH <- betas[["PH"]][[paste0("beta_", period)]]
      ey0     <- ybar_PH - beta_PH

      cells[[paste0(sg_name, "|||ey0_",  period)]] <- ey0
      cells[[paste0(sg_name, "|||frac_", period)]] <-
        if (!is.na(ey0) && ey0 != 0) 1 + beta_PH / ey0 else NA_real_

      for (site_label in names(TARGET_SITES)) {
        beta <- betas[[site_label]][[paste0("beta_", period)]]
        cells[[paste0(sg_name, "|||norm_", period, "_", site_label)]] <-
          if (!is.na(ey0) && ey0 != 0) beta / ey0 else NA_real_
      }
    }
  }

  cells
}

# ============================================================================
# BOOTSTRAP: assemble bootstrapped df, run all regressions, return normalized stats
#
# Treatment states resampled with replacement; duplicate states appear as
# additional copies of their rows (pairs cluster bootstrap).
# Controls always included in full.
# ============================================================================

TX_STATES <- sort(unique(base_wide$state[base_wide$treated == 1L]))
cat(sprintf("\nTreatment states (%d): %s\n", length(TX_STATES),
            paste(TX_STATES, collapse = ", ")))

if (DRY_RUN) {
  cat("\nDRY RUN: running once on full data (no resampling)...\n")
  t0  <- proc.time()
  res <- run_one_draw(base_wide)
  cat(sprintf("Done in %.1fs. Sample cells:\n", (proc.time() - t0)[["elapsed"]]))
  show_keys <- grep("Full sample", names(res), value = TRUE)
  print(round(res[show_keys], 4))
  cat("\n(Set DRY_RUN <- FALSE to run the full bootstrap.)\n")
  quit(save = "no")
}

set.seed(SEED)
boot_draws <- lapply(seq_len(B), function(b) sample(TX_STATES, replace = TRUE))

one_boot <- function(states_b) {
  tryCatch({
    # Build bootstrap treated sample: concatenate rows for each drawn state
    # (a state drawn twice contributes two copies of all its observations)
    tx_rows <- lapply(states_b, function(s) {
      base_wide[base_wide$treated == 1L & base_wide$state == s, , drop = FALSE]
    })
    df_b <- rbind(
      do.call(rbind, tx_rows),
      base_wide[base_wide$treated == 0L, , drop = FALSE]
    )
    run_one_draw(df_b)
  }, error = function(e) {
    warning(sprintf("Bootstrap draw error: %s", conditionMessage(e)))
    NULL
  })
}

# ============================================================================
# RUN
# ============================================================================

cat(sprintf("\nStarting bootstrap: B=%d on %d cores...\n", B, CORES))
t_boot <- proc.time()

boot_results <- parallel::mclapply(
  boot_draws,
  one_boot,
  mc.cores     = CORES,
  mc.set.seed  = FALSE   # parent seed already set; children inherit RNG state
)

elapsed <- (proc.time() - t_boot)[["elapsed"]]
cat(sprintf("Bootstrap complete: %.1fs  (%.1f min)\n", elapsed, elapsed / 60))

n_err <- sum(sapply(boot_results, is.null))
if (n_err > 0) cat(sprintf("WARNING: %d draws returned errors/NULL\n", n_err))

# ============================================================================
# AGGREGATE: SD across draws = bootstrap SE
# ============================================================================

good  <- Filter(Negate(is.null), boot_results)
cat(sprintf("Usable draws: %d / %d\n", length(good), B))

# Stack into matrix [n_good × n_cells]
boot_mat <- do.call(rbind, good)
boot_se  <- apply(boot_mat, 2, sd, na.rm = TRUE)

# Reshape SE vector into a wide data frame matching the table script's structure
se_df <- data.frame(group = names(SUBGROUPS), stringsAsFactors = FALSE)
for (period in c("st", "lt")) {
  for (site_label in names(TARGET_SITES)) {
    col <- paste0("se_norm_", period, "_", site_label)
    se_df[[col]] <- sapply(names(SUBGROUPS), function(g) {
      k <- paste0(g, "|||norm_", period, "_", site_label)
      if (k %in% names(boot_se)) boot_se[[k]] else NA_real_
    })
  }
  se_df[[paste0("se_ey0_",  period)]] <- sapply(names(SUBGROUPS), function(g) {
    k <- paste0(g, "|||ey0_", period)
    if (k %in% names(boot_se)) boot_se[[k]] else NA_real_
  })
  se_df[[paste0("se_frac_", period)]] <- sapply(names(SUBGROUPS), function(g) {
    k <- paste0(g, "|||frac_", period)
    if (k %in% names(boot_se)) boot_se[[k]] else NA_real_
  })
}
rownames(se_df) <- NULL

# ============================================================================
# SAVE
# ============================================================================

point_est <- readRDS(file.path(int_dir, "normalized_het_results.rds"))

out <- list(
  se_df        = se_df,        # wide SE data frame (join onto table script's wide)
  boot_mat     = boot_mat,     # raw draws [n_good × n_cells]
  boot_se      = boot_se,      # named SE vector
  boot_draws   = boot_draws,   # state vectors for each draw (reproducibility)
  point_est    = point_est,    # point estimates (for convenience)
  B            = B,
  n_good       = length(good),
  CORES        = CORES,
  SEED         = SEED,
  TX_STATES    = TX_STATES,
  elapsed_sec  = elapsed
)

out_path <- file.path(int_dir, "normalized_het_bootstrap.rds")
saveRDS(out, out_path)
cat(sprintf("\nSaved: %s\n", out_path))
cat(sprintf("Total elapsed: %.1fs  (%.1f min)\n",
            (proc.time() - t_boot)[["elapsed"]],
            (proc.time() - t_boot)[["elapsed"]] / 60))
