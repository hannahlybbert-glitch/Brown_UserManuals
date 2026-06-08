# Balanced vs Unbalanced Panel — Winsorized min/machine/week — win_min

Pooled three-period TWFE: `dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week`. SE clustered by state.  
β_ST: τ ∈ [0,3]. β_LT: τ ∈ [4,8]. β_pre: τ ∈ [−16,−5].  
**Balanced** = machine×cohort pairs present in all 25 event-window weeks. Format: β (SE).

| Estimate | All XXX (pooled) (Unbal) | Pornhub (Unbal) | xVideos (Unbal) | All XXX (pooled) (Bal) | Pornhub (Bal) | xVideos (Bal) |
|:---|:---|:---|:---|:---|:---|:---|
| **β_pre** | -0.0361 (0.0664) | -0.0014 (0.0169) | -0.0268 (0.0169) | -0.0765 (0.1788) | 0.1179 (0.0417) | 0.0291 (0.0765) |
| **β_ST** | -0.3326 (0.0597) | -0.5551 (0.0397) | 0.1838 (0.0382) | -0.8096 (0.3462) | -1.0709 (0.0928) | 0.4317 (0.1410) |
| **β_LT** | -0.5398 (0.0936) | -0.6459 (0.0443) | 0.2451 (0.0579) | -1.3755 (0.2576) | -1.2034 (0.1223) | 0.4470 (0.1374) |
| **N (obs) / N (m×c)** | 15,230,112 / 1,591,680 | 15,230,112 / 1,591,680 | 15,230,112 / 1,591,680 | 2,267,650 / 90,706 | 2,267,650 / 90,706 | 2,267,650 / 90,706 |
