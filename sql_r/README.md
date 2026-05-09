# SQL in R: NorthStar relational pipeline

This folder contains the relational mirror of the MongoDB pipeline. It
loads the same 9 NorthStar CSV files into a SQLite database and runs 9
analytical queries that answer the same business questions, so the 2
paradigms can be compared directly in the report.

## Files

- `load_northstar.R` builds `northstar.sqlite` from the CSVs, applies the
  same zone canonicalisation as `mongodb/clean_and_build.py`, and adds 6
  join indexes. Idempotent, safe to rerun.
- `queries.R` runs 9 SQL queries via `DBI::dbGetQuery`. Each query is
  paired in comments with its MongoDB equivalent.
- `northstar.sqlite` is created by the loader. Not committed to git.

## Install R, RStudio and the 3 packages used here

You need R itself plus a small set of packages: `DBI`, `RSQLite` and
`readr`. Pick 1 of the 3 paths below.

### Path A: Install R locally on your Mac

1. Download the latest R for macOS PKG installer from
   <https://cran.r-project.org/bin/macosx/>. Pick the version that
   matches your chip (Apple silicon vs Intel) and run the installer.
2. Optional but recommended: install RStudio Desktop (free) from
   <https://posit.co/download/rstudio-desktop/>.
3. Open RStudio (or the R.app that came with R), then in the console
   paste and run:

   ```
   install.packages(c("DBI", "RSQLite", "readr"))
   ```

4. From a Terminal in the `sql_r` folder, run:

   ```
   Rscript load_northstar.R
   Rscript queries.R
   ```

   Or open each file in RStudio and click Source.

### Path B: Use Posit Cloud (no local install)

1. Sign in at <https://posit.cloud>. The free tier is fine for a single
   coursework project.
2. Create a new RStudio project.
3. Upload the 3 files from this folder (`load_northstar.R`, `queries.R`
   and `README.md`) plus the 9 CSVs from the `northstar_dataset` folder.
4. Adjust `DATASET_DIR` at the top of `load_northstar.R` to the upload
   location, for example `"/cloud/project/northstar_dataset"`.
5. Run `install.packages(c("DBI", "RSQLite", "readr"))` in the R
   console, then source the 2 scripts.

### Path C: Use a Google Colab notebook with the R kernel

1. Open a fresh Colab and switch the runtime to R via Runtime,
   Change runtime type, R.
2. Upload the 9 CSVs to the Colab file space.
3. Paste the contents of `load_northstar.R` into the first cell, fix
   `DATASET_DIR`, then run.
4. Paste `queries.R` into the next cell and run. Each `dbGetQuery` call
   prints a tidy table.

## What the loader builds

The 9 tables produced by `load_northstar.R` are:

| Table       | Rows | Primary key       | Notes                                                         |
|-------------|------|-------------------|---------------------------------------------------------------|
| customers   |  650 | customer_id       | home_zone is canonicalised at load time                       |
| orders      | 1250 | order_id          | pickup_zone and dropoff_zone are canonicalised                |
| deliveries  |  950 | delivery_id       | references orders, drivers, vehicles, hubs                    |
| drivers     |  170 | driver_id         | base_zone is canonicalised                                    |
| vehicles    |  120 | vehicle_id        | assigned_zone is canonicalised                                |
| hubs        |    8 | hub_id            | zone is canonicalised                                         |
| incidents   |  280 | incident_id       | references deliveries                                         |
| complaints  |  320 | complaint_id      | references orders and customers                               |
| app_events  |  640 | event_id          | zone_context is canonicalised, references customers and orders |

Indexes created on join keys: `idx_orders_customer`,
`idx_deliveries_order`, `idx_deliveries_driver`,
`idx_complaints_order`, `idx_app_events_order`,
`idx_incidents_delivery`.

## Mapping SQL queries to MongoDB queries

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

S9 is the demonstrative window function that has no direct equivalent
in the MongoDB scripts. The relational paradigm expresses
"top N per group" naturally; the document paradigm needs `$setWindowFields`
or a multi stage pipeline to do the same.

## Reproducing the report figures

Both scripts print their results to stdout. Capture them with shell
redirection if the report needs to embed the raw output:

```
Rscript load_northstar.R 2>&1 | tee load.log
Rscript queries.R        2>&1 | tee queries.log
```
