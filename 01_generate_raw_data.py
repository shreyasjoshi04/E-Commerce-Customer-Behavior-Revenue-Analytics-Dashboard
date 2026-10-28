"""
01_generate_raw_data.py
-----------------------
Generates a synthetic, intentionally messy e-commerce transaction dataset
(~12,000 rows) for an Indian online retailer.

The raw file contains realistic data-quality problems so the cleaning step
(02_data_cleaning.py) has real work to do:
  * duplicate rows
  * inconsistent text casing / extra whitespace
  * mixed date formats
  * missing values (age, payment method, city)
  * a few invalid values (negative / zero quantity)

Run:  python scripts/01_generate_raw_data.py
Out:  data/raw/ecommerce_transactions_raw.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_CUSTOMERS = 20000
TARGET_ORDERS = 11800          # before injecting duplicates (final raw rows ~12,000)
START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------- catalogue
CATALOGUE = {
    "Electronics": [("Wireless Earbuds", 1999), ("Smartwatch", 4499), ("Bluetooth Speaker", 2499),
                    ("Power Bank", 1299), ("Smartphone Case", 399), ("Laptop Stand", 1599)],
    "Fashion":     [("Men's T-Shirt", 699), ("Women's Kurti", 1099), ("Running Shoes", 2999),
                    ("Denim Jeans", 1799), ("Sunglasses", 999), ("Handbag", 2199)],
    "Home & Kitchen": [("Air Fryer", 5499), ("Mixer Grinder", 3299), ("Bedsheet Set", 1499),
                       ("Cookware Set", 2799), ("Table Lamp", 899), ("Storage Boxes", 599)],
    "Beauty & Personal Care": [("Face Serum", 899), ("Hair Dryer", 1599), ("Perfume", 1999),
                               ("Skincare Combo", 1299), ("Trimmer", 1399), ("Sunscreen", 449)],
    "Books & Stationery": [("Novel", 349), ("Notebook Pack", 299), ("Fountain Pen", 599),
                           ("Study Planner", 399), ("Art Supplies Kit", 799), ("Business Book", 499)],
    "Sports & Fitness": [("Yoga Mat", 899), ("Dumbbell Set", 2499), ("Resistance Bands", 599),
                         ("Cricket Bat", 1999), ("Football", 799), ("Protein Shaker", 399)],
}
CATEGORY_WEIGHTS = np.array([0.24, 0.22, 0.16, 0.14, 0.10, 0.14])

CITIES = ["Pune", "Mumbai", "Bengaluru", "Delhi", "Hyderabad", "Chennai",
          "Kolkata", "Ahmedabad", "Jaipur", "Nagpur"]
CITY_WEIGHTS = np.array([0.18, 0.17, 0.15, 0.14, 0.10, 0.08, 0.06, 0.05, 0.04, 0.03])

PAYMENTS = ["UPI", "Credit Card", "Debit Card", "Cash on Delivery", "Net Banking", "Wallet"]
PAY_WEIGHTS = np.array([0.38, 0.20, 0.14, 0.17, 0.06, 0.05])

# Monthly seasonality (festive Oct-Nov, year-end Dec, Jan sale, mid-year dip)
SEASON = {1: 1.10, 2: 0.90, 3: 0.95, 4: 0.90, 5: 0.92, 6: 0.88,
          7: 0.95, 8: 1.00, 9: 1.05, 10: 1.45, 11: 1.35, 12: 1.20}

# --------------------------------------------------------------- customers
customers = pd.DataFrame({
    "customer_id": [f"CUST{str(i).zfill(5)}" for i in range(1, N_CUSTOMERS + 1)],
    "gender": rng.choice(["Male", "Female"], N_CUSTOMERS, p=[0.52, 0.48]),
    "age": np.clip(rng.normal(32, 9, N_CUSTOMERS).round(), 18, 65).astype(int),
    "city": rng.choice(CITIES, N_CUSTOMERS, p=CITY_WEIGHTS / CITY_WEIGHTS.sum()),
})
# sign-up dates spread across the window (some customers join late -> "new" customers)
span_days = (END - START).days
customers["signup_date"] = START + pd.to_timedelta(
    (rng.beta(1.0, 1.6, N_CUSTOMERS) * span_days * 0.95).astype(int), unit="D")

# heterogeneous purchase propensity (heavy-tailed: few power users, many one-timers)
propensity = rng.gamma(shape=1.2, scale=1.0, size=N_CUSTOMERS)
customers["propensity"] = propensity / propensity.sum()

# ------------------------------------------------------------------ orders
cust_idx = rng.choice(N_CUSTOMERS, size=TARGET_ORDERS, p=customers["propensity"].values)
rows = []
all_days = pd.date_range(START, END, freq="D")
day_weights = np.array([SEASON[d.month] * (1.25 if d.weekday() >= 5 else 1.0) for d in all_days])
day_weights = day_weights / day_weights.sum()

for i, ci in enumerate(cust_idx, start=1):
    c = customers.iloc[ci]
    # order date must be on/after signup date: resample until valid (bounded tries)
    for _ in range(20):
        d = all_days[rng.choice(len(all_days), p=day_weights)]
        if d >= c["signup_date"]:
            break
    else:
        d = c["signup_date"] + pd.Timedelta(days=int(rng.integers(0, 30)))
        d = min(d, END)

    cat = rng.choice(list(CATALOGUE), p=CATEGORY_WEIGHTS)
    product, base_price = CATALOGUE[cat][rng.integers(0, len(CATALOGUE[cat]))]
    unit_price = round(base_price * rng.uniform(0.92, 1.08), 2)
    qty = int(rng.choice([1, 2, 3, 4], p=[0.68, 0.20, 0.08, 0.04]))

    festive = d.month in (10, 11) or (d.month == 1)
    discount = float(rng.choice([0, 5, 10, 15, 20, 25, 30],
                                p=[0.18, 0.14, 0.20, 0.18, 0.14, 0.10, 0.06] if festive
                                else [0.40, 0.18, 0.18, 0.12, 0.07, 0.03, 0.02]))

    pay = rng.choice(PAYMENTS, p=PAY_WEIGHTS)
    status = rng.choice(["Delivered", "Cancelled", "Returned"], p=[0.89, 0.05, 0.06])

    rows.append({
        "order_id": f"ORD{str(i).zfill(6)}",
        "customer_id": c["customer_id"],
        "order_date": d,
        "gender": c["gender"],
        "age": c["age"],
        "city": c["city"],
        "product_category": cat,
        "product_name": product,
        "quantity": qty,
        "unit_price": unit_price,
        "discount_pct": discount,
        "payment_method": pay,
        "order_status": status,
    })

df = pd.DataFrame(rows)

# ---------------------------------------------------- inject data-quality issues
n = len(df)

# 1) mixed date formats
fmt_mask = rng.random(n) < 0.25
df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
df.loc[fmt_mask, "order_date"] = pd.to_datetime(df.loc[fmt_mask, "order_date"]).dt.strftime("%d/%m/%Y")

# 2) messy text (case + whitespace)
def mess(series, p):
    out = series.astype(object).copy()
    idx = rng.random(len(series)) < p
    choices = rng.integers(0, 3, idx.sum())
    vals = out[idx].astype(str).tolist()
    vals = [v.lower() if c == 0 else v.upper() if c == 1 else f" {v} " for v, c in zip(vals, choices)]
    out[idx] = vals
    return out

for col in ["product_category", "city", "payment_method", "order_status", "gender"]:
    df[col] = mess(df[col], 0.04)

# 3) missing values
df["age"] = df["age"].astype("float")
df.loc[rng.random(n) < 0.03, "age"] = np.nan
df.loc[rng.random(n) < 0.02, "payment_method"] = np.nan
df.loc[rng.random(n) < 0.015, "city"] = np.nan
df.loc[rng.random(n) < 0.01, "discount_pct"] = np.nan

# 4) invalid quantities
bad = rng.choice(n, size=25, replace=False)
df.loc[bad[:15], "quantity"] = 0
df.loc[bad[15:], "quantity"] = -1

# 5) duplicate rows (exact copies)
dups = df.sample(n=210, random_state=SEED)
df = pd.concat([df, dups], ignore_index=True).sample(frac=1, random_state=SEED).reset_index(drop=True)

out = Path(__file__).resolve().parents[1] / "data" / "raw" / "ecommerce_transactions_raw.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print(f"Raw dataset written: {out}  ->  {len(df):,} rows, {df['customer_id'].nunique():,} customers")
