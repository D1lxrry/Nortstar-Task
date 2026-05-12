# NorthStar Urban Mobility & Logistics, Databases and Analytics coursework

This repo holds my full submission for the UWL Databases and Analytics
module. The coursework is built around the NorthStar Urban Mobility &
Logistics case study and asks for the same business questions to be
answered using 4 different paradigms: MongoDB, SQL through R, R
analytics, and Python data processing.

The deliverable form is **3 Google Colab notebooks**, linked below.
A random marker can click any of the badges, hit *Runtime > Run all*,
and watch the whole pipeline build and run on their own Colab machine.
No upload, no Drive mount, no Atlas credentials to copy. Everything
the notebooks need (raw CSVs, cleaned CSVs, schema) is committed to
this repo and pulled at runtime over HTTPS.

## The 3 notebooks

| Notebook | Marking bands | Open in Colab |
|----------|---------------|---------------|
| 1. Python Data Processing | Python data processing (20) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/D1lxrry/Northstar-Task/blob/main/colab_notebooks/01_python_data_processing.ipynb) |
| 2. SQL in R and R Analytics | SQL in R (15) + R analytics (15) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/D1lxrry/Northstar-Task/blob/main/colab_notebooks/02_r_sql_and_analytics.ipynb) |
| 3. MongoDB and Query Optimisation | MongoDB development (20) + Query optimisation (10) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/D1lxrry/Northstar-Task/blob/main/colab_notebooks/03_mongodb_and_query_optimisation.ipynb) |

Each notebook follows the same shape: methodology-phase sections,
real code with real results, a final table that maps each section
to the rubric line it satisfies.

**Notebook 2 needs the R runtime.** In Colab, before pressing Run all,
go to *Runtime > Change runtime type > R*, click Save, then run.
Notebooks 1 and 3 use the default Python runtime.

**Notebook 3 tries my live Atlas cluster first** and falls back to
`mongomock` (an in-memory MongoDB) if the cluster is paused or
unreachable. Every cell runs to completion either way.

## What lives where

| Folder              | Paradigm                  | Marks band                                   |
|---------------------|---------------------------|----------------------------------------------|
| `colab_notebooks/`  | 3 Colab notebooks         | The deliverable form for the marker          |
| `mongodb/`          | MongoDB / PyMongo         | MongoDB development (20), Query opt (10)     |
| `sql_r/`            | R + SQLite + DBI          | SQL in R (15)                                |
| `r_analytics/`      | R + tidyverse + ggplot    | R analytics (15)                             |
| `python_processing/`| pandas + scipy + sklearn  | Python data processing (20)                  |
| `northstar_dataset/`| 9 raw CSVs from the brief | Source data, read by every pipeline          |
| `python_processing/cleaned/` | Cleaned CSVs after ETL | Same data, post canonicalisation     |
| `figures/`          | Charts and tables         | Used by the reports                          |

The single academic writeup lives alongside the code as a Word document:

- `Final Database Report.docx` covers all 5 marking bands in one
  deliverable, with a 150-word abstract on page 1 and clickable links to
  the GitHub repo and the 3 Colab notebooks at the top.

## How to read this in 5 minutes

1. Skim this README so you know the layout.
2. Click the *Open In Colab* badge for notebook 1 and watch it run.
3. Open `mongodb/schema_design.md` if you want the embedded vs
   referenced reasoning in writing.
4. Open `Final Database Report.docx` for the formal academic
   writeup of all 5 bands in one document.

## Running the pipelines locally

Each subfolder has a `README.md` listing the exact shell commands.
The headline path on a Mac with Python 3.10+ and R 4.3+ is:

```
mongodb/             # ensure mongodb/.env has MONGODB_URI, then
                     python3 -m pip install "pymongo[srv]" python-dotenv
                     python3 load_northstar.py
                     python3 queries_demo.py
                     python3 clean_and_build.py
                     python3 queries_v2.py
                     python3 indexes_explain.py
                     python3 install_indexes.py

sql_r/               Rscript load_northstar.R
                     Rscript queries.R

r_analytics/         Rscript analysis.R

python_processing/   python3 -m pip install pandas numpy scipy matplotlib scikit-learn
                     python3 etl.py
                     python3 analyse.py
```

The 9 raw CSVs are at `northstar_dataset/` in the repo so every
loader picks them up by relative path.

## What the data ended up saying

Whichever paradigm I queried, the same answer came out. Failed
deliveries cluster by pickup zone (chi square p = 0.0103, the same
number in scipy and R), not by anything intrinsic to the order.
A random forest over 9 candidate predictors lands at 5-fold ROC AUC
of 0.487 plus or minus 0.064, basically a coin flip. The practical
takeaway for NorthStar is to fix the failing zones rather than spend
modelling effort trying to flag risky orders one by one.

## Reproducibility notes

- Atlas free tier auto-pauses after 60 days idle. Notebook 3 still
  runs in that case because it falls back to `mongomock`. If you want
  the live cluster, sign into Atlas and click Resume Cluster.
- Free tier requires `0.0.0.0/0` on the Network Access allow list for
  any non-Atlas client to connect. That entry is already in place.
- Notebook 2 needs the R runtime. Switch via *Runtime > Change runtime
  type > R* before Run all.

## Author

Larry Oguabia, UWL Databases and Analytics, 2025-2026 academic year.
Submitted 12 May 2026.
