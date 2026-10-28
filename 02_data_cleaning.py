"""
02_data_cleaning.py
-------------------
Cleans the raw e-commerce transactions and writes an analysis-ready file.

Steps
  1. Load raw data and profile quality issues
  2. Remove exact duplicate rows
  3. Standardise text columns (strip + proper case + canonical labels)
  4. Parse mixed date formats
  5. Handle missing values (documented imputation rules)
  6. Remove invalid records (quantity <= 0)
  7. Feature engineering (revenue, month, quarter, age group, etc.)

Run:  python scripts/02_data_cleaning.py
In :  data/raw/ecommerce_transactions_raw.csv
Out:  data/processed/ecommerce_transactions_clean.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ecommerce_transactions_raw.csv"
CLEAN = ROOT / "data" / "processed" / "ecommerce_transactions_clean.csv"

df = pd.read_csv(RAW)
print("=== RAW DATA PROFILE ===")
print(f"Rows: {len(df):,} | Columns: {df.shape[1]}")
print("Missing values per column:\n", df.isna().sum()[df.isna().sum() > 0], "\n")
print(f"Exact duplicate rows: {df.duplicated().sum():,}")
raw_rows = len(df)

# 1) duplicates ---------------------------------------------------------------
df = df.drop_duplicates().copy()
assert df["order_id"].is_unique, "order_id should be unique after dropping exact duplicates"

# 2) text standardisation -----------------------------------------------------
for col in ["gender", "city", "product_category", "payment_method", "order_status"]:
    df[col] = df[col].astype("string").str.strip()

CANON = {
    "product_category": {
        "electronics": "Electronics", "fashion": "Fashion",
        "home & kitchen": "Home & Kitchen",
        "beauty & personal care": "Beauty & Personal Care",
        "books & stationery": "Books & Stationery",
        "sports & fitness": "Sports & Fitness",
    },
    "payment_method": {
        "upi": "UPI", "credit card": "Credit Card", "debit card": "Debit Card",
        "cash on delivery": "Cash on Delivery", "net banking": "Net Banking", "wallet": "Wallet",
    },
    "order_status": {"delivered": "Delivered", "cancelled": "Cancelled", "returned": "Returned"},
    "gender": {"male": "Male", "female": "Female"},
    "city": {c.lower(): c for c in ["Pune", "Mumbai", "Bengaluru", "Delhi", "Hyderabad",
                                    "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Nagpur"]},
}
for col, mapping in CANON.items():
    df[col] = df[col].str.lower().map(mapping)

# 3) dates (two formats present: YYYY-MM-DD and DD/MM/YYYY) -------------------
iso = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce")
dmy = pd.to_datetime(df["order_date"], format="%d/%m/%Y", errors="coerce")
df["order_date"] = iso.fillna(dmy)
assert df["order_date"].notna().all(), "Unparsed dates remain"

# 4) missing values -----------------------------------------------------------
# customer-level attributes: fill from the same customer's other orders first
for col in ["age", "city", "gender"]:
    df[col] = df.groupby("customer_id")[col].transform(lambda s: s.fillna(s.dropna().iloc[0]) if s.notna().any() else s)

df["age"] = df["age"].fillna(df["age"].median()).round().astype(int)    # median imputation
df["city"] = df["city"].fillna("Unknown")
df["gender"] = df["gender"].fillna("Unknown")
df["payment_method"] = df["payment_method"].fillna(df["payment_method"].mode()[0])  # mode imputation
df["discount_pct"] = df["discount_pct"].fillna(0)                                   # no discount recorded -> 0

# 5) invalid records -----------------------------------------------------------
invalid = (df["quantity"] <= 0).sum()
df = df[df["quantity"] > 0].copy()

# 6) feature engineering -------------------------------------------------------
df["gross_amount"] = (df["quantity"] * df["unit_price"]).round(2)
df["discount_amount"] = (df["gross_amount"] * df["discount_pct"] / 100).round(2)
df["revenue"] = (df["gross_amount"] - df["discount_amount"]).round(2)       # net order value
# Only delivered orders count as realised revenue
df["is_realised"] = (df["order_status"] == "Delivered").astype(int)
df["realised_revenue"] = df["revenue"] * df["is_realised"]

df["order_year"] = df["order_date"].dt.year
df["order_month"] = df["order_date"].dt.month
df["order_month_name"] = df["order_date"].dt.strftime("%b")
df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
df["order_quarter"] = "Q" + df["order_date"].dt.quarter.astype(str)
df["day_of_week"] = df["order_date"].dt.day_name()
df["age_group"] = pd.cut(df["age"], bins=[17, 24, 34, 44, 54, 100],
                         labels=["18-24", "25-34", "35-44", "45-54", "55+"]).astype(str)

df = df.sort_values(["order_date", "order_id"]).reset_index(drop=True)

CLEAN.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(CLEAN, index=False, date_format="%Y-%m-%d")

print("\n=== CLEANING SUMMARY ===")
print(f"Raw rows            : {raw_rows:,}")
print(f"Duplicates removed  : {raw_rows - (len(df) + invalid):,}")
print(f"Invalid qty removed : {invalid:,}")
print(f"Clean rows          : {len(df):,}")
print(f"Customers           : {df['customer_id'].nunique():,}")
print(f"Date range          : {df['order_date'].min().date()} -> {df['order_date'].max().date()}")
print(f"Remaining nulls     : {int(df.isna().sum().sum())}")
print(f"Saved -> {CLEAN}")
