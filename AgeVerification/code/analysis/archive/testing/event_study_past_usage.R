# Author: Matt Brown, assisted by Claude
# Created: 2026-03-03
# Purpose: Heterogeneity by pre-period XXX/substitute usage history
#
# Three mutually exclusive subgroups:
#   sub_users  — Any pre-period XV or XNXX usage (XV + XNXX minutes > 0)
#   no_sub     — Pre-period XXX usage but no substitutes (any XXX > 0, XV + XNXX = 0)
#   no_xxx     — No pre-period XXX usage at all
#
# Part A — Event study plots (all 7 sites × 3 subgroups)
# Part B — Pooled pre/ST/LT ATT (7 sites × 3 subgroups × 2 DVs) → markdown tables
#
# Usage:
#   Rscript code/analysis/event_study_past_usage.R
#
# Outputs:
#   output/analysis/event_study_subgroups/{slug}_{subgroup}_over60.png
#   output/analysis/heterogeneity_table_past_usage_over60.md
#   output/analysis/heterogeneity_table_past_usage_win_min.md

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(tidyr)
  library(fixest)
  library(ggplot2)
  library(here)
})

# ============================================================================
# CONSTANTS
# ============================================================================

project_root <- here::here()
data_dir  <- file.path(project_root, "data", "Aggregation", "machine_panel")
demo_file <- file.path(project_root, "data", "ProcessComscore",
                       "full_demographics", "full_machine_person_demos.parquet")
laws_file <- file.path(project_root, "raw", "statelaws", "statelaws_dates.csv")
agg_csv   <- file.path(project_root, "data", "Aggregation", "final_aggregated.csv")
out_subgroups <- file.path(project_root, "output", "analysis", "event_study_subgroups", "past_usage")
out_tables    <- file.path(project_root, "output", "analysis")
dir.create(out_subgroups, recursive = TRUE, showWarnings = FALSE)

EXCLUDE_STATES  <- c("DC", "XX", "ZZ")
EXCLUDE_TREATED <- "TX"
CUTOFF_DATE    <- as.Date("2024-11-24")
T_MIN <- -16L; T_MAX <- 8L
t_range <- T_MIN:T_MAX
MAROON  <- "#8c1515"

XXX_SLUGS <- c("PORNHUB.COM", "CHATURBATE.COM", "XHAMSTER.COM",
                "XNXX.COM",   "XVIDEOS.COM",    "other_XXX_sites")

SITES <- list(
  list(key = "all_xxx",         label = "All XXX",    slug = "all_xxx"),
  list(key = "PORNHUB.COM",     label = "Pornhub",    slug = "PORNHUB_COM"),
  list(key = "XVIDEOS.COM",     label = "xVideos",    slug = "XVIDEOS_COM"),
  list(key = "XHAMSTER.COM",    label = "xHamster",   slug = "XHAMSTER_COM"),
  list(key = "XNXX.COM",        label = "XNXX",       slug = "XNXX_COM"),
  list(key = "CHATURBATE.COM",  label = "Chaturbate", slug = "CHATURBATE_COM"),
  list(key = "other_XXX_sites", label = "Other XXX",  slug = "other_XXX"),
  list(key = "VPN_clean",       label = "VPN (clean)",        slug = "VPN_clean"),
  list(key = "allVPN",          label = "All VPN",            slug = "allVPN")
)

# ============================================================================
# LOAD SHARED DATA
# ============================================================================

cat("Loading week→date map...\n")
week_dates <- read.csv(agg_csv,
    colClasses = c(week_of_sample = "integer", week_start_date = "character")) |>
  select(week_of_sample, week_start_date) |>
  distinct() |>
  mutate(week_start_date = as.Date(week_start_date))

cat("Loading state laws...\n")
laws <- read.csv(laws_file, stringsAsFactors = FALSE, na.strings = c("", "NA"))
laws$day_effective <- as.Date(laws$day_effective, format = "%d%b%Y")
treated_all <- sort(laws$state[!is.na(laws$day_passed)])
law_date    <- setNames(laws$day_effective, laws$state)
qualifying  <- treated_all[!is.na(law_date[treated_all]) &
                            law_date[treated_all] < CUTOFF_DATE &
                            !treated_all %in% EXCLUDE_TREATED]
cat(sprintf("  Qualifying (%d): %s\n", length(qualifying),
            paste(qualifying, collapse = ", ")))

