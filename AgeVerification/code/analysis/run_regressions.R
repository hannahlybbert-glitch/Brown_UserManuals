# Author: Matt Brown, assisted by Claude
# Created: 2026-03-07
# Purpose: Run all stacked TWFE regressions and save results to
#          output/analysis/*/intermediate/regression_results.rds.
#          Output generation (plots, tables) is handled by separate scripts.
#
# Requires: data/intermediate_combined/stacked_panel.rds,
#           data/intermediate_combined/xxx_win_wide.rds
#           (produced by prepare_combined.R)
#
# Loops over all three combined modes in sequence:
#   combined         → output/analysis/combined/intermediate/
#   desktop_combined → output/analysis/intermediate/
#   mobile_combined  → output/analysis/mobile/intermediate/
#
# Section selection via CLI args (default = all):
#   Rscript code/analysis/run_regressions.R             # all sections
#   Rscript code/analysis/run_regressions.R het         # Section C only
#   Rscript code/analysis/run_regressions.R event pooled
# Args: "event", "pooled", "het", "diagnostics"

# ============================================================================
# FLAGS
# ============================================================================

args    <- commandArgs(trailingOnly = TRUE)
run_all <- length(args) == 0L
RUN_HOMOGENEOUS_EVENT_STUDY <- run_all || "event"       %in% args
RUN_HOMOGENEOUS_POOLED      <- run_all || "pooled"      %in% args
RUN_HETEROGENEOUS           <- run_all || "het"         %in% args
RUN_DIAGNOSTICS             <- run_all || "diagnostics" %in% args
RUN_VPN_XXX                 <- run_all || "vpn_xxx"      %in% args
RUN_VPN_NOXXX               <- run_all || "vpn_noxxx"    %in% args
RUN_PH_VPNSPLIT             <- run_all || "ph_vpnsplit"  %in% args
RUN_VPN_NOXXX               <- run_all || "vpn_noxxx"   %in% args

# ============================================================================
# SETUP
# ============================================================================

suppressPackageStartupMessages({
  library(arrow)
  library(broom)
  library(dplyr)
  library(fixest)
  library(here)
})

# ============================================================================
# LOOP OVER ALL THREE COMBINED MODES
# ============================================================================

# RUN_MODE env var (set by per-mode SLURM scripts for parallel jobs).
# Empty or unset → run all three modes sequentially (default).
.run_mode_env  <- Sys.getenv("RUN_MODE", unset = "")
COMBINED_MODES <- if (nzchar(.run_mode_env)) .run_mode_env else
                    c("combined", "desktop_combined", "mobile_combined", "single_user")

# xxx_win_wide is identical across all three combined modes (same int_dir).
# Load it once here to avoid three redundant 80MB reads.
{
  .int_dir_combined <- file.path(here::here(), "data", "intermediate_combined")
  cat("Pre-loading xxx_win_wide (shared across all modes)...\n")
  t0 <- proc.time()
  xxx_win_wide <- readRDS(file.path(.int_dir_combined, "xxx_win_wide.rds"))
  cat(sprintf("  Loaded: %s rows  (%.1fs)\n\n",
      format(nrow(xxx_win_wide), big.mark = ","),
      (proc.time() - t0)[["elapsed"]]))
  rm(.int_dir_combined, t0)
}

