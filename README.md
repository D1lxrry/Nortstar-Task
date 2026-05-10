# NorthStar Urban Mobility, Databases and Analytics coursework

This repo holds my full submission for the UWL Databases and Analytics
module. The coursework is built around the NorthStar Urban Mobility
case study and asks for the same business questions to be answered
using 4 different paradigms: MongoDB, SQL through R, R analytics, and
Python data processing. All 4 pipelines run end to end. All 5 Colab
notebooks under `colab_notebooks/` are self-contained, so a marker can
hit Run all on any of them and reproduce the work.

If you only have a minute, open
[`colab_notebooks/01_mongodb_pipeline.ipynb`](colab_notebooks/01_mongodb_pipeline.ipynb)
in Colab and click Run all. That single notebook stands up the whole
MongoDB pipeline against the Atlas cluster and prints the 12
aggregations the report describes.

## What lives where

| Folder              | Paradigm               | Marks band           |
|---------------------|------------------------|----------------------|
| `mongodb/`          | MongoDB / PyMongo      | MongoDB development (20), Query optimisation (10) |
| `sql_r/`            | R + SQLite + DBI       | SQL in R (15)        |
| `r_analytics/`      | R + tidyverse + ggplot | R analytics (15)     |
| `python_processing/`| pandas + scipy + sklearn | Python data processing (20) |
| `colab_notebooks/`  | All 5 pipelines as Colab notebooks | Deliverable (GitHub plus Colab) |

The 5 academic style writeups live alongside the code as Word
documents:

- `NorthStar MongoDB Session Report.docx`
- `Query Optimisation Report.docx`
- `SQL in R Report.docx`
- `R Analytics Report.docx`
- `Python Data Processing Report.docx`

## How to read this in 5 minutes

1. Skim this README so you know the layout.
2. Open `mongodb/schema_design.md` for the embedded order document
   schema and the reasoning behind embedded vs referenced.
3. Open any of the 5 Word reports for the formal academic writeup of
   that section, including the actual numbers each pipeline produced.
4. If you want to run anything yourself, every subfolder has a
   `README.md` with the exact shell commands. The Colab notebooks
   need no local setup at all, just open one and Run all.

## How to run everything

### The local way (Mac)

Open a Terminal in each subfolder and run the listed commands. The
order that makes most sense for reproducing the project from scratch
is:

```
mongodb/             # ensure mongodb/.env has your MONGODB_URI, then
                     python3 -m pip install "pymongo[srv]" python-dotenv
                     python3 load_northstar.py
                     python3 queries_demo.py
                     python3 clean_and_build.py
                     python3 queries_v2.py
                     python3 indexes_explain.py
                     python3 install_indexes.py

sql_r/               # builds northstar.sqlite, runs the 9 SQL queries
                     Rscript load_northstar.R
                     Rscript queries.R

r_analytics/         # 5 ggplot charts, 4 hypothesis tests, logistic regression
                     Rscript analysis.R

python_processing/   # pandas ETL plus scipy chi square plus random forest
                     python3 -m pip install pandas numpy scipy matplotlib scikit-learn
                     python3 etl.py
                     python3 analyse.py
```

The 9 raw NorthStar CSVs are committed under `northstar_dataset/` at
the repo root, so the local pipelines and the Colab notebooks can
both read them without any setup. If you keep them somewhere else
on disk, edit the `DATASET_DIR` constant at the top of
`load_northstar.py`, `etl.py` and `load_northstar.R`.

### The Colab way

Open any of these URLs in your browser. The first 2 need an Atlas
connection string in a Colab Secret named `MONGODB_URI`; the last 3
are fully self contained.

```
colab_notebooks/01_mongodb_pipeline.ipynb       Atlas pipeline
colab_notebooks/02_query_optimisation.ipynb     indexing experiment
colab_notebooks/03_sql_in_r.ipynb               9 SQL queries (R kernel)
colab_notebooks/04_r_analytics.ipynb            ggplot + tests + glm (R kernel)
colab_notebooks/05_python_data_processing.ipynb pandas + sklearn
```

For 03 and 04 set the runtime to R via Runtime, Change runtime type, R.
Both R notebooks pull the 9 CSVs straight from this GitHub repo at
runtime (the `northstar_dataset/` folder), so the marker does not have
to upload anything. Click Run all from the top and the data is fetched
inside the first code cell.

## What the data ended up saying

Whichever paradigm I queried, the same answer came out. Failed deliveries
cluster by pickup zone (chi square p = 0.0103, the same number from scipy and
from R), and not by anything intrinsic to the order. When I tried to predict
failure with a random forest over 9 candidate predictors, 5 fold ROC AUC came
out at 0.487 plus or minus 0.064, basically a coin flip. So the practical
takeaway for NorthStar is to fix the high failure zones rather than spend
modelling effort trying to flag risky orders one by one.

## Reproducibility notes

- Atlas free tier auto-pauses after 60 days idle. If a Colab notebook
  cannot reach the cluster, sign into Atlas and click Resume Cluster.
- Free tier requires `0.0.0.0/0` on the Network Access allow list for
  Colab to connect. Add it under Network Access in the Atlas UI.
- Notebook 04 used to depend on the SQLite database produced by
  notebook 03, but it now rebuilds the SQLite file at runtime from
  the GitHub-hosted CSVs, so the 2 notebooks are independent.

## Author

Laz, UWL Databases and Analytics, 2025-2026 academic year. Submitted
12 May 2026.
