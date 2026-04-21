# NorthStar MongoDB schema design

## Why I picked the order as the root document

I started by listing every question in the brief. They almost all reduce to one
of 2 shapes: "what happened to this specific order" or "group orders by attribute
X and aggregate". So the order is the obvious thing to centre the document around.
Customer, delivery, incidents, complaints and in-app events all describe the
lifecycle of an order, so they belong inside that document. Drivers, vehicles
and hubs are operational reference data that get queried in their own right
(driver performance, hub capacity, vehicle maintenance), so they stay in
separate collections.

In practical terms this gives 1 new collection, `orders_aggregate`, where each document
has the shape sketched below. The 9 raw collections produced by `load_northstar.py` stay
exactly as they are, so SQL style queries and the loader for the report still work
unchanged. `orders_aggregate` is a derived view, rebuilt from the raw collections by
`clean_and_build.py` whenever the underlying data changes.

```
{
  "_id": ObjectId(...),
  "order_id": "O00023",
  "service_type": "Passenger",
  "priority_level": "Medium",
  "pickup_zone": "North",          // canonical, post cleanup
  "dropoff_zone": "Central",       // canonical, post cleanup
  "order_value": 96.07,
  "order_created_at": ISODate(...),

  "customer": {                    // EMBEDDED snapshot
    "customer_id": "C0077",
    "home_zone": "North",          // canonical, post cleanup
    "customer_type": "Repeat",
    "loyalty_score": 72,
    "app_engagement_score": 58
  },

  "delivery": {                    // EMBEDDED, 0 or 1
    "delivery_id": "D00045",
    "driver_id": "DR0021",         // REFERENCE only, drivers stays separate
    "vehicle_id": "V0019",         // REFERENCE only
    "hub_id": "H03",               // REFERENCE only
    "delivery_status": "Failed",
    "route_distance_km": 15.56,
    "customer_rating_post_delivery": 2.38,
    "incidents": [                 // EMBEDDED array, 0..n
      { "incident_id": "I00012", "incident_type": "TrafficDelay", "severity": "Medium" }
    ]
  },

  "complaints": [ ... ],           // EMBEDDED array, 0..n
  "app_events": [ ... ]            // EMBEDDED array, 0..n
}
```

## What I embedded and why

The customer goes in as a snapshot. Almost every analytical query I wrote reads
at least 1 customer field (home_zone for cohorting, loyalty_score for
segmentation, app_engagement_score for behavioural questions), so embedding kills
a `$lookup` on the dominant access pattern. The snapshot also matches what the
business actually wants: when I run a report on Q3 orders, I want the customer
attributes as they were in Q3, not as they are today after a profile edit.

Delivery is 1:1 with order, so it goes in directly as a sub-document. Of 1250
orders, 950 have a delivery, the rest were never dispatched. The full document
sits well under 100 KB, nowhere near the 16 MB BSON cap. The advantage is that
"did this order fulfil and how" reads as 1 document.

Incidents nest inside the delivery. Median is 0 per delivery, max around 3, and
they only ever get read in the context of their parent. I never had a query that
asked about an incident in isolation. `$unwind` over an embedded array is enough.

Complaints sit on the order rather than the delivery, because some complaints
relate to the order itself (price, missing items) rather than the delivery. That
also makes a query like "orders with both a complaint and a failed delivery"
trivial: 1 document, 2 fields.

App events are embedded too. Cardinality is small per order (median 0, max
around 5) and the natural query is funnel shaped, "what app events preceded
this order and what happened next". A `$size` operator on the embedded array
gives me that without joining.

## What I kept as a separate collection

Drivers, vehicles and hubs all stay where they are. They exist on their own
terms, get queried in their own terms (driver performance, vehicle maintenance,
hub capacity), and embedding driver attributes in every order would duplicate
them 1250 times and invalidate them every time a driver's training_score
changes. Worse, "which drivers have the worst rating this quarter" would have
to iterate the orders collection instead of the small drivers one. Reference
wins here.

I also kept the 9 raw collections that `load_northstar.py` produces. They are
the audit trail. `orders_aggregate` is a derived view that `clean_and_build.py`
rebuilds whenever the raw data shifts, in the same way a materialised view
gets rebuilt against a relational source.

## Trade offs I accepted

The snapshot loses currency on purpose. A customer who changes their loyalty
tier next week will not retroactively change last quarter's reports. That is
the right answer for analytics but it would be the wrong answer for a live
checkout system.

There is some write amplification. Inserting a new order means assembling the
customer snapshot plus any related child docs. I decided that was fine because
the analytics workload is read heavy, and the coursework is not pretending to
be a live OLTP system.

There is also some duplication. An incident shows up both in the standalone
`incidents` collection and inside the parent order's `delivery.incidents`
array. The total cost is small because there are only 280 incidents, and the
duplication only exists while the raw collections are kept around as the
audit trail.

## Zone canonicalisation rule (used by clean_and_build.py)

A side discovery from `queries_demo.py` Q4 was that the same zone is spelled in up
to 3 different ways across collections. The cleanup pass collapses all 16 raw spellings
into 7 canonical title cased zones using the table below. The same map is applied to
every zone field in every collection so that any future query can group by zone
without surprises.

| Canonical | Raw spellings folded in           |
|-----------|------------------------------------|
| Airport   | AIRPORT, Airport                   |
| Central   | CENTRAL, Central, Ctr              |
| East      | EAST, East                         |
| North     | NORTH, North, north                |
| Riverside | RiverSide, Riverside               |
| South     | SOUTH, South                       |
| West      | WEST, West                         |

Note `Ctr` is collapsed into `Central` because the data dictionary describes it as
an abbreviation. If a future analysis needs to keep them apart, the raw collections
still hold the original spelling.

## How this maps to the rubric

For MongoDB development (20 marks), the schema, the cleanup script and the
analytical queries between them give evidence of schema design,
aggregation, embedded vs referenced reasoning and `$lookup`.

For Python data processing (part of 20 marks), `clean_and_build.py` is a small
pandas-free pipeline that normalises raw fields and assembles a derived
collection, which is enough to count toward the data processing brief in its
own right.

For query optimisation (10 marks), once `orders_aggregate` is in place I index
`order_id`, `customer_id`, `service_type` and `pickup_zone` and capture the
`explain()` output before and after the indexes go on. That experiment lives
in `indexes_explain.py` and the matching report.