for (.current_mode in COMBINED_MODES) {
  Sys.setenv(ANALYSIS_MODE = .current_mode)
  source(here::here("code", "analysis", "_source", "config.R"))
  source(here::here("code", "analysis", "_source", "helpers.R"))

  cat("\n")
  cat(strrep("#", 70), "\n", sep = "")
  cat(sprintf("# MODE: %s\n", .current_mode))
  cat(sprintf("#   int_dir:  %s\n", int_dir))
  cat(sprintf("#   out_base: %s\n", out_base))
  cat(strrep("#", 70), "\n\n", sep = "")

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
# control_states was renamed to never_treated_states in prepare_combined.R;
# support both for backward compatibility with existing desktop/mobile RDS files.
control_states  <- if (!is.null(sp$control_states)) sp$control_states else sp$never_treated_states
balanced_mcs    <- sp$balanced_mcs
rm(sp)

# In desktop_combined / mobile_combined modes, restrict to one device type.
if (!is.null(MOBILE_FILTER)) {
  stacked_base <- stacked_base |> filter(mobile == MOBILE_FILTER)
  cat(sprintf("  MOBILE_FILTER=%d applied: %s rows remaining\n",
      MOBILE_FILTER, format(nrow(stacked_base), big.mark = ",")))
}

# In single_user mode, drop shared-device machines (gender == "Shared").
if (SINGLE_USER_FILTER) {
  n_before     <- nrow(stacked_base)
  stacked_base <- stacked_base |> filter(is.na(gender) | gender != "Shared")
  cat(sprintf("  SINGLE_USER_FILTER applied: dropped %s shared-device rows, %s remaining\n",
      format(n_before - nrow(stacked_base), big.mark = ","),
      format(nrow(stacked_base),            big.mark = ",")))
}

cat(sprintf("  Stacked: %s rows | %d clusters | %d cohorts\n",
    format(nrow(stacked_base), big.mark = ","), n_clusters, length(qualifying)))

# Pre-cache all_xxx duration for this mode — it is loaded in sections A+B, C,
# and D, and costs ~450s each time from parquet. Load it once and reuse.
cat("Pre-caching all_xxx duration...\n")
t0 <- proc.time()
.all_xxx_cache <- load_site_duration("all_xxx")
cat(sprintf("  Cached: %s rows  (%.1fs)\n\n",
    format(nrow(.all_xxx_cache), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))
rm(t0)

# Drop-in replacement: returns cache for all_xxx, calls parquet for everything else.
load_site_cached <- function(key) {
  if (key == "all_xxx") .all_xxx_cache else load_site_duration(key)
}

# SITES_FULL, BAL_SITES, dvs, PRE/SHORT/LONG_WINDOW sourced from config.R

# ============================================================================
# RESULTS STORAGE
# Load existing RDS (if present) so sections can run independently and
# accumulate results without overwriting previous runs.
# ============================================================================

results_path <- file.path(out_int_dir, "regression_results.rds")
if (file.exists(results_path)) {
  cat(sprintf("Loading existing regression_results.rds (%s)...\n",
              format(file.size(results_path) / 1e6, digits = 3, nsmall = 1)))
  results <- readRDS(results_path)
  # Ensure all top-level keys exist (forward-compat with older RDS)
  for (k in c("event", "pooled", "interacted", "balanced"))
    if (is.null(results[[k]])) results[[k]] <- list()
} else {
  results <- list(
    event      = list(),
    pooled     = list(),
    interacted = list(),
    balanced   = list()
  )
}

results$meta <- list(
  n_clusters = n_clusters,
  n_cohorts  = length(qualifying),
  qualifying = qualifying
)

# ============================================================================
# SECTIONS A + B: HOMOGENEOUS EVENT STUDY + POOLED ATT
# ============================================================================

if (RUN_HOMOGENEOUS_EVENT_STUDY || RUN_HOMOGENEOUS_POOLED) {
  cat("\n", strrep("=", 60), "\n", sep = "")
  cat(sprintf("Homogeneous regressions: %d sites × %d DVs\n",
              length(SITES_FULL), length(dvs)))
  cat(strrep("=", 60), "\n\n", sep = "")

  for (s_idx in seq_along(SITES_FULL)) {
    site <- SITES_FULL[[s_idx]]
    cat(sprintf("--- %s ---\n", site$label))

    t0       <- proc.time()
    dur_data <- load_site_cached(site$key)
    cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
        format(nrow(dur_data), big.mark = ","),
        (proc.time() - t0)[["elapsed"]]))

    df <- stacked_base |>
      left_join(dur_data, by = c("machine_id", "week_of_sample"))
    rm(dur_data)
    df <- attach_dvs(df, site$key, xxx_win_wide)

    results$event [[site$slug]] <- list()
    results$pooled[[site$slug]] <- list()

    for (dv in dvs) {
      dv_label <- if (dv == "over60") ">60s binary" else "Win. min/machine (p95)"

      if (RUN_HOMOGENEOUS_EVENT_STUDY) {
        t1  <- proc.time()
        fit <- feols(as.formula(sprintf(
          "%s ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week", dv)),
          data = df, cluster = ~state, warn = FALSE, notes = FALSE)
        cat(sprintf("  [ES] %s: N=%s, R2_within=%.4f  (%.1fs)\n",
            dv_label, format(fit$nobs, big.mark = ","),
            fit$r2["r2_within"], (proc.time() - t1)[["elapsed"]]))
        flush.console()

        baseline_mean <- mean(df[[dv]][df$treated == 1L & df$rel_week == -1L],
                              na.rm = TRUE)
        results$event[[site$slug]][[dv]] <- list(
          coefs         = extract_coefs(fit),
          baseline_mean = baseline_mean,
          n_obs         = fit$nobs,
          r2_within     = unname(fit$r2["r2_within"])
        )
        rm(fit)
      }

      if (RUN_HOMOGENEOUS_POOLED) {
        t1  <- proc.time()
        res <- run_pooled(df, dv)
        cat(sprintf("  [PL] %s: N=%s  (%.1fs)\n",
            dv_label, format(res$n_obs, big.mark = ","),
            (proc.time() - t1)[["elapsed"]]))
        results$pooled[[site$slug]][[dv]] <- res
      }
    }

    rm(df); gc()
    cat("\n")
  }
  saveRDS(results, results_path)
  cat(sprintf("[checkpoint A+B] Saved  (%.1f MB)\n", file.size(results_path) / 1e6))
}

