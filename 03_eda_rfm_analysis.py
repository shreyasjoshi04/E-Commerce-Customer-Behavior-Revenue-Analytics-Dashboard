# %% [markdown]
# # E-Commerce Customer Behavior & Revenue Analytics
# EDA, KPI analysis, RFM segmentation and churn analysis on the cleaned transactions.
#
# **Input:** `data/processed/ecommerce_transactions_clean.csv`
# **Outputs:** summary tables in `data/processed/` (used by Power BI) and charts in `images/`

# %%
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                     # safe for running as a script; notebooks override below
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:                                      # inside Jupyter: show charts inline
    get_ipython().run_line_magic("matplotlib", "inline")   # noqa: F821
except NameError:
    pass

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:                         # notebook: cwd is notebooks/
    ROOT = Path.cwd().parent
PROC, IMG = ROOT / "data" / "processed", ROOT / "images"
IMG.mkdir(exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "font.size": 10})
PALETTE = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2"]
inr = lambda x: f"₹{x/1e6:.1f}M" if abs(x) >= 1e6 else f"₹{x/1e3:.0f}K"

df = pd.read_csv(PROC / "ecommerce_transactions_clean.csv", parse_dates=["order_date"])
delivered = df[df["order_status"] == "Delivered"].copy()
print(df.shape, delivered.shape)
df.head()

# %% [markdown]
# ## 1. Headline KPIs
# Realised revenue = net order value (after discount) of **Delivered** orders only.

# %%
snapshot = df["order_date"].max() + pd.Timedelta(days=1)
cust_orders = delivered.groupby("customer_id")["order_id"].nunique()

kpis = {
    "Total Orders": df["order_id"].nunique(),
    "Delivered Orders": delivered["order_id"].nunique(),
    "Total Customers": df["customer_id"].nunique(),
    "Realised Revenue (INR)": round(delivered["revenue"].sum(), 2),
    "Average Order Value (INR)": round(delivered["revenue"].mean(), 2),
    "Revenue per Customer (INR)": round(delivered["revenue"].sum() / delivered["customer_id"].nunique(), 2),
    "Repeat Purchase Rate (%)": round((cust_orders >= 2).mean() * 100, 2),
    "Cancellation Rate (%)": round((df["order_status"] == "Cancelled").mean() * 100, 2),
    "Return Rate (%)": round((df["order_status"] == "Returned").mean() * 100, 2),
    "Avg Discount (%)": round(df["discount_pct"].mean(), 2),
}
kpi_df = pd.DataFrame(kpis.items(), columns=["kpi", "value"])
kpi_df.to_csv(PROC / "kpi_summary.csv", index=False)
kpi_df

# %% [markdown]
# ## 2. Revenue trend & seasonality

# %%
monthly = (delivered.groupby("year_month")
           .agg(revenue=("revenue", "sum"), orders=("order_id", "nunique"),
                customers=("customer_id", "nunique"), aov=("revenue", "mean"))
           .reset_index())
monthly["mom_growth_pct"] = (monthly["revenue"].pct_change() * 100).round(2)
monthly.to_csv(PROC / "monthly_revenue.csv", index=False)

fig, ax = plt.subplots(figsize=(10, 4.2))
ax.plot(monthly["year_month"], monthly["revenue"], marker="o", color=PALETTE[0], lw=2)
ax.fill_between(range(len(monthly)), monthly["revenue"], alpha=0.1, color=PALETTE[0])
ax.set_xticks(range(len(monthly)))
ax.set_xticklabels(monthly["year_month"], rotation=60, ha="right")
ax.set_title("Monthly Realised Revenue (festive peak in Oct–Nov)", fontweight="bold", loc="left")
ax.yaxis.set_major_formatter(lambda v, _: inr(v))
plt.tight_layout(); plt.savefig(IMG / "01_monthly_revenue.png"); plt.show()

# seasonality: average revenue by calendar month across both years
season = delivered.groupby("order_month")["revenue"].sum()
print("Peak month:", season.idxmax(), "| Share of revenue in Oct–Dec:",
      f"{season.loc[[10, 11, 12]].sum() / season.sum():.1%}")

# %% [markdown]
# ## 3. Product, payment, geography and demographics

# %%
cat = (delivered.groupby("product_category")
       .agg(revenue=("revenue", "sum"), orders=("order_id", "nunique"), units=("quantity", "sum"),
            avg_discount=("discount_pct", "mean")).sort_values("revenue", ascending=False).reset_index())
cat["revenue_share_pct"] = (cat["revenue"] / cat["revenue"].sum() * 100).round(2)
cat.to_csv(PROC / "category_performance.csv", index=False)

