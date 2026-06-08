# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Check what p95 was baked into xxx_win_wide.rds for PORNHUB.COM
#          and compare against compute_p95_2022() run fresh.
#
# Usage (from project root):
#   Rscript code/descriptives/data_validation/check_xxx_win_wide_p95.R

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(here)
})

Sys.setenv(ANALYSIS_MODE = "combined")
source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

cat("Loading stacked panel...\n")
sp              <- readRDS(file.path(here::here(), "data", "intermediate_combined", "stacked_panel.rds"))
needed_weeks    <- sp$needed_weeks
needed_machines <- sp$needed_machines
rm(sp)

cat("Loading xxx_win_wide.rds...\n")
xxx_win_wide <- readRDS(file.path(here::here(), "data", "intermediate_combined", "xxx_win_wide.rds"))

cat(sprintf("\nxxx_win_wide columns: %s\n", paste(colnames(xxx_win_wide), collapse = ", ")))

ph_col <- grep("PORNHUB", colnames(xxx_win_wide), value = TRUE)
if (length(ph_col) == 0L) stop("No PORNHUB column found in xxx_win_wide.")
cat(sprintf("Using column: %s\n", ph_col))

# The max of the PH win_min column in 2022 weeks is the baked-in p95 / 60
cat("\n--- xxx_win_wide baked-in values (PORNHUB.COM, 2022 baseline weeks) ---\n")
ph_wide_bl <- xxx_win_wide |>
  filter(week_of_sample %in% 1:52) |>
  pull(!!ph_col)

cat(sprintf("  N rows:          %s\n",   format(length(ph_wide_bl), big.mark = ",")))
cat(sprintf("  Max win_min:     %.4f min  => implied p95 = %.1f sec (%.2f min)\n",
    max(ph_wide_bl, na.rm = TRUE),
    max(ph_wide_bl, na.rm = TRUE) * 60,
    max(ph_wide_bl, na.rm = TRUE)))
cat(sprintf("  Mean win_min:    %.4f min\n", mean(ph_wide_bl, na.rm = TRUE)))
cat(sprintf("  p95  win_min:    %.4f min\n", quantile(ph_wide_bl, 0.95, na.rm = TRUE)))

# Now compute p95 fresh from the parquet file
cat("\n--- compute_p95_2022('PORNHUB.COM') fresh from parquet ---\n")
p95_fresh <- compute_p95_2022("PORNHUB.COM")
cat(sprintf("  Fresh p95:       %.1f sec  (%.2f min)\n", p95_fresh, p95_fresh / 60))

cat("\n--- COMPARISON ---\n")
implied_p95_sec <- max(ph_wide_bl, na.rm = TRUE) * 60
cat(sprintf("  xxx_win_wide implied p95:  %.1f sec  (%.2f min)\n",
    implied_p95_sec, implied_p95_sec / 60))
cat(sprintf("  Fresh p95:                 %.1f sec  (%.2f min)\n",
    p95_fresh, p95_fresh / 60))
cat(sprintf("  Difference:                %.1f sec  (%.2f min)\n",
    p95_fresh - implied_p95_sec, (p95_fresh - implied_p95_sec) / 60))

cat("\nDone.\n")
