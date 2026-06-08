# Author: Matt Brown, assisted by Claude
# Created: 2026-03-20
# Purpose: Normalize regression results and write normalized het tables.
#   Reads data/intermediate/normalized_het_results.rds (from create_normalized_het_regressions.R).
#
#   For each subgroup g:
#     E[Y^PH(0)_g] = ȳ^PH_{g,treated,post} − β^PH_g
#     Normalized TE = β^s_g / E[Y^PH(0)_g]   for s ∈ {PH, XV, XNXX}
#     Fraction remaining = 1 + β^PH / E[Y^PH(0)]
#
# Outputs: output/analysis/normalized_het/{ST,LT}_table.{tex,csv}

suppressPackageStartupMessages({
  library(dplyr)
  library(here)
  library(tidyr)
})

source(here::here("code", "analysis", "_source", "config.R"))

# ============================================================================
# LOAD RESULTS
# ============================================================================

rds_path <- file.path(out_int_dir, "normalized_het_results.rds")
cat(sprintf("Loading %s...\n", rds_path))
inp       <- readRDS(rds_path)
res_df    <- inp$res_df
sg_order  <- inp$subgroups

out_dir <- file.path(out_base, "normalized_het")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# NORMALIZE
# ============================================================================

# E[Y^PH(0)_g] per subgroup, per period: ȳ^PH_{treated,post} − β^PH
ph_res <- res_df |>
  filter(site == "PH") |>
  transmute(
    group,
    n_mach,
    ey0_st = ybar_st - beta_st,
    ey0_lt = ybar_lt - beta_lt
  )

# Normalized betas: β^site / E[Y^PH(0)]
norm_df <- res_df |>
  left_join(ph_res |> select(group, ey0_st, ey0_lt), by = "group") |>
  mutate(
    norm_st = beta_st / ey0_st,
    norm_lt = beta_lt / ey0_lt
  )

# Fraction remaining = 1 + β^PH / E[Y^PH(0)] = E[Y^PH(1)] / E[Y^PH(0)]
frac_df <- norm_df |>
  filter(site == "PH") |>
  transmute(
    group,
    frac_st = 1 + norm_st,
    frac_lt = 1 + norm_lt
  )

# ============================================================================
# ASSEMBLE WIDE TABLE
# ============================================================================

wide <- norm_df |>
  select(site, group, norm_st, norm_lt) |>
  pivot_wider(names_from = site, values_from = c(norm_st, norm_lt)) |>
  left_join(ph_res |> select(group, n_mach, ey0_st, ey0_lt), by = "group") |>
  left_join(frac_df, by = "group") |>
  mutate(group = factor(group, levels = sg_order)) |>
  arrange(group)

# Save CSV
csv_path <- file.path(out_dir, "normalized_het_results.csv")
write.csv(wide, csv_path, row.names = FALSE)
cat(sprintf("CSV: %s\n", csv_path))

# ============================================================================
# LaTeX OUTPUT
# ============================================================================

GROUP_SECTIONS <- list(
  "Full sample"     = NULL,
  "PH bin 0"        = "\\textit{Pre-period PH usage}",
  "Age 18-34"       = "\\textit{Age}",
  "Income: low"     = "\\textit{Income}",
  "Kids: no"        = "\\textit{Children present}",
  "VPN user: no"    = "\\textit{VPNclean}",
  "allVPN user: no" = "\\textit{allVPN}"
)

make_latex_table <- function(wide, period = "ST") {
  sfx          <- tolower(period)
  period_label <- if (period == "ST") "Short-run ($\\tau = 0$--$3$)"
                  else                "Long-run ($\\tau = 4$--$8$)"

  norm_ph   <- paste0("norm_", sfx, "_PH")
  norm_xv   <- paste0("norm_", sfx, "_XV")
  norm_xnxx <- paste0("norm_", sfx, "_XNXX")
  ey0       <- paste0("ey0_",  sfx)
  frac      <- paste0("frac_", sfx)

  header <- c(
    "\\begin{landscape}",
    "\\begin{table}[htbp]",
    "\\centering",
    sprintf("\\caption{Normalized treatment effects by subgroup --- %s}", period_label),
    sprintf("\\label{tab:normalized_het_%s}", sfx),
    "\\begin{tabular}{lrr rrrr}",
    "\\toprule",
    # Row 1: spanning header covers all four normalized columns (cols 4–7)
    paste("& & &",
          "\\multicolumn{4}{c}{As fraction of counterfactual PH consumption} \\\\"),
    "\\cmidrule(lr){4-7}",
    # Row 2: substantive label (top) + math notation (bottom) via \shortstack
    paste(
      "Group",
      "$n$ (000s)",
      "\\shortstack{Counterfactual \\\\\\\\ PH (min/wk)}",
      "\\shortstack{PH decline \\\\\\\\ $\\hat{\\beta}^{\\text{PH}}/E[Y^{\\text{PH}}(0)]$}",
      "\\shortstack{$\\to$ xVideos \\\\\\\\ $\\hat{\\beta}^{\\text{XV}}/E[Y^{\\text{PH}}(0)]$}",
      "\\shortstack{$\\to$ XNXX \\\\\\\\ $\\hat{\\beta}^{\\text{XNXX}}/E[Y^{\\text{PH}}(0)]$}",
      "\\shortstack{Remaining on PH \\\\\\\\ $1 + \\hat{\\beta}^{\\text{PH}}/E[Y^{\\text{PH}}(0)]$}",
      sep = " & "),
    "\\\\ \\midrule"
  )

  body <- character(0)
  for (i in seq_len(nrow(wide))) {
    row   <- wide[i, ]
    gname <- as.character(row$group)

    if (gname %in% names(GROUP_SECTIONS) && !is.null(GROUP_SECTIONS[[gname]])) {
      body <- c(body,
                sprintf("\\midrule\n\\multicolumn{7}{l}{%s} \\\\",
                        GROUP_SECTIONS[[gname]]))
    }

    fmt <- function(x, d = 3) if (is.na(x)) "---" else sprintf(paste0("%.", d, "f"), x)

    data_row <- paste(
      gname,
      fmt(row$n_mach / 1000, 1),
      fmt(row[[ey0]]),
      fmt(row[[norm_ph]]),
      fmt(row[[norm_xv]]),
      fmt(row[[norm_xnxx]]),
      fmt(row[[frac]]),
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
      "\\textit{Notes}: Each row reports results from a separate TWFE regression ",
      "restricted to the indicated subgroup. Outcome is winsorized minutes/machine/week. ",
      "$E[Y^{\\text{PH}}(0)]$ is the estimated counterfactual Pornhub consumption ",
      "in the post period: $\\bar{y}^{\\text{PH}}_{g,\\text{treated},\\text{post}} - ",
      "\\hat{\\beta}^{\\text{PH}}_g$. ",
      "All columns are expressed as fractions of $E[Y^{\\text{PH}}(0)]$. ",
      "Fraction remaining $= 1 + \\hat{\\beta}^{\\text{PH}}/E[Y^{\\text{PH}}(0)]$. ",
      "Machine$\\times$cohort and cohort$\\times$week FEs; SE clustered by state.\n",
      "\\end{minipage}"
    ),
    "\\end{table}",
    "\\end{landscape}"
  )

  paste(c(header, body, footer), collapse = "\n")
}

for (period in c("ST", "LT")) {
  tex  <- make_latex_table(wide, period)
  path <- file.path(out_dir, sprintf("%s_table.tex", period))
  writeLines(tex, path)
  cat(sprintf("LaTeX (%s): %s\n", period, path))
}

cat("Done.\n")
