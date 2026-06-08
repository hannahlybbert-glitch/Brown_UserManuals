# Author: Hannah Lybbert, assisted by Claude
# Created: 2026-05-21
# Purpose: Dot plot of long-term ATT (beta_LT) for top-25 adult sites + other_adult.
#   Sites on y-axis (rank 1 at top, other_adult at bottom).
#   beta_LT with 95% CI on x-axis. Vertical reference line at zero.
#
# Requires:
#   output/analysis/combined/top_25/intermediate/regression_results_top25.rds
#
# Output:
#   output/analysis/combined/top_25/top25_regression_plot.png

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(here)
})

Sys.setenv(ANALYSIS_MODE = "combined")
source(here::here("code", "analysis", "_source", "config.R"))

out_dir      <- file.path(here::here(), "output", "analysis", "combined", "top_25")
results_path <- file.path(out_dir, "intermediate", "regression_results_top25.rds")

cat("Loading results...\n")
results <- readRDS(results_path)
if (length(results$pooled) == 0L) stop("results$pooled is empty.")

# ============================================================================
# BUILD PLOT DATA
# ============================================================================

compliance_raw  <- read.csv(here::here("raw", "compliance", "top_25_compliance.csv"),
                            stringsAsFactors = FALSE)
names(compliance_raw) <- gsub("[^a-z]", "", tolower(names(compliance_raw)))
COMPLIANT_KEYS  <- compliance_raw$site[tolower(trimws(compliance_raw$compliant)) == "yes"]

DISPLAY_NAMES <- c(
  "PORNHUB.COM"       = "Pornhub.com",
  "XHAMSTER.COM"      = "xHamster.com",
  "CHATURBATE.COM"    = "Chaturbate.com",
  "SPANKBANG.COM"     = "SpankBang.com",
  "LIVEJASMIN.COM"    = "LiveJasmin.com",
  "REDTUBE.COM"       = "Redtube.com",
  "STRIPCHAT.COM"     = "Stripchat.com",
  "YOUPORN.COM"       = "Youporn.com",
  "CAMSODA.COM"       = "Camsoda.com",
  "Various, Inc"      = "Various, Inc.",
  "E621.NET"          = "E621.net",
  "XHAMSTERLIVE.COM"  = "xHamsterLive.com",
  "FAPHOUSE.COM"      = "Faphouse.com",
  "XVIDEOS.COM"       = "XVideos.com",
  "XNXX.COM"          = "XNXX.com",
  "RULE34.XXX"        = "Rule 34",
  "LITEROTICA.COM"    = "Literotica.com",
  "FETLIFE.COM"       = "FetLife.com",
  "F95ZONE.TO"        = "F95zone.to",
  "GAMCORE.COM"       = "Gamcore.com",
  "NHENTAI.NET"       = "nHentai.net",
  "MYFREECAMS.COM"    = "MyFreeCams.com",
  "VS3.COM"           = "VS3.com",
  "BANGCREATIVES.COM" = "Bang! Creative",
  "E-HENTAI.ORG"      = "e-Hentai.org"
)

rows <- lapply(results$pooled, function(entry) {
  # Skip combined virtual sites (other_compliant, other_top25_adult) — no rank
  if (is.null(entry$rank)) return(NULL)
  res <- entry$win_min
  data.frame(
    rank          = entry$rank,
    key           = entry$key,
    label         = gsub("\\.[a-zA-Z]+$", "",
                         if (entry$key == "other_adult") "Non top 25"
                         else if (entry$key %in% names(DISPLAY_NAMES)) DISPLAY_NAMES[[entry$key]]
                         else gsub("^\\d+\\.\\s*", "", entry$label)),
    baseline_mean = entry$baseline_mean,
    beta_lt       = res$beta_longterm,
    se_lt         = res$se_longterm,
    stringsAsFactors = FALSE
  )
})

df <- dplyr::bind_rows(rows) |>
  dplyr::mutate(
    ci_lo      = beta_lt - 1.96 * se_lt,
    ci_hi      = beta_lt + 1.96 * se_lt,
    y_label    = sprintf("%s\n(%.2f min)", label, baseline_mean),
    compliance = dplyr::case_when(
      key %in% COMPLIANT_KEYS ~ "compliant",
      key == "other_adult"    ~ "other",
      TRUE                    ~ "noncompliant"
    ),
    group_order = dplyr::case_when(
      compliance == "compliant"    ~ 1L,
      compliance == "noncompliant" ~ 2L,
      TRUE                         ~ 3L
    )
  ) |>
  dplyr::arrange(group_order, dplyr::desc(baseline_mean))

# Factor for y-axis: within each group, ascending baseline_mean → highest at top
site_order <- df |>
  dplyr::arrange(group_order, baseline_mean) |>
  dplyr::pull(key)

df <- df |>
  dplyr::mutate(
    site_f      = factor(key, levels = site_order),
    group_panel = factor(compliance,
                         levels = c("compliant", "noncompliant", "other"))
  )

y_labels <- setNames(df$y_label, df$key)

STRIP_LABELS <- c(
  compliant    = "Compliant",
  noncompliant = "Noncompliant",
  other        = "Other"
)

# ============================================================================
# THEME
# ============================================================================

theme_top25 <- function(base_size = 11) {
  theme_bw(base_size = base_size) +
    theme(
      panel.grid.minor    = element_blank(),
      panel.grid.major.y  = element_blank(),
      panel.grid.major.x  = element_line(color = "gray92"),
      panel.border        = element_blank(),
      axis.line.x         = element_line(color = "black", linewidth = 0.4),
      axis.ticks.y        = element_blank(),
      axis.text.y         = element_text(size = 10, lineheight = 0.85),
      axis.text.x         = element_text(size = 13),
      axis.title.x        = element_text(size = 15, margin = margin(t = 8)),
      legend.position     = "none",
      panel.spacing.y     = unit(4, "pt"),
      strip.background    = element_rect(fill = "gray95", color = NA),
      strip.text.y.left   = element_text(size = 10, face = "bold",
                                         angle = 0, hjust = 1),
      strip.placement     = "outside"
    )
}

# ============================================================================
# PLOT
# ============================================================================

COL_COMPLIANT    <- MAROON
COL_NONCOMPLIANT <- NAVY
COL_OTHER        <- "grey50"

p <- ggplot(df, aes(x = beta_lt, y = site_f, color = compliance)) +
  geom_vline(xintercept = 0, linetype = "dashed",
             linewidth = 0.5, color = "gray40") +
  geom_errorbar(aes(xmin = ci_lo, xmax = ci_hi),
                width = 0, linewidth = 0.55,
                orientation = "y") +
  geom_point(size = 2.5) +
  facet_grid(group_panel ~ ., scales = "free_y", space = "free_y", switch = "y",
             labeller = labeller(group_panel = STRIP_LABELS)) +
  scale_color_manual(
    values = c(compliant    = COL_COMPLIANT,
               noncompliant = COL_NONCOMPLIANT,
               other        = COL_OTHER),
    guide = "none"
  ) +
  scale_x_continuous(name = "Change in weekly minutes per machine") +
  scale_y_discrete(labels = y_labels, expand = expansion(add = 0.6)) +
  labs(y = NULL) +
  theme_top25()

out_path <- file.path(out_dir, "top25_regression_plot.png")
ggsave(out_path, p, width = 9, height = 10, dpi = 300)
cat(sprintf("Wrote: %s\n", out_path))

cat("\nAll done.\n")