# ============================================================================
# SECTION C: HETEROGENEOUS — spec-3 interacted model (all_xxx only)
# ============================================================================

if (RUN_HETEROGENEOUS) {
  cat("\n", strrep("=", 60), "\n", sep = "")
  cat("Heterogeneous regressions — spec 3 interacted (all_xxx)\n")
  cat(strrep("=", 60), "\n\n", sep = "")

  het_covs_path <- file.path(int_dir, "het_covs.rds")
  if (!file.exists(het_covs_path)) {
    stop("het_covs.rds not found. Re-run prepare_desktop.R, prepare_mobile.R, or prepare_combined.R.")
  }
  cat("Loading het_covs from RDS...\n")
  het_covs <- readRDS(het_covs_path)

  results$interacted <- list()

  HET_SITES <- SITES_FULL

  for (s_idx in seq_along(HET_SITES)) {
    site <- HET_SITES[[s_idx]]
    cat(sprintf("--- %s ---\n", site$label))

    t0       <- proc.time()
    dur_data <- load_site_cached(site$key)
    cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
        format(nrow(dur_data), big.mark = ","),
        (proc.time() - t0)[["elapsed"]]))

    df <- stacked_base |>
      left_join(dur_data, by = c("machine_id", "week_of_sample"))
    rm(dur_data)
    df <- attach_dvs(df, site$key, xxx_win_wide)

    cat("  [INT] win_min ...\n")
    t1 <- proc.time()
    fit <- tryCatch(
      run_interacted(df, "win_min", het_covs),
      error = function(e) {
        cat(sprintf("    ERROR: %s\n", conditionMessage(e))); NULL
      }
    )
    if (!is.null(fit)) {
      cat(sprintf("  [INT] N=%s, R2_within=%.4f  (%.1fs)\n",
          format(fit$nobs, big.mark = ","),
          fit$r2["r2_within"], (proc.time() - t1)[["elapsed"]]))
      results$interacted[[site$slug]] <- list(
        win_min = list(
          coefs     = tidy(fit) |> select(term, estimate, std.error, p.value),
          n_obs     = fit$nobs,
          r2_within = unname(fit$r2["r2_within"])
        )
      )
      rm(fit)
    }
    rm(df); gc()
    cat("\n")
  }

  rm(het_covs); gc()
  cat("\n")
  saveRDS(results, results_path)
  cat(sprintf("[checkpoint C] Saved  (%.1f MB)\n", file.size(results_path) / 1e6))
}

