# did_dow_buckets.R
# Day-of-week bucket DiD: effect of AV law on winsorized minutes per machine-week,
# broken down by day of week (Mon–Sun).
#
# Day: derived from session `date` column (already local date).
# DV: sum of pmin(session_duration, session_P95) / 60 per machine-week-DOW-bucket.
# Effects reported as % change vs. control-state mean in post period.
#
# Sites: Pornhub and Xvideos

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(fixest)
  library(here)
})

source(here::here("code", "analysis", "_source", "config.R"))
source(here::here("code", "analysis", "_source", "helpers.R"))

OUTDIR    <- here::here("output", "descriptives", "pages_assessment")
BASE_DATE <- as.Date("2022-01-01")
dir.create(OUTDIR, recursive = TRUE, showWarnings = FALSE)

DOW_LBLS <- c("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# ── load stacked panel ────────────────────────────────────────────────────────
cat("Loading stacked panel...\n")
panel_obj    <- readRDS(here::here("data", "intermediate", "stacked_panel.rds"))
stacked_base <- panel_obj$stacked_base |>
  mutate(
    pre       = as.integer(rel_week %in% PRE_WINDOW),
    shortterm = as.integer(rel_week %in% SHORT_WINDOW),
    longterm  = as.integer(rel_week %in% LONG_WINDOW)
  )
cat(sprintf("  %s rows | %d cohorts | %d clusters\n",
    format(nrow(stacked_base), big.mark=","),
    length(panel_obj$qualifying), panel_obj$n_clusters))

# ── helpers ───────────────────────────────────────────────────────────────────

compute_session_p95 <- function(slug) {
  read_parquet(
    here::here("data", "ProcessComscore", "merged_cat_session_files",
               paste0(slug, "_sessions.parquet")),
    col_select = c("treated", "duration")
  ) |>
    filter(treated == 0, !is.na(duration)) |>
    pull(duration) |>
    quantile(0.95)
}

# Aggregate sessions → machine×week×DOW bucket (winsorized minutes DV)
make_dow_mw <- function(slug, p95_sec) {
  cat(sprintf("  Aggregating %s sessions by day of week...\n", slug))
  read_parquet(
    here::here("data", "ProcessComscore", "merged_cat_session_files",
               paste0(slug, "_sessions.parquet")),
    col_select = c("machine_id", "date", "duration")
  ) |>
    filter(!is.na(duration), !is.na(date)) |>
    mutate(
      week_of_sample = as.integer(
        as.numeric(difftime(as.Date(date), BASE_DATE, units = "days")) %/% 7
      ) + 1L,
      dow     = as.integer(format(as.Date(date), "%u")),  # ISO: Mon=1 … Sun=7
      win_sec = pmin(duration, p95_sec)
    ) |>
    group_by(machine_id, week_of_sample, dow) |>
    summarise(win_min = sum(win_sec) / 60, .groups = "drop")
}

# Bucket stats: share of sessions and winsorized minutes per DOW,
# from control-state sessions (treated==0)
bucket_stats_dow <- function(slug, p95_sec) {
  df <- read_parquet(
    here::here("data", "ProcessComscore", "merged_cat_session_files",
               paste0(slug, "_sessions.parquet")),
    col_select = c("treated", "date", "duration")
  ) |>
    filter(treated == 0, !is.na(duration), !is.na(date)) |>
    mutate(
      dow     = as.integer(format(as.Date(date), "%u")),
      win_sec = pmin(duration, p95_sec)
    )
  total_n   <- nrow(df)
  total_min <- sum(df$win_sec) / 60
  df |>
    group_by(dow) |>
    summarise(
      share_sessions = n() / total_n,
      share_minutes  = sum(win_sec) / 60 / total_min,
      .groups = "drop"
    )
}

# Run TWFE and extract short + long term estimates with ctrl_post_mean
run_twfe <- function(df_joined, dv = "win_min") {
  fml <- as.formula(sprintf(
    "%s ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week",
    dv))
  fit <- tryCatch(
    feols(fml, data = df_joined, cluster = ~state, warn = FALSE, notes = FALSE),
    error = function(e) { cat("    ERROR:", conditionMessage(e), "\n"); NULL }
  )
  if (is.null(fit)) return(NULL)

  cf   <- coef(fit)
  se_v <- sqrt(diag(vcov(fit)))
  ci   <- confint(fit, level = 0.95)

  ctrl_short_mean <- mean(df_joined[[dv]][df_joined$treated == 0 &
                                          df_joined$rel_week %in% SHORT_WINDOW])
  ctrl_long_mean  <- mean(df_joined[[dv]][df_joined$treated == 0 &
                                          df_joined$rel_week %in% LONG_WINDOW])

  bind_rows(lapply(list(
    list(period="short", term="treated:shortterm", ctrl_mean=ctrl_short_mean),
    list(period="long",  term="treated:longterm",  ctrl_mean=ctrl_long_mean)
  ), function(x) {
    b  <- unname(cf[x$term])
    s  <- unname(se_v[x$term])
    lo <- ci[x$term, 1]
    hi <- ci[x$term, 2]
    data.frame(
      period         = x$period,
      beta_m         = b,
      se_m           = s,
      ci_lo_m        = lo,
      ci_hi_m        = hi,
      ctrl_post_mean = x$ctrl_mean,
      pct_change     = b  / x$ctrl_mean,
      pct_ci_lo      = lo / x$ctrl_mean,
      pct_ci_hi      = hi / x$ctrl_mean,
      stringsAsFactors = FALSE
    )
  }))
}

# ── main loop ─────────────────────────────────────────────────────────────────
SITES <- list(
  list(slug = "pornhub", display = "Pornhub", main_key = "PORNHUB_COM"),
  list(slug = "xvideos", display = "Xvideos", main_key = "XVIDEOS_COM")
)

all_results <- bind_rows(lapply(SITES, function(site) {
  slug <- site$slug
  cat(sprintf("\n%s\n%s\n", strrep("─", 55), site$display))

  # Step 1: session P95 threshold
  p95_sec <- compute_session_p95(slug)
  cat(sprintf("  Session P95 = %.0fs (%.1f min)\n", p95_sec, p95_sec / 60))

  # Step 2: aggregate sessions → machine×week×DOW
  mw_dow <- make_dow_mw(slug, p95_sec)
  cat(sprintf("  %s machine-week-DOW rows\n",
              format(nrow(mw_dow), big.mark=",")))

  # Step 3: DOW stats from control sessions
  stats <- bucket_stats_dow(slug, p95_sec)

  # Step 4: pooled validation (sum all DOWs)
  cat("\n  [Pooled validation]\n")
  mw_total <- mw_dow |>
    group_by(machine_id, week_of_sample) |>
    summarise(win_min = sum(win_min), .groups = "drop")

  df_pooled <- stacked_base |>
    left_join(mw_total, by = c("machine_id", "week_of_sample")) |>
    mutate(win_min = coalesce(win_min, 0))

  pooled_res <- run_twfe(df_pooled, "win_min")
  for (per in c("short", "long")) {
    pr <- pooled_res[pooled_res$period == per, ]
    cat(sprintf("    %s-run pooled: β=%.4f (SE=%.4f)\n",
                per, pr$beta_m, pr$se_m))
  }

  # Step 5-6: per-DOW regressions
  cat("\n  [Per-DOW regressions]\n")
  dow_rows <- bind_rows(lapply(seq_len(7L), function(d) {
    cat(sprintf("    DOW %d/7: %s\n", d, DOW_LBLS[d]))

    df_d <- stacked_base |>
      left_join(
        filter(mw_dow, dow == d) |>
          select(machine_id, week_of_sample, win_min),
        by = c("machine_id", "week_of_sample")
      ) |>
      mutate(win_min = coalesce(win_min, 0))

    res <- run_twfe(df_d, "win_min")
    if (is.null(res)) return(NULL)

    st <- stats[stats$dow == d, ]
    res |> mutate(
      site           = site$display,
      dow            = d,
      dow_label      = DOW_LBLS[d],
      share_sessions = if (nrow(st) > 0) st$share_sessions else NA_real_,
      share_minutes  = if (nrow(st) > 0) st$share_minutes  else NA_real_,
      is_total       = FALSE
    )
  }))

  # Append pooled anchor
  pooled_rows <- pooled_res |> mutate(
    site           = site$display,
    dow            = 8L,
    dow_label      = "All",
    share_sessions = NA_real_,
    share_minutes  = NA_real_,
    is_total       = TRUE
  )

  bind_rows(dow_rows, pooled_rows)
}))

# ── save ──────────────────────────────────────────────────────────────────────
out_path <- file.path(OUTDIR, "did_dow_results.csv")
write.csv(all_results, out_path, row.names = FALSE)
cat(sprintf("\nSaved → %s  (%d rows)\n", out_path, nrow(all_results)))
