# Two passes. First, fold the 16 raw zone spellings down to the 7
# canonical title-cased values across every zone column in every
# collection. Then drop orders_aggregate and rebuild it from scratch
# by walking the orders and embedding the matching child docs.

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)
uri = os.getenv("MONGODB_URI", "").strip()
if not uri:
    sys.exit(f"MONGODB_URI is empty. Open {env_path} and paste your string.")

client = MongoClient(uri, serverSelectionTimeoutMS=10000)
db = client["northstar"]


# ---------------------------------------------------------------------------
# Canonical zone map. Keys are every raw spelling that has been observed in
# Q4 of queries_demo.py, values are the canonical title cased zone.
# Ctr is folded into Central because the data dictionary describes it as
# an abbreviation rather than a separate place.
# ---------------------------------------------------------------------------
ZONE_MAP = {
    "AIRPORT": "Airport", "Airport": "Airport",
    "CENTRAL": "Central", "Central": "Central", "Ctr": "Central",
    "EAST": "East", "East": "East",
    "NORTH": "North", "North": "North", "north": "North",
    "RiverSide": "Riverside", "Riverside": "Riverside",
    "SOUTH": "South", "South": "South",
    "WEST": "West", "West": "West",
}

# Every (collection, field) pair that holds a zone string.
ZONE_FIELDS = [
    ("orders", "pickup_zone"),
    ("orders", "dropoff_zone"),
    ("customers", "home_zone"),
    ("drivers", "base_zone"),
    ("vehicles", "assigned_zone"),
    ("hubs", "zone"),
    ("app_events", "zone_context"),
]


def _canonical_to_raw_aliases() -> dict:
    """Invert ZONE_MAP: for each canonical zone, list every raw spelling
    that should be folded into it, excluding the canonical itself.
    """
    out: dict = {}
    for raw, canonical in ZONE_MAP.items():
        if raw == canonical:
            continue
        out.setdefault(canonical, []).append(raw)
    return out


def phase1_normalise_zones() -> None:
    """Apply ZONE_MAP across every (collection, field) in ZONE_FIELDS.

    For each (collection, field) we issue 1 update_many per canonical zone
    using $in across all the raw aliases for that zone. That keeps the
    number of round trips small (7 canonicals x 7 fields = 49 calls) and
    avoids the pymongo-version-specific UpdateMany operation class.
    """
    print("Phase 1. Normalising zone fields")
    print("-" * 36)
    aliases = _canonical_to_raw_aliases()
    grand_total = 0
    for col_name, field in ZONE_FIELDS:
        col = db[col_name]
        col_modified = 0
        for canonical, raws in aliases.items():
            res = col.update_many(
                {field: {"$in": raws}},
                {"$set": {field: canonical}},
            )
            col_modified += res.modified_count
        grand_total += col_modified
        print(f"  {col_name}.{field:<14} updated {col_modified} docs")
    print(f"\n  Total documents touched: {grand_total}")


def _strip_id(doc: dict) -> dict:
    """Return a shallow copy of doc with the BSON _id key removed.

    Used so that embedded sub documents do not carry the ObjectId of the
    source collection's parent. Each orders_aggregate document gets its own
    _id.
    """
    return {k: v for k, v in doc.items() if k != "_id"}


def phase2_build_aggregate() -> None:
    """Build orders_aggregate by joining 5 raw collections in Python.

    Doing the joins in Python rather than 1 huge $lookup pipeline is more
    readable and easier to inspect, and the dataset is small enough that
    speed is not a concern.
    """
    print("\nPhase 2. Building orders_aggregate")
    print("-" * 36)

    db.orders_aggregate.drop()

    # Build lookup dicts once, then reuse them in the per order loop.
    customers = {c["customer_id"]: c for c in db.customers.find()}
    deliveries = {d["order_id"]: d for d in db.deliveries.find()}

    incidents_by_delivery: dict[str, list] = {}
    for inc in db.incidents.find():
        incidents_by_delivery.setdefault(inc["delivery_id"], []).append(inc)

    complaints_by_order: dict[str, list] = {}
    for c in db.complaints.find():
        complaints_by_order.setdefault(c["order_id"], []).append(c)

    events_by_order: dict[str, list] = {}
    for e in db.app_events.find():
        oid = e.get("order_id")
        if oid:
            events_by_order.setdefault(oid, []).append(e)

    docs = []
    for order in db.orders.find():
        order_id = order.get("order_id")
        customer_id = order.get("customer_id")

        agg = _strip_id(order)

        # Embedded customer snapshot.
        cust = customers.get(customer_id)
        agg["customer"] = _strip_id(cust) if cust else None

        # Embedded delivery, with embedded incidents inside it.
        deliv = deliveries.get(order_id)
        if deliv:
            deliv_doc = _strip_id(deliv)
            deliv_doc["incidents"] = [
                _strip_id(i)
                for i in incidents_by_delivery.get(deliv_doc["delivery_id"], [])
            ]
            agg["delivery"] = deliv_doc
        else:
            agg["delivery"] = None

        agg["complaints"] = [_strip_id(c) for c in complaints_by_order.get(order_id, [])]
        agg["app_events"] = [_strip_id(e) for e in events_by_order.get(order_id, [])]

        docs.append(agg)

    if docs:
        db.orders_aggregate.insert_many(docs)

    n = db.orders_aggregate.estimated_document_count()
    n_with_delivery = db.orders_aggregate.count_documents({"delivery": {"$ne": None}})
    n_with_complaints = db.orders_aggregate.count_documents({"complaints.0": {"$exists": True}})
    n_with_events = db.orders_aggregate.count_documents({"app_events.0": {"$exists": True}})
    print(f"  orders_aggregate documents inserted: {n}")
    print(f"    of which have an embedded delivery:    {n_with_delivery}")
    print(f"    of which have at least 1 complaint:    {n_with_complaints}")
    print(f"    of which have at least 1 app event:    {n_with_events}")


def post_summary() -> None:
    """Verify the cleanup by printing the distinct zone count per field."""
    print("\nPost cleanup zone distinct counts")
    print("-" * 36)
    for col_name, field in ZONE_FIELDS:
        vals = sorted(str(v) for v in db[col_name].distinct(field) if v is not None)
        print(f"  {col_name}.{field:<14} {len(vals)} distinct: {vals}")


def main() -> int:
    phase1_normalise_zones()
    phase2_build_aggregate()
    post_summary()
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
