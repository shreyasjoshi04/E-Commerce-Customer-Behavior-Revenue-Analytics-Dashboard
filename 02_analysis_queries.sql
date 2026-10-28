-- =====================================================================
-- 02_analysis_queries.sql  |  Business questions answered with SQL (PostgreSQL)
-- Techniques: filtering, aggregation, CASE, subqueries, CTEs, window functions
-- "Realised revenue" = revenue of Delivered orders (order_status = 'Delivered')
-- =====================================================================


-- Q1. Headline KPIs ----------------------------------------------------
SELECT
    COUNT(DISTINCT order_id)                                             AS total_orders,
    COUNT(DISTINCT customer_id)                                          AS total_customers,
    ROUND(SUM(realised_revenue), 2)                                      AS realised_revenue,
    ROUND(SUM(realised_revenue) / NULLIF(SUM(is_realised), 0), 2)        AS avg_order_value,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 2) AS cancellation_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Returned'  THEN 1 ELSE 0 END) / COUNT(*), 2) AS return_rate_pct
FROM transactions;


-- Q2. Monthly revenue with month-over-month growth (window function) ---
WITH monthly AS (
    SELECT year_month,
           SUM(realised_revenue)            AS revenue,
           SUM(is_realised)                 AS delivered_orders
    FROM transactions
    GROUP BY year_month
)
SELECT year_month,
       ROUND(revenue, 2) AS revenue,
       delivered_orders,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY year_month))
             / NULLIF(LAG(revenue) OVER (ORDER BY year_month), 0), 2) AS mom_growth_pct
FROM monthly
ORDER BY year_month;


-- Q3. Category performance & revenue share -----------------------------
SELECT product_category,
       ROUND(SUM(realised_revenue), 2)                                         AS revenue,
       SUM(CASE WHEN is_realised = 1 THEN quantity ELSE 0 END)                 AS units_sold,
       ROUND(100.0 * SUM(realised_revenue) / SUM(SUM(realised_revenue)) OVER (), 2) AS revenue_share_pct,
       RANK() OVER (ORDER BY SUM(realised_revenue) DESC)                       AS revenue_rank
FROM transactions
GROUP BY product_category
ORDER BY revenue DESC;


-- Q4. Payment method preference ----------------------------------------
SELECT payment_method,
       SUM(is_realised)                                           AS delivered_orders,
       ROUND(100.0 * SUM(is_realised) / SUM(SUM(is_realised)) OVER (), 2) AS order_share_pct,
       ROUND(SUM(realised_revenue) / NULLIF(SUM(is_realised), 0), 2)      AS avg_order_value
FROM transactions
GROUP BY payment_method
ORDER BY delivered_orders DESC;


-- Q5. Top 10 customers by lifetime value (CTE + RANK) ------------------
WITH customer_value AS (
    SELECT customer_id,
           city,
           SUM(is_realised)           AS delivered_orders,
           SUM(realised_revenue)      AS lifetime_value
    FROM transactions
    GROUP BY customer_id, city
)
SELECT RANK() OVER (ORDER BY lifetime_value DESC) AS rnk,
       customer_id, city, delivered_orders, ROUND(lifetime_value, 2) AS lifetime_value
FROM customer_value
ORDER BY lifetime_value DESC
LIMIT 10;


-- Q6. Repeat purchase rate (subquery) ----------------------------------
SELECT ROUND(100.0 * SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_purchase_rate_pct,
       COUNT(*)                                                                    AS buying_customers
FROM (
    SELECT customer_id, SUM(is_realised) AS orders
    FROM transactions
    GROUP BY customer_id
    HAVING SUM(is_realised) >= 1
) AS t;


-- Q7. Purchase-frequency distribution (CASE) ---------------------------
WITH freq AS (
    SELECT customer_id, SUM(is_realised) AS orders
    FROM transactions
    GROUP BY customer_id
    HAVING SUM(is_realised) >= 1
)
SELECT CASE WHEN orders = 1 THEN '1 order'
            WHEN orders = 2 THEN '2 orders'
            WHEN orders BETWEEN 3 AND 4 THEN '3-4 orders'
            ELSE '5+ orders' END AS frequency_bucket,
       COUNT(*)                                 AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_share_pct
FROM freq
GROUP BY 1
ORDER BY MIN(orders);


-- Q8. Discount impact on order value -----------------------------------
SELECT CASE WHEN discount_pct = 0   THEN '1. No discount'
            WHEN discount_pct <= 10 THEN '2. 1-10%'
            WHEN discount_pct <= 20 THEN '3. 11-20%'
            ELSE                         '4. 21-30%' END AS discount_band,
       SUM(is_realised)                                       AS delivered_orders,
       ROUND(SUM(realised_revenue) / NULLIF(SUM(is_realised), 0), 2) AS avg_order_value,
       ROUND(SUM(CASE WHEN is_realised = 1 THEN discount_amount ELSE 0 END), 2) AS discount_given
FROM transactions
GROUP BY 1
ORDER BY 1;


-- Q9. Seasonality: revenue by quarter and festive-season share ----------
SELECT order_quarter,
       ROUND(SUM(realised_revenue), 2) AS revenue,
       ROUND(100.0 * SUM(realised_revenue) / SUM(SUM(realised_revenue)) OVER (), 2) AS share_pct
FROM transactions
GROUP BY order_quarter
ORDER BY order_quarter;

SELECT ROUND(100.0 * SUM(CASE WHEN order_month IN (10, 11, 12) THEN realised_revenue ELSE 0 END)
             / SUM(realised_revenue), 2) AS oct_dec_revenue_share_pct
FROM transactions;


-- Q10. RFM segmentation in pure SQL (NTILE) ----------------------------
WITH snapshot AS (
    SELECT MAX(order_date) + 1 AS snapshot_date FROM transactions
),
base AS (
    SELECT customer_id,
           MAX(order_date)       AS last_order_date,
           SUM(is_realised)      AS frequency,
           SUM(realised_revenue) AS monetary
    FROM transactions
    WHERE order_status = 'Delivered'
    GROUP BY customer_id
),
rfm AS (
    SELECT b.customer_id, b.frequency, b.monetary,
           (s.snapshot_date - b.last_order_date) AS recency_days
    FROM base b CROSS JOIN snapshot s
),
scored AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY recency_days DESC)         AS r_score,   -- fewer days = higher score
           NTILE(5) OVER (ORDER BY frequency, monetary)       AS f_score,
           NTILE(5) OVER (ORDER BY monetary)                  AS m_score
    FROM rfm
)
SELECT customer_id, recency_days, frequency, ROUND(monetary, 2) AS monetary,
       r_score, f_score, m_score,
       CASE WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'New / Promising'
            WHEN r_score = 3  AND f_score <= 2 THEN 'Needs Attention'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score = 2                   THEN 'Hibernating'
            ELSE 'Lost' END AS segment