# ============================================================================
# SECTION D: DIAGNOSTICS — balanced panel
# ============================================================================

if (RUN_DIAGNOSTICS) {
  cat("\n", strrep("=", 60), "\n", sep = "")
  cat("Diagnostics — balanced panel comparison\n")
  cat(strrep("=", 60), "\n\n", sep = "")

  for (s_idx in seq_along(BAL_SITES)) {
    site <- BAL_SITES[[s_idx]]
    cat(sprintf("--- %s ---\n", site$label))

    t0       <- proc.time()
    dur_data <- load_site_cached(site$key)
    cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
        format(nrow(dur_data), big.mark = ","),
        (proc.time() - t0)[["elapsed"]]))

    df_site <- stacked_base |>
      left_join(dur_data, by = c("machine_id", "week_of_sample"))
    rm(dur_data)
    df_site <- attach_dvs(df_site, site$key, xxx_win_wide)

    df_bal     <- df_site |> filter(machine_cohort %in% balanced_mcs)
    n_unbal_mc <- n_distinct(df_site$machine_cohort)
    n_bal_mc   <- n_distinct(df_bal$machine_cohort)
    cat(sprintf("  m\u00d7c: unbalanced %s | balanced %s\n",
        format(n_unbal_mc, big.mark = ","),
        format(n_bal_mc,   big.mark = ",")))

    results$balanced[[site$slug]] <- list()

    for (dv in dvs) {
      cat(sprintf("  [BAL] %s\n", dv))

      t1         <- proc.time()
      fit_full   <- feols(as.formula(sprintf(
        "%s ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week", dv)),
        data = df_site, cluster = ~state, warn = FALSE, notes = FALSE)
      full_coefs <- extract_coefs(fit_full)
      cat(sprintf("    Unbalanced fit  (%.1fs)\n", (proc.time() - t1)[["elapsed"]]))
      rm(fit_full)

      t1       <- proc.time()
      fit_bal  <- feols(as.formula(sprintf(
        "%s ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week", dv)),
        data = df_bal, cluster = ~state, warn = FALSE, notes = FALSE)
      bal_coefs <- extract_coefs(fit_bal)
      cat(sprintf("    Balanced fit    (%.1fs)\n", (proc.time() - t1)[["elapsed"]]))
      rm(fit_bal)

      res_full <- run_pooled(df_site, dv)
      res_bal  <- run_pooled(df_bal,  dv)

      results$balanced[[site$slug]][[dv]] <- list(
        full_coefs = full_coefs,
        bal_coefs  = bal_coefs,
        res_full   = res_full,
        res_bal    = res_bal,
        n_unbal_mc = n_unbal_mc,
        n_bal_mc   = n_bal_mc
      )
    }

    rm(df_site, df_bal); gc()
    cat("\n")
  }
  saveRDS(results, results_path)
  cat(sprintf("[checkpoint D] Saved  (%.1f MB)\n", file.size(results_path) / 1e6))
}

# ============================================================================
# SECTION E: VPN EVENT STUDY + POOLED — PRE-PERIOD XXX VISITORS ONLY
# ============================================================================

