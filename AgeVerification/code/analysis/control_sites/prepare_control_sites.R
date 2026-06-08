# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-28
# Purpose: Build intermediate data for the control-sites regression pipeline.
#          Mirrors prepare_top25.R / prepare_combined.R. Must be run before
#          run_regressions_controls.R.
#
#          Builds per-site minutes wide table → controls_win_wide.rds.
#          No analysis-layer winsorization: total_duration is already winsorized
#          at the session level in the aggregation pipeline.
#
# Requires:
#   data/intermediate_combined/stacked_panel.rds
#   data/Aggregation/desktop_mobile_machine_panel/
#       machine_aggregated_{site}.parquet
#
# Output:
#   data/intermediate_combined/controls_win_wide.rds
#
# Usage:
#   Rscript code/analysis/control_sites/prepare_control_sites.R

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(here)
})

Sys.setenv(ANALYSIS_MODE = "combined")
source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

# data_dir is set by config.R to data/Aggregation/desktop_mobile_machine_panel/

cat("data_dir:    ", data_dir, "\n\n")

# ============================================================================
# CONTROL SITE LIST
# ============================================================================

CONTROL_SITES <- list(
  list(key = "Netflix Inc.",               label = "Netflix",            slug = "Netflix_Inc"),
  list(key = "Reddit",                     label = "Reddit",             slug = "Reddit"),
  list(key = "Twitter",                    label = "Twitter",            slug = "Twitter"),
  list(key = "ONLYFANS.COM",               label = "OnlyFans",           slug = "ONLYFANS_COM"),
  list(key = "Facebook",                   label = "Facebook",           slug = "Facebook"),
  list(key = "INSTRUCTURE.COM",            label = "Instructure",        slug = "INSTRUCTURE_COM"),
  list(key = "Wikimedia Foundation Sites", label = "Wikimedia",          slug = "Wikimedia_Foundation_Sites"),
  list(key = "eBay",                       label = "eBay",               slug = "eBay"),
  list(key = "Amazon Sites",               label = "Amazon",             slug = "Amazon_Sites"),
  list(key = "DUCKDUCKGO.COM",             label = "DuckDuckGo",         slug = "DUCKDUCKGO_COM"),
  list(key = "Enthusiast Gaming",          label = "Enthusiast Gaming",  slug = "Enthusiast_Gaming"),
  list(key = "Bytedance Inc.",             label = "Bytedance (TikTok)", slug = "Bytedance_Inc")
)

# ============================================================================
# LOAD STACKED PANEL  (for needed_weeks and needed_machines)
# ============================================================================

cat("Loading stacked panel...\n")
sp              <- readRDS(file.path(here::here(), "data", "intermediate_combined",
                                     "stacked_panel.rds"))
needed_machines <- sp$needed_machines
needed_weeks    <- sp$needed_weeks
rm(sp)
cat(sprintf("  needed_machines: %s\n\n", format(length(needed_machines), big.mark = ",")))

# ============================================================================
# BUILD CONTROLS_WIN_WIDE  (mirrors xxx_win_wide from prepare_combined.R)
#
# One win_{slug} column per site. Minutes = total_duration / 60, NA kept for
# machines with no visits — left_join in regressions coalesces to 0.
# ============================================================================

cat(strrep("=", 60), "\n")
cat(sprintf("Building controls_win_wide (%d sites)...\n", length(CONTROL_SITES)))
cat(strrep("=", 60), "\n")
t0_wide <- proc.time()

per_site <- lapply(seq_along(CONTROL_SITES), function(i) {
  s   <- CONTROL_SITES[[i]]
  t1  <- proc.time()
  dat <- open_dataset(
           file.path(data_dir, paste0("machine_aggregated_", s$key, ".parquet"))
         ) |>
         filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
         select(machine_id, week_of_sample, total_duration) |>
         collect()
  col <- paste0("win_", s$slug)
  cat(sprintf("  [%2d/12] %-35s %s rows  (%.1fs)\n",
      i, s$key, format(nrow(dat), big.mark = ","),
      (proc.time() - t1)[["elapsed"]]))
  dat |>
    mutate(!!col := total_duration / 60) |>
    select(machine_id, week_of_sample, !!col)
})

controls_win_wide <- Reduce(
  function(a, b) full_join(a, b, by = c("machine_id", "week_of_sample")),
  per_site
)

rm(per_site); gc()

cat(sprintf("\ncontrols_win_wide: %s rows, %d cols  (%.1fs total)\n\n",
    format(nrow(controls_win_wide), big.mark = ","),
    ncol(controls_win_wide),
    (proc.time() - t0_wide)[["elapsed"]]))

# ============================================================================
# SAVE
# ============================================================================

wide_path <- file.path(here::here(), "data", "intermediate_combined", "controls_win_wide.rds")
saveRDS(controls_win_wide, wide_path)
cat(sprintf("Saved: %s\n", wide_path))
cat("\nAll done.\n")
