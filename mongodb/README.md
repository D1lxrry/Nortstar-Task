# NorthStar MongoDB pipeline

MongoDB side of the coursework. Loads the 9 NorthStar CSVs into the
Atlas cluster, canonicalises zone spellings, builds the embedded
`orders_aggregate` collection, runs 12 analytical aggregations, and
profiles 4 query archetypes before vs after indexing.

The Atlas URI lives in a local `.env` (not committed). The
`.env.example` file is the safe stub.

## Files

- `load_northstar.py` bulk-loads the 9 raw CSVs into 9 collections.
- `clean_and_build.py` collapses 16 raw zone spellings into 7
  canonical values, then assembles `orders_aggregate` with embedded
  customer, delivery and incidents.
- `queries_demo.py` is the starter set, Q1 to Q6. Q4 is where the
  zone-quality issue surfaced.
- `queries_v2.py` is the analytical set, V1 to V6, against the
  embedded collection. V5 is the one query that needs `$lookup`
  because drivers are intentionally not embedded.
- `indexes_explain.py` runs the 4 archetypes through
  `executionStats` with and without the proposed indexes and prints
  a `docsExamined` reduction factor for each.
- `install_indexes.py` installs the recommended production index set.
- `schema_design.md` writes up the embedded vs referenced reasoning.
- `test_connection.py` pings the cluster and lists databases.
- `.env.example` is the stub for the Atlas connection string.

## Run

```
python3 -m pip install "pymongo[srv]" python-dotenv
python3 load_northstar.py
python3 clean_and_build.py
python3 queries_v2.py
python3 indexes_explain.py
```