if (RUN_VPN_XXX) {
  cat("\n", strrep("=", 60), "\n", sep = "")
  cat("VPN event study + pooled — pre-period XXX visitors only\n")
  cat(strrep("=", 60), "\n\n", sep = "")

  ever_xxx_machines <- xxx_win_wide |>
    semi_join(filter(stacked_base, rel_week < 0L),
              by = c("machine_id", "week_of_sample")) |>
    filter(win_min_allxxx > 0) |>
    distinct(machine_id)

  cat(sprintf("  XXX visitor machines: %s of %s total\n",
      format(n_distinct(ever_xxx_machines$machine_id), big.mark = ","),
      format(n_distinct(stacked_base$machine_id),      big.mark = ",")))

  stacked_xxx <- stacked_base |>
    semi_join(ever_xxx_machines, by = "machine_id")

  VPN_XXX_SITES <- list(
    list(key = "VPNclean", label = "VPN (clean) — XXX visitors", slug = "VPNclean_xxx"),
    list(key = "allVPN",   label = "All VPN — XXX visitors",     slug = "allVPN_xxx")
  )

  for (site in VPN_XXX_SITES) {
    cat(sprintf("--- %s ---\n", site$label))

    t0       <- proc.time()
    dur_data <- load_site_duration(site$key)
    cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
        format(nrow(dur_data), big.mark = ","),
        (proc.time() - t0)[["elapsed"]]))

    df <- stacked_xxx |>
      left_join(dur_data, by = c("machine_id", "week_of_sample"))
    rm(dur_data)
    df <- attach_dvs(df, site$key, xxx_win_wide)

    results$event [[site$slug]] <- list()
    results$pooled[[site$slug]] <- list()

    for (dv in dvs) {
      dv_label <- if (dv == "over60") ">60s binary" else "Win. min/machine (p95)"

      t1  <- proc.time()
      fit <- feols(as.formula(sprintf(
        "%s ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week", dv)),
        data = df, cluster = ~state, warn = FALSE, notes = FALSE)
      cat(sprintf("  [ES] %s: N=%s, R2_within=%.4f  (%.1fs)\n",
          dv_label, format(fit$nobs, big.mark = ","),
          fit$r2["r2_within"], (proc.time() - t1)[["elapsed"]]))
      flush.console()

      baseline_mean <- mean(df[[dv]][df$treated == 1L & df$rel_week == -1L],
                            na.rm = TRUE)
      results$event[[site$slug]][[dv]] <- list(
        coefs         = extract_coefs(fit),
        baseline_mean = baseline_mean,
        n_obs         = fit$nobs,
        r2_within     = unname(fit$r2["r2_within"])
      )
      rm(fit)

      t1  <- proc.time()
      res <- run_pooled(df, dv)
      cat(sprintf("  [PL] %s: N=%s  (%.1fs)\n",
          dv_label, format(res$n_obs, big.mark = ","),
          (proc.time() - t1)[["elapsed"]]))
      results$pooled[[site$slug]][[dv]] <- res
    }
    rm(df); gc()
    cat("\n")
  }

  rm(stacked_xxx, ever_xxx_machines); gc()
  saveRDS(results, results_path)
  cat(sprintf("[checkpoint E] Saved  (%.1f MB)\n", file.size(results_path) / 1e6))
}

# ============================================================================
# SECTION F: VPN EVENT STUDY + POOLED — MACHINES THAT NEVER VISITED XXX
# ============================================================================

