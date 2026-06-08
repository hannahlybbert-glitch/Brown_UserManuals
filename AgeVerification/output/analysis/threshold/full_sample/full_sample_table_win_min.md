# Pooled ATT — Win. min/machine (p95)

Stacked TWFE: dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week. SE clustered by state. beta_pre: tau in [-16,-5]; beta_ST: tau in [0,3]; beta_LT: tau in [4,8]. Baseline mean: treatment group mean in weeks -4 to -1. * p<0.10, ** p<0.05, *** p<0.01. SE in parentheses.

|              |Pornhub    |xVideos    |XNXX       |Other XXX (combined) |All XXX (pooled) |
|:-------------|:----------|:----------|:----------|:--------------------|:----------------|
|              |(1)        |(2)        |(3)        |(4)                  |(5)              |
|β_pre         |-0.0662**  |-0.0124    |0.0386     |-0.0458              |-0.0859          |
|              |(0.0306)   |(0.0344)   |(0.0390)   |(0.0967)             |(0.1287)         |
|β_ST          |-0.6293*** |0.1942***  |0.1918***  |0.0745               |-0.1688*         |
|              |(0.0469)   |(0.0418)   |(0.0387)   |(0.0940)             |(0.0994)         |
|β_LT          |-0.8161*** |0.3176***  |0.2014***  |-0.1881**            |-0.4852***       |
|              |(0.0592)   |(0.0825)   |(0.0551)   |(0.0749)             |(0.1207)         |
|Baseline mean |1.3522     |0.9965     |0.7811     |3.1865               |6.3163           |
|N (obs)       |30,004,950 |30,004,950 |30,004,950 |30,004,950           |30,004,950       |
|N (machines)  |489,023    |489,023    |489,023    |489,023              |489,023          |
