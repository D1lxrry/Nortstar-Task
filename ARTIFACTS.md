# Submission artefacts index

Everything below is what I am handing in for the UWL Databases and
Analytics module, NorthStar Urban Mobility & Logistics case study.
The right-hand column shows which line of the rubric each artefact
is meant to satisfy. Submission date: 12 May 2026.

## 1. Written report (single .docx at repo root)

| File | Marks bands covered | What it covers |
|------|---------------------|----------------|
| `NorthStar Consolidated Report.docx` | All 5 bands (80 marks of the 80-mark written submission) | Single deliverable. 18 numbered code listings pointing at the source files and line ranges, 9 numbered figures plus 5 native tables, clickable links to the GitHub repo and the 3 Colab notebooks at the top. |

The remaining 20 marks come from the in-person demo, which references
the same notebooks live.

## 2. Colab notebooks (`colab_notebooks/`)

| Notebook | Runtime | Bands | Standalone? |
|----------|---------|-------|-------------|
| `01_python_data_processing.ipynb`        | Python | Python data processing (20) | Yes, pulls CSVs from the repo at runtime. |
| `02_r_sql_and_analytics.ipynb`           | R      | SQL in R (15) + R analytics (15) | Yes, pulls CSVs from the repo at runtime. |
| `03_mongodb_and_query_optimisation.ipynb`| Python | MongoDB (20) + Query optimisation (10) | Yes. Tries live Atlas first, falls back to mongomock if cluster unreachable. |

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
- The R notebook used to depend on a SQLite database built by an
  earlier notebook. It now rebuilds the SQLite file at runtime from
  the GitHub hosted CSVs, so the 3 notebooks are independent.
