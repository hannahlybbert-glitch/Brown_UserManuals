# did_tod_buckets.R
# Time-of-day bucket DiD: effect of AV law on winsorized minutes per machine-week,
# broken down by 2-hour local-time bucket.
#
# Buckets: [0,2), [2,4), ..., [22,24) local time
# Local time: UTC (from first_ss2k) + standard-time offset for machine's home state.
# DV: sum of pmin(session_duration, session_P95) / 60 per machine-week-bucket.
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

# ── state → standard-time UTC offset ─────────────────────────────────────────
# Fixed standard-time offsets (no DST). Sessions near bucket boundaries during
# DST (~Mar–Nov) may be misassigned by 1 hour but this is symmetric across
# treated and control and does not bias the DiD.
TZ_OFFSET <- c(
  # Eastern (-5)
  CT=-5, DC=-5, DE=-5, FL=-5, GA=-5, IN=-5, KY=-5, MA=-5, MD=-5, ME=-5,
  MI=-5, NC=-5, NH=-5, NJ=-5, NY=-5, OH=-5, PA=-5, RI=-5, SC=-5, TN=-5,
  VA=-5, VT=-5, WV=-5,
  # Central (-6)
  AL=-6, AR=-6, IA=-6, IL=-6, KS=-6, LA=-6, MN=-6, MO=-6, MS=-6, ND=-6,
  NE=-6, OK=-6, SD=-6, TX=-6, WI=-6,
  # Mountain (-7)
  AZ=-7, CO=-7, ID=-7, MT=-7, NM=-7, UT=-7, WY=-7,
  # Pacific (-8)
  CA=-8, NV=-8, OR=-8, WA=-8,
  # Other
  AK=-9, HI=-10
)

# Bucket labels
N_BUCKETS   <- 12L
BUCKET_LBLS <- c(
  "12–2am", "2–4am", "4–6am", "6–8am",
  "8–10am", "10am–12pm",
  "12–2pm", "2–4pm", "4–6pm", "6–8pm",
  "8–10pm", "10pm–12am"
)

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

# Per-session P95 from control-state sessions
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

# Aggregate sessions → machine×week×TOD bucket (winsorized minutes DV)
make_tod_mw <- function(slug, p95_sec) {
  cat(sprintf("  Aggregating %s sessions by time of day...\n", slug))
  df <- read_parquet(
    here::here("data", "ProcessComscore", "merged_cat_session_files",
               paste0(slug, "_sessions.parquet")),
    col_select = c("machine_id", "date", "first_ss2k", "duration", "state")
  ) |>
    filter(!is.na(duration), !is.na(first_ss2k), state %in% names(TZ_OFFSET)) |>
    mutate(
      week_of_sample = as.integer(
        as.numeric(difftime(as.Date(date), BASE_DATE, units = "days")) %/% 7
      ) + 1L,
      utc_hour   = (first_ss2k %% 86400L) %/% 3600L,
      tz_off     = TZ_OFFSET[state],
      local_hour = (utc_hour + tz_off + 24L) %% 24L,
      bucket     = local_hour %/% 2L + 1L,        # 1–12
      win_sec    = pmin(duration, p95_sec)
    ) |>
    group_by(machine_id, week_of_sample, bucket) |>
    summarise(win_min = sum(win_sec) / 60, .groups = "drop")
  df
}

# Bucket stats: share of sessions and winsorized minutes per bucket,
# from control-state sessions (treated==0)
bucket_stats_tod <- function(slug, p95_sec) {
  df <- read_parquet(
    here::here("data", "ProcessComscore", "merged_cat_session_files",
               paste0(slug, "_sessions.parquet")),
    col_select = c("treated", "post", "first_ss2k", "duration", "state")
  ) |>
    filter(treated == 0, !is.na(duration), !is.na(first_ss2k),
           state %in% names(TZ_OFFSET)) |>
    mutate(
      utc_hour   = (first_ss2k %% 86400L) %/% 3600L,
      tz_off     = TZ_OFFSET[state],
      local_hour = (utc_hour + tz_off + 24L) %% 24L,
      bucket     = local_hour %/% 2L + 1L,
      win_sec    = pmin(duration, p95_sec)
    )
  total_n   <- nrow(df)
  total_min <- sum(df$win_sec) / 60
  df |>
    group_by(bucket) |>
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

  # Step 2: aggregate sessions → machine×week×bucket
  mw_bucket <- make_tod_mw(slug, p95_sec)
  cat(sprintf("  %s machine-week-bucket rows\n",
              format(nrow(mw_bucket), big.mark=",")))

  # Step 3: bucket stats from control sessions
  stats <- bucket_stats_tod(slug, p95_sec)

  # Step 4: pooled validation (sum all buckets)
  cat("\n  [Pooled validation]\n")
  mw_total <- mw_bucket |>
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

  # Step 5-6: per-bucket regressions
  cat("\n  [Per-bucket regressions]\n")
  bucket_rows <- bind_rows(lapply(seq_len(N_BUCKETS), function(b) {
    cat(sprintf("    Bucket %d/12: %s\n", b, BUCKET_LBLS[b]))

    df_b <- stacked_base |>
      left_join(
        filter(mw_bucket, bucket == b) |>
          select(machine_id, week_of_sample, win_min),
        by = c("machine_id", "week_of_sample")
      ) |>
      mutate(win_min = coalesce(win_min, 0))

    res <- run_twfe(df_b, "win_min")
    if (is.null(res)) return(NULL)

    st <- stats[stats$bucket == b, ]
    res |> mutate(
      site           = site$display,
      bucket         = b,
      bucket_label   = BUCKET_LBLS[b],
      share_sessions = if (nrow(st) > 0) st$share_sessions else NA_real_,
      share_minutes  = if (nrow(st) > 0) st$share_minutes  else NA_real_,
      is_total       = FALSE
    )
  }))

  # Append pooled anchor
  pooled_rows <- pooled_res |> mutate(
    site           = site$display,
    bucket         = N_BUCKETS + 1L,
    bucket_label   = "All",
    share_sessions = NA_real_,
    share_minutes  = NA_real_,
    is_total       = TRUE
  )

  bind_rows(bucket_rows, pooled_rows)
}))

# ── save ──────────────────────────────────────────────────────────────────────
out_path <- file.path(OUTDIR, "did_tod_results.csv")
write.csv(all_results, out_path, row.names = FALSE)
cat(sprintf("\nSaved → %s  (%d rows)\n", out_path, nrow(all_results)))