pay = (delivered.groupby("payment_method")
       .agg(orders=("order_id", "nunique"), revenue=("revenue", "sum"), aov=("revenue", "mean"))
       .sort_values("orders", ascending=False).reset_index())
city = (delivered.groupby("city").agg(revenue=("revenue", "sum"), customers=("customer_id", "nunique"))
        .sort_values("revenue", ascending=False).reset_index())
age = delivered.groupby("age_group").agg(revenue=("revenue", "sum"), customers=("customer_id", "nunique")).reset_index()

fig, axes = plt.subplots(2, 2, figsize=(12, 8))
axes[0, 0].barh(cat["product_category"][::-1], cat["revenue"][::-1], color=PALETTE[0])
axes[0, 0].set_title("Revenue by Category", fontweight="bold", loc="left")
axes[0, 0].xaxis.set_major_formatter(lambda v, _: inr(v))
axes[0, 1].bar(pay["payment_method"], pay["orders"], color=PALETTE[1])
axes[0, 1].set_title("Orders by Payment Method", fontweight="bold", loc="left")
axes[0, 1].tick_params(axis="x", rotation=30)
axes[1, 0].bar(city["city"], city["revenue"], color=PALETTE[2])
axes[1, 0].set_title("Revenue by City", fontweight="bold", loc="left")
axes[1, 0].tick_params(axis="x", rotation=45); axes[1, 0].yaxis.set_major_formatter(lambda v, _: inr(v))
axes[1, 1].bar(age["age_group"], age["revenue"], color=PALETTE[4])
axes[1, 1].set_title("Revenue by Age Group", fontweight="bold", loc="left")
axes[1, 1].yaxis.set_major_formatter(lambda v, _: inr(v))
plt.tight_layout(); plt.savefig(IMG / "02_category_payment_city_age.png"); plt.show()
cat

# %% [markdown]
# ## 4. Discount impact

# %%
delivered["discount_band"] = pd.cut(delivered["discount_pct"], bins=[-1, 0, 10, 20, 30],
                                    labels=["No discount", "1–10%", "11–20%", "21–30%"])
disc = (delivered.groupby("discount_band", observed=True)
        .agg(orders=("order_id", "nunique"), avg_order_value=("revenue", "mean"),
             revenue=("revenue", "sum"), discount_given=("discount_amount", "sum")).reset_index())
disc.to_csv(PROC / "discount_analysis.csv", index=False)

fig, ax1 = plt.subplots(figsize=(8, 4))
ax1.bar(disc["discount_band"].astype(str), disc["orders"], color=PALETTE[5], alpha=0.85)
ax1.set_ylabel("Orders")
ax2 = ax1.twinx(); ax2.plot(disc["discount_band"].astype(str), disc["avg_order_value"], color=PALETTE[3], marker="o")
ax2.set_ylabel("Avg order value (₹)"); ax2.grid(False)
ax1.set_title("Orders & AOV by Discount Band", fontweight="bold", loc="left")
plt.tight_layout(); plt.savefig(IMG / "03_discount_impact.png"); plt.show()
disc

# %% [markdown]
# ## 5. RFM segmentation
# * **Recency** – days since last delivered order (lower is better)
# * **Frequency** – number of delivered orders
# * **Monetary** – total realised revenue
#
# Each metric is scored 1–5 using quintiles; customers are then mapped to named segments.

# %%
rfm = (delivered.groupby("customer_id")
       .agg(last_order=("order_date", "max"), frequency=("order_id", "nunique"), monetary=("revenue", "sum"))
       .reset_index())
rfm["recency"] = (snapshot - rfm["last_order"]).dt.days

