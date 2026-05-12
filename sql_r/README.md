# SQL in R

Relational mirror of the MongoDB pipeline. The same 9 NorthStar
CSVs go into a SQLite database, then 9 SQL queries answer the same
business questions as the MongoDB aggregations in `mongodb/`, so
the 2 paradigms can be compared in the report.

## Files

- `load_northstar.R` builds `northstar.sqlite` from the CSVs,
  applies the same zone canonicalisation as
  `mongodb/clean_and_build.py`, and adds 6 join-key indexes.
  Idempotent, safe to rerun.
- `queries.R` runs the 9 SQL queries via `DBI::dbGetQuery`. Each
  one is paired in comments with its MongoDB equivalent.
- `northstar.sqlite` is built by the loader. Gitignored.

## Run

Needs R 4.3+ and 3 packages: `DBI`, `RSQLite`, `readr`.

```
install.packages(c("DBI", "RSQLite", "readr"))
Rscript load_northstar.R
Rscript queries.R
```

## What the loader builds

| Table       | Rows | Primary key       | Notes                                                         |
|-------------|------|-------------------|---------------------------------------------------------------|
| customers   |  650 | customer_id       | home_zone canonicalised at load time                          |
| orders      | 1250 | order_id          | pickup_zone and dropoff_zone canonicalised                    |
| deliveries  |  950 | delivery_id       | references orders, drivers, vehicles, hubs                    |
| drivers     |  170 | driver_id         | base_zone canonicalised                                       |
| vehicles    |  120 | vehicle_id        | assigned_zone canonicalised                                   |
| hubs        |    8 | hub_id            | zone canonicalised                                            |
| incidents   |  280 | incident_id       | references deliveries                                         |
| complaints  |  320 | complaint_id      | references orders and customers                               |
| app_events  |  640 | event_id          | zone_context canonicalised, references customers and orders   |

Join-key indexes created: `idx_orders_customer`,
`idx_deliveries_order`, `idx_deliveries_driver`,
`idx_complaints_order`, `idx_app_events_order`,
`idx_incidents_delivery`.

## SQL to MongoDB mapping

| SQL query | MongoDB equivalent             | Technique focus                                       |
|-----------|--------------------------------|-------------------------------------------------------|
| S1        | queries_demo.Q1                | `GROUP BY` on a single column                         |
| S2        | queries_demo.Q2                | `GROUP BY` on a different table                       |
| S3        | queries_demo.Q3                | Multi metric aggregation                              |
| S4        | queries_v2.V1                  | `INNER JOIN` plus `CASE WHEN` conditional aggregation |
| S5        | queries_v2.V2                  | `INNER JOIN` plus `AVG`                               |
| S6        | queries_v2.V3                  | 3 way join with `GROUP BY` and `LIMIT`                |
| S7        | queries_v2.V4                  | `LEFT JOIN` to preserve childless rows                |
| S8        | queries_v2.V5                  | `INNER JOIN` plus driver level aggregation            |
| S9        | (no direct equivalent)         | `RANK() OVER PARTITION BY` window function            |

S9 is the demonstrative window function. The relational paradigm
expresses "top N per group" naturally; the document paradigm needs
`$setWindowFields` or a multi stage pipeline to do the same.
