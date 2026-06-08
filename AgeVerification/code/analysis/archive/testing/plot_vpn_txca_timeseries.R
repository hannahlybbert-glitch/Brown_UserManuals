# ============================================================================
# plot_vpn_txca_timeseries.R
# Author: Matt Brown, assisted by Claude
# Created: 2026-03-19
# Purpose: Monthly time series of VPN spend and transactions for TX and CA —
#          the two highest-coverage states in the ConsumerEdge panel.
#          Event: Pornhub shutdown date from phshutdown_dates.csv.
#
# No imputation: uses raw observed data only.
#
# Output:
#   output/analysis/ConsumerEdge/timeseries/txca_monthly_spend.png
#   output/analysis/ConsumerEdge/timeseries/txca_monthly_trans.png
# ============================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(here)
  library(lubridate)
  library(tidyr)
})

source(here::here("code", "analysis", "_source", "config.R"))

TS_DIR <- file.path(project_root, "output", "analysis", "ConsumerEdge", "timeseries")
dir.create(TS_DIR, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# Load data
# ============================================================================

ce <- read.csv(
  file.path(project_root, "data", "ConsumerEdge", "vpn_state_week_2022_2024.csv"),
  stringsAsFactors = FALSE
)
ce$week_start <- as.Date(ce$week_start)

# Drop the pre-2022 partial week (first observation, 2021-12-27 — panel artifact)
ce <- ce |> filter(week_start >= as.Date("2022-01-01"))

# Brand share subtitle: ExpressVPN / NordVPN / Other for TX+CA combined
brand_shares <- ce |>
  filter(STATE_ABBR %in% c("TX", "CA")) |>
  mutate(brand_group = case_when(
    grepl("EXPRESS", BRAND_NAME, ignore.case = TRUE) ~ "ExpressVPN",
    grepl("NORDVPN", BRAND_NAME, ignore.case = TRUE) ~ "NordVPN",
    TRUE                                              ~ "Other"
  )) |>
  group_by(brand_group) |>
  summarise(spend = sum(spend, na.rm = TRUE), .groups = "drop") |>
  mutate(pct = round(100 * spend / sum(spend)))

pct <- setNames(brand_shares$pct, brand_shares$brand_group)
brand_subtitle <- sprintf(
  "ConsumerEdge panel, weighted by demographics of panelists  \u2502  ExpressVPN %d%%  \u2502  NordVPN %d%%  \u2502  Other %d%%",
  pct["ExpressVPN"], pct["NordVPN"], pct["Other"]
)

# Aggregate to monthly
monthly <- ce |>
  filter(STATE_ABBR %in% c("TX", "CA")) |>
  mutate(month = floor_date(week_start, "month")) |>
  group_by(STATE_ABBR, month) |>
  summarise(spend = sum(spend, na.rm = TRUE),
            trans = sum(trans,  na.rm = TRUE),
            .groups = "drop") |>
  rename(state = STATE_ABBR)

# TX event date — Pornhub shutdown, consistent with main analysis
laws_raw <- read.csv(
  file.path(project_root, "raw", "statelaws", "phshutdown_dates.csv"),
  stringsAsFactors = FALSE, na.strings = c("", "NA")
)
tx_law_date  <- as.Date(laws_raw$date_PH_shutdown[laws_raw$state == "TX"])
tx_law_month <- floor_date(tx_law_date, "month")

# ============================================================================
# Plot helper
# ============================================================================

save_txca_plot <- function(data, y_var, y_label, title_str, out_path, sec_label = "Difference: TX \u2212 CA (thousands of dollars)") {
  colors <- c("CA" = NAVY, "TX" = MAROON)

  # Convert to $000s
  data <- data |> mutate(y_k = .data[[y_var]] / 1e3)

  # Difference series (TX - CA) in $000s, rescaled to primary axis
  wide <- data |>
    select(state, month, y_k) |>
    pivot_wider(names_from = state, values_from = y_k) |>
    mutate(diff = TX - CA)

  # Linear mapping: diff -> primary axis scale so it's visible on same plot
  diff_vals <- wide$diff
  y_vals    <- data$y_k
  scale_fac <- diff(range(y_vals, na.rm = TRUE)) / diff(range(diff_vals, na.rm = TRUE))
  offset    <- mean(y_vals, na.rm = TRUE) - scale_fac * mean(diff_vals, na.rm = TRUE)
  wide$diff_mapped <- offset + scale_fac * diff_vals

  p <- ggplot(data, aes(x = month, y = y_k, color = state)) +
    # Difference line on primary axis (rescaled), grey, behind state lines
    geom_line(data = wide, aes(x = month, y = diff_mapped),
              color = "gray60", linewidth = 0.7, linetype = "solid",
              inherit.aes = FALSE) +
    geom_line(linewidth = 0.9) +
    geom_point(size = 1.8) +
    geom_vline(xintercept = tx_law_month,
               linetype = "dashed", color = "gray40", linewidth = 0.5) +
    annotate("text", x = tx_law_month + 15, y = Inf,
             label = "Pornhub\nshut down", hjust = 0, vjust = 1.4,
             size = 2.8, color = "gray40") +
    scale_color_manual(values = colors, name = NULL) +
    scale_x_date(date_breaks = "6 months", date_labels = "%b %Y") +
    scale_y_continuous(
      name     = y_label,
      sec.axis = sec_axis(
        transform = ~ (. - offset) / scale_fac,
        name      = sec_label
      )
    ) +
    labs(
      x        = NULL,
      title    = title_str,
      subtitle = brand_subtitle
    ) +
    theme_bw() +
    theme(
      panel.grid.minor        = element_blank(),
      panel.border            = element_blank(),
      axis.line               = element_line(color = "black", linewidth = 0.4),
      axis.text.x             = element_text(angle = 30, hjust = 1, size = 8),
      axis.title.y.right      = element_text(color = "gray50", size = 9),
      axis.text.y.right       = element_text(color = "gray50"),
      plot.title              = element_text(size = 12),
      plot.subtitle           = element_text(size = 8, color = "gray40"),
      axis.title              = element_text(size = 10),
      legend.position         = "top",
      legend.text             = element_text(size = 10)
    )

  ggsave(out_path, p, width = 9, height = 4.5, dpi = 300)
  cat(sprintf("  Saved: %s\n", basename(out_path)))
  invisible(out_path)
}

# ============================================================================
# Save plots
# ============================================================================

cat("Saving TX/CA monthly time series...\n")
cat(sprintf("  Brand shares: %s\n", brand_subtitle))

save_txca_plot(
  monthly,
  y_var     = "spend",
  y_label   = "Spending in ConsumerEdge panel, weighted by\ndemographics of panelists (thousands of dollars)",
  title_str = "VPN Spend: Texas vs California, 2022\u20132024",
  out_path  = file.path(TS_DIR, "txca_monthly_spend.png")
)

save_txca_plot(
  monthly,
  y_var     = "trans",
  y_label   = "Transactions in ConsumerEdge panel, weighted by\ndemographics of panelists (thousands)",
  title_str = "VPN Transactions: Texas vs California, 2022\u20132024",
  out_path  = file.path(TS_DIR, "txca_monthly_trans.png"),
  sec_label = "Difference: TX \u2212 CA (thousands)"
)

cat("Done.\n")