rfm["R"] = pd.qcut(rfm["recency"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
# Frequency has many ties (most customers order once/twice) -> break ties by spend so quintiles are meaningful
rfm["F"] = pd.qcut((rfm["frequency"] + rfm["monetary"] / (rfm["monetary"].max() * 2)).rank(method="first"),
                   5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["rfm_score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)


def segment(r):
    R, F = r["R"], r["F"]
    if R >= 4 and F >= 4: return "Champions"
    if R >= 3 and F >= 3: return "Loyal Customers"
    if R >= 4 and F <= 2: return "New / Promising"
    if R == 3 and F <= 2: return "Needs Attention"
    if R <= 2 and F >= 3: return "At Risk"
    if R == 2:            return "Hibernating"
    return "Lost"


rfm["segment"] = rfm.apply(segment, axis=1)
rfm["is_churned"] = (rfm["recency"] > 90).astype(int)      # no purchase in last 90 days
rfm["monetary"] = rfm["monetary"].round(2)

# attach customer attributes for Power BI slicers
attrs = df.sort_values("order_date").groupby("customer_id").last()[["gender", "age", "age_group", "city"]].reset_index()
rfm = rfm.merge(attrs, on="customer_id", how="left")
rfm.to_csv(PROC / "rfm_segments.csv", index=False, date_format="%Y-%m-%d")

seg = (rfm.groupby("segment")
       .agg(customers=("customer_id", "count"), avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"), revenue=("monetary", "sum"), churn_rate=("is_churned", "mean"))
       .sort_values("revenue", ascending=False).reset_index())
seg["customer_share_pct"] = (seg["customers"] / seg["customers"].sum() * 100).round(1)
seg["revenue_share_pct"] = (seg["revenue"] / seg["revenue"].sum() * 100).round(1)
seg[["avg_recency", "avg_frequency", "churn_rate"]] = seg[["avg_recency", "avg_frequency", "churn_rate"]].round(2)
seg.to_csv(PROC / "rfm_segment_summary.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].barh(seg["segment"][::-1], seg["customers"][::-1], color=PALETTE[0])
axes[0].set_title("Customers per RFM Segment", fontweight="bold", loc="left")
axes[1].barh(seg["segment"][::-1], seg["revenue"][::-1], color=PALETTE[1])
axes[1].set_title("Revenue per RFM Segment", fontweight="bold", loc="left")
axes[1].xaxis.set_major_formatter(lambda v, _: inr(v))
plt.tight_layout(); plt.savefig(IMG / "04_rfm_segments.png"); plt.show()
seg

# %% [markdown]
# ## 6. Churn & retention

# %%
churn_rate = rfm["is_churned"].mean() * 100
top20 = rfm.sort_values("monetary", ascending=False).head(int(len(rfm) * 0.2))
pareto = top20["monetary"].sum() / rfm["monetary"].sum() * 100

# cohort retention: % of customers (by first-order month) who purchase again in following months
first = delivered.groupby("customer_id")["order_date"].min().dt.to_period("M").rename("cohort")
tmp = delivered.merge(first, on="customer_id")
tmp["period"] = tmp["order_date"].dt.to_period("M")
tmp["month_index"] = (tmp["period"] - tmp["cohort"]).apply(lambda x: x.n)
cohort = tmp.groupby(["cohort", "month_index"])["customer_id"].nunique().unstack(fill_value=0)
retention = cohort.div(cohort[0], axis=0).round(3)
retention.to_csv(PROC / "cohort_retention.csv")

fig, ax = plt.subplots(figsize=(10, 5.5))
im = ax.imshow(retention.iloc[:, :13].values, cmap="Blues", vmin=0, vmax=0.4, aspect="auto")
ax.set_xticks(range(13)); ax.set_yticks(range(len(retention)))
ax.set_yticklabels([str(i) for i in retention.index], fontsize=7)
ax.set_xlabel("Months since first purchase"); ax.set_title("Cohort Retention", fontweight="bold", loc="left")
ax.grid(False); plt.colorbar(im, ax=ax, label="Retention rate")
plt.tight_layout(); plt.savefig(IMG / "05_cohort_retention.png"); plt.show()

print(f"Churn rate (no purchase in 90 days): {churn_rate:.1f}%")
print(f"Top 20% customers contribute {pareto:.1f}% of revenue")

# %% [markdown]
# ## 7. Key insights (auto-generated from the data)

# %%
top_cat = cat.iloc[0]
champ = seg[seg["segment"] == "Champions"].iloc[0]
q4_share = season.loc[[10, 11, 12]].sum() / season.sum() * 100
insights = [
    f"{top_cat['product_category']} is the top category with {top_cat['revenue_share_pct']:.1f}% of realised revenue.",
    f"Oct–Dec generate {q4_share:.1f}% of annual revenue -> plan inventory and campaigns for the festive season.",
    f"Champions are {champ['customer_share_pct']:.1f}% of customers but {champ['revenue_share_pct']:.1f}% of revenue.",
    f"Repeat purchase rate is {kpis['Repeat Purchase Rate (%)']:.1f}%; churn (90-day inactivity) is {churn_rate:.1f}%.",
    f"The top 20% of customers contribute {pareto:.1f}% of revenue (Pareto effect).",
    f"UPI is the most used payment method ({pay.iloc[0]['orders'] / pay['orders'].sum() * 100:.1f}% of delivered orders).",
]
(ROOT / "data" / "processed" / "key_insights.txt").write_text("\n".join(f"- {i}" for i in insights), encoding="utf-8")
for i in insights:
    print("•", i)
