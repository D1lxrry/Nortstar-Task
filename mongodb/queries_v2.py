# Six analytical queries against orders_aggregate. Each one answers a
# specific business question. After clean_and_build.py builds the
# embedded collection most of these become single-document reads.

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
oa = db.orders_aggregate


def header(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def v1_failure_rate_by_service() -> None:
    """V1. Failure rate per service line.

    Business question. NorthStar runs 5 service lines (Passenger, Parcel,
    Retail, Business, Medical). Which lines fail to fulfil most often?
    Combined with the revenue ranking from queries_demo.Q3 this points at
    where operational fixes will have the biggest revenue impact.

    Why the embedded schema helps. delivery_status sits inside the order
    document, so the pipeline is a single $group on `orders_aggregate`
    with no $lookup. If we still had separate collections this would need
    a $lookup from orders to deliveries first.
    """
    header("V1. Failure rate by service_type")
    pipeline = [
        {"$match": {"delivery": {"$ne": None}}},
        {
            "$group": {
                "_id": "$service_type",
                "total": {"$sum": 1},
                "failed": {
                    "$sum": {
                        "$cond": [{"$eq": ["$delivery.delivery_status", "Failed"]}, 1, 0]
                    }
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "service_type": "$_id",
                "total": 1,
                "failed": 1,
                "failure_rate_pct": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$failed", "$total"]}, 100]},
                        2,
                    ]
                },
            }
        },
        {"$sort": {"failure_rate_pct": -1}},
    ]
    for r in oa.aggregate(pipeline):
        print(
            f"  {r['service_type']:<10} "
            f"total={r['total']:>4}  failed={r['failed']:>4}  "
            f"rate={r['failure_rate_pct']:>5}%"
        )


def v2_avg_rating_by_zone() -> None:
    """V2. Customer satisfaction by zone, post cleanup.

    Business question. Where do customers rate the service worst? Lowest
    rated zones are candidates for the operational deep dive in the
    report.

    Why the embedded schema helps. customer_rating_post_delivery is a
    field on the embedded delivery doc, and pickup_zone has been
    canonicalised in phase 1 of clean_and_build, so the $group only
    produces 7 buckets rather than the 16 we saw in queries_demo Q4.
    """
    header("V2. Average delivery rating by pickup_zone (post cleanup)")
    pipeline = [
        {"$match": {"delivery.customer_rating_post_delivery": {"$ne": None}}},
        {
            "$group": {
                "_id": "$pickup_zone",
                "avg_rating": {"$avg": "$delivery.customer_rating_post_delivery"},
                "n": {"$sum": 1},
            }
        },
        {"$sort": {"avg_rating": 1}},
    ]
    for r in oa.aggregate(pipeline):
        print(
            f"  {str(r['_id']):<12} "
            f"avg_rating={r['avg_rating']:.2f}  n={r['n']}"
        )


def v3_compound_risk_orders() -> None:
    """V3. Orders with both a complaint and a failed delivery.

    Business question. Which orders are double trouble? An order that
    failed to deliver AND generated a complaint is the worst possible
    outcome and the most likely customer churn signal.

    Why the embedded schema helps. The match needs 2 conditions on 2
    different child collections (complaints and deliveries). With separate
    collections this is at minimum 2 $lookups plus a $match. With the
    embedded schema it is a single $match using the dot notation
    `delivery.delivery_status` and the array test `complaints.0`
    (true if the array has at least 1 element).
    """
    header("V3. Orders with both a complaint and a failed delivery")
    n_match = oa.count_documents(
        {
            "complaints.0": {"$exists": True},
            "delivery.delivery_status": "Failed",
        }
    )
    pipeline = [
        {
            "$match": {
                "complaints.0": {"$exists": True},
                "delivery.delivery_status": "Failed",
            }
        },
        {
            "$project": {
                "_id": 0,
                "order_id": 1,
                "service_type": 1,
                "pickup_zone": 1,
                "complaint_count": {"$size": "$complaints"},
                "rating": "$delivery.customer_rating_post_delivery",
            }
        },
        {"$sort": {"complaint_count": -1, "rating": 1}},
        {"$limit": 5},
    ]
    print(f"  Matching orders in total: {n_match}")
    print(f"  Top 5 by complaint count, then by lowest rating:")
    for r in oa.aggregate(pipeline):
        rating = r.get("rating")
        rating_str = "N/A" if rating is None else f"{rating:.2f}"
        print(
            f"    {r['order_id']:<8} {r['service_type']:<10} "
            f"{str(r['pickup_zone']):<10} "
            f"complaints={r['complaint_count']}  rating={rating_str}"
        )


