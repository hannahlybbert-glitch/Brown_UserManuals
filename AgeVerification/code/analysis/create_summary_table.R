# Author: Hannah Lybbert, assisted by Claude
# Created: 05/04/2026
# Purpose: Single combined summary table for the paper (10 cols x 22 rows).
#          22 data rows: state (2), gender (4), age (3), HH income (3),
#          children present (2), device type (2), XXX usage tercile
#          (Non Visitor + 3 terciles), total (1).
#          10 columns: share of sample, PH visits, PH minutes, XV visits,
#          XV minutes, XNXX visits, XNXX minutes, all XXX visits, all XXX
#          minutes, N.
#          Columns: share of sample, PH/XV/XNXX/all-XXX visits & minutes, N.
#          "Visits" = share of subgroup with >= 1 in-panel week of positive
#          winsorized minutes within the analysis window [T_MIN, T_MAX].
#          "Minutes" = per-machine mean of winsorized weekly minutes across
#          in-panel analysis-window weeks, then averaged across the subgroup.
#          "Treated state" = machine's state appears in phshutdown_dates.csv.
#
# Requires: data/intermediate_combined/stacked_panel.rds
#           data/intermediate_combined/xxx_win_wide.rds
#           raw/statelaws/phshutdown_dates.csv
#
# Outputs:
#   output/analysis/.../summary_tables/summary_table.md
#   output/analysis/.../summary_tables/summary_table.tex
#
# Usage:
#   Rscript code/analysis/create_summary_table.R

