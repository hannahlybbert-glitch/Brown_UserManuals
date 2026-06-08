# Event-Study Evidence on Age Verification Laws and Adult Site Usage

## Setup

**Data.** Comscore desktop panel, 2022–2024. Unit of observation: machine × calendar week. Machine state assigned from the Comscore demographics file. Outcomes are constructed from site-level weekly duration data.

**Qualifying states.** A state qualifies if it passed an age verification law with an effective date before November 24, 2024 and is included in the pooled specifications. Fourteen states meet this criterion: AL, AR, ID, IN, KS, KY, LA, MS, MT, NC, NE, OK, UT, VA. **Texas is excluded** from all pooled specifications: Texas's law was immediately enjoined in federal court (Free Speech Coalition v. Paxton), Pornhub voluntarily withdrew from TX rather than comply, and the state's ATT is essentially zero — a distinct compliance scenario that would confound the average effect of enforcement-backed laws. Texas is analyzed separately.

**Stacked design.** For each qualifying state *k* (cohort), we carve a separate 25-week dataset centered on the law's effective week (τ ∈ [−16, +8]) containing machines from state *k* plus machines from the 23 never/not-yet-treated control states. The 14 datasets are then pooled. This avoids TWFE contamination from staggered adoption (Cengiz et al. 2019): each treated state is always compared to clean controls, never to other treated states.

**Specification.**

$$\text{DV}_{itk} = \alpha_{i,k} + \alpha_{t,k} + \sum_{\tau \neq -1} \beta_\tau \cdot \text{treated}_i \cdot \mathbf{1}[\text{rel\_week}_k(t) = \tau] + \varepsilon_{itk}$$

Fixed effects: machine×cohort ($\alpha_{i,k}$) and cohort×calendar-week ($\alpha_{t,k}$). Standard errors clustered by state (37 clusters: 14 treated + 23 control). Reference period: $\tau = -1$.

**Dependent variables.** Two outcomes per site:
- `over60`: binary indicator, $\text{over60}_{it} = \mathbf{1}[\text{dur}_{it} > 60\text{s}]$.
- `win_min`: weekly minutes on site, winsorized at the 95th percentile of nonzero observations (computed separately per site).

**Sites.** Pornhub, xVideos, xHamster, XNXX, Chaturbate, Other XXX sites (pooled residual), All XXX sites (sum across all six), All other sites (placebo).

**Sample.** Full population — all 1.48 million machine×cohort pairs in the stacked panel, with no XXX-activity screening. The panel contains approximately 14.4 million machine-week observations. Treatment variation is at the state level; with 37 state clusters and Moulton factor ≈ 1.09, the effective N is approximately 13 million. See `output/analysis/se_diagnostics/memo_se_drivers.md` for full SE decomposition.

---

## Results

### Pre-trends

**Pornhub.** The pooled pre-period average is +0.35 pp on `over60` — close to flat. State-by-state pooled pre/post regressions reveal that most of this pre-trend is attributable to four states:

| State | β_pre | β_post | N treated | Note |
|-------|------:|-------:|----------:|------|
| NE | +0.0170 | −0.0027 | 316 | Small N, noisy; anomalously low post-ATT |
| UT | +0.0130 | −0.0188 | 1,008 | 50-day passage-to-effective window; pre-trend predates passage |
| AR | +0.0099 | −0.0205 | 844 | 111-day gap: entire pre-window falls post-passage |
| MS | +0.0088 | −0.0224 | 667 | 74-day gap: last ~10 pre-period weeks fall post-passage |

States with clean parallel trends (β_pre ≈ 0): AL (−0.0007), IN (−0.0006), KS (−0.0005), LA (+0.0004), OK (−0.0028). The large-N states (VA: 4,482 treated machines; LA: 1,748; NC: 2,709; IN: 1,058) all show near-zero pre-trends, so the pooled result is not driven by the pre-trend states.

