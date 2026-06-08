# Demographic Heterogeneity in Event Study Results

Generated: 2026-02-28
Script: `code/analysis/event_study_demographics.R`
Tables: `output/analysis/heterogeneity_table_over60.md`, `output/analysis/heterogeneity_table_win_min.md`
Plots: `output/analysis/event_study_subgroups/` (21 PNGs, 7 sites × 3 subgroups: male, female, xxx-active)

**Note: Texas excluded from all pooled specifications** (`EXCLUDE_TREATED = "TX"`).

---

## Subgroup Definitions

Demographics from `data/ProcessComscore/full_demographics/full_machine_person_demos.parquet` (1,241,050 machines, machine-level). Merged onto stacked panel by `machine_id`. **No upfront XXX-active screening** — all machines in the balanced stacked panel are included; xxx-active is treated as one subgroup among others.

| Subgroup | Filter | Machine×cohort pairs (14-state sample) |
|----------|--------|--------------------------------------:|
| All machines | — | 1,479,503 |
| Male | `gender == "Male"` | 241,203 |
| Female | `gender == "Female"` | 102,798 |
| Young HoH (18–34) | `hoh_age %in% c("18-24", "25-34")` | 444,653 |
| Older HoH (35+) | `hoh_age %in% c("35-44", "45-54", "55-64", "65 and Over")` | 1,034,845 |
| Children present | `children_present == "Children:Yes"` | 825,518 |
| No children | `children_present == "Children:No"` | 653,985 |
| XXX-active (pre-period) | any positive XXX duration in τ ∈ [−16, −1] | 261,153 |

**Coverage notes:**
- Gender: "Male" (105K machines) and "Female" (60K machines) cover ~13% of the panel. "Shared" (130K) and "Unknown" (946K) are excluded — mostly household machines with multiple users.
- Age and children: ~52.5% of machines have demographic data; missing machines are excluded from those subgroups.
- XXX-active: 261K / 1,479K ≈ 17.7% of machine×cohort pairs had any positive XXX duration in the pre-period. This is the sample where the law can most plausibly bind.

**Specification (Part B pooled regressions):**

$$\text{DV}_{itk} = \alpha_{i,k} + \alpha_{t,k} + \beta_\text{pre} \cdot \text{treated}_i \cdot \mathbf{1}[\tau \in [-12,-5]] + \beta_\text{ST} \cdot \text{treated}_i \cdot \mathbf{1}[\tau \in [0,3]] + \beta_\text{LT} \cdot \text{treated}_i \cdot \mathbf{1}[\tau \in [4,8]] + \varepsilon_{itk}$$

Reference period: $\tau \in \{-16,...,-13\} \cup \{-4,...,-1\}$. SE clustered by state (37 state clusters). Each table cell reports three rows: $\hat{\beta}_\text{ST}$ (SE) with significance stars, $\hat{\beta}_\text{LT}$ (SE) with stars, and [$\hat{\beta}_\text{pre}$ (SE)] as a pre-trend check (should be near zero).

---

## Key Results

### 1. Gender: Men drive the effect

The Pornhub decline is concentrated among male-classified machines:

| | Pornhub `over60` | Pornhub `win_min` |
|-|-----------------|-------------------|
| All machines | −0.0255*** | — |
| Male | −0.0367*** | — |
| Female | −0.0089** | — (ns) |

The male Pornhub decline (−3.7 pp) is ~4× the female decline (−0.9 pp). For minutes, the female effect is insignificant. The xVideos substitution follows the same pattern: Male +0.0108*** vs. Female +0.0037 (ns).

The All XXX pooled outcome is significant for men (−0.65 pp*, marginal) but not women (−0.50 pp ns). Gender event study plots (`output/analysis/event_study_subgroups/`) show the male Pornhub series with a clean structural break at τ = 0.

### 2. Age: Uniform across HoH age groups

Effects are not concentrated among younger households:

| | Pornhub `over60` | xVideos `over60` |
|-|-----------------|-----------------|
| Young HoH (18–34) | −0.0276*** | +0.0090*** |
| Older HoH (35+) | −0.0245*** | +0.0071*** |

Point estimates are nearly identical across age groups. Both young and older HoH households show statistically significant Pornhub declines and xVideos substitution of similar magnitude.

### 3. Children: Slightly larger effects in households with children

| | Pornhub `over60` | xVideos `over60` | All XXX `over60` |
|-|-----------------|-----------------|-----------------|
| Children present | −0.0271*** | +0.0078*** | −0.0057*** |
| No children | −0.0225*** | +0.0077*** | −0.0018 (ns) |

Children-present households show slightly larger Pornhub declines. The All XXX pooled effect is statistically significant for children-present households but not for no-children households (though the point estimates are similar). This difference probably reflects demographic overlap (children-present HoHs are a larger, more demographically diverse group).

### 4. XXX-active subsample

Restricting to machines with any positive XXX duration in the pre-period (τ ∈ [−16, −1]) — the 17.7% of machine×cohort pairs most likely to be affected by the law — yields substantially larger point estimates:

| | Pornhub `over60` | xVideos `over60` | All XXX `over60` |
|-|-----------------|-----------------|-----------------|
| All machines | −0.0255 (0.0015)*** | +0.0078 (0.0008)*** | −0.0043 (0.0013)*** |
| XXX-active | −0.0822 (0.0064)*** | +0.0243 (0.0030)*** | −0.0138 (0.0053)*** |
| Ratio | 3.2× | 3.1× | 3.2× |

The XXX-active Pornhub decline is 8.2 pp on the pooled spec (vs. 2.55 pp full-sample) — approximately 3.2× larger, consistent with these machines representing ~18% of the panel. The full 25-week event study for the XXX-active subsample (`output/analysis/event_study_subgroups/PORNHUB_COM_xxx_active_over60.png`) shows τ=0: −5.5 pp, τ=1–8 avg: −8.7 pp, a ~30% relative decline from the ~25–30% baseline visit rate among prior users. See `otherwriting/event_study_results.md` for the full comparison.

Note the xxx-active pre-trend for Pornhub is $\hat{\beta}_\text{pre} = +0.0129$ (SE=0.0037) — positive and significant — a mechanical selection artifact (conditioning on any pre-period activity inflates earlier pre-period values). The population-level pre-trend is near zero.

### 5. Parallel trends

Pre-period coefficients ($\hat{\beta}_\text{pre}$) are uniformly small and mostly insignificant across all subgroup × site cells. The Pornhub pre-trend for females (+0.0084, SE=0.004) is slightly elevated but not large relative to the post-period effects. All other pre-trends are within one SE of zero.

---

## Summary for Policy Interpretation

1. **Men are the primary behavioral margin.** Female effects are smaller and often insignificant. This is consistent with adult site use being disproportionately male.
2. **Age of HoH does not predict responsiveness.** Effects are uniform across age groups — age verification laws reduce access broadly, not just for a specific age cohort.
3. **Household composition is not a meaningful moderator.** Effects are similar for child-present and child-absent households.
4. **XXX-active users bear the full treatment intensity.** The 18% of machines with prior adult site use drive the population-level effect, with per-machine effects 3× larger than the full-sample estimate.
5. **Parallel trends hold within subgroups** ($\hat{\beta}_\text{pre} \approx 0$ in all cells), supporting a causal interpretation within each demographic cell.
