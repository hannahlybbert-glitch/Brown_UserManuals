# Balanced vs Unbalanced Panel — Winsorized min/machine/week — win_min

Pooled three-period TWFE: `dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week`. SE clustered by state.  
β_ST: τ ∈ [0,3]. β_LT: τ ∈ [4,8]. β_pre: τ ∈ [−16,−5].  
**Balanced** = machine×cohort pairs present in all 25 event-window weeks. Format: β (SE).

| Estimate | All XXX (pooled) (Unbal) | Pornhub (Unbal) | xVideos (Unbal) | All XXX (pooled) (Bal) | Pornhub (Bal) | xVideos (Bal) |
|:---|:---|:---|:---|:---|:---|:---|
| **β_pre** | -0.2863 (0.2992) | -0.1152 (0.0701) | -0.0721 (0.0829) | -0.1537 (0.2936) | -0.2118 (0.1257) | 0.0033 (0.1072) |
| **β_ST** | 0.0316 (0.2970) | -0.8913 (0.0724) | 0.3804 (0.1271) | -0.0745 (0.3243) | -1.0506 (0.1084) | 0.4628 (0.1280) |
| **β_LT** | -0.5316 (0.2857) | -1.3230 (0.1158) | 0.6491 (0.1258) | -0.4222 (0.2361) | -1.5215 (0.1921) | 0.8542 (0.1400) |
| **N (obs) / N (m×c)** | 3,369,231 / 233,322 | 3,369,231 / 233,322 | 3,369,231 / 233,322 | 1,616,725 / 64,669 | 1,616,725 / 64,669 | 1,616,725 / 64,669 |
