# Author: Matt Brown, assisted by Claude
# Created: 2026-03-20; Updated: 2026-04-24
# Purpose: Run site × subgroup TWFE regressions for normalized het analysis.
#   Loops over all sites in SITES_FULL. For each site × subgroup: saves beta,
#   SE, and within-subgroup baseline mean (treatment group, τ = −4 to −1) so
#   downstream scripts can normalize as beta / baseline_mean_treat.
#
# Subgroups: Full sample, fine age bins (18–24 … 65+), device type, children.
#
# Requires: data/intermediate.../stacked_panel.rds
#           data/intermediate.../xxx_win_wide.rds
#
# Saves: output/.../intermediate/normalized_het_results.rds

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

if (!is.null(MOBILE_FILTER)) {
  stacked_base <- stacked_base |> filter(mobile == MOBILE_FILTER)
  cat(sprintf("  MOBILE_FILTER=%d applied: %s rows remaining\n",
      MOBILE_FILTER, format(nrow(stacked_base), big.mark = ",")))
}

cat("Loading xxx_win_wide... ")
t0 <- proc.time()
xxx_win_wide <- readRDS(file.path(int_dir, "xxx_win_wide.rds"))
cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# BUILD SUBGROUP COVARIATES
# ============================================================================

cat("\nBuilding subgroup covariates... ")
t0 <- proc.time()

AGE_BINS <- c("18-24", "25-34", "35-44", "45-54", "55-64", "65+")

base_covs <- stacked_base |>
  mutate(
    age_bin_fine = factor(
      dplyr::case_when(
        hoh_age == "18-24" ~ "18-24",
        hoh_age == "25-34" ~ "25-34",
        hoh_age == "35-44" ~ "35-44",
        hoh_age == "45-54" ~ "45-54",
        hoh_age == "55-64" ~ "55-64",
        hoh_age == "65+"   ~ "65+",
        TRUE               ~ NA_character_
      ),
      levels = AGE_BINS
    ),
    kids = as.integer(children_present == "Children:Yes")
  )

cat(sprintf("%.1fs\n", (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# SUBGROUP DEFINITIONS
# ============================================================================

subgroups <- list(
  "Full sample"     = TRUE,
  "Age: 18-24"      = quote(age_bin_fine == "18-24"),
  "Age: 25-34"      = quote(age_bin_fine == "25-34"),
  "Age: 35-44"      = quote(age_bin_fine == "35-44"),
  "Age: 45-54"      = quote(age_bin_fine == "45-54"),
  "Age: 55-64"      = quote(age_bin_fine == "55-64"),
  "Age: 65+"        = quote(age_bin_fine == "65+"),
  "Device: desktop" = quote(mobile == 0L),
  "Device: mobile"  = quote(mobile == 1L),
  "Kids: no"        = quote(kids == 0L),
  "Kids: yes"       = quote(kids == 1L)
)

BASELINE_WINDOW <- -4:-1

VPN_KEYS <- c("VPNclean", "allVPN")
HET_SITES <- SITES_FULL[!sapply(SITES_FULL, `[[`, "key") %in% VPN_KEYS]

# ============================================================================
# MAIN LOOP: site × subgroup
# ============================================================================

results  <- list()
n_sites  <- length(HET_SITES)
n_sgs    <- length(subgroups)
n_total  <- n_sites * n_sgs
n_done   <- 0L

for (site in HET_SITES) {
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
    df_g <- if (isTRUE(expr)) df_site else df_site |> filter(!!expr)

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
      baseline_mean_treat = baseline_mean_treat
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
  subgroups = names(subgroups),
  sites     = HET_SITES
)

out_path <- file.path(out_int_dir, "normalized_het_results.rds")
saveRDS(out, out_path)

cat(sprintf("\nSaved: %s\n", out_path))
cat(sprintf("Total elapsed: %.1fs\n", (proc.time() - t_global)[["elapsed"]]))
