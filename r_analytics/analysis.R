# R analytics on NorthStar. R was new to me when I started this so the
# style is more pipe-heavy than I would write in Python. Charts and
# test outputs land in charts/.
#
# Needs sql_r/load_northstar.R to have run first so northstar.sqlite
# exists.

suppressPackageStartupMessages({
  library(DBI)
  library(RSQLite)
  library(dplyr)
  library(tidyr)
  library(readr)
  library(ggplot2)
  library(scales)
})

set.seed(42)  # for reproducible jitter on the scatter

# look for the sqlite file in the usual spots
candidates <- c(
  "../sql_r/northstar.sqlite",
  "../northstar.sqlite",
  "northstar.sqlite"
)
sqlite_path <- NA_character_
for (p in candidates) {
  if (file.exists(p)) { sqlite_path <- p; break }
}
if (is.na(sqlite_path)) {
  stop("northstar.sqlite not found. Run sql_r/load_northstar.R first.")
}
cat("Connecting to:", normalizePath(sqlite_path), "\n")

con <- dbConnect(RSQLite::SQLite(), sqlite_path)
on.exit(dbDisconnect(con), add = TRUE)

charts_dir <- "charts"
dir.create(charts_dir, showWarnings = FALSE)

save_chart <- function(plot, name, w = 8, h = 5) {
  path <- file.path(charts_dir, paste0(name, ".png"))
  ggsave(path, plot, width = w, height = h, dpi = 150, bg = "white")
  cat("  saved", path, "\n")
}

# ---------------------------------------------------------------------
# 1. Pull tables
# ---------------------------------------------------------------------
orders     <- as_tibble(dbReadTable(con, "orders"))
deliveries <- as_tibble(dbReadTable(con, "deliveries"))
customers  <- as_tibble(dbReadTable(con, "customers"))
drivers    <- as_tibble(dbReadTable(con, "drivers"))
incidents  <- as_tibble(dbReadTable(con, "incidents"))
complaints <- as_tibble(dbReadTable(con, "complaints"))
app_events <- as_tibble(dbReadTable(con, "app_events"))

# ---------------------------------------------------------------------
# 2. Build the analytical data frame.
#
#   The unit of analysis is the order. Customer attributes, the matching
#   delivery and counts of complaints/app events are joined as wide
#   columns. Orders without a delivery are kept (they will be filtered
#   per analysis as needed).
# ---------------------------------------------------------------------
complaint_counts <- complaints |>
  count(order_id, name = "complaint_count")

event_counts <- app_events |>
  filter(!is.na(order_id)) |>
  count(order_id, name = "app_event_count")

incident_counts <- incidents |>
  count(delivery_id, name = "incident_count")

dat <- orders |>
  left_join(deliveries, by = "order_id") |>
  left_join(customers, by = "customer_id", suffix = c("", "_cust")) |>
  left_join(drivers, by = "driver_id", suffix = c("", "_drv")) |>
  left_join(incident_counts, by = "delivery_id") |>
  left_join(complaint_counts, by = "order_id") |>
  left_join(event_counts, by = "order_id") |>
  mutate(
    incident_count   = coalesce(incident_count, 0L),
    complaint_count  = coalesce(complaint_count, 0L),
    app_event_count  = coalesce(app_event_count, 0L),
    has_delivery     = !is.na(delivery_id),
    failed           = delivery_status == "Failed",
    delivered        = !is.na(delivery_status) & delivery_status %in% c("OnTime", "Delayed", "Failed"),
    priority_level   = factor(priority_level, levels = c("Low", "Medium", "High", "Critical")),
    service_type     = factor(service_type),
    pickup_zone      = factor(pickup_zone)
  )

cat("\nAnalytical data frame: ", nrow(dat), " orders, ", ncol(dat), " columns.\n", sep = "")

# ---------------------------------------------------------------------
# 3. Descriptive statistics
# ---------------------------------------------------------------------
cat("\n--- Descriptive statistics ---\n")
cat(sprintf("Orders with a delivery:     %d (%.1f%%)\n",
            sum(dat$has_delivery), 100 * mean(dat$has_delivery)))
cat(sprintf("Failed deliveries:           %d (%.1f%% of delivered)\n",
            sum(dat$failed, na.rm = TRUE),
            100 * mean(dat$failed[dat$delivered], na.rm = TRUE)))
