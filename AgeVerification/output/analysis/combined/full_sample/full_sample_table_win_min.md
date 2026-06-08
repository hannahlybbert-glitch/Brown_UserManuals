# Pooled ATT — Win. min/machine (p95)

Stacked TWFE: dv ~ treated:pre + treated:shortterm + treated:longterm | machine_cohort + cohort_week. SE clustered by state. beta_pre: tau in [-16,-5]; beta_ST: tau in [0,3]; beta_LT: tau in [4,8]. Baseline mean: treatment group mean in weeks -4 to -1. * p<0.10, ** p<0.05, *** p<0.01. SE in parentheses.

|              |Pornhub    |XVideos    |XNXX       |Other XXX (combined) |All XXX (pooled) |
|:-------------|:----------|:----------|:----------|:--------------------|:----------------|
|              |(1)        |(2)        |(3)        |(4)                  |(5)              |
|β_pre         |-0.0506**  |0.0139     |0.0036     |-0.0921              |-0.1252          |
|              |(0.0221)   |(0.0364)   |(0.0412)   |(0.0928)             |(0.1251)         |
|β_ST          |-0.5794*** |0.1960***  |0.1520***  |0.0184               |-0.2130***       |
|              |(0.0405)   |(0.0452)   |(0.0360)   |(0.0867)             |(0.0760)         |
|β_LT          |-0.7619*** |0.3163***  |0.1578***  |-0.2093**            |-0.4971***       |
|              |(0.0460)   |(0.0704)   |(0.0601)   |(0.0834)             |(0.1025)         |
|Baseline mean |1.4015     |0.9669     |0.7796     |3.1969               |6.3449           |
|N (obs)       |33,558,770 |33,558,770 |33,558,770 |33,558,770           |33,558,770       |
|N (machines)  |554,866    |554,866    |554,866    |554,866              |554,866          |
