# NorthStar Colab notebooks

These are the runnable form of the coursework, the GitHub plus Colab
half of the deliverable. Each notebook covers 1 of the 5 marked
sections of the project and runs end to end on its own. Open any of
them in Colab and click Run all.

## What is in each notebook

`01_mongodb_pipeline.ipynb` runs on the Python kernel. It connects to
my free tier Atlas cluster, loads the 9 CSVs, and runs the 12
aggregations the report walks through, including the `$lookup` stage
that joins drivers in. It also builds `orders_aggregate`, the embedded
order document collection.

`02_query_optimisation.ipynb` is also Python. For 4 query archetypes
it drops every secondary index, captures `explain()`, builds the
proposed indexes, captures `explain()` again, and prints before and
after side by side. The numbers go into the Query Optimisation report.

`03_sql_in_r.ipynb` runs on the R kernel. It rebuilds a normalised
SQLite mirror of the 9 CSVs and runs the 9 SQL queries that the report
covers, including the `RANK() OVER PARTITION BY` window function.

`04_r_analytics.ipynb` is also R. It does the tidyverse data prep, the
5 ggplot2 charts, the 4 hypothesis tests, and the logistic regression
of delivery failure on the candidate predictors.

`05_python_data_processing.ipynb` is Python again. It runs the pandas
ETL, the data quality scorecard, the scipy chi square tests that pair
with the R tests, and the scikit-learn random forest classifier.

The 5 notebooks together cover 80 of the 80 written marks. The 20
mark in person demo references the same notebooks at runtime.

## Setup, once per session

For notebooks 01 and 02 (the MongoDB ones) Atlas needs to know about
the Colab IP and the notebook needs the connection string. The IP
side is `0.0.0.0/0` in Atlas Network Access, which is the standard
free tier compromise. The string side is a Colab Secret named
`MONGODB_URI`. Open notebook 01, click the key icon in the left
sidebar, add a new secret with that name and your full SRV URI, and
flip Notebook access ON. The cell then reads it with
`userdata.get('MONGODB_URI')` so the password never goes into the
source.

For notebooks 03 and 04 the runtime has to be R rather than Python.
`Runtime` then `Change runtime type` then `R` and Save. The runtime
restarts on the R kernel.

The R notebooks (03, 04) and notebook 05 read the 9 CSVs directly
from the GitHub repo over HTTPS, so no upload or Drive mount is
needed. The first code cell of each calls `read.csv` (or
`pandas.read_csv`) against
`https://raw.githubusercontent.com/D1lxrry/Nortstar-Task/main/northstar_dataset/...`
and stores the resulting data frames.

Notebooks 01 and 02 do not need the CSVs at runtime because they
read from Atlas, where the data was loaded earlier.

## What order to run them in

End to end runtimes are roughly 5 minutes for 01, 1 minute for 02,
2 minutes for 03, 3 minutes for 04 and 3 minutes for 05. The 5 are
independent now (04 used to depend on 03, but it has been made self
contained), so a marker can pick any one and click Run all without
running the others first.

## Pushing to GitHub

The standard workflow is to keep this `colab_notebooks/` folder in a
git repository, then open notebooks directly from GitHub in Colab via
the URL pattern `https://colab.research.google.com/github/USER/REPO/blob/main/colab_notebooks/01_mongodb_pipeline.ipynb`.
The `Open in Colab` browser extension gives a 1 click button on every
`.ipynb` file in a GitHub view.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `MONGODB_URI is None` | Secret not toggled on for this notebook | Re open the Secrets pane, toggle Notebook access |
| `pymongo.errors.ServerSelectionTimeoutError` SSL | Common on first run | Just retry the cell; it usually clears |
| `pymongo.errors.OperationFailure: bad auth` | Wrong password | Reset the Atlas database user password and update the Secret |
| `pymongo.errors.ServerSelectionTimeoutError`, no SSL message | Atlas Network Access blocking the Colab IP | Add `0.0.0.0/0` to Atlas Network Access |
| `No such file: northstar.sqlite` in notebook 04 | Notebook 03 has not been run in this session | Run notebook 03 first |
| R kernel says package not found | Runtime not switched to R, or session restarted | `Runtime` -> `Change runtime type` -> `R`, then re run setup cell |
