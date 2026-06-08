# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-04-24
# Purpose: 2022 pre-treatment XXX activity summary tables for the analysis sample.
#   Uses the same machine sample as create_demo_summary_tables.R (stacked_panel.rds).
#   Sites: Pornhub, xVideos, XNXX, All XXX.
#   Groups: Full Sample | Ever-Treated | Never-Treated.
#
# Table 1: Share of machines that ever visit each site in 2022 (weeks 1-52).
# Table 2: Average weekly winsorized minutes per machine in 2022.
#
# Requires: data/intermediate_combined/stacked_panel.rds
#           data/intermediate_combined/xxx_win_wide.rds
#
# Outputs:
#   output/analysis/.../full_sample/xxx_2022_visit_share.{md,tex}
#   output/analysis/.../full_sample/xxx_2022_weekly_mins.{md,tex}
#
# Usage:
#   Rscript code/analysis/machine_xxx_2022_sum_table.R

suppressPackageStartupMessages({
  library(dplyr)
  library(knitr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD ANALYSIS SAMPLE
# ============================================================================

cat("Loading stacked panel...\n")
sp           <- readRDS(file.path(int_dir, "stacked_panel.rds"))
stacked_base <- sp$stacked_base
rm(sp)

if (!is.null(MOBILE_FILTER)) stacked_base <- stacked_base[stacked_base$mobile == MOBILE_FILTER, ]

machines <- stacked_base |>
  group_by(machine_id) |>
  summarise(
    ever_treated = as.integer(max(treated) == 1),
    first_week   = min(week_of_sample),
    .groups      = "drop"
  ) |>
  filter(first_week <= 52L)
rm(stacked_base)

cat(sprintf("  Unique machines in analysis sample: %s\n",
            format(nrow(machines), big.mark = ",")))

# ============================================================================
# LOAD 2022 ACTIVITY
# ============================================================================

WEEKS_2022 <- 1:52

cat("Loading xxx_win_wide...\n")
xxx_win_wide <- readRDS(file.path(int_dir, "xxx_win_wide.rds"))

# Restrict to 2022 and the analysis sample; machines with no 2022 rows are
# naturally excluded (not in panel during 2022).
activity_2022 <- xxx_win_wide |>
  filter(week_of_sample %in% WEEKS_2022) |>
  inner_join(machines, by = "machine_id")

cat(sprintf("  Machine-weeks in 2022: %s\n",
            format(nrow(activity_2022), big.mark = ",")))
cat(sprintf("  Machines with 2022 activity: %s\n",
            format(n_distinct(activity_2022$machine_id), big.mark = ",")))
rm(xxx_win_wide)

# ============================================================================
# PER-MACHINE SUMMARIES
# ============================================================================

SITE_COLS <- c("win_PORNHUB_COM", "win_XVIDEOS_COM", "win_XNXX_COM", "win_min_allxxx")

machine_stats <- activity_2022 |>
  group_by(machine_id, ever_treated) |>
  summarise(
    across(
      all_of(SITE_COLS),
      list(
        any_visit  = ~ as.integer(any(.x > 0, na.rm = TRUE)),
        avg_wk_min = ~ mean(.x, na.rm = TRUE)
      )
    ),
    .groups = "drop"
  )

full  <- machine_stats
ever  <- machine_stats |> filter(ever_treated == 1L)
never <- machine_stats |> filter(ever_treated == 0L)

GROUPS  <- list("Full Sample" = full, "Never-Treated" = never, "Ever-Treated" = ever)
GROUP_N <- sapply(GROUPS, nrow)

# ============================================================================
# BUILD TABLES
# ============================================================================

SITES <- list(
  list(col = "win_PORNHUB_COM",  label = "Pornhub"),
  list(col = "win_XVIDEOS_COM",  label = "xVideos"),
  list(col = "win_XNXX_COM",     label = "XNXX"),
  list(col = "win_min_allxxx",   label = "All XXX")
)

n_row <- c("N (machines)", format(GROUP_N, big.mark = ","))

make_table <- function(stat_suffix, fmt_fn) {
  body <- do.call(rbind, lapply(SITES, function(s) {
    col  <- paste0(s$col, "_", stat_suffix)
    vals <- sapply(GROUPS, function(g) fmt_fn(mean(g[[col]], na.rm = TRUE)))
    c(s$label, vals)
  }))
  tbl           <- as.data.frame(rbind(body, n_row), stringsAsFactors = FALSE)
  colnames(tbl) <- c(" ", names(GROUPS))
  rownames(tbl) <- NULL
  tbl
}

visit_tbl <- make_table("any_visit",  function(x) sprintf("%.1f%%", 100 * x))
mins_tbl  <- make_table("avg_wk_min", function(x) sprintf("%.2f",   x))

# ============================================================================
# WRITE OUTPUTS
# ============================================================================

out_dir <- file.path(out_base, "summary_tables")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

note_visit <- paste0(
  "Sample: unique machines from stacked_panel.rds that have at least one in-panel week ",
  "in 2022 (weeks 1-52). Visit share = fraction of machines with at least one week of ",
  "positive winsorized minutes on the site in 2022. ",
  "Ever-treated = machine appears as treated == 1 in at least one cohort slice."
)

note_mins <- paste0(
  "Same sample as the visit share table. ",
  "Avg weekly minutes = per-machine mean of winsorized weekly minutes across ",
  "in-panel weeks in 2022, then averaged across machines in each group. ",
  "Winsorization applied at the session level in the aggregation pipeline."
)

SITE_LABELS <- c("Pornhub", "XVideos", "XNXX", "Any XXX site")

make_xxx_tex <- function(stat_suffix, fmt_fn, row_labels, n_label) {
  col_ns  <- format(GROUP_N, big.mark = ",")
  tex_row <- function(label, vals) paste0(paste(c(label, vals), collapse = " & "), " \\\\")

  data_rows <- unname(mapply(function(s, lbl) {
    col  <- paste0(s$col, "_", stat_suffix)
    vals <- sapply(GROUPS, function(g) {
      v <- fmt_fn(mean(g[[col]], na.rm = TRUE))
      gsub("%", "\\\\%", v)
    })
    tex_row(lbl, vals)
  }, SITES, row_labels))

  c(
    "\\begin{tabular}{lrrr}",
    "\\toprule",
    tex_row("", names(GROUPS)),
    tex_row("", sprintf("(N = %s)", col_ns)),
    "\\midrule",
    data_rows,
    "\\midrule",
    tex_row(n_label, col_ns),
    "\\bottomrule",
    "\\end{tabular}"
  )
}

write_pair <- function(tbl, stem, title, note, stat_suffix, fmt_fn, row_labels, n_label) {
  writeLines(
    c(sprintf("# %s", title), "", note, "", kable(tbl, format = "markdown")),
    file.path(out_dir, paste0(stem, ".md"))
  )
  writeLines(
    make_xxx_tex(stat_suffix, fmt_fn, row_labels, n_label),
    file.path(out_dir, paste0(stem, ".tex"))
  )
  cat(sprintf("Wrote: %s/{md,tex}\n", file.path(out_dir, stem)))
}

write_pair(
  visit_tbl,
  stem        = "xxx_2022_visit_share",
  title       = "XXX Site Visit Share — 2022 (Pre-Treatment)",
  note        = note_visit,
  stat_suffix = "any_visit",
  fmt_fn      = function(x) sprintf("%.1f%%", 100 * x),
  row_labels  = SITE_LABELS,
  n_label     = "N observed in 2022"
)

write_pair(
  mins_tbl,
  stem        = "xxx_2022_weekly_mins",
  title       = "Avg Weekly XXX Minutes per Machine — 2022 (Pre-Treatment)",
  note        = note_mins,
  stat_suffix = "avg_wk_min",
  fmt_fn      = function(x) sprintf("%.2f", x),
  row_labels  = SITE_LABELS,
  n_label     = "N"
)

cat("\nAll done.\n")
