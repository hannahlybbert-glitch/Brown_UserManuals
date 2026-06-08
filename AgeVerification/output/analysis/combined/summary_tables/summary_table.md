# Summary Table

Sample: unique machines from stacked_panel.rds (prepare_combined.R), analysis window rel_week in [-16, 8]. Share of sample denominator excludes machines with missing values for the row variable. Visits = share of machines with at least one in-panel analysis-window week of positive winsorized minutes. Minutes = per-machine mean of winsorized weekly minutes across in-panel analysis-window weeks, then averaged across machines in the subgroup. Treated state = machine's state appears in phshutdown_dates.csv. †Non Visitor = machines with zero average weekly all-XXX minutes across the analysis window (τ = -16 to +8). Light/Moderate/Heavy terciles divide machines with positive all-XXX usage into equal thirds by per-machine average weekly winsorized all-XXX minutes. Unlike the demographic rows, this is a behavioral measure derived from observed usage during the full 25-week analysis period.

|                   |Share of Sample |PH Visits |PH Minutes |XV Visits |XV Minutes |XNXX Visits |XNXX Minutes |All XXX Visits |All XXX Minutes |N       |
|:------------------|:---------------|:---------|:----------|:---------|:----------|:-----------|:------------|:--------------|:---------------|:-------|
|State              |                |          |           |          |           |            |             |               |                |        |
|Treated            |52.8%           |19.1%     |0.98       |12.3%     |0.69       |9.2%        |0.58         |33.2%          |4.30            |292,987 |
|Non-Treated        |47.2%           |20.4%     |1.05       |12.6%     |0.64       |9.2%        |0.52         |35.8%          |4.63            |261,897 |
|Gender             |                |          |           |          |           |            |             |               |                |        |
|Male               |18.9%           |31.5%     |2.56       |22.7%     |2.29       |18.2%       |2.04         |50.0%          |12.55           |104,816 |
|Female             |13.5%           |21.9%     |1.14       |13.1%     |0.59       |12.3%       |0.64         |39.4%          |3.86            |74,724  |
|Shared             |18.4%           |22.4%     |0.70       |13.5%     |0.29       |8.9%        |0.16         |39.5%          |2.94            |102,189 |
|Unknown            |49.2%           |13.6%     |0.50       |7.9%      |0.20       |5.0%        |0.11         |25.2%          |2.08            |273,155 |
|Age                |                |          |           |          |           |            |             |               |                |        |
|18-24              |14.7%           |27.5%     |1.36       |15.8%     |0.49       |9.7%        |0.23         |45.0%          |4.10            |81,389  |
|25-44              |29.3%           |23.8%     |1.27       |14.8%     |0.77       |11.3%       |0.61         |40.6%          |4.94            |162,459 |
|45+                |56.1%           |15.5%     |0.79       |10.3%     |0.66       |8.0%        |0.61         |28.5%          |4.30            |311,033 |
|HH Income          |                |          |           |          |           |            |             |               |                |        |
|<$60k              |55.4%           |18.8%     |1.13       |12.6%     |0.83       |10.1%       |0.74         |33.3%          |5.19            |307,198 |
|$60k-$99k          |12.3%           |22.2%     |1.28       |15.0%     |0.90       |11.8%       |0.77         |39.0%          |6.12            |68,266  |
|$100k+             |32.3%           |20.3%     |0.72       |11.2%     |0.30       |6.7%        |0.16         |34.7%          |2.57            |179,420 |
|Children Present   |                |          |           |          |           |            |             |               |                |        |
|Yes                |50.2%           |23.3%     |1.01       |13.8%     |0.49       |9.5%        |0.36         |39.8%          |3.81            |278,750 |
|No                 |49.8%           |16.1%     |1.02       |11.0%     |0.85       |8.9%        |0.76         |29.0%          |5.11            |276,134 |
|Device Type        |                |          |           |          |           |            |             |               |                |        |
|Desktop            |87.1%           |16.3%     |0.56       |9.6%      |0.23       |6.2%        |0.13         |29.7%          |2.34            |483,291 |
|Mobile             |12.9%           |42.9%     |4.10       |31.9%     |3.59       |29.5%       |3.45         |66.4%          |18.75           |71,593  |
|XXX Usage Tercile† |                |          |           |          |           |            |             |               |                |        |
|Non Visitor        |65.6%           |-         |-          |-         |-          |-           |-            |-              |-               |363,765 |
|Light              |11.5%           |26.7%     |0.03       |10.0%     |0.01       |5.9%        |0.01         |100.0%         |0.13            |63,707  |
|Moderate           |11.5%           |64.1%     |0.68       |33.9%     |0.18       |22.4%       |0.13         |100.0%         |1.90            |63,706  |
|Heavy              |11.5%           |80.9%     |8.11       |64.5%     |5.61       |51.9%       |4.70         |100.0%         |36.79           |63,706  |
|Total              |100.0%          |19.7%     |1.01       |12.4%     |0.67       |9.2%        |0.56         |34.4%          |4.46            |554,884 |