suppressPackageStartupMessages({
  library(dplyr)
  library(knitr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD & DEDUPLICATE TO UNIQUE MACHINES
# ============================================================================

cat("Loading stacked panel...\n")
sp           <- readRDS(file.path(int_dir, "stacked_panel.rds"))
stacked_base <- sp$stacked_base
rm(sp)

if (!is.null(MOBILE_FILTER)) stacked_base <- stacked_base[stacked_base$mobile == MOBILE_FILTER, ]

# Unique machine-weeks in the analysis window (used to filter xxx_win_wide)
analysis_mw <- distinct(stacked_base, machine_id, week_of_sample)

machines <- stacked_base |>
  group_by(machine_id) |>
  summarise(
    state            = first(state),
    gender           = first(gender),
    hoh_age          = first(hoh_age),
    children_present = first(children_present),
    hh_income        = first(hh_income),
    mobile           = first(mobile),
    .groups = "drop"
  )

cat(sprintf("  Unique machines:      %s\n", format(nrow(machines),    big.mark = ",")))
cat(sprintf("  Unique machine-weeks: %s\n", format(nrow(analysis_mw), big.mark = ",")))
rm(stacked_base)

# ============================================================================
# TREATED STATE FLAG
# ============================================================================

laws           <- read.csv(ph_shutdown_file, stringsAsFactors = FALSE, na.strings = c("", "NA"))
treated_states <- unique(laws$state[!is.na(laws$state)])

machines <- machines |>
  mutate(treated_state = if_else(state %in% treated_states, "Treated", "Non-Treated"))

# ============================================================================
# RE-BIN DEMOGRAPHICS
# ============================================================================

machines <- machines |>
  mutate(
    age_bin3 = case_when(
      hoh_age == "18-24"                                    ~ "18-24",
      hoh_age %in% c("25-34", "35-44")                     ~ "25-44",
      hoh_age %in% c("45-54", "55-64", "65 and Over")      ~ "45+",
      TRUE                                                  ~ NA_character_
    ),
    inc_bin3 = case_when(
      hh_income %in% c("HHI:Less than 25k", "HHI:25k-39k", "HHI:40k-59k") ~ "<$60k",
      hh_income %in% c("HHI:60k-74k", "HHI:75k-99k")                      ~ "$60k-$99k",
      hh_income == "HHI:100k+"                                              ~ "$100k+",
      TRUE                                                                  ~ NA_character_
    ),
    device_type = if_else(as.logical(mobile), "Mobile", "Desktop")
  )

# ============================================================================
# LOAD ACTIVITY IN ANALYSIS WINDOW
# ============================================================================

cat("Loading xxx_win_wide...\n")
xxx_win_wide <- readRDS(file.path(int_dir, "xxx_win_wide.rds"))

SITE_COLS <- c("win_PORNHUB_COM", "win_XVIDEOS_COM", "win_XNXX_COM", "win_min_allxxx")

machine_activity <- xxx_win_wide |>
  semi_join(analysis_mw, by = c("machine_id", "week_of_sample")) |>
  group_by(machine_id) |>
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

rm(xxx_win_wide, analysis_mw)

machines <- left_join(machines, machine_activity, by = "machine_id")
rm(machine_activity)

machines <- machines |>
  mutate(
    win_min_allxxx_avg_wk_min = coalesce(win_min_allxxx_avg_wk_min, 0),
    usage_tercile = dplyr::case_when(
      win_min_allxxx_avg_wk_min == 0 ~ "Non Visitor",
      TRUE ~ c("Tercile: Light", "Tercile: Moderate", "Tercile: Heavy")[
        ntile(if_else(win_min_allxxx_avg_wk_min > 0, win_min_allxxx_avg_wk_min, NA_real_), 3)
      ]
    )
  )

cat(sprintf("  Machines with activity data: %s\n",
            format(sum(!is.na(machines$win_PORNHUB_COM_any_visit)), big.mark = ",")))

# ============================================================================
# SUMMARY HELPERS
# ============================================================================

SITE_DEFS <- list(
  list(col = "win_PORNHUB_COM",  label = "PH"),
  list(col = "win_XVIDEOS_COM",  label = "XV"),
  list(col = "win_XNXX_COM",     label = "XNXX"),
  list(col = "win_min_allxxx",   label = "All XXX")
)

# Returns the 9 data values for one subgroup (share, 8 activity cols) + N.
# n_denom: denominator for "share of sample" (non-missing count for the variable).
summarise_subgroup <- function(df, n_denom) {
  n_sub     <- nrow(df)
  share_pct <- sprintf("%.1f%%", 100 * n_sub / n_denom)

  site_stats <- unlist(lapply(SITE_DEFS, function(s) {
    visit_col <- paste0(s$col, "_any_visit")
    min_col   <- paste0(s$col, "_avg_wk_min")
    c(
      sprintf("%.1f%%", 100 * mean(df[[visit_col]], na.rm = TRUE)),
      sprintf("%.2f",         mean(df[[min_col]],   na.rm = TRUE))
    )
  }))

  c(share_pct, format(n_sub, big.mark = ","), site_stats)
}

COLS <- c(
  "Share of Sample",
  "N",
  "PH Visits", "PH Minutes",
  "XV Visits", "XV Minutes",
  "XNXX Visits", "XNXX Minutes",
  "All XXX Visits", "All XXX Minutes"
)

# Builds a section block: one header row + one row per level.
# Shares denominate over non-missing machines for that column.
make_section <- function(header, col, levels, labels) {
  n_denom <- sum(!is.na(machines[[col]]))
  rows <- lapply(seq_along(levels), function(i) {
    sub <- machines[!is.na(machines[[col]]) & machines[[col]] == levels[i], ]
    c(paste0("  ", labels[i]), summarise_subgroup(sub, n_denom))
  })
  rbind(
    c(header, rep("", length(COLS))),
    do.call(rbind, rows)
  )
}

# Custom section for XXX usage: Non Visitor row (dashes) + three tercile rows.
# Shares denominate over the full sample since Non Visitor covers everyone.
make_usage_tercile_section <- function() {
  n_total  <- nrow(machines)
  n_nv     <- sum(machines$usage_tercile == "Non Visitor", na.rm = TRUE)
  nv_row   <- c("  Non Visitor",
                sprintf("%.1f%%", 100 * n_nv / n_total),
                format(n_nv, big.mark = ","),
                rep("-", length(COLS) - 2L))

  tercile_rows <- lapply(
    list(c("Tercile: Light", "Light"),
         c("Tercile: Moderate", "Moderate"),
         c("Tercile: Heavy", "Heavy")),
    function(lv) {
      sub <- machines[!is.na(machines$usage_tercile) & machines$usage_tercile == lv[1], ]
      c(paste0("  ", lv[2]), summarise_subgroup(sub, n_total))
    }
  )

  rbind(
    c("XXX Usage Tercile", rep("", length(COLS))),
    nv_row,
    do.call(rbind, tercile_rows)
  )
}

# ============================================================================
# BUILD TABLE BODY
# ============================================================================

placeholder_row <- function(label) c(paste0("  ", label), rep("[placeholder]", length(COLS)))

total_stats       <- summarise_subgroup(machines, nrow(machines))
total_stats[1]    <- "100.0%"   # share is exactly 100% for the full sample
total_row         <- c("Total", total_stats)

body <- rbind(
  make_section("State", "treated_state",
               c("Treated", "Non-Treated"),
               c("Treated", "Non-Treated")),
  make_section("Gender", "gender",
               c("Male", "Female", "Shared", "Unknown"),
               c("Male", "Female", "Shared", "Unknown")),
  make_section("Age", "age_bin3",
               c("18-24", "25-44", "45+"),
               c("18-24", "25-44", "45+")),
  make_section("HH Income", "inc_bin3",
               c("<$60k", "$60k-$99k", "$100k+"),
               c("<$60k", "$60k-$99k", "$100k+")),
  make_section("Children Present", "children_present",
               c("Children:Yes", "Children:No"),
               c("Yes", "No")),
  make_section("Device Type", "device_type",
               c("Desktop", "Mobile"),
               c("Desktop", "Mobile")),
  make_usage_tercile_section(),
  total_row
)

tbl           <- as.data.frame(body, stringsAsFactors = FALSE)
colnames(tbl) <- c(" ", COLS)
rownames(tbl) <- NULL

# ============================================================================
# CONSOLE PREVIEW
# ============================================================================

cat("=", strrep("=", 110), "\n", sep = "")
cat("  SUMMARY TABLE\n")
cat("=", strrep("=", 110), "\n", sep = "")
print(tbl, row.names = FALSE)

# ============================================================================
# WRITE OUTPUTS
# ============================================================================

out_dir <- file.path(out_base, "summary_tables")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

note <- paste0(
  "Sample: unique machines from stacked_panel.rds (prepare_combined.R), ",
  "analysis window rel_week in [", T_MIN, ", ", T_MAX, "]. ",
  "Share of sample denominator excludes machines with missing values for the row variable. ",
  "Visits = share of machines with at least one in-panel analysis-window week of positive ",
  "winsorized minutes. ",
  "Minutes = per-machine mean of winsorized weekly minutes across in-panel analysis-window ",
  "weeks, then averaged across machines in the subgroup. ",
  "Treated state = machine's state appears in phshutdown_dates.csv. ",
  "Non Visitor = machines with zero average weekly all-XXX minutes across the analysis window ",
  "(τ = ", T_MIN, " to +", T_MAX, "). ",
  "Light/Moderate/Heavy terciles divide machines with positive all-XXX usage into equal thirds ",
  "by per-machine average weekly winsorized all-XXX minutes. ",
  "Unlike the demographic rows, this is a behavioral measure derived from observed usage during the full 25-week analysis period."
)

md_path  <- file.path(out_dir, "summary_table.md")
tex_path <- file.path(out_dir, "summary_table.tex")

writeLines(
  c("# Summary Table", "", note, "", kable(tbl, format = "markdown")),
  md_path
)
cat(sprintf("Wrote: %s\n", md_path))

# --- LaTeX ----------------------------------------------------------------

esc_pct  <- function(x) gsub("%", "\\\\%", x)
n_cols   <- length(COLS) + 1L
col_fmt  <- "lrl@{\\hskip 15pt}r@{\\hskip 3pt}cr@{\\hskip 3pt}cr@{\\hskip 3pt}cr@{\\hskip 3pt}c"  # 15pt gap before PH Visits; 3pt nudge before each Minutes col

tex_row <- function(cells) paste0(paste(esc_pct(cells), collapse = " & "), " \\\\")
sec_hdr <- function(title) sprintf("\\multicolumn{%d}{l}{\\textbf{%s}} \\\\", n_cols, title)

make_tex_section <- function(header, col, levels, tex_labels) {
  n_denom <- sum(!is.na(machines[[col]]))
  rows    <- lapply(seq_along(levels), function(i) {
    sub   <- machines[!is.na(machines[[col]]) & machines[[col]] == levels[i], ]
    cells <- c(paste0("\\quad ", tex_labels[i]), summarise_subgroup(sub, n_denom))
    tex_row(cells)
  })
  c(sec_hdr(header), unlist(rows))
}

total_tex       <- summarise_subgroup(machines, nrow(machines))
total_tex[1]    <- "100.0%"

make_tex_usage_tercile_section <- function() {
  n_total  <- nrow(machines)
  n_nv     <- sum(machines$usage_tercile == "Non Visitor", na.rm = TRUE)
  nv_cells <- c("\\quad Non Visitor",
                sprintf("%.1f%%", 100 * n_nv / n_total),
                format(n_nv, big.mark = ","),
                rep("-", length(COLS) - 2L))

  tercile_rows <- lapply(
    list(c("Tercile: Light", "Light"),
         c("Tercile: Moderate", "Moderate"),
         c("Tercile: Heavy", "Heavy")),
    function(lv) {
      sub   <- machines[!is.na(machines$usage_tercile) & machines$usage_tercile == lv[1], ]
      cells <- c(paste0("\\quad ", lv[2]), summarise_subgroup(sub, n_total))
      tex_row(cells)
    }
  )

  c(sec_hdr("XXX Usage Tercile"),
    tex_row(nv_cells),
    unlist(tercile_rows))
}

tex_lines <- c(
  sprintf("\\begin{tabular}{%s}", col_fmt),
  "\\toprule",
  paste0(" & & & \\multicolumn{2}{c}{Pornhub} & \\multicolumn{2}{c}{XVideos}",
         " & \\multicolumn{2}{c}{XNXX} & \\multicolumn{2}{c}{All XXX} \\\\"),
  "\\cmidrule(r){4-5}\\cmidrule(r){6-7}\\cmidrule(r){8-9}\\cmidrule(r){10-11}",
  tex_row(c("", "Share of Sample", "N", "Visits", "Minutes", "Visits", "Minutes",
              "Visits", "Minutes", "Visits", "Minutes")),
  "\\midrule",
  make_tex_section("State", "treated_state",
                   c("Treated", "Non-Treated"),
                   c("Treated", "Non-Treated")),
  "\\addlinespace",
  make_tex_section("Gender", "gender",
                   c("Male", "Female", "Shared", "Unknown"),
                   c("Male", "Female", "Shared", "Unknown")),
  "\\addlinespace",
  make_tex_section("Age", "age_bin3",
                   c("18-24", "25-44", "45+"),
                   c("18--24", "25--44", "45+")),
  "\\addlinespace",
  make_tex_section("Household Income", "inc_bin3",
                   c("<$60k", "$60k-$99k", "$100k+"),
                   c("$<$\\$60k", "\\$60k--\\$99k", "\\$100k+")),
  "\\addlinespace",
  make_tex_section("Children Present", "children_present",
                   c("Children:Yes", "Children:No"),
                   c("Yes", "No")),
  "\\addlinespace",
  make_tex_section("Device Type", "device_type",
                   c("Desktop", "Mobile"),
                   c("Desktop", "Mobile")),
  "\\addlinespace",
  make_tex_usage_tercile_section(),
  "\\midrule",
  tex_row(c("Total", total_tex)),
  "\\bottomrule",
  "\\end{tabular}"
)

writeLines(tex_lines, tex_path)
cat(sprintf("Wrote: %s\n", tex_path))

cat("\nAll done.\n")