FROM scored
ORDER BY monetary DESC
LIMIT 50;


-- Q11. Churned customers: no delivered order in the last 90 days -------
WITH snapshot AS (SELECT MAX(order_date) + 1 AS snapshot_date FROM transactions),
last_purchase AS (
    SELECT customer_id, MAX(order_date) AS last_order_date, SUM(realised_revenue) AS lifetime_value
    FROM transactions
    WHERE order_status = 'Delivered'
    GROUP BY customer_id
)
SELECT COUNT(*) AS customers,
       SUM(CASE WHEN (s.snapshot_date - l.last_order_date) > 90 THEN 1 ELSE 0 END) AS churned_customers,
       ROUND(100.0 * SUM(CASE WHEN (s.snapshot_date - l.last_order_date) > 90 THEN 1 ELSE 0 END) / COUNT(*), 2) AS churn_rate_pct,
       ROUND(SUM(CASE WHEN (s.snapshot_date - l.last_order_date) > 90 THEN l.lifetime_value ELSE 0 END), 2) AS revenue_at_churned_customers
FROM last_purchase l CROSS JOIN snapshot s;


-- Q12. Monthly cohort retention (CTEs) ---------------------------------
WITH delivered AS (
    SELECT customer_id, year_month,
           CAST(SUBSTR(year_month, 1, 4) AS INT) * 12 + CAST(SUBSTR(year_month, 6, 2) AS INT) AS month_num
    FROM transactions
    WHERE order_status = 'Delivered'
),
cohorts AS (
    SELECT customer_id, MIN(month_num) AS cohort_month_num, MIN(year_month) AS cohort
    FROM delivered
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT d.customer_id, c.cohort, d.month_num - c.cohort_month_num AS month_index
    FROM delivered d JOIN cohorts c USING (customer_id)
)
SELECT cohort,
       COUNT(DISTINCT CASE WHEN month_index = 0 THEN customer_id END) AS cohort_size,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN month_index = 1 THEN customer_id END)
             / NULLIF(COUNT(DISTINCT CASE WHEN month_index = 0 THEN customer_id END), 0), 2) AS retained_m1_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN month_index = 3 THEN customer_id END)
             / NULLIF(COUNT(DISTINCT CASE WHEN month_index = 0 THEN customer_id END), 0), 2) AS retained_m3_pct
FROM activity
GROUP BY cohort
ORDER BY cohort;


-- Q13. High-value customers: spend above overall average (subquery) ---
SELECT customer_id, ROUND(SUM(realised_revenue), 2) AS total_spend
FROM transactions
GROUP BY customer_id
HAVING SUM(realised_revenue) > (
    SELECT AVG(customer_total) FROM (
        SELECT SUM(realised_revenue) AS customer_total FROM transactions GROUP BY customer_id
    ) AS x
)
ORDER BY total_spend DESC
LIMIT 20;


-- Q14. Best-selling category in each city (ROW_NUMBER) -----------------
WITH city_cat AS (
    SELECT city, product_category, SUM(realised_revenue) AS revenue,
           ROW_NUMBER() OVER (PARTITION BY city ORDER BY SUM(realised_revenue) DESC) AS rn
    FROM transactions
    GROUP BY city, product_category
)
SELECT city, product_category AS top_category, ROUND(revenue, 2) AS revenue
FROM city_cat
WHERE rn = 1
ORDER BY revenue DESC;


-- Q15. Cancellation & return rate by category --------------------------
SELECT product_category,
       COUNT(*) AS orders,
       ROUND(100.0 * SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 2) AS cancel_rate_pct,
       ROUND(100.0 * SUM(CASE WHEN order_status = 'Returned'  THEN 1 ELSE 0 END) / COUNT(*), 2) AS return_rate_pct
FROM transactions
GROUP BY product_category
ORDER BY return_rate_pct DESC;


-- Q16. RFM segment summary (uses the rfm_segments table) ---------------
SELECT segment,
       COUNT(*)                                   AS customers,
       ROUND(SUM(monetary), 2)                    AS revenue,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 2) AS revenue_share_pct,
       ROUND(100.0 * SUM(is_churned) / COUNT(*), 2) AS churn_rate_pct
FROM rfm_segments
GROUP BY segment
ORDER BY revenue DESC;