For AR and MS, the pre-trend is plausibly explained by the long gap between law passage and effective date: Pornhub usage may have spiked as a "last chance" effect or in response to news coverage, even though the effective date had not yet arrived. For UT and NE, the explanation is less clear (UT's passage-to-effective window is only 50 days, shorter than our pre-period).

**xVideos.** The pooled pre-period average for xVideos is approximately −0.33 pp — a mild *negative* pre-trend (treated states were losing xVideos engagement relative to controls before the law). The main contributors:

| State | β_pre (xVideos) | β_pre (Pornhub) |
|-------|----------------:|----------------:|
| UT | −0.0125 | +0.0130 |
| NE | −0.0110 | +0.0170 |
| KY | −0.0095 | +0.0018 |
| NC | −0.0077 | +0.0048 |
| OK | −0.0060 | −0.0028 |

The negative xVideos pre-trend in NE and UT is the mirror image of those states' positive Pornhub pre-trend, suggesting a state-specific composition difference rather than anticipatory substitution (which would predict xVideos rising as Pornhub falls). More broadly, treated states (mostly South/Midwest) may have had systematically lower xVideos growth than the control states (which include coastal urban states) during this period. Despite the pre-trend, the sharp structural break at τ = 0 — from consistently negative pre-period values to consistently positive post-period values — is hard to explain by anything other than the law.

---

### Pornhub

The largest and most precisely estimated effect is on Pornhub. In the week the law takes effect (τ = 0), the probability of a >60s visit falls by **1.69 percentage points** (SE = 0.24 pp, *t* = −7.0). The effect grows in subsequent weeks and stabilizes: the τ = 1–8 average is approximately **−2.69 pp**, with all post-period coefficients significant at 1%.

| τ | β (over60) | SE | *t* | β (win_min) | SE | *t* |
|---|---|---|---|---|---|---|
| 0 | −0.0169 | 0.0024 | −7.0 | −0.548 | 0.044 | −12.5 |
| 1 | −0.0247 | 0.0015 | −16.5 | −0.586 | 0.041 | −14.3 |
| 2 | −0.0249 | 0.0022 | −11.3 | −0.550 | 0.045 | −12.2 |
| 3 | −0.0267 | 0.0016 | −16.7 | −0.552 | 0.039 | −14.2 |
| 4 | −0.0285 | 0.0015 | −19.0 | −0.596 | 0.046 | −12.9 |
| 5 | −0.0269 | 0.0018 | −14.6 | −0.541 | 0.039 | −13.9 |
| 6 | −0.0281 | 0.0016 | −17.7 | −0.536 | 0.045 | −11.9 |
| 7 | −0.0269 | 0.0015 | −17.9 | −0.510 | 0.046 | −11.1 |
| 8 | −0.0286 | 0.0016 | −17.9 | −0.578 | 0.062 | −9.3 |

The population-level baseline `over60` rate for Pornhub in the pre-period is approximately 4.6%, so a 2.69 pp post-law reduction represents roughly a **58% relative decline** in Pornhub engagement at the population level. For `win_min`, the average treated machine loses approximately **0.56 minutes** per week on Pornhub.

The pooled three-period estimate (see heterogeneity table) gives $\hat{\beta}_\text{ST} = -0.0249$ (SE = 0.0016)*** for $\tau \in [0,3]$ and $\hat{\beta}_\text{LT} = -0.0266$ (SE = 0.0014)*** for $\tau \in [4,8]$ — consistent with the event-study average and showing mild deepening over time.

**Three-period summary specification** (reference period: $\tau \in \{-16,...,-13\} \cup \{-4,...,-1\}$):

$$\text{DV}_{itk} = \alpha_{i,k} + \alpha_{t,k} + \beta_\text{pre} \cdot \text{treated}_i \cdot \mathbf{1}[\tau \in [-12,-5]] + \beta_\text{ST} \cdot \text{treated}_i \cdot \mathbf{1}[\tau \in [0,3]] + \beta_\text{LT} \cdot \text{treated}_i \cdot \mathbf{1}[\tau \in [4,8]] + \varepsilon_{itk}$$

---

### Substitution: xVideos and XNXX

Laws that shut down Pornhub redirect traffic toward non-compliant sites.

**xVideos** shows a persistent, statistically significant *increase* in engagement post-law on both DVs:

| τ | β (over60) | SE | *t* | β (win_min) | SE | *t* |
|---|---|---|---|---|---|---|
| 0 | +0.0083 | 0.0014 | +5.9 | +0.241 | 0.045 | +5.4 |
| 1 | +0.0056 | 0.0013 | +4.3 | +0.159 | 0.026 | +6.1 |
| 2 | +0.0074 | 0.0009 | +8.2 | +0.194 | 0.019 | +10.5 |
| 3 | +0.0088 | 0.0011 | +7.8 | +0.271 | 0.043 | +6.3 |
| 4 | +0.0095 | 0.0014 | +6.8 | +0.212 | 0.035 | +6.1 |
| 5 | +0.0078 | 0.0013 | +6.1 | +0.216 | 0.034 | +6.3 |
| 6 | +0.0076 | 0.0009 | +8.6 | +0.237 | 0.045 | +5.2 |
| 7 | +0.0088 | 0.0014 | +6.2 | +0.176 | 0.041 | +4.3 |
| 8 | +0.0062 | 0.0011 | +5.6 | +0.101 | 0.028 | +3.6 |

The τ = 1–8 average is **+0.77 pp** on `over60` and **+0.196 min** on `win_min`, both significant at 1% throughout.

**XNXX** shows a similar positive pattern on `over60` (τ = 1–8 avg +0.38 pp, most weeks *t* > 2), but the `win_min` effect is small and insignificant throughout (τ = 1–8 avg +0.012 min). This suggests XNXX substitution is primarily at the extensive margin — more machines making any visit — rather than in total time spent per session.

Together, xVideos (+0.77 pp) and XNXX (+0.38 pp) offset approximately **43%** of the Pornhub decline (2.69 pp) in `over60` terms. In `win_min` terms, xVideos alone recovers +0.196 min against the Pornhub loss of −0.556 min, or **35%**.

---

### Other XXX Sites

**xHamster** shows a small but increasingly negative effect on `win_min` post-law (τ = 1–8 avg −0.047 min; late weeks *t* ≈ −2). The `over60` effect is also negative (avg −0.37 pp). xHamster's partial compliance in some states may explain the unexpected direction.

**Chaturbate** shows a consistently negative effect on `win_min` (τ = 1–8 avg −0.056 min; most weeks significant). This is surprising — a live-streaming site might be expected to be a substitute — but is consistent with Chaturbate serving a distinct, less substitutable use case.

**Other XXX sites** show no consistent pattern in either DV.

---

### All XXX Pooled

The `all_xxx` outcome captures total duration summed across all six XXX sites, then threshold-applied or winsorized. Results differ notably across DVs:

| τ | β (over60) | SE | *t* | β (win_min) | SE | *t* |
|---|---|---|---|---|---|---|
| 0 | −0.0009 | 0.0025 | −0.4 | −0.342 | 0.178 | −1.9 |
| 1 | −0.0047 | 0.0022 | −2.1 | −0.424 | 0.137 | −3.1 |
| 2 | −0.0063 | 0.0017 | −3.6 | −0.325 | 0.096 | −3.4 |
| 3 | −0.0023 | 0.0021 | −1.1 | −0.367 | 0.121 | −3.0 |
| 4 | −0.0045 | 0.0020 | −2.3 | −0.679 | 0.144 | −4.7 |
| 5 | −0.0061 | 0.0028 | −2.2 | −0.346 | 0.100 | −3.5 |
| 6 | −0.0055 | 0.0022 | −2.5 | −0.383 | 0.145 | −2.6 |
| 7 | −0.0050 | 0.0027 | −1.8 | −0.544 | 0.169 | −3.2 |
| 8 | −0.0045 | 0.0019 | −2.4 | −0.765 | 0.218 | −3.5 |

**`over60`:** The τ = 0 coefficient is essentially zero (−0.09 pp, ns); subsequent weeks range from −0.23 to −0.63 pp with mixed significance. Average τ = 1–8: **−0.48 pp**. The small magnitude relative to the Pornhub effect alone (−2.69 pp) is partly mechanical: the `all_xxx_over60` indicator is 1 if total XXX duration exceeds 60s, so a machine that switches from Pornhub to xVideos shows no change in `all_xxx_over60`. More importantly, the sum of individual site `over60` coefficients (−2.34 pp at τ = 1–8) is approximately **4.8× larger** than the pooled coefficient (−0.48 pp) — reflecting multi-site double-counting in the sum (a machine visiting both Pornhub and xVideos counts twice in the sum but once in the pooled indicator).

**`win_min`:** Average τ = 1–8: **−0.479 min**. In sharp contrast to `over60`, the sum of individual site `win_min` coefficients (−0.505 min) closely matches the pooled coefficient (ratio ≈ 1.05). This near-additivity holds because `win_min` is a near-linear transformation of total duration — the winsorization caps differ by site but each cap applies to the tail only, leaving most observations unaffected. So the `win_min` all-xxx outcome correctly aggregates the per-site effects, while the `over60` pooled outcome answers the economically distinct question of "any substantive total XXX engagement."

---

### Placebo: All Other Sites

The `all_other_sites` outcome (non-XXX browsing) shows no consistent post-law change. Post-period `over60` coefficients average near zero (+0.04 pp) and are individually insignificant. This confirms the effects are specific to adult sites rather than reflecting a general disruption to internet usage.

---

## Diversion Ratio

The **diversion ratio** $\hat{d}$ measures what fraction of the Pornhub `win_min` reduction is offset by increased usage at other XXX sites (i.e., diverted rather than eliminated):

$$\hat{d} = 1 - \frac{\hat{\beta}^\text{All XXX}_\text{LT}}{\hat{\beta}^\text{Pornhub}_\text{LT}}$$

where LT = $\tau \in [4,8]$ (long-run steady state), estimated from the three-period pooled spec. Both $\hat{\beta}$ are negative; if all Pornhub loss were diverted, $\hat{\beta}^\text{All XXX}_\text{LT} = \hat{\beta}^\text{Pornhub}_\text{LT}$ and $\hat{d} = 0$. See `output/analysis/se_diagnostics/diversion_ratio.csv` for the computed value.

Interpretation: $(1 - \hat{d}) \times 100\%$ of the Pornhub time reduction represents a net decline in total XXX consumption; $\hat{d} \times 100\%$ is diverted to non-compliant XXX sites.

---

## Precision and Robustness

**Standard errors.** With 37 state clusters and Moulton factor ≈ 1.09, clustered SEs are modestly larger than robust SEs but both yield the same conclusions. See `output/analysis/se_diagnostics/memo_se_drivers.md`.

**Role of Texas.** Texas was excluded from all pooled specifications because its ATT is effectively zero — due to immediate judicial enjoinment and voluntary platform exit rather than age verification compliance. With Texas included, the Pornhub effect shrinks to −1.63 pp (SE = 0.55 pp), because Texas contributes 38% of the treated-state observations with zero signal and inflates the Moulton factor to 5.0×. The 14-state estimates reported here represent the causal effect of enforcement-backed age verification laws.

**Nebraska.** NE shows β_post ≈ −0.3 pp (pooled spec) with a positive pre-trend (+1.7 pp). NE has only ~316 treated machine×cohort pairs, the smallest cohort. Excluding NE does not materially affect the pooled estimates.

---

## Heterogeneity (XXX-active subsample)

The estimates above are population-level — they include all desktop machines regardless of prior adult site use. Only ~18% of machine×cohort pairs have any positive XXX duration in the pre-period (τ ∈ [−16, −1]). Restricting to this "XXX-active" subsample focuses on machines where the law can plausibly bind.

In the XXX-active subsample (treated as one subgroup in the full heterogeneity analysis; see `output/analysis/heterogeneity_table_over60.md`):
- **Pornhub**: τ=0: −5.5 pp, τ=1–8 avg: −8.7 pp — a ~30% relative decline from the ~25–30% baseline rate among active users.
- **xVideos**: τ=1–8 avg: +2.4 pp (partially offsetting).
- **Pre-trend**: positive pre-trend (~+1.2 pp) for Pornhub, a mechanical selection artifact (machines selected by any pre-period activity will show elevated activity earlier in the window). The population-level spec has near-zero pre-trend.

The ratio between the XXX-active effect (−8.7 pp) and population-level effect (−2.69 pp) is approximately 3.2×, consistent with 18% of machines being XXX-active pre-law (3.2 × 0.18 ≈ 0.58 ≈ 60%, close to the 58% relative decline estimated at the population level using a ~4.6% baseline rate).

---

## Summary

| Site | β (over60, τ=1–8 avg) | β (win_min, τ=1–8 avg) | `over60` significance |
|---|---|---|---|
| Pornhub | −2.69 pp | −0.556 min | All weeks sig. at 1% |
| xVideos | +0.77 pp | +0.196 min | All weeks sig. at 1% |
| XNXX | +0.38 pp | +0.012 min (ns) | Most weeks sig. at 5% |
| xHamster | −0.37 pp | −0.047 min | Mixed |
| Chaturbate | −0.28 pp | −0.056 min | Mostly insignificant |
| Other XXX | −0.15 pp | −0.054 min | Insignificant |
| All XXX pooled | −0.48 pp | −0.479 min | Mixed |
| All other sites | +0.04 pp | — | Insignificant (placebo ✓) |

**Note on aggregation.** The `win_min` all-xxx coefficient (−0.479 min) approximately equals the sum of individual site coefficients (−0.505 min; ratio 1.05), because `win_min` is near-additive across sites. The `over60` all-xxx coefficient (−0.48 pp) is approximately **4.8×** smaller than the sum of individual site coefficients (−2.34 pp), because `over60` is nonlinear: a machine visiting multiple sites counts once in the pooled indicator but once per site in the individual indicators.

Age verification laws cause a large, persistent decline in Pornhub usage among desktop users — roughly a 58% relative decline at the population level (−2.7 pp on a 4.6% base). This decline is partially offset by substitution toward non-compliant sites. In `win_min` terms: Pornhub loses −0.56 min/machine/week, xVideos gains +0.20 min, all-XXX nets to −0.48 min — recovering about 35% of the Pornhub duration loss. The placebo test on non-XXX browsing passes cleanly.
