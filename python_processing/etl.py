# Pandas ETL. Reads the 9 CSVs, scores them before cleaning, applies
# zone canonicalisation, then writes cleaned/ plus the wide table that
# analyse.py uses.

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# CSVs ship under northstar_dataset/ at the repo root.
DATASET_DIR = Path(__file__).resolve().parent.parent / "northstar_dataset"
OUT_DIR = Path(__file__).resolve().parent / "cleaned"
OUT_DIR.mkdir(exist_ok=True)

CSV_FILES = [
    "customers", "orders", "deliveries", "drivers", "vehicles",
    "hubs", "incidents", "complaints", "app_events",
]

# Same canonical zone map as in mongodb/clean_and_build.py and
# sql_r/load_northstar.R, so the 3 paradigms agree.
ZONE_MAP = {
    "AIRPORT": "Airport", "Airport": "Airport",
    "CENTRAL": "Central", "Central": "Central", "Ctr": "Central",
    "EAST": "East", "East": "East",
    "NORTH": "North", "North": "North", "north": "North",
    "RiverSide": "Riverside", "Riverside": "Riverside",
    "SOUTH": "South", "South": "South",
    "WEST": "West", "West": "West",
}

# (table, primary key, list of (foreign key column, referenced table))
SCHEMA = {
    "customers":  ("customer_id",  []),
    "orders":     ("order_id",     [("customer_id", "customers")]),
    "deliveries": ("delivery_id",  [
        ("order_id",   "orders"),
        ("driver_id",  "drivers"),
        ("vehicle_id", "vehicles"),
        ("hub_id",     "hubs"),
    ]),
    "drivers":    ("driver_id",   []),
    "vehicles":   ("vehicle_id",  []),
    "hubs":       ("hub_id",      []),
    "incidents":  ("incident_id",  [("delivery_id", "deliveries")]),
    "complaints": ("complaint_id", [
        ("order_id",    "orders"),
        ("customer_id", "customers"),
    ]),
    "app_events": ("event_id",    [
        ("customer_id", "customers"),
        ("order_id",    "orders"),
    ]),
}

ZONE_FIELDS_BY_TABLE = {
    "customers":  ["home_zone"],
    "orders":     ["pickup_zone", "dropoff_zone"],
    "drivers":    ["base_zone"],
    "vehicles":   ["assigned_zone"],
    "hubs":       ["zone"],
    "app_events": ["zone_context"],
}


# ---------------------------------------------------------------------
# Stage 1. Extract
# ---------------------------------------------------------------------
def extract() -> dict[str, pd.DataFrame]:
    print("Stage 1. Extracting CSVs")
    print("-" * 36)
    frames: dict[str, pd.DataFrame] = {}
    for name in CSV_FILES:
        path = DATASET_DIR / f"{name}.csv"
        df = pd.read_csv(path)
        frames[name] = df
        print(f"  {name:<12} {df.shape[0]:>5} rows  {df.shape[1]:>2} cols")
    return frames


