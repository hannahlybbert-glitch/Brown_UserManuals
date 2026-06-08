# did_session_buckets.R
# Session-bucket DiD: effect of AV law on winsorized minutes per machine-week,
# broken down by per-session duration bucket.
#
# Bucket boundaries: [0,1], (1,5], (5,10], (10,15], (20,25], ... (5-min steps)
# up to the per-session P95 computed from control-period sessions.
# Last bucket = (last_5min_break, P95] labeled "(win.)".
#
# DV: sum of min(session_duration, p95) / 60 per machine-week-bucket.
# Effects reported as % change vs. control-state mean in post period.
#
# Runs pooled (all-bucket) regression FIRST as a sanity check vs. main win_min.

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

# ── reference: existing win_min results ───────────────────────────────────────
main_res <- readRDS(here::here("output", "analysis", "intermediate",
                               "regression_results.rds"))
ref_est <- function(site_slug, period) {
  r    <- main_res[["pooled"]][[site_slug]][["win_min"]]
  term <- if (period == "short") "beta_shortterm" else "beta_longterm"
  se_t <- if (period == "short") "se_shortterm"   else "se_longterm"
  list(beta = r[[term]], se = r[[se_t]])
}

# ── helpers ───────────────────────────────────────────────────────────────────

# Per-session P95 from control-period sessions (treated==0)
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

# Build bucket breakpoints (seconds): [0,1], (1,5], (5,10], ..., (k,P95]
make_edges <- function(p95_sec) {
  p95_min       <- p95_sec / 60
  fixed_breaks  <- c(0, 1, seq(5, floor(p95_min / 5) * 5, by = 5))
  fixed_breaks  <- fixed_breaks[fixed_breaks < p95_min]
  c(fixed_breaks, p95_min) * 60   # back to seconds
}

# Human-readable label for each bucket
make_labels <- function(edges_sec, p95_sec) {
  n   <- length(edges_sec) - 1L
  fmt <- function(x) sprintf("%.0f", x / 60)
  lbl <- sprintf("(%s,%s]", sapply(edges_sec[-length(edges_sec)], fmt),
                             sapply(edges_sec[-1], fmt))
  lbl[1] <- sprintf("[0,%s]", fmt(edges_sec[2]))   # closed on left for first bucket
  lbl[n] <- sprintf("(%s,%.1f]\n(win.)",
                    fmt(edges_sec[n]), p95_sec / 60)
  lbl
}

# Aggregate sessions → machine×week×bucket (winsorized minutes DV)
make_bucket_mw <- function(slug, edges_sec, p95_sec) {
  cat(sprintf("  Aggregating %s sessions...\n", slug))
  read_parquet(
    here::here("data", "ProcessComscore", "merged_cat_session_files",
               paste0(slug, "_sessions.parquet")),
    col_select = c("machine_id", "date", "duration")
  ) |>
    filter(!is.na(duration)) |>
    mutate(
      week_of_sample = as.integer(
        as.numeric(difftime(as.Date(date), BASE_DATE, units = "days")) %/% 7
      ) + 1L,
      win_sec = pmin(duration, p95_sec),
      bucket  = findInterval(duration, edges_sec, rightmost.closed = TRUE),
      bucket  = pmax(1L, pmin(bucket, length(edges_sec) - 1L))
    ) |>
    group_by(machine_id, week_of_sample, bucket) |>
    summarise(win_min = sum(win_sec) / 60, .groups = "drop")
}

