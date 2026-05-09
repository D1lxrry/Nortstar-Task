# Apply the recommended index set on orders_aggregate.
# Re-running is safe: existing indexes with the same name are skipped.

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)
uri = os.getenv("MONGODB_URI", "").strip()
if not uri:
    sys.exit(f"MONGODB_URI is empty. Open {env_path} and paste your string.")

client = MongoClient(uri, serverSelectionTimeoutMS=10000)
db = client["northstar"]
oa = db.orders_aggregate


# Index recommendations from Section 7 of Query Optimisation Report.docx.
# Each entry: (key spec list, options dict, justification).
INDEXES = [
    (
        [("order_id", ASCENDING)],
        {"unique": True, "name": "order_id_unique"},
        "Point lookups and a primary key style integrity constraint (Q_C).",
    ),
    (
        [("service_type", ASCENDING), ("delivery.delivery_status", ASCENDING)],
        {"name": "service_type_delivery_status"},
        "Compound predicate covering V1 and Q_B. Most selective field first.",
    ),
    (
        [("pickup_zone", ASCENDING)],
        {"name": "pickup_zone_1"},
        "Reporting filter for V2 and V4.",
    ),
    (
        [("delivery.driver_id", ASCENDING)],
        {"name": "delivery_driver_id_1"},
        "Driver level aggregation in V5.",
    ),
    (
        [("customer.customer_id", ASCENDING)],
        {"name": "customer_customer_id_1"},
        "Customer cohort analysis (planned R analytics step).",
    ),
]


def main() -> int:
    print("Installing recommended index set on orders_aggregate")
    print("-" * 56)
    for keys, opts, why in INDEXES:
        try:
            name = oa.create_index(keys, **opts)
            print(f"  + {name}")
            print(f"      keys: {dict(keys)}")
            print(f"      why:  {why}")
        except Exception as exc:
            print(f"  ! {opts.get('name')}: {exc}")

    print()
    print("Final indexes installed on orders_aggregate")
    print("-" * 56)
    for ix in oa.list_indexes():
        print(f"  - {ix['name']:<35} keys={dict(ix['key'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
