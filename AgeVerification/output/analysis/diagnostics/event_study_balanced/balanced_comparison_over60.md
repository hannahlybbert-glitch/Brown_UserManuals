# Balanced vs Unbalanced Panel — Pr(>60s on site) — over60

Pooled three-period TWFE: `dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week`. SE clustered by state.  
β_ST: τ ∈ [0,3]. β_LT: τ ∈ [4,8]. β_pre: τ ∈ [−16,−5].  
**Balanced** = machine×cohort pairs present in all 25 event-window weeks. Format: β (SE).

| Estimate | All XXX (pooled) (Unbal) | Pornhub (Unbal) | xVideos (Unbal) | All XXX (pooled) (Bal) | Pornhub (Bal) | xVideos (Bal) |
|:---|:---|:---|:---|:---|:---|:---|
| **β_pre** | 0.0000 (0.0008) | -0.0007 (0.0004) | -0.0008 (0.0004) | 0.0040 (0.0022) | 0.0000 (0.0016) | -0.0023 (0.0015) |
| **β_ST** | -0.0031 (0.0008) | -0.0200 (0.0018) | 0.0084 (0.0006) | -0.0055 (0.0015) | -0.0335 (0.0020) | 0.0126 (0.0011) |
| **β_LT** | -0.0052 (0.0010) | -0.0292 (0.0016) | 0.0112 (0.0011) | -0.0055 (0.0031) | -0.0495 (0.0034) | 0.0166 (0.0025) |
| **N (obs) / N (m×c)** | 15,230,112 / 1,591,680 | 15,230,112 / 1,591,680 | 15,230,112 / 1,591,680 | 2,267,650 / 90,706 | 2,267,650 / 90,706 | 2,267,650 / 90,706 |