if (RUN_VPN_NOXXX) {
  cat("\n", strrep("=", 60), "\n", sep = "")
  cat("VPN event study + pooled — machines that never visited XXX\n")
  cat(strrep("=", 60), "\n\n", sep = "")

  ever_xxx_machines <- xxx_win_wide |>
    semi_join(filter(stacked_base, rel_week < 0L),
              by = c("machine_id", "week_of_sample")) |>
    filter(win_min_allxxx > 0) |>
    distinct(machine_id)

  stacked_noxxx <- stacked_base |>
    anti_join(ever_xxx_machines, by = "machine_id")

  cat(sprintf("  Never-XXX machines: %s of %s total\n",
      format(n_distinct(stacked_noxxx$machine_id), big.mark = ","),
      format(n_distinct(stacked_base$machine_id),  big.mark = ",")))

  VPN_NOXXX_SITES <- list(
    list(key = "VPNclean", label = "VPN (clean) — never XXX", slug = "VPNclean_noxxx"),
    list(key = "allVPN",   label = "All VPN — never XXX",     slug = "allVPN_noxxx")
  )

  for (site in VPN_NOXXX_SITES) {
    cat(sprintf("--- %s ---\n", site$label))

    t0       <- proc.time()
    dur_data <- load_site_duration(site$key)
    cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
        format(nrow(dur_data), big.mark = ","),
        (proc.time() - t0)[["elapsed"]]))

    df <- stacked_noxxx |>
      left_join(dur_data, by = c("machine_id", "week_of_sample"))
    rm(dur_data)
    df <- attach_dvs(df, site$key, xxx_win_wide)

    results$event [[site$slug]] <- list()
    results$pooled[[site$slug]] <- list()

    for (dv in dvs) {
      dv_label <- if (dv == "over60") ">60s binary" else "Win. min/machine (p95)"

      t1  <- proc.time()
      fit <- feols(as.formula(sprintf(
        "%s ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week", dv)),
        data = df, cluster = ~state, warn = FALSE, notes = FALSE)
      cat(sprintf("  [ES] %s: N=%s, R2_within=%.4f  (%.1fs)\n",
          dv_label, format(fit$nobs, big.mark = ","),
          fit$r2["r2_within"], (proc.time() - t1)[["elapsed"]]))
      flush.console()

      baseline_mean <- mean(df[[dv]][df$treated == 1L & df$rel_week == -1L],
                            na.rm = TRUE)
      results$event[[site$slug]][[dv]] <- list(
        coefs         = extract_coefs(fit),
        baseline_mean = baseline_mean,
        n_obs         = fit$nobs,
        r2_within     = unname(fit$r2["r2_within"])
      )
      rm(fit)

      t1  <- proc.time()
      res <- run_pooled(df, dv)
      cat(sprintf("  [PL] %s: N=%s  (%.1fs)\n",
          dv_label, format(res$n_obs, big.mark = ","),
          (proc.time() - t1)[["elapsed"]]))
      results$pooled[[site$slug]][[dv]] <- res
    }
    rm(df); gc()
    cat("\n")
  }

  rm(stacked_noxxx, ever_xxx_machines); gc()
  saveRDS(results, results_path)
  cat(sprintf("[checkpoint F] Saved  (%.1f MB)\n", file.size(results_path) / 1e6))
}

# ============================================================================
# SECTION G: PORNHUB EVENT STUDY + POOLED — SPLIT BY PRE-PERIOD CLEANVPN STATUS
# ============================================================================

