# Power BI Build Guide – E-Commerce Customer Behavior & Revenue Analytics

> The `.pbix` file itself can't be generated outside Power BI Desktop, so this guide gives you everything
> needed to build it in ~45 minutes. After building, save it as `powerbi/Ecommerce_Analytics_Dashboard.pbix`
> and add screenshots to `images/` (e.g. `dashboard_overview.png`).

## 1. Load the data
**Home → Get Data → Text/CSV**, load:

| Table name in Power BI | File |
|---|---|
| `Transactions` | `data/processed/ecommerce_transactions_clean.csv` |
| `RFM` | `data/processed/rfm_segments.csv` |

Optional: `MonthlyRevenue` (`monthly_revenue.csv`), `CohortRetention` (`cohort_retention.csv`).
(Or connect straight to PostgreSQL: *Get Data → PostgreSQL database* → tables `transactions`, `rfm_segments`.)

In Power Query check types: `order_date` = Date, `revenue`/`unit_price`/`discount_amount` = Fixed decimal, `quantity` = Whole number.

## 2. Date table (Modeling → New table)
```DAX
Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2024, 1, 1 ), DATE ( 2025, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month No", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "Year-Month", FORMAT ( [Date], "YYYY-MM" ),
    "Quarter", "Q" & QUARTER ( [Date] )
)
```
Select `Date[Month]` → *Sort by column* → `Month No`. Mark `Date` as a date table.

## 3. Relationships (Model view)
* `Date[Date]` 1 ──► * `Transactions[order_date]`
* `RFM[customer_id]` 1 ──► * `Transactions[customer_id]`

> Filters flow from `RFM` to `Transactions`, not the reverse. On the RFM/Churn page use slicers built from the
> **RFM** table (`RFM[city]`, `RFM[age_group]`, `RFM[gender]`).

## 4. DAX measures
Create a table `_Measures` (Home → Enter Data, blank) and add these measures.

```DAX
-- Core KPIs ----------------------------------------------------------
Total Revenue =
CALCULATE ( SUM ( Transactions[revenue] ), Transactions[order_status] = "Delivered" )

Total Orders =
CALCULATE ( DISTINCTCOUNT ( Transactions[order_id] ), Transactions[order_status] = "Delivered" )

Total Customers =
CALCULATE ( DISTINCTCOUNT ( Transactions[customer_id] ), Transactions[order_status] = "Delivered" )

Avg Order Value = DIVIDE ( [Total Revenue], [Total Orders] )

Revenue per Customer = DIVIDE ( [Total Revenue], [Total Customers] )

Units Sold =
CALCULATE ( SUM ( Transactions[quantity] ), Transactions[order_status] = "Delivered" )

-- Retention ----------------------------------------------------------
Repeat Customers =
COUNTROWS (
    FILTER (
        VALUES ( Transactions[customer_id] ),
        CALCULATE ( DISTINCTCOUNT ( Transactions[order_id] ), Transactions[order_status] = "Delivered" ) >= 2
    )
)

Repeat Purchase Rate = DIVIDE ( [Repeat Customers], [Total Customers] )

Churned Customers = CALCULATE ( COUNTROWS ( RFM ), RFM[is_churned] = 1 )

Churn Rate = DIVIDE ( [Churned Customers], COUNTROWS ( RFM ) )

Revenue at Risk (Churned) =
CALCULATE ( SUM ( RFM[monetary] ), RFM[is_churned] = 1 )

-- Order health -------------------------------------------------------
Cancellation Rate =
DIVIDE ( CALCULATE ( COUNTROWS ( Transactions ), Transactions[order_status] = "Cancelled" ), COUNTROWS ( Transactions ) )

Return Rate =
DIVIDE ( CALCULATE ( COUNTROWS ( Transactions ), Transactions[order_status] = "Returned" ), COUNTROWS ( Transactions ) )

-- Discounts ----------------------------------------------------------
Avg Discount % = AVERAGE ( Transactions[discount_pct] ) / 100

Discount Given =
CALCULATE ( SUM ( Transactions[discount_amount] ), Transactions[order_status] = "Delivered" )

-- Time intelligence --------------------------------------------------
Revenue LY = CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )

Revenue YoY % = DIVIDE ( [Total Revenue] - [Revenue LY], [Revenue LY] )

Revenue PM = CALCULATE ( [Total Revenue], DATEADD ( 'Date'[Date], -1, MONTH ) )

Revenue MoM % = DIVIDE ( [Total Revenue] - [Revenue PM], [Revenue PM] )

-- Share / ranking ----------------------------------------------------
Category Revenue Share % =
DIVIDE ( [Total Revenue], CALCULATE ( [Total Revenue], ALL ( Transactions[product_category] ) ) )

Segment Revenue Share % =
DIVIDE ( SUM ( RFM[monetary] ), CALCULATE ( SUM ( RFM[monetary] ), ALL ( RFM[segment] ) ) )

Champions Customers = CALCULATE ( COUNTROWS ( RFM ), RFM[segment] = "Champions" )
```

## 5. Dashboard layout (3 pages)

**Page 1 – Executive Overview**
* KPI cards: Total Revenue · Total Orders · Total Customers · AOV · Repeat Purchase Rate · Churn Rate
* Line chart: `Date[Year-Month]` × Total Revenue (with Revenue MoM % in tooltip)
* Clustered column: Revenue by `Date[Quarter]`, split by `Date[Year]`
* Slicers: Year, Quarter, Product category

**Page 2 – Product & Customer Analysis**
* Bar: Revenue by `product_category` (+ Category Revenue Share %)
* Donut: Orders by `payment_method`
* Column: Revenue by `age_group`; filled map / bar: Revenue by `city`
* Column + line: Orders & AOV by discount band (create a calculated column `Discount Band` from `discount_pct`)
* Slicers: City, Gender, Age group

**Page 3 – RFM & Churn**
* Cards: Churn Rate · Revenue at Risk · Champions Customers
* Bar: Customers by `RFM[segment]`; bar: Revenue by `RFM[segment]`
* Matrix: `segment` × (customers, avg recency, avg frequency, revenue, churn rate)
* Scatter: Frequency vs Monetary, coloured by segment
* Slicers from the **RFM** table: City, Age group, Gender, Segment

**Formatting tips**
* Theme: one accent colour (blue) + one highlight (orange); consistent ₹ format (`₹#,0`).
* Add a title and short subtitle on each page; align visuals to a grid; turn on *Sync slicers* across pages.
* Use bookmarks + page navigator buttons for a polished, app-like feel.
