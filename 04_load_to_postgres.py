"""
04_load_to_postgres.py
----------------------
Loads the cleaned transactions and RFM table into PostgreSQL.

Prerequisites
  1. PostgreSQL running locally and a database created:  CREATE DATABASE ecommerce_db;
  2. pip install -r requirements.txt
  3. Edit the connection settings below (or set the env vars PGUSER, PGPASSWORD, PGHOST, PGPORT, PGDATABASE)

Run:  python scripts/04_load_to_postgres.py
"""
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
USER = os.getenv("PGUSER", "postgres")
PASSWORD = os.getenv("PGPASSWORD", "your_password")
HOST = os.getenv("PGHOST", "localhost")
PORT = os.getenv("PGPORT", "5432")
DB = os.getenv("PGDATABASE", "ecommerce_db")

engine = create_engine(f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}")

# 1) create tables
with engine.begin() as conn:
    conn.execute(text((ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8")))
print("Schema created.")

# 2) load data
tx = pd.read_csv(ROOT / "data" / "processed" / "ecommerce_transactions_clean.csv", parse_dates=["order_date"])
tx.to_sql("transactions", engine, if_exists="append", index=False, method="multi", chunksize=2000)

rfm = pd.read_csv(ROOT / "data" / "processed" / "rfm_segments.csv", parse_dates=["last_order"])
rfm = rfm.rename(columns={"R": "r_score", "F": "f_score", "M": "m_score"})
rfm.to_sql("rfm_segments", engine, if_exists="append", index=False, method="multi", chunksize=2000)

with engine.connect() as conn:
    n_tx = conn.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    n_rfm = conn.execute(text("SELECT COUNT(*) FROM rfm_segments")).scalar()
print(f"Loaded {n_tx:,} transactions and {n_rfm:,} RFM customer rows into '{DB}'.")
