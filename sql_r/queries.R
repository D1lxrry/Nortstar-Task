# 9 SQL queries against northstar.sqlite. S1-S8 pair with the MongoDB
# aggregations in mongodb/queries_v2.py. S9 is the window function that
# Mongo cannot express as cleanly.

suppressPackageStartupMessages({
  library(DBI)
  library(RSQLite)
})

con <- dbConnect(RSQLite::SQLite(), "northstar.sqlite")

run <- function(title, sql) {
  cat("\n", title, "\n", strrep("-", nchar(title)), "\n", sep = "")
  result <- dbGetQuery(con, sql)
  print(result, row.names = FALSE)
  invisible(result)
}

# ---- S1. Orders by priority_level ------------------------------------
# MongoDB equivalent: queries_demo.Q1
run("S1. Orders grouped by priority_level",
"SELECT priority_level, COUNT(*) AS orders
   FROM orders
  GROUP BY priority_level
  ORDER BY orders DESC")

# ---- S2. Complaints by complaint_type --------------------------------
# MongoDB equivalent: queries_demo.Q2
run("S2. Complaints grouped by complaint_type",
"SELECT complaint_type, COUNT(*) AS complaints
   FROM complaints
  GROUP BY complaint_type
  ORDER BY complaints DESC")

# ---- S3. Revenue per service_type ------------------------------------
# MongoDB equivalent: queries_demo.Q3
run("S3. Revenue per service_type",
"SELECT service_type,
        COUNT(*)                       AS orders,
        ROUND(SUM(order_value), 2)     AS total_revenue,
        ROUND(AVG(order_value), 2)     AS avg_value
   FROM orders
  GROUP BY service_type
  ORDER BY total_revenue DESC")

# ---- S4. Failure rate by service_type --------------------------------
# MongoDB equivalent: queries_v2.V1
# Demonstrates INNER JOIN plus conditional aggregation with CASE WHEN.
run("S4. Failure rate by service_type",
"SELECT o.service_type,
        COUNT(*)                                                    AS total,
        SUM(CASE WHEN d.delivery_status = 'Failed' THEN 1 ELSE 0 END) AS failed,
        ROUND(100.0 *
              SUM(CASE WHEN d.delivery_status = 'Failed' THEN 1 ELSE 0 END) /
              COUNT(*), 2)                                           AS failure_rate_pct
   FROM orders     o
   JOIN deliveries d ON o.order_id = d.order_id
  GROUP BY o.service_type
  ORDER BY failure_rate_pct DESC")

# ---- S5. Average rating by pickup_zone -------------------------------
# MongoDB equivalent: queries_v2.V2
run("S5. Average delivery rating by pickup_zone (post cleanup)",
"SELECT o.pickup_zone,
        ROUND(AVG(d.customer_rating_post_delivery), 2) AS avg_rating,
        COUNT(*)                                       AS n
   FROM orders     o
   JOIN deliveries d ON o.order_id = d.order_id
  WHERE d.customer_rating_post_delivery IS NOT NULL
  GROUP BY o.pickup_zone
  ORDER BY avg_rating ASC")

# ---- S6. Compound risk: complaint AND failed delivery ----------------
# MongoDB equivalent: queries_v2.V3
# Demonstrates joining 3 tables and aggregating on each order.
run("S6. Top 5 orders with both a complaint and a failed delivery",
"SELECT o.order_id,
        o.service_type,
        o.pickup_zone,
        COUNT(c.complaint_id)              AS complaint_count,
        d.customer_rating_post_delivery    AS rating
   FROM orders     o
   JOIN deliveries d ON o.order_id = d.order_id
   JOIN complaints c ON o.order_id = c.order_id
  WHERE d.delivery_status = 'Failed'
  GROUP BY o.order_id, o.service_type, o.pickup_zone, d.customer_rating_post_delivery
  ORDER BY complaint_count DESC, rating ASC
  LIMIT 5")

# ---- S7. Incidents per delivery, by zone -----------------------------
# MongoDB equivalent: queries_v2.V4
# Demonstrates LEFT JOIN so deliveries without incidents still count.
run("S7. Incidents per delivery, by pickup_zone",
"SELECT o.pickup_zone,
        COUNT(DISTINCT d.delivery_id)               AS deliveries,
        COUNT(i.incident_id)                        AS incidents,
        ROUND(1.0 * COUNT(i.incident_id) /
              COUNT(DISTINCT d.delivery_id), 3)     AS rate
   FROM orders     o
   JOIN deliveries d ON o.order_id    = d.order_id
   LEFT JOIN incidents i ON d.delivery_id = i.delivery_id
  GROUP BY o.pickup_zone
  ORDER BY rate DESC")

# ---- S8. Driver performance ------------------------------------------
# MongoDB equivalent: queries_v2.V5
run("S8. Top 10 drivers by completed deliveries",
"SELECT d.driver_id,
        dr.employment_type,
        dr.base_zone,
        COUNT(*)                                            AS deliveries,
        ROUND(AVG(d.customer_rating_post_delivery), 2)      AS avg_rating
   FROM deliveries d
   JOIN drivers    dr ON d.driver_id = dr.driver_id
  GROUP BY d.driver_id, dr.employment_type, dr.base_zone
  ORDER BY deliveries DESC
  LIMIT 10")

# ---- S9. Window function: top 3 drivers per zone ---------------------
# No direct MongoDB equivalent in queries_v2; the relational paradigm
# expresses this naturally with a window function. Demonstrates the
# extra analytical reach of SQL on this kind of question.
run("S9. Top 3 drivers per base_zone by avg rating (window function)",
"WITH driver_stats AS (
   SELECT dr.base_zone,
          d.driver_id,
          COUNT(*)                                            AS deliveries,
          ROUND(AVG(d.customer_rating_post_delivery), 2)      AS avg_rating,
          RANK() OVER (
            PARTITION BY dr.base_zone
            ORDER BY AVG(d.customer_rating_post_delivery) DESC
          )                                                   AS rank_in_zone
     FROM deliveries d
     JOIN drivers    dr ON d.driver_id = dr.driver_id
    WHERE d.customer_rating_post_delivery IS NOT NULL
    GROUP BY dr.base_zone, d.driver_id
 )
 SELECT base_zone, driver_id, deliveries, avg_rating, rank_in_zone
   FROM driver_stats
  WHERE rank_in_zone <= 3
  ORDER BY base_zone, rank_in_zone")

dbDisconnect(con)