# ---------------------------------------------------------------------
# Stage 2 and 4. Data quality scorecard
# ---------------------------------------------------------------------
def quality_report(frames: dict[str, pd.DataFrame], stage: str) -> pd.DataFrame:
    rows: list[dict] = []
    for table, (pk, fks) in SCHEMA.items():
        df = frames[table]
        n = len(df)
        null_total = int(df.isna().sum().sum())
        dup_pk = int(df[pk].duplicated().sum()) if pk in df.columns else None
        zones = ZONE_FIELDS_BY_TABLE.get(table, [])
        zone_distinct = sum(df[z].nunique(dropna=True) for z in zones if z in df.columns)
        fk_violations = 0
        for fk_col, ref_table in fks:
            if fk_col in df.columns and ref_table in frames:
                ref_pk = SCHEMA[ref_table][0]
                ref_keys = set(frames[ref_table][ref_pk].dropna().unique())
                fk_violations += int(df[fk_col].dropna().apply(
                    lambda v, k=ref_keys: v not in k
                ).sum())
        rows.append({
            "stage": stage,
            "table": table,
            "rows": n,
            "null_cells": null_total,
            "duplicate_pk": dup_pk,
            "fk_violations": fk_violations,
            "zone_distinct_total": zone_distinct,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Stage 3. Transform
# ---------------------------------------------------------------------
def canon_zone(s: pd.Series) -> pd.Series:
    return s.astype("object").map(lambda v: ZONE_MAP.get(v, v) if pd.notna(v) else v)


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Best effort datetime parsing for any column whose name implies a time."""
    out = df.copy()
    for col in out.columns:
        lower = col.lower()
        if any(k in lower for k in ("_at", "_time", "_date", "timestamp")):
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def transform(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    print("\nStage 3. Transforming")
    print("-" * 36)
    cleaned: dict[str, pd.DataFrame] = {}
    for table, df in frames.items():
        df = parse_dates(df)
        for zone_col in ZONE_FIELDS_BY_TABLE.get(table, []):
            if zone_col in df.columns:
                df[zone_col] = canon_zone(df[zone_col])
        cleaned[table] = df
        print(f"  {table:<12} dates parsed, zones canonicalised")
    return cleaned


# ---------------------------------------------------------------------
# Build the analytical wide table
# ---------------------------------------------------------------------
def build_analytical(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per order with delivery, customer, driver, and counts."""
    orders = frames["orders"].copy()

    # Aggregate child tables to per order counts.
    complaint_counts = (
        frames["complaints"].groupby("order_id").size().rename("complaint_count")
    )
    event_counts = (
        frames["app_events"].dropna(subset=["order_id"]).groupby("order_id")
        .size().rename("app_event_count")
    )
    incident_counts = (
        frames["incidents"].groupby("delivery_id").size().rename("incident_count")
    )

    deliveries = frames["deliveries"].merge(
        incident_counts, left_on="delivery_id", right_index=True, how="left"
    )
    deliveries["incident_count"] = deliveries["incident_count"].fillna(0).astype(int)

    df = (
        orders
        .merge(deliveries, on="order_id", how="left", suffixes=("", "_delivery"))
        .merge(frames["customers"], on="customer_id", how="left", suffixes=("", "_cust"))
        .merge(complaint_counts, left_on="order_id", right_index=True, how="left")
        .merge(event_counts, left_on="order_id", right_index=True, how="left")
    )
    df["complaint_count"] = df["complaint_count"].fillna(0).astype(int)
    df["app_event_count"] = df["app_event_count"].fillna(0).astype(int)
    df["incident_count"] = df["incident_count"].fillna(0).astype(int)

    # Derived features.
    df["has_delivery"] = df["delivery_id"].notna()
    df["delivered"] = df["delivery_status"].isin(["OnTime", "Delayed", "Failed"])
    df["failed"] = df["delivery_status"].eq("Failed")
    if "order_created_at" in df.columns:
        df["order_hour"] = df["order_created_at"].dt.hour
        df["order_dow"] = df["order_created_at"].dt.dayofweek
    df["log_distance_km"] = np.log1p(df["route_distance_km"].fillna(0))

    return df


# ---------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------
def save(frames: dict[str, pd.DataFrame], analytical: pd.DataFrame) -> None:
    print("\nStage 5. Loading to cleaned/")
    print("-" * 36)
    for name, df in frames.items():
        path = OUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"  wrote {path.relative_to(OUT_DIR.parent)}")
    analytical_path = OUT_DIR / "orders_full.csv"
    analytical.to_csv(analytical_path, index=False)
    print(f"  wrote {analytical_path.relative_to(OUT_DIR.parent)} ({len(analytical)} rows, {analytical.shape[1]} cols)")


def main() -> int:
    if not DATASET_DIR.exists():
        sys.exit(f"Dataset folder not found: {DATASET_DIR}")

    raw = extract()

    print("\nStage 2. Pre cleanup data quality scorecard")
    print("-" * 36)
    pre = quality_report(raw, "before")
    print(pre.to_string(index=False))

    cleaned = transform(raw)

    print("\nStage 4. Post cleanup data quality scorecard")
    print("-" * 36)
    post = quality_report(cleaned, "after")
    print(post.to_string(index=False))

    diff = post.copy()
    diff["zone_distinct_diff"] = pre["zone_distinct_total"] - post["zone_distinct_total"]
    diff_path = OUT_DIR / "data_quality.csv"
    pd.concat([pre, post]).to_csv(diff_path, index=False)
    print(f"\n  Quality scorecard saved to {diff_path.relative_to(OUT_DIR.parent)}")

    analytical = build_analytical(cleaned)

    print(f"\nAnalytical table built: {len(analytical)} rows, {analytical.shape[1]} columns")

    save(cleaned, analytical)
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
