# Balanced vs Unbalanced Panel — Pr(>60s on site) — over60

Pooled three-period TWFE: `dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week`. SE clustered by state.  
β_ST: τ ∈ [0,3]. β_LT: τ ∈ [4,8]. β_pre: τ ∈ [−16,−5].  
**Balanced** = machine×cohort pairs present in all 25 event-window weeks. Format: β (SE).

| Estimate | All XXX (pooled) (Unbal) | Pornhub (Unbal) | xVideos (Unbal) | All XXX (pooled) (Bal) | Pornhub (Bal) | xVideos (Bal) |
|:---|:---|:---|:---|:---|:---|:---|
| **β_pre** | -0.0016 (0.0023) | 0.0005 (0.0019) | -0.0007 (0.0016) | -0.0011 (0.0036) | -0.0007 (0.0036) | -0.0012 (0.0017) |
| **β_ST** | -0.0009 (0.0026) | -0.0223 (0.0029) | 0.0119 (0.0022) | -0.0026 (0.0036) | -0.0262 (0.0044) | 0.0105 (0.0029) |
| **β_LT** | -0.0056 (0.0030) | -0.0401 (0.0051) | 0.0187 (0.0030) | -0.0066 (0.0041) | -0.0438 (0.0065) | 0.0205 (0.0030) |
| **N (obs) / N (m×c)** | 3,369,231 / 233,322 | 3,369,231 / 233,322 | 3,369,231 / 233,322 | 1,616,725 / 64,669 | 1,616,725 / 64,669 | 1,616,725 / 64,669 |