# Bucket stats from pre-law control sessions
bucket_stats <- function(slug, edges_sec, p95_sec, n_buckets) {
  df <- read_parquet(
    here::here("data", "ProcessComscore", "merged_cat_session_files",
               paste0(slug, "_sessions.parquet")),
    col_select = c("treated", "post", "duration")
  ) |>
    filter(treated == 0, post == 0 | is.na(post), !is.na(duration)) |>
    mutate(
      win_sec = pmin(duration, p95_sec),
      bucket  = findInterval(duration, edges_sec, rightmost.closed = TRUE),
      bucket  = pmax(1L, pmin(bucket, n_buckets))
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
run_twfe <- function(df_joined, dv = "win_min", slug_label = "") {
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

  # control-post means for normalisation
  ctrl_short_mean <- mean(df_joined[[dv]][df_joined$treated == 0 &
                                          df_joined$rel_week %in% SHORT_WINDOW])
  ctrl_long_mean  <- mean(df_joined[[dv]][df_joined$treated == 0 &
                                          df_joined$rel_week %in% LONG_WINDOW])

  bind_rows(lapply(list(
    list(period="short", term="treated:shortterm", ctrl_mean=ctrl_short_mean),
    list(period="long",  term="treated:longterm",  ctrl_mean=ctrl_long_mean)
  ), function(x) {
    b    <- unname(cf[x$term])
    s    <- unname(se_v[x$term])
    lo   <- ci[x$term, 1]
    hi   <- ci[x$term, 2]
    data.frame(
      period        = x$period,
      beta_m        = b,
      se_m          = s,
      ci_lo_m       = lo,
      ci_hi_m       = hi,
      ctrl_post_mean = x$ctrl_mean,
      pct_change    = b  / x$ctrl_mean,
      pct_ci_lo     = lo / x$ctrl_mean,
      pct_ci_hi     = hi / x$ctrl_mean,
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

  # ── Step 1: bucket definitions ─────────────────────────────────────────────
  p95_sec   <- compute_session_p95(slug)
  edges_sec <- make_edges(p95_sec)
  n_buckets <- length(edges_sec) - 1L
  labels    <- make_labels(edges_sec, p95_sec)

  cat(sprintf("  Per-session P95 = %.1fs (%.1f min)\n", p95_sec, p95_sec/60))
  cat(sprintf("  Buckets (%d): %s\n", n_buckets, paste(labels, collapse=" | ")))

  # ── Step 2: aggregate sessions → machine×week×bucket ─────────────────────
  mw_bucket <- make_bucket_mw(slug, edges_sec, p95_sec)

  # ── Step 3: bucket stats (share of sessions & minutes) ────────────────────
  stats <- bucket_stats(slug, edges_sec, p95_sec, n_buckets)

  # ── Step 4: pooled validation regression ──────────────────────────────────
  cat("\n  [Pooled validation regression]\n")
  mw_total <- mw_bucket |>
    group_by(machine_id, week_of_sample) |>
    summarise(win_min = sum(win_min), .groups = "drop")

  df_pooled <- stacked_base |>
    left_join(mw_total, by = c("machine_id", "week_of_sample")) |>
    mutate(win_min = coalesce(win_min, 0))

  pooled_res <- run_twfe(df_pooled, "win_min")

  cat("  Pooled result (this script vs. main regression):\n")
  for (per in c("short", "long")) {
    pr  <- pooled_res[pooled_res$period == per, ]
    ref <- ref_est(site$main_key, per)
    cat(sprintf("    %s-run:  pooled = %.4f (SE %.4f) | main win_min = %.4f (SE %.4f)\n",
                per, pr$beta_m, pr$se_m, ref$beta, ref$se))
  }

  # ── Step 5-6: per-bucket regressions ──────────────────────────────────────
  cat("\n  [Per-bucket regressions]\n")
  bucket_rows <- bind_rows(lapply(seq_len(n_buckets), function(b) {
    cat(sprintf("    Bucket %d/%d: %s\n", b, n_buckets,
                gsub("\n", " ", labels[b])))

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
      bucket_label   = labels[b],
      share_sessions = if (nrow(st) > 0) st$share_sessions else NA_real_,
      share_minutes  = if (nrow(st) > 0) st$share_minutes  else NA_real_,
      is_total       = FALSE
    )
  }))

  # ── append pooled anchor row ───────────────────────────────────────────────
  pooled_rows <- pooled_res |> mutate(
    site           = site$display,
    bucket         = n_buckets + 1L,
    bucket_label   = "Total\nmin",
    share_sessions = NA_real_,
    share_minutes  = NA_real_,
    is_total       = TRUE
  )

  bind_rows(bucket_rows, pooled_rows)
}))

# ── save ──────────────────────────────────────────────────────────────────────
out_path <- file.path(OUTDIR, "did_bucket_results.csv")
write.csv(all_results, out_path, row.names = FALSE)
cat(sprintf("\nSaved → %s  (%d rows)\n", out_path, nrow(all_results)))
