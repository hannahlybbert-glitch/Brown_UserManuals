# Purpose: Quick check — share of desktop vs mobile within each gender category
#          in the main analysis sample (unique machines).
#
# Usage:
#   ANALYSIS_MODE=combined Rscript code/analysis/check_gender_device.R

suppressPackageStartupMessages({
  library(dplyr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

cat("Loading stacked panel...\n")
sp           <- readRDS(file.path(int_dir, "stacked_panel.rds"))
stacked_base <- sp$stacked_base
rm(sp)

if (!is.null(MOBILE_FILTER)) stacked_base <- stacked_base[stacked_base$mobile == MOBILE_FILTER, ]

machines <- stacked_base |>
  group_by(machine_id) |>
  summarise(
    gender = first(gender),
    mobile = first(mobile),
    .groups = "drop"
  )

result <- machines |>
  group_by(gender) |>
  summarise(
    n_total   = n(),
    n_desktop = sum(mobile == 0L),
    n_mobile  = sum(mobile == 1L),
    pct_desktop = round(100 * n_desktop / n_total, 1),
    pct_mobile  = round(100 * n_mobile  / n_total, 1),
    .groups = "drop"
  ) |>
  arrange(gender)

cat("\n=== Desktop vs Mobile share by gender (unique machines) ===\n\n")
print(as.data.frame(result), row.names = FALSE)
cat("\n")