cat(sprintf("Orders with at least 1 complaint: %d (%.1f%%)\n",
            sum(dat$complaint_count > 0),
            100 * mean(dat$complaint_count > 0)))

cat("\nMean order_value by service_type:\n")
print(dat |>
        group_by(service_type) |>
        summarise(
          n = n(),
          mean_value = round(mean(order_value, na.rm = TRUE), 2),
          median_value = round(median(order_value, na.rm = TRUE), 2)
        ),
      n = 5)

# ---------------------------------------------------------------------
# 4. Visualisations
# ---------------------------------------------------------------------
cat("\n--- Saving charts to charts/ ---\n")

# Chart 1: Revenue by service_type bar chart with order count overlay
p1_data <- dat |>
  group_by(service_type) |>
  summarise(
    revenue = sum(order_value, na.rm = TRUE),
    orders = n()
  ) |>
  arrange(desc(revenue))

p1 <- ggplot(p1_data, aes(x = reorder(service_type, -revenue), y = revenue)) +
  geom_col(fill = "#1f77b4") +
  geom_text(aes(label = paste0(orders, " orders")),
            vjust = -0.4, size = 3.5) +
  scale_y_continuous(labels = label_comma(prefix = "GBP ")) +
  labs(
    title = "Revenue by service line",
    subtitle = "Total order value summed within each service type",
    x = "Service type", y = "Total revenue"
  ) +
  theme_minimal(base_size = 12)
save_chart(p1, "01_revenue_by_service")

# Chart 2: Customer rating distribution faceted by service_type
p2 <- dat |>
  filter(!is.na(customer_rating_post_delivery)) |>
  ggplot(aes(x = customer_rating_post_delivery, fill = service_type)) +
  geom_histogram(binwidth = 0.5, colour = "white", alpha = 0.85) +
  facet_wrap(~ service_type, ncol = 3) +
  labs(
    title = "Distribution of customer ratings, by service line",
    subtitle = "Half star bins, post delivery ratings only",
    x = "Customer rating", y = "Number of deliveries"
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "none")
save_chart(p2, "02_rating_distribution", w = 9, h = 5)

# Chart 3: Failure rate heatmap zone x service_type
p3_data <- dat |>
  filter(delivered) |>
  group_by(pickup_zone, service_type) |>
  summarise(
    failed = sum(failed, na.rm = TRUE),
    n = n(),
    failure_rate = failed / n,
    .groups = "drop"
  )

p3 <- ggplot(p3_data, aes(x = service_type, y = pickup_zone, fill = failure_rate)) +
  geom_tile(colour = "white") +
  geom_text(aes(label = sprintf("%.0f%%", 100 * failure_rate)),
            colour = "white", size = 3.4) +
  scale_fill_gradient(low = "#cce4f7", high = "#b22234",
                      labels = label_percent(),
                      name = "Failure rate") +
  labs(
    title = "Delivery failure rate, pickup zone by service line",
    x = "Service type", y = "Pickup zone"
  ) +
  theme_minimal(base_size = 12)
save_chart(p3, "03_failure_heatmap", w = 8, h = 5)

# Chart 4: Route distance vs rating with delivery_status colour and smoother
p4 <- dat |>
  filter(!is.na(route_distance_km), !is.na(customer_rating_post_delivery)) |>
  ggplot(aes(x = route_distance_km, y = customer_rating_post_delivery,
             colour = delivery_status)) +
  geom_point(alpha = 0.5, size = 1.2) +
  geom_smooth(method = "loess", se = FALSE) +
  scale_colour_manual(values = c(OnTime = "#2ca02c", Delayed = "#ff7f0e", Failed = "#d62728")) +
  labs(
    title = "Customer rating versus route distance",
    subtitle = "Loess smoother per delivery outcome",
    x = "Route distance (km)", y = "Customer rating",
    colour = "Outcome"
  ) +
  theme_minimal(base_size = 12)
save_chart(p4, "04_distance_vs_rating", w = 9, h = 5)

# Chart 5: Boxplot of rating by pickup_zone, ordered by median
zone_order <- dat |>
  filter(!is.na(customer_rating_post_delivery)) |>
  group_by(pickup_zone) |>
  summarise(med = median(customer_rating_post_delivery)) |>
  arrange(med) |>
  pull(pickup_zone) |>
  as.character()

