# Author: Matt Brown, assisted by Claude
# Created: 2026-03-20; Updated: 2026-04-24
# Purpose: Normalized het table from normalized_het_results.rds.
#   For each subgroup: beta_ST, beta_LT normalized by within-subgroup baseline mean.
#   Baseline mean = treatment group mean in periods -4 to -1.
#
# Outputs: output/.../normalized_het/{ST,LT}_table.{tex,csv}

suppressPackageStartupMessages({
  library(dplyr)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD RESULTS
# ============================================================================

rds_path <- file.path(out_int_dir, "normalized_het_results.rds")
cat(sprintf("Loading %s...\n", rds_path))
inp      <- readRDS(rds_path)
res_df   <- inp$res_df
sg_order <- inp$subgroups

out_dir <- file.path(out_base, "normalized_het")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# NORMALIZE
# ============================================================================

norm_df <- res_df |>
  mutate(
    norm_st = beta_st / baseline_mean_treat,
    norm_lt = beta_lt / baseline_mean_treat,
    # SE / baseline_mean_treat gives correct CI width (baseline is observed, not estimated)
    se_norm_st = se_st / baseline_mean_treat,
    se_norm_lt = se_lt / baseline_mean_treat
  ) |>
  mutate(group = factor(group, levels = sg_order)) |>
  arrange(group)

# Save CSV
csv_path <- file.path(out_dir, "normalized_het_results.csv")
write.csv(norm_df, csv_path, row.names = FALSE)
cat(sprintf("CSV: %s\n", csv_path))

# ============================================================================
# GROUP SECTION HEADERS (for LaTeX)
# ============================================================================

GROUP_SECTIONS <- list(
  "Full sample"     = NULL,
  "Age: 18-24"      = "\\textit{Age}",
  "Device: desktop" = "\\textit{Device type}",
  "Kids: no"        = "\\textit{Children present}"
)

# ============================================================================
# LaTeX TABLE
# ============================================================================

stars <- function(p) {
  if (is.na(p))  return("")
  if (p < 0.01)  return("***")
  if (p < 0.05)  return("**")
  if (p < 0.10)  return("*")
  return("")
}

fmt <- function(x, d = 3) if (is.na(x)) "---" else sprintf(paste0("%.", d, "f"), x)

make_latex_table <- function(df, period = "ST") {
  sfx          <- tolower(period)
  period_label <- if (period == "ST") "Short-run ($\\tau = 0$--$3$)"
                  else                "Long-run ($\\tau = 4$--$8$)"

  beta_col  <- paste0("beta_", sfx)
  norm_col  <- paste0("norm_", sfx)
  se_col    <- paste0("se_norm_", sfx)

  header <- c(
    "\\begin{table}[htbp]",
    "\\centering",
    sprintf("\\caption{Normalized subgroup ATTs --- %s}", period_label),
    sprintf("\\label{tab:norm_het_%s}", sfx),
    "\\begin{tabular}{lrr rr}",
    "\\toprule",
    paste("Group", "$n$ (machines)",
          "Baseline mean (min/wk)",
          "Normalized ATT",
          "SE (normalized)",
          sep = " & "),
    "\\\\ \\midrule"
  )

  body <- character(0)
  for (i in seq_len(nrow(df))) {
    row   <- df[i, ]
    gname <- as.character(row$group)

    if (gname %in% names(GROUP_SECTIONS) && !is.null(GROUP_SECTIONS[[gname]])) {
      body <- c(body,
                sprintf("\\midrule\n\\multicolumn{5}{l}{%s} \\\\",
                        GROUP_SECTIONS[[gname]]))
    }

    data_row <- paste(
      gname,
      format(row$n_mach, big.mark = ","),
      fmt(row$baseline_mean_treat),
      fmt(row[[norm_col]]),
      fmt(row[[se_col]]),
      sep = " & "
    )
    body <- c(body, paste0(data_row, " \\\\"))
  }

  footer <- c(
    "\\bottomrule",
    "\\end{tabular}",
    "\\vspace{4pt}",
    paste0(
      "\\begin{minipage}{\\linewidth}\\footnotesize\n",
      "\\textit{Notes}: Each row is a separate pooled TWFE regression restricted to ",
      "the indicated subgroup. Outcome: winsorized minutes/machine/week on All XXX. ",
      "Baseline mean = within-subgroup treatment group mean in $\\tau \\in \\{-4,\\ldots,-1\\}$. ",
      "Normalized ATT $=$ $\\hat{\\beta}$ / baseline mean; SE normalized by same constant. ",
      "Machine$\\times$cohort and cohort$\\times$week FEs; SE clustered by state.\n",
      "\\end{minipage}"
    ),
    "\\end{table}"
  )

  paste(c(header, body, footer), collapse = "\n")
}

for (period in c("ST", "LT")) {
  tex  <- make_latex_table(norm_df, period)
  path <- file.path(out_dir, sprintf("%s_table.tex", period))
  writeLines(tex, path)
  cat(sprintf("LaTeX (%s): %s\n", period, path))
}

cat("Done.\n")
