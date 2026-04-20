# Six starter queries against the raw collections. Q1-Q3 are warmups
# ($group + $sort), Q4 is the diagnostic that surfaced the messy zone
# capitalisation (see ZONE_MAP in clean_and_build.py), Q5 is the $lookup
# join, Q6 lists raw delivery_status values.
#
# Note for me: Q5 first returned nothing on a clean Atlas because
# delivery_status had "Failed", "FAILED" and "failed" all in the data.
# The case-insensitive regex match below is the fix.

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


def header(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def q1_priority_distribution():
    # workload mix across priority bands
    header("Q1. Orders grouped by priority_level")
    pipeline = [
        {"$group": {"_id": "$priority_level", "orders": {"$sum": 1}}},
        {"$sort": {"orders": -1}},
    ]
    for row in db.orders.aggregate(pipeline):
        print(f"  {str(row['_id']):<15} {row['orders']}")


def q2_complaints_by_type():
    header("Q2. Complaints grouped by complaint_type")
    pipeline = [
        {"$group": {"_id": "$complaint_type", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
    ]
    for row in db.complaints.aggregate(pipeline):
        print(f"  {str(row['_id']):<25} {row['n']}")


def q3_revenue_by_service():
    header("Q3. Revenue per service_type")
    pipeline = [
        {
            "$group": {
                "_id": "$service_type",
                "orders": {"$sum": 1},
                "total_revenue": {"$sum": "$order_value"},
                "avg_value": {"$avg": "$order_value"},
            }
        },
        {"$sort": {"total_revenue": -1}},
    ]
    for row in db.orders.aggregate(pipeline):
        total = row.get("total_revenue") or 0
        avg = row.get("avg_value") or 0
        print(
            f"  {str(row['_id']):<15} orders={row['orders']:>4}"
            f"  total={total:>10.2f}  avg={avg:>7.2f}"
        )


def q4_zone_case_issues():
    # THIS is the query that surfaced the zone mess. First run gave me
    # Central, central, CENTRAL and Ctr as separate values. Counted 16
    # raw spellings collapsing to 7 real zones. Fix lives in
    # clean_and_build.py.
    header("Q4. Distinct pickup_zone values in orders (data quality check)")
    distinct = sorted(str(z) for z in db.orders.distinct("pickup_zone") if z)
    print(f"  {len(distinct)} distinct values:")
    for z in distinct:
        print(f"    {z!r}")


def q5_join_order_delivery():
    # $lookup orders to deliveries, then keep only failed ones.
    # First version of this returned 0 rows because the literal match
    # was case sensitive and the data had Failed/FAILED/failed. Regex
    # below is the cheap fix that also doubles as a data quality check.
    header("Q5. First 5 orders whose delivery failed ($lookup join)")
    pipeline = [
        {
            "$lookup": {
                "from": "deliveries",
                "localField": "order_id",
                "foreignField": "order_id",
                "as": "delivery",
            }
        },
        {"$unwind": "$delivery"},
        # Case-insensitive match so data quality variants like Failed, FAILED all count.
        {"$match": {"delivery.delivery_status": {"$regex": "^failed$", "$options": "i"}}},
        {
            "$project": {
                "_id": 0,
                "order_id": 1,
                "customer_id": 1,
                "service_type": 1,
                "pickup_zone": 1,
                "delivery_status": "$delivery.delivery_status",
                "route_distance_km": "$delivery.route_distance_km",
                "rating": "$delivery.customer_rating_post_delivery",
            }
        },
        {"$limit": 5},
    ]
    for row in db.orders.aggregate(pipeline):
        print(f"  {row}")


def q6_delivery_status_survey():
    # added this after Q5 to confirm how many spelling variants exist
    header("Q6. Distinct delivery_status values (diagnostic)")
    pipeline = [
        {"$group": {"_id": "$delivery_status", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
    ]
    for row in db.deliveries.aggregate(pipeline):
        print(f"  {str(row['_id']):<25} {row['n']}")


if __name__ == "__main__":
    q1_priority_distribution()
    q2_complaints_by_type()
    q3_revenue_by_service()
    q4_zone_case_issues()
    q5_join_order_delivery()
    q6_delivery_status_survey()
