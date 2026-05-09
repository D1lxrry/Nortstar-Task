# Build northstar.sqlite from the 9 CSVs. Applies the same zone
# canonicalisation as the MongoDB side so SQL and Mongo queries agree.

suppressPackageStartupMessages({
  library(DBI)
  library(RSQLite)
  library(readr)
})

# Find the dataset relative to wherever this script lives. The repo
# layout puts northstar_dataset/ at the repo root, one level up from
# sql_r/. When sourcing from RStudio the working directory differs,
# so check both.
script_dir <- tryCatch(dirname(sys.frame(1)$ofile),
                       error = function(e) getwd())
DATASET_DIR <- normalizePath(file.path(script_dir, "..", "northstar_dataset"),
                             mustWork = FALSE)
if (!dir.exists(DATASET_DIR)) {
  DATASET_DIR <- normalizePath(file.path(getwd(), "..", "northstar_dataset"),
                               mustWork = FALSE)
}
SQLITE_PATH <- "northstar.sqlite"

# Canonical zone map. Mirrors ZONE_MAP in mongodb/clean_and_build.py.
zone_map <- c(
  "AIRPORT" = "Airport",   "Airport" = "Airport",
  "CENTRAL" = "Central",   "Central" = "Central",  "Ctr" = "Central",
  "EAST" = "East",         "East" = "East",
  "NORTH" = "North",       "North" = "North",      "north" = "North",
  "RiverSide" = "Riverside", "Riverside" = "Riverside",
  "SOUTH" = "South",       "South" = "South",
  "WEST" = "West",         "West" = "West"
)

canon_zone <- function(x) {
  if (is.null(x)) return(x)
  s <- as.character(x)
  out <- zone_map[s]
  out[is.na(out)] <- s[is.na(out)]
  unname(out)
}

# ----------------------------------------------------------------------
# Open or create the SQLite database
# ----------------------------------------------------------------------
con <- dbConnect(RSQLite::SQLite(), SQLITE_PATH)

# Drop existing tables so reruns are idempotent.
for (t in dbListTables(con)) {
  dbExecute(con, paste0("DROP TABLE IF EXISTS \"", t, "\""))
}

# ----------------------------------------------------------------------
# Helper to load a single CSV with optional zone canonicalisation
# ----------------------------------------------------------------------
load_csv <- function(name, zone_cols = character(0)) {
  path <- file.path(DATASET_DIR, paste0(name, ".csv"))
  df <- readr::read_csv(path, show_col_types = FALSE, progress = FALSE)
  for (col in zone_cols) {
    if (col %in% names(df)) df[[col]] <- canon_zone(df[[col]])
  }
  dbWriteTable(con, name, as.data.frame(df), overwrite = TRUE)
  cat(sprintf("  %-12s %5d rows\n", name, nrow(df)))
  invisible(nrow(df))
}

cat("Loading CSVs into SQLite database\n")
cat("---------------------------------\n")
load_csv("customers",  zone_cols = "home_zone")
load_csv("orders",     zone_cols = c("pickup_zone", "dropoff_zone"))
load_csv("deliveries")
load_csv("drivers",    zone_cols = "base_zone")
load_csv("vehicles",   zone_cols = "assigned_zone")
load_csv("hubs",       zone_cols = "zone")
load_csv("incidents")
load_csv("complaints")
load_csv("app_events", zone_cols = "zone_context")

# ----------------------------------------------------------------------
# Indexes. SQLite already creates a hidden rowid index, but we add
# explicit indexes on join keys so the EXPLAIN QUERY PLAN output for
# multi table queries shows IDX SCAN rather than full table scans.
# ----------------------------------------------------------------------
cat("\nCreating join indexes\n")
cat("---------------------------------\n")

idx_sqls <- c(
  "CREATE INDEX idx_orders_customer    ON orders(customer_id)",
  "CREATE INDEX idx_deliveries_order   ON deliveries(order_id)",
  "CREATE INDEX idx_deliveries_driver  ON deliveries(driver_id)",
  "CREATE INDEX idx_complaints_order   ON complaints(order_id)",
  "CREATE INDEX idx_app_events_order   ON app_events(order_id)",
  "CREATE INDEX idx_incidents_delivery ON incidents(delivery_id)"
)
for (sql in idx_sqls) {
  dbExecute(con, sql)
  cat("  +", sub("CREATE INDEX ", "", sql), "\n")
}

# ----------------------------------------------------------------------
# Verification: distinct zone values per zone field
# ----------------------------------------------------------------------
cat("\nPost cleanup zone distinct counts\n")
cat("---------------------------------\n")
zone_fields <- list(
  c("orders",     "pickup_zone"),
  c("orders",     "dropoff_zone"),
  c("customers",  "home_zone"),
  c("drivers",    "base_zone"),
  c("vehicles",   "assigned_zone"),
  c("hubs",       "zone"),
  c("app_events", "zone_context")
)
for (pair in zone_fields) {
  tbl <- pair[1]; fld <- pair[2]
  vals <- dbGetQuery(
    con,
    sprintf("SELECT DISTINCT %s AS v FROM %s WHERE %s IS NOT NULL ORDER BY %s",
            fld, tbl, fld, fld)
  )$v
  cat(sprintf("  %s.%-14s %d distinct: %s\n",
              tbl, fld, length(vals), paste(vals, collapse = ", ")))
}

dbDisconnect(con)
cat(sprintf("\nDatabase saved to %s\n", normalizePath(SQLITE_PATH)))
