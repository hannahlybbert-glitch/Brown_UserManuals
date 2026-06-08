# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21 (updated: 2026-05-28)
# Purpose: Build all intermediate data for the top-25 regression pipeline.
#          Must be run before run_regressions_top25.R.
#
#          1. Computes per-site p95 winsorization thresholds → top25_p95.rds
#          2. Builds other-compliant wide table → top25_other_compliant_win_wide.rds
#             (compliant sites excluding Pornhub)
#          3. Builds other-noncompliant wide table → top25_other_noncompliant_win_wide.rds
#             (noncompliant sites excluding XVIDEOS and XNXX)
#
#          Tables 2 and 3 are built and saved sequentially so only one is in
#          memory at a time. Pornhub, XVIDEOS, XNXX, and other_adult are loaded
#          individually by run_regressions_top25.R.
#
# Requires:
#   data/intermediate_combined/stacked_panel.rds
#   data/Aggregation/top25/desktop_mobile_machine_panel/machine_aggregated_*.parquet
#   output/ProcessComscore/data_structure_validation/top25_adult_sites.csv
#   raw/compliance/top_25_compliance.csv
#
# Output:
#   output/analysis/combined/top_25/intermediate/top25_p95.rds
#   data/intermediate_combined/top25_other_compliant_win_wide.rds
#   data/intermediate_combined/top25_other_noncompliant_win_wide.rds
#
# Usage:
#   Rscript code/analysis/top25/prepare_top25.R

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(here)
})

Sys.setenv(ANALYSIS_MODE = "combined")
source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

# Override data_dir to top-25 combined panel
data_dir    <- file.path(here::here(), "data", "Aggregation", "top25",
                         "desktop_mobile_machine_panel")
out_int_dir <- file.path(here::here(), "output", "analysis", "combined",
                         "top_25", "intermediate")
dir.create(out_int_dir, recursive = TRUE, showWarnings = FALSE)

cat("data_dir:    ", data_dir,    "\n")
cat("out_int_dir: ", out_int_dir, "\n\n")

# ============================================================================
# LOAD STACKED PANEL  (for needed_machines — must match regression run)
# ============================================================================

cat("Loading stacked panel...\n")
sp              <- readRDS(file.path(here::here(), "data", "intermediate_combined",
                                     "stacked_panel.rds"))
needed_machines <- sp$needed_machines
needed_weeks    <- sp$needed_weeks
rm(sp)
cat(sprintf("  needed_machines: %s\n\n", format(length(needed_machines), big.mark = ",")))

# ============================================================================
# SITE LIST  (top 25 + other_adult, same as run_regressions_top25.R)
# ============================================================================

top25_csv <- read.csv(
  here::here("output", "ProcessComscore", "data_structure_validation",
             "top25_adult_sites.csv"),
  stringsAsFactors = FALSE
)

TOP25_SITES <- c(
  lapply(seq_len(nrow(top25_csv)), function(i) {
    nm <- top25_csv$top_web_name[i]
    list(key  = nm,
         slug = gsub("[^A-Za-z0-9]", "_", nm),
         rank = top25_csv$rank[i])
  }),
  list(list(key = "other_adult", slug = "other_adult", rank = 26L))
)

# ============================================================================
# COMPUTE P95 PER SITE
# (compute_p95_2022 uses data_dir + needed_machines as free variables)
# ============================================================================

cat(strrep("=", 60), "\n")
cat(sprintf("Computing p95 for %d sites\n", length(TOP25_SITES)))
cat(strrep("=", 60), "\n\n")

top25_p95 <- list()

for (site in TOP25_SITES) {
  t0  <- proc.time()
  p95 <- compute_p95_2022(site$key)
  cat(sprintf("  [%2d/26] %-35s p95 = %.1f sec (%.2f min)  (%.1fs)\n",
      site$rank, site$key, p95, p95 / 60,
      (proc.time() - t0)[["elapsed"]]))
  top25_p95[[site$slug]] <- p95
}

# ============================================================================
# SAVE P95
# ============================================================================

out_path <- file.path(out_int_dir, "top25_p95.rds")
saveRDS(top25_p95, out_path)
cat(sprintf("\nSaved: %s\n\n", out_path))

# ============================================================================
# COMPLIANCE  (needed to define combined-group columns)
# ============================================================================

compliance_raw <- read.csv(
  here::here("raw", "compliance", "top_25_compliance.csv"),
  stringsAsFactors = FALSE
)
names(compliance_raw) <- gsub("[^a-z]", "", tolower(names(compliance_raw)))

compliant_sites    <- compliance_raw$site[tolower(trimws(compliance_raw$compliant)) == "yes"]
noncompliant_sites <- setdiff(compliance_raw$site, compliant_sites)