def v4_zone_incident_density() -> None:
    """V4. Incident density per delivery, by zone.

    Business question. Which zones cause the most operational pain per
    delivery, where an incident is anything from a traffic delay to a
    package damage report?

    Why the embedded schema helps. incidents are an array inside the
    embedded delivery, so $size on `delivery.incidents` gives the per
    delivery incident count without any join.
    """
    header("V4. Incidents per delivery, by pickup_zone")
    pipeline = [
        {"$match": {"delivery": {"$ne": None}}},
        {
            "$project": {
                "pickup_zone": 1,
                "incident_count": {
                    "$size": {"$ifNull": ["$delivery.incidents", []]}
                },
            }
        },
        {
            "$group": {
                "_id": "$pickup_zone",
                "deliveries": {"$sum": 1},
                "incidents": {"$sum": "$incident_count"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "zone": "$_id",
                "deliveries": 1,
                "incidents": 1,
                "incidents_per_delivery": {
                    "$round": [{"$divide": ["$incidents", "$deliveries"]}, 3]
                },
            }
        },
        {"$sort": {"incidents_per_delivery": -1}},
    ]
    for r in oa.aggregate(pipeline):
        print(
            f"  {str(r['zone']):<12} "
            f"deliveries={r['deliveries']:>4}  "
            f"incidents={r['incidents']:>4}  "
            f"rate={r['incidents_per_delivery']}"
        )


def v5_driver_performance() -> None:
    """V5. Top 10 drivers by completed deliveries, with rating.

    Business question. Who are the busiest drivers and how do customers
    rate them? Driver level work is for an internal performance review,
    not a customer report.

    Why this one DOES use $lookup. drivers is reference data and is kept
    as a separate collection by design (see schema_design.md). We compute
    the per driver aggregate from `orders_aggregate` first, then join the
    driver attributes (employment_type, base_zone) on at the end.
    """
    header("V5. Top 10 drivers by completed deliveries")
    pipeline = [
        {"$match": {"delivery.driver_id": {"$ne": None}}},
        {
            "$group": {
                "_id": "$delivery.driver_id",
                "deliveries": {"$sum": 1},
                "avg_rating": {"$avg": "$delivery.customer_rating_post_delivery"},
            }
        },
        {
            "$lookup": {
                "from": "drivers",
                "localField": "_id",
                "foreignField": "driver_id",
                "as": "driver",
            }
        },
        {"$unwind": "$driver"},
        {
            "$project": {
                "_id": 0,
                "driver_id": "$_id",
                "employment_type": "$driver.employment_type",
                "base_zone": "$driver.base_zone",
                "deliveries": 1,
                "avg_rating": {"$round": ["$avg_rating", 2]},
            }
        },
        {"$sort": {"deliveries": -1}},
        {"$limit": 10},
    ]
    for r in oa.aggregate(pipeline):
        rating = r.get("avg_rating")
        rating_str = "N/A" if rating is None else str(rating)
        print(
            f"  {r['driver_id']:<8} "
            f"{str(r['employment_type']):<10} "
            f"base={str(r['base_zone']):<10} "
            f"deliveries={r['deliveries']:>3}  "
            f"rating={rating_str}"
        )


def v6_app_engagement_vs_outcome() -> None:
    """V6. App engagement vs delivery outcome.

    Business question. Do customers who interact more with the app before
    placing an order get better delivery outcomes? If yes, app
    engagement is a real leading indicator and worth investing in. If no,
    it is vanity.

    Why the embedded schema helps. app_events is an embedded array on
    each order, so $size gives the per order engagement count, and we
    can $bucket on it directly without a join. With separate collections
    this would need an aggregation on app_events first to get a per
    order count, then a $lookup back into orders.
    """
    header("V6. Delivery outcome vs in app event count buckets")
    pipeline = [
        {"$match": {"delivery": {"$ne": None}}},
        {
            "$project": {
                "outcome": "$delivery.delivery_status",
                "events": {"$size": {"$ifNull": ["$app_events", []]}},
            }
        },
        {
            "$bucket": {
                "groupBy": "$events",
                "boundaries": [0, 1, 3, 5, 1000],
                "default": "Other",
                "output": {
                    "n": {"$sum": 1},
                    "OnTime": {
                        "$sum": {"$cond": [{"$eq": ["$outcome", "OnTime"]}, 1, 0]}
                    },
                    "Delayed": {
                        "$sum": {"$cond": [{"$eq": ["$outcome", "Delayed"]}, 1, 0]}
                    },
                    "Failed": {
                        "$sum": {"$cond": [{"$eq": ["$outcome", "Failed"]}, 1, 0]}
                    },
                },
            }
        },
    ]
    for r in oa.aggregate(pipeline):
        bucket = r["_id"]
        n = r["n"] or 1
        ontime_pct = round(100 * r["OnTime"] / n, 1)
        failed_pct = round(100 * r["Failed"] / n, 1)
        print(
            f"  events>={bucket:<4} "
            f"n={n:>4}  "
            f"OnTime={r['OnTime']:>3} ({ontime_pct}%)  "
            f"Delayed={r['Delayed']:>3}  "
            f"Failed={r['Failed']:>3} ({failed_pct}%)"
        )


def main() -> int:
    v1_failure_rate_by_service()
    v2_avg_rating_by_zone()
    v3_compound_risk_orders()
    v4_zone_incident_density()
    v5_driver_performance()
    v6_app_engagement_vs_outcome()
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
