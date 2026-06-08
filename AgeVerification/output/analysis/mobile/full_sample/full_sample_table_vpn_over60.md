# VPN Pooled ATT by XXX-visitor status — Pr(>60s)

Stacked TWFE: dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week. SE clustered by state. beta_pre: tau in [-16,-5]; beta_ST: tau in [0,3]; beta_LT: tau in [4,8]. * p<0.10, ** p<0.05, *** p<0.01. SE in parentheses.

|             |VPN clean — XXX visitors |VPN clean — never XXX |All VPN — XXX visitors |All VPN — never XXX |
|:------------|:------------------------|:---------------------|:----------------------|:-------------------|
|β_pre        |-0.0001                  |-0.0003               |0.0004                 |0.0004              |
|             |(0.0003)                 |(0.0004)              |(0.0008)               |(0.0011)            |
|β_ST         |0.0000                   |-0.0003               |-0.0004                |-0.0026*            |
|             |(0.0004)                 |(0.0004)              |(0.0008)               |(0.0014)            |
|β_LT         |-0.0004                  |0.0003                |-0.0015*               |-0.0028             |
|             |(0.0004)                 |(0.0006)              |(0.0009)               |(0.0019)            |
|N (obs)      |4,663,239                |1,566,015             |4,663,239              |1,566,015           |
|N (machines) |301,001                  |132,046               |301,001                |132,046             |