to_slug <- function(x) gsub("[^A-Za-z0-9]", "_", x)

other_compliant_keys    <- setdiff(compliant_sites, "PORNHUB.COM")
other_noncompliant_keys <- setdiff(noncompliant_sites, c("XVIDEOS.COM", "XNXX.COM"))

other_compliant_slugs    <- to_slug(other_compliant_keys)
other_noncompliant_slugs <- to_slug(other_noncompliant_keys)

cat(sprintf("other_compliant sites (%d):          %s\n",
    length(other_compliant_keys), paste(other_compliant_keys, collapse = ", ")))
cat(sprintf("other_noncompliant_top25 sites (%d): %s\n\n",
    length(other_noncompliant_keys), paste(other_noncompliant_keys, collapse = ", ")))

# ============================================================================
# HELPER: load one site parquet into a narrow win_{slug} frame
# ============================================================================

load_site_frame <- function(s) {
  col <- paste0("win_", s$slug)
  t1  <- proc.time()
  dat <- open_dataset(
           file.path(data_dir, paste0("machine_aggregated_", s$key, ".parquet"))
         ) |>
         filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
         select(machine_id, week_of_sample, total_duration) |>
         collect()
  cat(sprintf("    %-35s %s rows  (%.1fs)\n",
      s$key, format(nrow(dat), big.mark = ","),
      (proc.time() - t1)[["elapsed"]]))
  dat |>
    mutate(!!col := total_duration / 60) |>
    select(machine_id, week_of_sample, !!col)
}

# ============================================================================
# BUILD 1: OTHER COMPLIANT WIN WIDE
# Compliant sites excluding Pornhub. Pornhub is loaded individually by the
# regression script.
# ============================================================================

cat(strrep("=", 60), "\n")
cat(sprintf("Building other_compliant_win_wide (%d sites)...\n", length(other_compliant_keys)))
cat(strrep("=", 60), "\n")
t0 <- proc.time()

compliant_site_list <- Filter(function(s) s$key %in% other_compliant_keys, TOP25_SITES)
per_site            <- lapply(compliant_site_list, load_site_frame)

other_compliant_win_wide <- Reduce(
  function(a, b) full_join(a, b, by = c("machine_id", "week_of_sample")),
  per_site
) |>
  mutate(
    win_other_compliant = rowSums(across(all_of(paste0("win_", other_compliant_slugs))), na.rm = TRUE)
  )

rm(per_site); gc()

cat(sprintf("\n  %s rows, %d cols  (%.1fs)\n\n",
    format(nrow(other_compliant_win_wide), big.mark = ","),
    ncol(other_compliant_win_wide),
    (proc.time() - t0)[["elapsed"]]))

compliant_path <- file.path(here::here(), "data", "intermediate_combined",
                            "top25_other_compliant_win_wide.rds")
saveRDS(other_compliant_win_wide, compliant_path)
cat(sprintf("Saved: %s\n\n", compliant_path))
rm(other_compliant_win_wide); gc()

# ============================================================================
# BUILD 2: OTHER NONCOMPLIANT WIN WIDE
# Noncompliant sites excluding XVIDEOS and XNXX. Those two are loaded
# individually by the regression script.
# ============================================================================

cat(strrep("=", 60), "\n")
cat(sprintf("Building other_noncompliant_win_wide (%d sites)...\n", length(other_noncompliant_keys)))
cat(strrep("=", 60), "\n")
t0 <- proc.time()

noncompliant_site_list <- Filter(function(s) s$key %in% other_noncompliant_keys, TOP25_SITES)
per_site               <- lapply(noncompliant_site_list, load_site_frame)

other_noncompliant_win_wide <- Reduce(
  function(a, b) full_join(a, b, by = c("machine_id", "week_of_sample")),
  per_site
) |>
  mutate(
    win_other_noncompliant_top25 = rowSums(across(all_of(paste0("win_", other_noncompliant_slugs))), na.rm = TRUE)
  )

rm(per_site); gc()

cat(sprintf("\n  %s rows, %d cols  (%.1fs)\n\n",
    format(nrow(other_noncompliant_win_wide), big.mark = ","),
    ncol(other_noncompliant_win_wide),
    (proc.time() - t0)[["elapsed"]]))

noncompliant_path <- file.path(here::here(), "data", "intermediate_combined",
                               "top25_other_noncompliant_win_wide.rds")
saveRDS(other_noncompliant_win_wide, noncompliant_path)
cat(sprintf("Saved: %s\n", noncompliant_path))
rm(other_noncompliant_win_wide); gc()

cat("\nAll done.\n")
