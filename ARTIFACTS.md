# Submission artefacts index

Everything below is what I am handing in for the UWL Databases and
Analytics module, NorthStar Urban Mobility case study. The right-hand
column shows which line of the rubric each artefact is meant to
satisfy. Submission date: 12 May 2026.

## 1. Written reports (5 .docx files at repo root)

| File | Marks band | What it covers |
|------|------------|----------------|
| `NorthStar MongoDB Session Report.docx`   | MongoDB development, 20 marks      | Cluster creation, schema reasoning, 12 PyMongo aggregations including `$lookup`. |
| `Query Optimisation Report.docx`          | Query optimisation, 10 marks       | 4 query archetypes profiled before and after indexes, with explain plans. |
| `SQL in R Report.docx`                    | SQL in R, 15 marks                 | Normalised SQLite mirror, 9 SQL queries including a window function. |
| `R Analytics Report.docx`                 | R analytics, 15 marks              | tidyverse prep, 5 ggplot charts, 4 hypothesis tests, logistic regression. |
| `Python Data Processing Report.docx`      | Python data processing, 20 marks   | pandas ETL, scipy chi square, scikit-learn random forest. |

Total covered: 80 of 80 written marks. The remaining 20 marks come
from the in person demo, which references the same notebooks live.

## 2. Colab notebooks (`colab_notebooks/`)

| Notebook | Runtime | Standalone? |
|----------|---------|-------------|
| `01_mongodb_pipeline.ipynb`        | Python | Needs `MONGODB_URI` Colab Secret. |
| `02_query_optimisation.ipynb`      | Python | Needs `MONGODB_URI` Colab Secret. |
| `03_sql_in_r.ipynb`                | R      | Yes, the CSVs are pulled from the GitHub repo at runtime. |
| `04_r_analytics.ipynb`             | R      | Yes, the CSVs are pulled from the GitHub repo at runtime. |
| `05_python_data_processing.ipynb`  | Python | Yes, the CSVs are pulled from the GitHub repo at runtime. |

Each notebook reproduces the corresponding section end to end. The
marker can press Run all on any of them.

## 3. Local code pipelines

Each subfolder is independently runnable on a Mac with Python 3.10+
and R 4.3+. Open a Terminal in the subfolder and run the commands
below.

| Folder | Commands | What it does |
|--------|----------|--------------|
| `mongodb/`           | `python3 load_northstar.py && python3 queries_v2.py` | Atlas pipeline, 12 aggregations. |
| `mongodb/`           | `python3 indexes_explain.py`                         | Optimisation experiment. |
| `sql_r/`             | `Rscript load_northstar.R && Rscript queries.R`      | SQLite mirror plus 9 SQL queries. |
| `r_analytics/`       | `Rscript analysis.R`                                 | 5 charts, 4 tests, 1 glm. |
| `python_processing/` | `python3 etl.py && python3 analyse.py`               | pandas ETL plus chi square plus random forest. |

## 4. Setup helpers

| File | Purpose |
|------|---------|
| `README.md`                                  | Top level orientation and how to run anything in 5 minutes. |
| `colab_notebooks/SETUP_CHECKLIST.md`         | Step by step Colab setup, roughly 5 minutes. |
| `mongodb/.env.example`                       | Sanitised template for the Atlas URI secret. |
| `mongodb/schema_design.md`                   | Embedded vs referenced reasoning for the order document. |
| `LICENSE`                                    | MIT licence covering all code. |

## 5. What the data said in the end

The same answer came out of every paradigm I queried. Delivery failures cluster
by pickup zone, and nothing about the order itself predicts whether it will
fail. The chi square test on pickup zone gave p = 0.0103 in both scipy and R.
A random forest with 9 candidate predictors only managed 5 fold ROC AUC of
0.487 plus or minus 0.064, which is no better than a coin flip.

Practically that means NorthStar should focus operational fixes on the zones
that fail most, rather than trying to flag risky orders one by one.

## 6. What is intentionally NOT in this repo

- `mongodb/.env`. Holds the live Atlas password for my database
  user. The `.env.example` file is the safe stub instead.
- The 2 UWL brief PDFs and the assignment guide docx. They are
  course teaching material, not mine to redistribute.

## 7. Reproducibility caveats

- Atlas free tier auto pauses after 60 days idle. If a notebook
  cannot reach the cluster, sign into Atlas and click Resume Cluster.
- Free tier requires `0.0.0.0/0` on the Network Access allow list
  for Colab to reach it. Add it under Network Access in the Atlas UI.
- Notebook 04 used to depend on the SQLite database from notebook
  03. It now rebuilds the SQLite file at runtime from the GitHub
  hosted CSVs, so the 5 notebooks are independent.
