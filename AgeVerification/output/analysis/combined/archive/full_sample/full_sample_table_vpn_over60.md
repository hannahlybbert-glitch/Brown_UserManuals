# VPN Pooled ATT by XXX-visitor status — Pr(>60s)

Stacked TWFE: dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week. SE clustered by state. beta_pre: tau in [-16,-5]; beta_ST: tau in [0,3]; beta_LT: tau in [4,8]. * p<0.10, ** p<0.05, *** p<0.01. SE in parentheses.

|             |VPN clean — XXX visitors |VPN clean — never XXX |All VPN — XXX visitors |All VPN — never XXX |
|:------------|:------------------------|:---------------------|:----------------------|:-------------------|
|β_pre        |-0.0000                  |-0.0000               |0.0001                 |-0.0001             |
|             |(0.0003)                 |(0.0001)              |(0.0003)               |(0.0003)            |
|β_ST         |0.0005**                 |-0.0000               |-0.0003                |0.0001              |
|             |(0.0002)                 |(0.0001)              |(0.0003)               |(0.0003)            |
|β_LT         |0.0003                   |0.0000                |-0.0002                |-0.0005**           |
|             |(0.0003)                 |(0.0001)              |(0.0004)               |(0.0002)            |
|N (obs)      |17,166,650               |16,394,538            |17,166,650             |16,394,538          |
|N (machines) |1,271,810                |2,057,578             |1,271,810              |2,057,578           |
