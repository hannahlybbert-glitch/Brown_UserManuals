# VPN Pooled ATT by XXX-visitor status — Win. min/machine (p95)

Stacked TWFE: dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week. SE clustered by state. beta_pre: tau in [-16,-5]; beta_ST: tau in [0,3]; beta_LT: tau in [4,8]. * p<0.10, ** p<0.05, *** p<0.01. SE in parentheses.

|             |VPN clean — XXX visitors |VPN clean — never XXX |All VPN — XXX visitors |All VPN — never XXX |
|:------------|:------------------------|:---------------------|:----------------------|:-------------------|
|β_pre        |0.0004                   |0.0028                |-0.0168*               |0.0258              |
|             |(0.0013)                 |(0.0019)              |(0.0101)               |(0.0175)            |
|β_ST         |0.0024                   |-0.0007               |-0.0154**              |-0.0291**           |
|             |(0.0031)                 |(0.0021)              |(0.0069)               |(0.0145)            |
|β_LT         |-0.0004                  |0.0025                |-0.0322**              |-0.0328             |
|             |(0.0018)                 |(0.0037)              |(0.0152)               |(0.0231)            |
|N (obs)      |4,663,239                |1,566,015             |4,663,239              |1,566,015           |
|N (machines) |301,001                  |132,046               |301,001                |132,046             |