p5 <- dat |>
  filter(!is.na(customer_rating_post_delivery)) |>
  mutate(pickup_zone = factor(pickup_zone, levels = zone_order)) |>
  ggplot(aes(x = pickup_zone, y = customer_rating_post_delivery, fill = pickup_zone)) +
  geom_boxplot(alpha = 0.85, outlier.alpha = 0.35) +
  labs(
    title = "Customer rating by pickup zone",
    subtitle = "Zones ordered by median rating, ascending",
    x = "Pickup zone", y = "Customer rating"
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "none")
save_chart(p5, "05_rating_by_zone", w = 9, h = 5)

# ---------------------------------------------------------------------
# 5. Statistical tests
# ---------------------------------------------------------------------
cat("\n--- Statistical tests ---\n")

# T1. Chi square: is delivery outcome independent of pickup_zone?
tab_zone <- with(filter(dat, delivered), table(pickup_zone, delivery_status))
chi_zone <- chisq.test(tab_zone)
cat("\nT1. Chi square: pickup_zone vs delivery_status\n")
print(tab_zone)
cat(sprintf("  X^2 = %.2f, df = %d, p = %.4g\n",
            chi_zone$statistic, chi_zone$parameter, chi_zone$p.value))

# T2. Chi square: is delivery outcome independent of service_type?
tab_svc <- with(filter(dat, delivered), table(service_type, delivery_status))
chi_svc <- chisq.test(tab_svc)
cat("\nT2. Chi square: service_type vs delivery_status\n")
print(tab_svc)
cat(sprintf("  X^2 = %.2f, df = %d, p = %.4g\n",
            chi_svc$statistic, chi_svc$parameter, chi_svc$p.value))

# T3. Welch t-test: route_distance for failed vs non failed deliveries
fd <- dat |> filter(delivered) |> mutate(failed = delivery_status == "Failed")
t_dist <- t.test(route_distance_km ~ failed, data = fd, var.equal = FALSE)
cat("\nT3. Welch t-test: route_distance_km (Failed vs not Failed)\n")
cat(sprintf("  mean Failed = %.2f km, mean other = %.2f km\n",
            mean(fd$route_distance_km[fd$failed], na.rm = TRUE),
            mean(fd$route_distance_km[!fd$failed], na.rm = TRUE)))
cat(sprintf("  t = %.2f, df = %.1f, p = %.4g\n",
            t_dist$statistic, t_dist$parameter, t_dist$p.value))

# T4. Pearson correlation: app_engagement_score vs customer_rating
cor_data <- dat |>
  filter(!is.na(app_engagement_score), !is.na(customer_rating_post_delivery))
cor_test <- cor.test(cor_data$app_engagement_score,
                     cor_data$customer_rating_post_delivery)
cat("\nT4. Pearson correlation: app_engagement_score vs customer_rating\n")
cat(sprintf("  n = %d, r = %.3f, p = %.4g\n",
            nrow(cor_data), cor_test$estimate, cor_test$p.value))

# ---------------------------------------------------------------------
# 6. Logistic regression: P(Failed) ~ features
# ---------------------------------------------------------------------
cat("\n--- Logistic regression for delivery failure ---\n")
mdl_data <- dat |>
  filter(delivered) |>
  mutate(failed = as.integer(delivery_status == "Failed")) |>
  select(failed, service_type, pickup_zone, route_distance_km,
         loyalty_score, app_engagement_score, priority_level) |>
  drop_na()

cat(sprintf("n used in model: %d\n", nrow(mdl_data)))

fit <- glm(failed ~ service_type + pickup_zone + route_distance_km +
                    loyalty_score + app_engagement_score + priority_level,
           data = mdl_data, family = binomial)
print(summary(fit))

# Convert log odds to odds ratios for the report.
or <- exp(coef(fit))
or_ci <- exp(confint.default(fit))
or_table <- data.frame(
  term = names(or),
  odds_ratio = round(or, 3),
  ci_low = round(or_ci[, 1], 3),
  ci_high = round(or_ci[, 2], 3),
  row.names = NULL
)
cat("\nOdds ratios with 95% confidence intervals\n")
print(or_table)

# Save the model summary so the report can reference it verbatim.
saveRDS(fit, file.path(charts_dir, "logistic_model.rds"))
write_csv(or_table, file.path(charts_dir, "odds_ratios.csv"))
cat("\nModel artefacts saved to charts/logistic_model.rds and charts/odds_ratios.csv\n")

cat("\nDone.\n")
