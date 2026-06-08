# VPN Pooled ATT by XXX-visitor status — Win. min/machine (p95)

Stacked TWFE: dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week. SE clustered by state. beta_pre: tau in [-16,-5]; beta_ST: tau in [0,3]; beta_LT: tau in [4,8]. * p<0.10, ** p<0.05, *** p<0.01. SE in parentheses.

|             |VPN clean — XXX visitors |VPN clean — never XXX |All VPN — XXX visitors |All VPN — never XXX |
|:------------|:------------------------|:---------------------|:----------------------|:-------------------|
|β_pre        |0.0005                   |0.0003                |0.0009                 |-0.0062*            |
|             |(0.0021)                 |(0.0004)              |(0.0032)               |(0.0035)            |
|β_ST         |0.0029*                  |-0.0003               |0.0022                 |-0.0004             |
|             |(0.0017)                 |(0.0005)              |(0.0038)               |(0.0024)            |
|β_LT         |0.0028                   |0.0002                |0.0048                 |-0.0061**           |
|             |(0.0020)                 |(0.0008)              |(0.0043)               |(0.0024)            |
|N (obs)      |12,503,411               |14,828,523            |12,503,411             |14,828,523          |
|N (machines) |970,809                  |1,925,532             |970,809                |1,925,532           |