if (RUN_PH_VPNSPLIT) {
  cat("\n", strrep("=", 60), "\n", sep = "")
  cat("Pornhub event study + pooled — split by pre-period CleanVPN status\n")
  cat(strrep("=", 60), "\n\n", sep = "")

  # Identify machines with any CleanVPN usage in the pre-period
  cat("  Loading VPNclean duration to identify pre-period VPN users...\n")
  t0 <- proc.time()
  vpn_dur <- load_site_duration("VPNclean")
  cat(sprintf("  VPNclean loaded: %s rows  (%.1fs)\n",
      format(nrow(vpn_dur), big.mark = ","),
      (proc.time() - t0)[["elapsed"]]))

  pre_vpn_machines <- vpn_dur |>
    semi_join(filter(stacked_base, rel_week < 0L),
              by = c("machine_id", "week_of_sample")) |>
    filter(total_duration > 0) |>
    distinct(machine_id)
  rm(vpn_dur); gc()

  cat(sprintf("  Pre-period VPN machines: %s of %s total (%.1f%%)\n",
      format(nrow(pre_vpn_machines), big.mark = ","),
      format(n_distinct(stacked_base$machine_id), big.mark = ","),
      100 * nrow(pre_vpn_machines) / n_distinct(stacked_base$machine_id)))

  stacked_vpn   <- stacked_base |> semi_join(pre_vpn_machines, by = "machine_id")
  stacked_novpn <- stacked_base |> anti_join(pre_vpn_machines, by = "machine_id")
  rm(pre_vpn_machines)

  cat(sprintf("  VPN subset:    %s rows | %s machine\u00d7cohort\n",
      format(nrow(stacked_vpn),              big.mark = ","),
      format(n_distinct(stacked_vpn$machine_cohort), big.mark = ",")))
  cat(sprintf("  No-VPN subset: %s rows | %s machine\u00d7cohort\n",
      format(nrow(stacked_novpn),              big.mark = ","),
      format(n_distinct(stacked_novpn$machine_cohort), big.mark = ",")))

  # Load Pornhub duration once — reused for both subsets
  cat("  Loading Pornhub duration...\n")
  t0 <- proc.time()
  ph_dur <- load_site_duration("PORNHUB.COM")
  cat(sprintf("  Pornhub loaded: %s rows  (%.1fs)\n",
      format(nrow(ph_dur), big.mark = ","),
      (proc.time() - t0)[["elapsed"]]))

  PH_VPN_SUBSETS <- list(
    list(data = stacked_vpn,   label = "Pornhub \u2014 pre-period VPN users", slug = "PORNHUB_COM_vpn"),
    list(data = stacked_novpn, label = "Pornhub \u2014 no pre-period VPN",    slug = "PORNHUB_COM_novpn")
  )

  for (sub in PH_VPN_SUBSETS) {
    cat(sprintf("--- %s ---\n", sub$label))

    df <- sub$data |>
      left_join(ph_dur, by = c("machine_id", "week_of_sample"))
    df <- attach_dvs(df, "PORNHUB.COM", xxx_win_wide)

    results$event [[sub$slug]] <- list()
    results$pooled[[sub$slug]] <- list()

    for (dv in dvs) {
      dv_label <- if (dv == "over60") ">60s binary" else "Win. min/machine (p95)"

      t1  <- proc.time()
      fit <- feols(as.formula(sprintf(
        "%s ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week", dv)),
        data = df, cluster = ~state, warn = FALSE, notes = FALSE)
      cat(sprintf("  [ES] %s: N=%s, R2_within=%.4f  (%.1fs)\n",
          dv_label, format(fit$nobs, big.mark = ","),
          fit$r2["r2_within"], (proc.time() - t1)[["elapsed"]]))
      flush.console()

      baseline_mean <- mean(df[[dv]][df$treated == 1L & df$rel_week == -1L],
                            na.rm = TRUE)
      results$event[[sub$slug]][[dv]] <- list(
        coefs         = extract_coefs(fit),
        baseline_mean = baseline_mean,
        n_obs         = fit$nobs,
        r2_within     = unname(fit$r2["r2_within"])
      )
      rm(fit)

      t1  <- proc.time()
      res <- run_pooled(df, dv)
      cat(sprintf("  [PL] %s: N=%s  (%.1fs)\n",
          dv_label, format(res$n_obs, big.mark = ","),
          (proc.time() - t1)[["elapsed"]]))
      results$pooled[[sub$slug]][[dv]] <- res
    }
    rm(df); gc()
    cat("\n")
  }

  rm(stacked_vpn, stacked_novpn, ph_dur); gc()
  saveRDS(results, results_path)
  cat(sprintf("[checkpoint G] Saved  (%.1f MB)\n", file.size(results_path) / 1e6))
}

# ============================================================================
# SAVE RESULTS (final — also written after each section above as checkpoints)
# ============================================================================

  dir.create(out_int_dir, recursive = TRUE, showWarnings = FALSE)
  saveRDS(results, results_path)
  cat(sprintf("\nSaved: %s  (%.1f MB)\n",
      results_path, file.size(results_path) / 1e6))

} # end COMBINED_MODES loop

cat("\nAll done.\n")
