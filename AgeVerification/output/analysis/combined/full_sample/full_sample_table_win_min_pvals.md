# Pooled ATT p-values — Win. min/machine (p95)

Stacked TWFE: dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week. SE clustered by state. beta_pre: tau in [-16,-5]; beta_ST: tau in [0,3]; beta_LT: tau in [4,8]. Baseline mean: treatment group mean in weeks -4 to -1. * p<0.10, ** p<0.05, *** p<0.01. SE in parentheses.

|                   |Pornhub (1) |XVideos (2) |XNXX (3)   |Other XXX (4) |All XXX (5) |
|:------------------|:-----------|:-----------|:----------|:-------------|:-----------|
|$p_{\mathrm{pre}}$ |0.0220      |0.7023      |0.9309     |0.3209        |0.3166      |
|$p_{\mathrm{ST}}$  |0.0000      |0.0000      |0.0000     |0.8315        |0.0051      |
|$p_{\mathrm{LT}}$  |0.0000      |0.0000      |0.0087     |0.0121        |0.0000      |
|Baseline mean      |1.4015      |0.9669      |0.7796     |3.1969        |6.3449      |
|N (obs)            |33,558,770  |33,558,770  |33,558,770 |33,558,770    |33,558,770  |
|N (machines)       |554,866     |554,866     |554,866    |554,866       |554,866     |
