# Summary Table

Sample: unique machines from stacked_panel.rds (prepare_combined.R), analysis window rel_week in [-16, 8]. Share of sample denominator excludes machines with missing values for the row variable. Visits = share of machines with at least one in-panel analysis-window week of positive winsorized minutes. Minutes = per-machine mean of winsorized weekly minutes across in-panel analysis-window weeks, then averaged across machines in the subgroup. Treated state = machine's state appears in phshutdown_dates.csv. †Non Visitor = machines with zero average weekly all-XXX minutes across the analysis window (τ = -16 to +8). Light/Moderate/Heavy terciles divide machines with positive all-XXX usage into equal thirds by per-machine average weekly winsorized all-XXX minutes. Unlike the demographic rows, this is a behavioral measure derived from observed usage during the full 25-week analysis period.

|                   |Share of Sample |PH Visits |PH Minutes |XV Visits |XV Minutes |XNXX Visits |XNXX Minutes |All XXX Visits |All XXX Minutes |N       |
|:------------------|:---------------|:---------|:----------|:---------|:----------|:-----------|:------------|:--------------|:---------------|:-------|
|State              |                |          |           |          |           |            |             |               |                |        |
|Treated            |47.7%           |18.8%     |0.94       |12.0%     |0.65       |9.0%        |0.56         |32.9%          |4.14            |233,136 |
|Non-Treated        |52.3%           |20.4%     |1.05       |12.6%     |0.64       |9.1%        |0.52         |35.8%          |4.62            |255,887 |
|Gender             |                |          |           |          |           |            |             |               |                |        |
|Male               |18.8%           |31.4%     |2.52       |22.5%     |2.21       |18.0%       |1.99         |49.9%          |12.34           |92,123  |
|Female             |13.1%           |21.4%     |1.10       |12.7%     |0.57       |11.9%       |0.62         |38.9%          |3.74            |64,232  |
|Shared             |18.5%           |22.3%     |0.70       |13.5%     |0.29       |8.9%        |0.16         |39.6%          |2.96            |90,313  |
|Unknown            |49.6%           |13.7%     |0.50       |7.9%      |0.20       |5.0%        |0.11         |25.4%          |2.08            |242,355 |
|Age                |                |          |           |          |           |            |             |               |                |        |
|18-24              |14.7%           |27.4%     |1.33       |15.6%     |0.47       |9.5%        |0.22         |44.9%          |4.00            |71,952  |
|25-44              |29.2%           |23.5%     |1.25       |14.6%     |0.74       |11.1%       |0.58         |40.3%          |4.85            |142,770 |
|45+                |56.1%           |15.6%     |0.78       |10.3%     |0.64       |7.9%        |0.60         |28.6%          |4.26            |274,298 |
|HH Income          |                |          |           |          |           |            |             |               |                |        |
|<$60k              |54.7%           |18.6%     |1.10       |12.4%     |0.79       |9.8%        |0.71         |33.0%          |5.06            |267,413 |
|$60k-$99k          |12.5%           |22.3%     |1.27       |15.1%     |0.93       |11.9%       |0.81         |39.3%          |6.28            |61,010  |
|$100k+             |32.8%           |20.3%     |0.71       |11.2%     |0.30       |6.8%        |0.16         |34.9%          |2.56            |160,600 |
|Children Present   |                |          |           |          |           |            |             |               |                |        |
|Yes                |50.3%           |23.2%     |1.00       |13.8%     |0.48       |9.5%        |0.36         |39.8%          |3.80            |246,040 |
|No                 |49.7%           |15.9%     |0.99       |10.9%     |0.81       |8.7%        |0.73         |28.9%          |4.99            |242,983 |
|Device Type        |                |          |           |          |           |            |             |               |                |        |
|Desktop            |87.5%           |16.3%     |0.55       |9.6%      |0.23       |6.2%        |0.13         |29.8%          |2.34            |427,809 |
|Mobile             |12.5%           |42.6%     |4.08       |31.7%     |3.55       |29.3%       |3.43         |66.3%          |18.71           |61,214  |
|XXX Usage Tercile† |                |          |           |          |           |            |             |               |                |        |
|Non Visitor        |65.6%           |-         |-          |-         |-          |-           |-            |-              |-               |320,784 |
|Light              |11.5%           |26.4%     |0.03       |9.8%      |0.01       |5.7%        |0.00         |100.0%         |0.13            |56,080  |
|Moderate           |11.5%           |63.8%     |0.66       |33.5%     |0.18       |21.9%       |0.12         |100.0%         |1.85            |56,080  |
|Heavy              |11.5%           |80.8%     |7.99       |64.3%     |5.44       |51.5%       |4.58         |100.0%         |36.34           |56,079  |
|Total              |100.0%          |19.6%     |1.00       |12.3%     |0.65       |9.1%        |0.54         |34.4%          |4.39            |489,023 |