base_date <- as.Date("2022-01-01")
law_wos <- setNames(
  sapply(qualifying, function(s)
    as.integer(law_date[s] - base_date) %/% 7L + 1L),
  qualifying
)

cat("Loading machine demographics...\n")
demos <- read_parquet(demo_file,
    col_select = c("machine_id", "state")) |>
  distinct(machine_id, .keep_all = TRUE) |>
  filter(!state %in% EXCLUDE_STATES)

cat("Loading presence panel...\n")
t0 <- proc.time()
presence <- read_parquet(file.path(data_dir, "machine_week_presence.parquet")) |>
  inner_join(select(demos, machine_id, state), by = "machine_id") |>
  filter(!is.na(state), !state %in% EXCLUDE_STATES)
cat(sprintf("  %s rows | %s machines  (%.1fs)\n",
    format(nrow(presence), big.mark = ","),
    format(n_distinct(presence$machine_id), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))

control_states <- setdiff(unique(presence$state), treated_all)
rm(demos)

# ============================================================================
# BUILD STACKED PANEL
# ============================================================================

cat("\nBuilding stacked panel...\n")
t0 <- proc.time()

stacked_base <- lapply(qualifying, function(s) {
  wos_0        <- law_wos[[s]]
  window_weeks <- wos_0 + t_range
  presence |>
    filter(week_of_sample %in% window_weeks,
           state == s | state %in% control_states) |>
    mutate(
      cohort   = s,
      rel_week = as.integer(week_of_sample - wos_0),
      treated  = as.integer(state == s)
    ) |>
    select(machine_id, week_of_sample, state, cohort, rel_week, treated)
}) |> bind_rows() |>
  mutate(
    machine_cohort = paste0(machine_id, "__", cohort),
    cohort_week    = paste0(cohort,     "__", week_of_sample)
  )

rm(presence)
cat(sprintf("Stacked: %s rows | %s machine×cohort | %d clusters  (%.1fs)\n",
    format(nrow(stacked_base),                      big.mark = ","),
    format(n_distinct(stacked_base$machine_cohort), big.mark = ","),
    n_distinct(stacked_base$state),
    (proc.time() - t0)[["elapsed"]]))

needed_weeks    <- sort(unique(as.integer(outer(unname(law_wos), t_range, "+"))))
needed_machines <- unique(stacked_base$machine_id)

# ============================================================================
# STEP 1 — identify any-XXX-active machine×cohort pairs
# ============================================================================

cat("\nBuilding any-XXX-active set...\n")
t0 <- proc.time()

all_xxx_dur <- lapply(XXX_SLUGS, function(s) {
  open_dataset(file.path(data_dir, paste0("machine_aggregated_", s, ".parquet"))) |>
    filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
    select(machine_id, week_of_sample, total_duration) |>
    collect()
}) |>
  bind_rows() |>
  group_by(machine_id, week_of_sample) |>
  summarise(total_duration = sum(total_duration, na.rm = TRUE), .groups = "drop")

xxx_active_mcs <- stacked_base |>
  filter(rel_week < 0L) |>
  select(machine_id, week_of_sample, machine_cohort) |>
  left_join(all_xxx_dur, by = c("machine_id", "week_of_sample")) |>
  group_by(machine_cohort) |>
  summarise(any_xxx = any(!is.na(total_duration) & total_duration > 0), .groups = "drop") |>
  filter(any_xxx) |>
  pull(machine_cohort)

rm(all_xxx_dur)
cat(sprintf("  xxx-active: %s of %s machine×cohort pairs  (%.1fs)\n",
    format(length(xxx_active_mcs), big.mark = ","),
    format(n_distinct(stacked_base$machine_cohort), big.mark = ","),
    (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# STEP 2 — identify substitute-users (XV or XNXX > 0 in pre-period)
# ============================================================================

cat("\nBuilding substitute-user set (XV or XNXX > 0 in pre-period)...\n")
t0 <- proc.time()

load_site_min <- function(site_slug) {
  open_dataset(file.path(data_dir,
      paste0("machine_aggregated_", site_slug, ".parquet"))) |>
    filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
    select(machine_id, week_of_sample, total_duration) |>
    collect()
}

xv_dur   <- load_site_min("XVIDEOS.COM")
xnxx_dur <- load_site_min("XNXX.COM")

pre_rows <- stacked_base |>
  filter(rel_week < 0L) |>
  select(machine_id, week_of_sample, machine_cohort)

sub_tot_tbl <- pre_rows |>
  left_join(rename(xv_dur,   xv_min   = total_duration), by = c("machine_id", "week_of_sample")) |>
  left_join(rename(xnxx_dur, xnxx_min = total_duration), by = c("machine_id", "week_of_sample")) |>
  replace_na(list(xv_min = 0, xnxx_min = 0)) |>
  group_by(machine_cohort) |>
  summarise(sub_tot = sum(xv_min + xnxx_min), .groups = "drop")

rm(pre_rows, xv_dur, xnxx_dur)

sub_users_mcs <- sub_tot_tbl |> filter(sub_tot > 0) |> pull(machine_cohort)
no_sub_mcs    <- setdiff(xxx_active_mcs, sub_users_mcs)   # XXX-active but no XV/XNXX
no_xxx_mcs    <- setdiff(unique(stacked_base$machine_cohort), xxx_active_mcs)

cat(sprintf("  Sub-users (XV/XNXX > 0): %s\n", format(length(sub_users_mcs), big.mark = ",")))
cat(sprintf("  XXX-active, no subs:     %s\n", format(length(no_sub_mcs),    big.mark = ",")))
cat(sprintf("  No XXX at all:           %s\n", format(length(no_xxx_mcs),    big.mark = ",")))
cat(sprintf("  (%.1fs)\n", (proc.time() - t0)[["elapsed"]]))

# ============================================================================
# SUBGROUPS
# ============================================================================

SUBGROUPS <- list(
  list(id = "sub",       label = "Any substitute usage (XV or XNXX)",
       fn = function(df) filter(df, machine_cohort %in% sub_users_mcs)),
  list(id = "no_sub",    label = "XXX-active, no substitute usage",
       fn = function(df) filter(df, machine_cohort %in% no_sub_mcs)),
  list(id = "no_xxx",    label = "No past XXX usage",
       fn = function(df) filter(df, machine_cohort %in% no_xxx_mcs))
)

cat("\nSubgroup sizes (machine×cohort pairs):\n")
for (sg in SUBGROUPS) {
  n <- n_distinct(sg$fn(stacked_base)$machine_cohort)
  cat(sprintf("  %-40s %s\n", sg$label, format(n, big.mark = ",")))
}

# ============================================================================
# HELPERS
# ============================================================================

load_site_duration <- function(site_key) {
  if (site_key == "all_xxx") {
    lapply(XXX_SLUGS, function(s) {
      open_dataset(file.path(data_dir, paste0("machine_aggregated_", s, ".parquet"))) |>
        filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
        select(machine_id, week_of_sample, total_duration) |>
        collect()
    }) |>
      bind_rows() |>
      group_by(machine_id, week_of_sample) |>
      summarise(total_duration = sum(total_duration, na.rm = TRUE), .groups = "drop")
  } else {
    open_dataset(file.path(data_dir, paste0("machine_aggregated_", site_key, ".parquet"))) |>
      filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
      select(machine_id, week_of_sample, total_duration) |>
      collect()
  }
}

compute_p95_2022 <- function(site_key) {
  dur <- if (site_key == "all_xxx") {
    lapply(XXX_SLUGS, function(s) {
      open_dataset(file.path(data_dir, paste0("machine_aggregated_", s, ".parquet"))) |>
        filter(week_of_sample %in% 1:52, machine_id %in% needed_machines) |>
        select(machine_id, week_of_sample, total_duration) |>
        collect()
    }) |>
      bind_rows() |>
      group_by(machine_id, week_of_sample) |>
      summarise(total_duration = sum(total_duration, na.rm = TRUE), .groups = "drop")
  } else {
    open_dataset(file.path(data_dir, paste0("machine_aggregated_", site_key, ".parquet"))) |>
      filter(week_of_sample %in% 1:52, machine_id %in% needed_machines) |>
      select(total_duration) |>
      collect()
  }
  quantile(dur$total_duration[dur$total_duration > 0], 0.95, na.rm = TRUE)
}

extract_coefs <- function(fit) {
  idx   <- grep("treated", names(coef(fit)))
  betas <- coef(fit)[idx]
  se_v  <- sqrt(diag(vcov(fit)))[idx]
  ci    <- confint(fit, level = 0.95)[idx, , drop = FALSE]
  coefs <- data.frame(
    rel_week = as.integer(regmatches(names(betas), regexpr("-?\\d+", names(betas)))),
    beta     = as.numeric(betas),
    se       = as.numeric(se_v),
    ci_lo    = ci[, 1],
    ci_hi    = ci[, 2],
    stringsAsFactors = FALSE
  )
  ref_row <- data.frame(rel_week = -1L, beta = 0, se = NA_real_, ci_lo = 0, ci_hi = 0)
  bind_rows(coefs, ref_row) |> arrange(rel_week)
}

save_subgroup_plot <- function(coefs, site_label, subgroup_label, slug, sg_slug, n_cl, baseline_mean) {
  p <- ggplot(coefs, aes(x = rel_week)) +
    geom_errorbar(aes(ymin = ci_lo, ymax = ci_hi), width = 0.3, color = MAROON, linewidth = 0.6) +
    geom_line(aes(y = beta),  color = MAROON, linewidth = 0.9) +
    geom_point(aes(y = beta), color = MAROON, size = 2) +
    geom_hline(yintercept = 0, linetype = "dashed", linewidth = 0.5) +
    geom_vline(xintercept = 0, linetype = "dashed", color = "gray50", linewidth = 0.5) +
    annotate("text", x = 0.25, y = 0,
             label = sprintf("(mean = %.3f)", baseline_mean),
             hjust = 0, vjust = 1.6, size = 2.8, color = "gray40") +
    scale_x_continuous(breaks = seq(T_MIN, T_MAX, by = 4)) +
    labs(
      x        = "Weeks relative to law effective date",
      y        = "Change in winsorized min/week",
      title    = sprintf("Stacked TWFE — %s  (%s)", site_label, subgroup_label),
      subtitle = sprintf(
        "Machine×cohort + cohort×week FE  |  SE clustered by state (%d clusters, %d cohorts)",
        n_cl, length(qualifying))
    ) +
    theme_bw() +
    theme(
      panel.grid.minor = element_blank(),
      panel.border     = element_blank(),
      axis.line        = element_line(color = "black", linewidth = 0.4),
      plot.title       = element_text(size = 12),
      plot.subtitle    = element_text(size = 8, color = "gray40"),
      axis.title       = element_text(size = 10),
      axis.text        = element_text(size = 9)
    )
  path <- file.path(out_subgroups, sprintf("%s_%s_win_min.png", slug, sg_slug))
  ggsave(path, p, width = 9, height = 4.5, dpi = 300)
  cat(sprintf("    → %s\n", path))
  invisible(p)
}

fmt_coef <- function(beta, se) sprintf("%.4f (%.4f)", beta, se)

run_pooled <- function(df, dv) {
  df2 <- df |>
    mutate(
      pre       = as.integer(rel_week %in% -16:-5),
      shortterm = as.integer(rel_week %in% 0:3),
      longterm  = as.integer(rel_week %in% 4:8)
    )
  fml <- as.formula(
    sprintf("%s ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week", dv)
  )
  tryCatch({
    fit  <- feols(fml, data = df2, cluster = ~state, warn = FALSE, notes = FALSE)
    cf   <- coef(fit)
    se_v <- sqrt(diag(vcov(fit)))
    pv   <- 2 * pnorm(-abs(cf / se_v))
    list(
      beta_pre       = unname(cf["treated:pre"]),
      se_pre         = unname(se_v["treated:pre"]),
      beta_shortterm = unname(cf["treated:shortterm"]),
      se_shortterm   = unname(se_v["treated:shortterm"]),
      p_shortterm    = unname(pv["treated:shortterm"]),
      beta_longterm  = unname(cf["treated:longterm"]),
      se_longterm    = unname(se_v["treated:longterm"]),
      p_longterm     = unname(pv["treated:longterm"]),
      n              = fit$nobs
    )
  }, error = function(e) {
    cat(sprintf("    ERROR: %s\n", conditionMessage(e)))
    list(beta_pre = NA_real_, se_pre = NA_real_,
         beta_shortterm = NA_real_, se_shortterm = NA_real_, p_shortterm = NA_real_,
         beta_longterm  = NA_real_, se_longterm  = NA_real_, p_longterm  = NA_real_,
         n = 0L)
  })
}

# ============================================================================
# RESULT STORAGE
# ============================================================================

dvs <- c("over60", "win_min")
sg_labels   <- sapply(SUBGROUPS, `[[`, "label")
site_labels <- sapply(SITES,     `[[`, "label")

results <- lapply(dvs, function(dv) {
  make_mat <- function()
    matrix(NA_character_, nrow = length(SUBGROUPS), ncol = length(SITES),
           dimnames = list(sg_labels, site_labels))
  list(ST = make_mat(), LT = make_mat(), PRE = make_mat())
})
names(results) <- dvs

# ============================================================================
# PRE-BUILD XXX SITE WIN_MINS (used for all_xxx and individual XXX sites)
# ============================================================================
cat("\nPre-building per-site XXX win_min (for all_xxx additive construction)...\n")
t0_prebuilt <- proc.time()

xxx_win_prebuilt <- lapply(XXX_SLUGS, function(s) {
  t1 <- proc.time()
  p95_s <- compute_p95_2022(s)
  dur_s <- open_dataset(file.path(data_dir, paste0("machine_aggregated_", s, ".parquet"))) |>
    filter(week_of_sample %in% needed_weeks, machine_id %in% needed_machines) |>
    select(machine_id, week_of_sample, total_duration) |>
    collect()
  result <- dur_s |>
    mutate(win_min_s = pmin(total_duration, p95_s) / 60) |>
    select(machine_id, week_of_sample, win_min_s)
  names(result)[3] <- paste0("win_", gsub("[^A-Za-z0-9]", "_", s))
  cat(sprintf("  %s: p95 = %.1f min  (%.1fs)\n", s, p95_s / 60,
              (proc.time() - t1)[["elapsed"]]))
  result
})

xxx_win_wide <- Reduce(
  function(a, b) full_join(a, b, by = c("machine_id", "week_of_sample")),
  xxx_win_prebuilt
) |>
  mutate(win_min_allxxx = rowSums(across(starts_with("win_")), na.rm = TRUE))

rm(xxx_win_prebuilt)
cat(sprintf("Pre-build complete: %s rows  (%.1fs total)\n",
    format(nrow(xxx_win_wide), big.mark = ","),
    (proc.time() - t0_prebuilt)[["elapsed"]]))

# ============================================================================
# MAIN LOOP — 7 sites
# ============================================================================
cat("\n", strrep("=", 60), "\n", sep = "")
cat("Running regressions: 7 sites × 3 subgroups\n")
cat(strrep("=", 60), "\n\n", sep = "")

for (s_idx in seq_along(SITES)) {
  site <- SITES[[s_idx]]
  cat(sprintf("--- %s (%s) ---\n", site$label, site$key))

  t0       <- proc.time()
  dur_data <- load_site_duration(site$key)
  cat(sprintf("  Loaded: %s rows  (%.1fs)\n",
      format(nrow(dur_data), big.mark = ","),
      (proc.time() - t0)[["elapsed"]]))

  df_site <- stacked_base |>
    left_join(dur_data, by = c("machine_id", "week_of_sample"))
  rm(dur_data)

  if (site$key == "all_xxx") {
    p95 <- compute_p95_2022(site$key)
    cat(sprintf("  p95 (summed, ref only) = %.1fs (%.1f min)\n", p95, p95 / 60))
    df_site <- df_site |>
      mutate(over60 = as.integer(!is.na(total_duration) & total_duration > 60)) |>
      left_join(select(xxx_win_wide, machine_id, week_of_sample, win_min_allxxx),
                by = c("machine_id", "week_of_sample")) |>
      mutate(win_min = coalesce(win_min_allxxx, 0)) |>
      select(-win_min_allxxx)

  } else if (site$key %in% XXX_SLUGS) {
    win_col <- paste0("win_", gsub("[^A-Za-z0-9]", "_", site$key))
    df_site <- df_site |>
      mutate(over60 = as.integer(!is.na(total_duration) & total_duration > 60)) |>
      left_join(select(xxx_win_wide, machine_id, week_of_sample, all_of(win_col)),
                by = c("machine_id", "week_of_sample")) |>
      rename(win_min = all_of(win_col)) |>
      mutate(win_min = coalesce(win_min, 0))

  } else {
    p95 <- compute_p95_2022(site$key)
    cat(sprintf("  p95 = %.1fs (%.1f min)\n", p95, p95 / 60))
    df_site <- df_site |>
      mutate(
        over60  = as.integer(!is.na(total_duration) & total_duration > 60),
        win_min = pmin(replace(total_duration, is.na(total_duration), 0), p95) / 60
      )
  }

  # ---- Part A: event study plots ----
  cat("  Part A — event study plots\n")
  for (sg in SUBGROUPS) {
    df_g <- sg$fn(df_site)
    n_cl <- n_distinct(df_g$state)
    baseline_mean <- mean(df_g$win_min[df_g$treated == 1L & df_g$rel_week == -1L], na.rm = TRUE)
    cat(sprintf("    %s: N=%s, %d clusters\n",
        sg$label, format(nrow(df_g), big.mark = ","), n_cl))
    tryCatch({
      fit <- feols(win_min ~ i(rel_week, treated, ref = -1) | machine_cohort + cohort_week,
                   data = df_g, cluster = ~state, warn = FALSE, notes = FALSE)
      coefs <- extract_coefs(fit)
      save_subgroup_plot(coefs, site$label, sg$label, site$slug, sg$id, n_cl, baseline_mean)
    }, error = function(e) {
      cat(sprintf("    ERROR (%s): %s\n", sg$label, conditionMessage(e)))
    })
  }

  # ---- Part B: pooled pre/post ----
  cat("  Part B — pooled pre/post\n")
  for (dv in dvs) {
    for (sg_idx in seq_along(SUBGROUPS)) {
      sg    <- SUBGROUPS[[sg_idx]]
      df_sg <- sg$fn(df_site)
      cat(sprintf("    %s / %-40s N=%s\n",
          dv, sg$label, format(nrow(df_sg), big.mark = ",")))
      res <- run_pooled(df_sg, dv)
      if (!is.na(res$beta_shortterm)) {
        results[[dv]][["ST"]] [sg_idx, s_idx] <- fmt_coef(res$beta_shortterm, res$se_shortterm)
        results[[dv]][["LT"]] [sg_idx, s_idx] <- fmt_coef(res$beta_longterm,  res$se_longterm)
        results[[dv]][["PRE"]][sg_idx, s_idx] <- fmt_coef(res$beta_pre,       res$se_pre)
      }
    }
  }

  rm(df_site)
  cat("\n")
}

# ============================================================================
# WRITE MARKDOWN TABLES
# ============================================================================

write_md_table <- function(res_mats, dv_label, filepath) {
  sl       <- colnames(res_mats[["ST"]])
  sg       <- rownames(res_mats[["ST"]])
  header   <- paste0("| Estimate | ", paste(sl, collapse = " | "), " |")
  sep_line <- paste0("|", paste(rep(":---|", length(sl) + 1L), collapse = ""))

  make_row <- function(label, mat, sg_name) {
    vals <- mat[sg_name, ]
    vals[is.na(vals)] <- "—"
    paste0("| **", label, "** | ", paste(vals, collapse = " | "), " |")
  }

  content <- c(
    sprintf("# Heterogeneity by Past Usage — %s\n", dv_label),
    "Pooled three-period TWFE. `dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week`. SE clustered by state.  ",
    "Reference period: τ ∈ {−4,...,−1}. β_ST: τ ∈ [0,3]. β_LT: τ ∈ [4,8]. β_pre: τ ∈ [−16,−5]. Format: β (SE).  ",
    "Subgroups defined by pre-period usage: **sub_users** = any XV or XNXX > 0; **no_sub** = any XXX but no XV/XNXX; **no_xxx** = no XXX at all.\n"
  )
  for (s in sg) {
    content <- c(content,
      sprintf("## %s\n", s),
      header,
      sep_line,
      make_row("β_ST",  res_mats[["ST"]],  s),
      make_row("β_LT",  res_mats[["LT"]],  s),
      make_row("β_pre", res_mats[["PRE"]], s),
      ""
    )
  }
  writeLines(content, filepath)
  cat(sprintf("Wrote: %s\n", filepath))
}

cat(strrep("=", 60), "\n", sep = "")
cat("Writing tables\n")
cat(strrep("=", 60), "\n\n", sep = "")

write_md_table(
  results[["over60"]],
  "Pr(>60s on site) — over60",
  file.path(out_tables, "heterogeneity_table_past_usage_over60.md")
)

write_md_table(
  results[["win_min"]],
  "Winsorized min/machine/week (p95) — win_min",
  file.path(out_tables, "heterogeneity_table_past_usage_win_min.md")
)

cat("\nAll done.\n")
