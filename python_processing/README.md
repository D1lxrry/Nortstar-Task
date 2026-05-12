# Python data processing pipeline

This folder is the Python contribution to the NorthStar Urban Mobility
coursework. It complements the MongoDB and SQL pipelines in
`mongodb/` and `sql_r/` by demonstrating how the same dataset is
extracted, validated, transformed and modelled using pandas, scipy
and scikit-learn.

## Files

- `etl.py` extracts the 9 raw CSVs, runs a 5 dimension data quality
  scorecard (nulls, duplicate primary keys, foreign key violations,
  zone canonicalisation, range checks), applies the canonicalisation,
  builds an analytical wide table and writes everything to `cleaned/`.
- `analyse.py` reads the cleaned data, runs scipy chi square tests
  that pair with the R chi square tests, and fits a scikit-learn
  random forest classifier for delivery failure with 5 fold cross
  validation, ROC AUC, confusion matrix and feature importance.
- `cleaned/` holds the cleaned per table CSVs plus `orders_full.csv`
  (the analytical wide table, 1 row per order).
- `charts/` holds the matplotlib output, plus `feature_importance.csv`
  and `cv_auc.csv` for downstream reporting.

## How to run

From a Terminal in this folder:

```
python3 -m pip install pandas numpy scipy matplotlib scikit-learn
python3 etl.py
python3 analyse.py
```

## How this pipeline differs from the SQL and MongoDB pipelines

| Stage           | MongoDB pipeline                          | SQL pipeline                | Python pipeline                                 |
|-----------------|-------------------------------------------|-----------------------------|-------------------------------------------------|
| Extract         | bulk insert per CSV                       | dbWriteTable per CSV        | pandas.read_csv                                 |
| Cleaning        | inline updateMany on zone fields          | applied during dbWriteTable | apply via pd.Series.map and pd.to_datetime     |
| Schema          | embedded order document                   | 9 normalised tables          | tidy wide table per analysis use                 |
| Analysis        | aggregation pipelines                     | SQL group/join queries       | pandas groupby and pivot_table                  |
| Stats / models  | none in MongoDB                           | none in SQL                  | scipy chi square, sklearn random forest         |
| Output          | orders_aggregate collection on Atlas      | northstar.sqlite file       | cleaned/*.csv plus charts/*.png                 |

Together the 3 paradigms cover the full ETL plus analytics lifecycle
demanded by the rubric, with the Python pipeline carrying the data
quality validation and the predictive modelling load.

## What the data quality scorecard reports

For each of the 9 tables the scorecard records the row count, the
total number of NA cells, the number of duplicated primary keys, the
number of foreign key values that have no match in the referenced
table, and a per table sum of distinct zone values across whichever
zone fields that table contains. The scorecard runs once before the
cleanup pass and once after, so the report can quote the diff. The
zone column should drop noticeably on the second pass: 16 raw zone
spellings collapse to 7 canonical ones across the dataset.

The scorecard is written to `cleaned/data_quality.csv` so it pastes
straight into the report appendix.

## Charts

`charts/` contains 4 PNGs that the consolidated report pulls in:

- `P1_feature_importance.png`: random forest feature importance.
- `P2_roc_curve.png`: ROC curve on the hold out test fold.
- `P3_confusion_matrix.png`: confusion matrix on the hold out test fold.
- `P4_failure_heatmap.png`: failure rate by pickup_zone and
  service_type, generated with matplotlib (the R equivalent in
  `r_analytics/charts/03_failure_heatmap.png` is ggplot, so the 2
  cross-check each other).
