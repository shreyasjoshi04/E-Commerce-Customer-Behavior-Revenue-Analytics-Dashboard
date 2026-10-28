-- =====================================================================
-- 01_schema.sql  |  PostgreSQL schema for the E-Commerce Analytics project
-- Run:  psql -U postgres -d ecommerce_db -f sql/01_schema.sql
-- (create the database first:  CREATE DATABASE ecommerce_db;)
-- =====================================================================

DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS rfm_segments;

CREATE TABLE transactions (
    order_id          VARCHAR(12)    PRIMARY KEY,
    customer_id       VARCHAR(12)    NOT NULL,
    order_date        DATE           NOT NULL,
    gender            VARCHAR(10),
    age               INT,
    city              VARCHAR(30),
    product_category  VARCHAR(40)    NOT NULL,
    product_name      VARCHAR(60)    NOT NULL,
    quantity          INT            NOT NULL CHECK (quantity > 0),
    unit_price        NUMERIC(10,2)  NOT NULL,
    discount_pct      NUMERIC(5,2)   NOT NULL DEFAULT 0,
    payment_method    VARCHAR(30),
    order_status      VARCHAR(15)    NOT NULL,
    gross_amount      NUMERIC(12,2),
    discount_amount   NUMERIC(12,2),
    revenue           NUMERIC(12,2),      -- net order value after discount
    is_realised       SMALLINT,           -- 1 = Delivered
    realised_revenue  NUMERIC(12,2),      -- revenue counted only for Delivered orders
    order_year        INT,
    order_month       INT,
    order_month_name  VARCHAR(3),
    year_month        VARCHAR(7),
    order_quarter     VARCHAR(2),
    day_of_week       VARCHAR(10),
    age_group         VARCHAR(10)
);

CREATE TABLE rfm_segments (
    customer_id   VARCHAR(12) PRIMARY KEY,
    last_order    DATE,
    frequency     INT,
    monetary      NUMERIC(12,2),
    recency       INT,
    r_score       SMALLINT,
    f_score       SMALLINT,
    m_score       SMALLINT,
    rfm_score     VARCHAR(3),
    segment       VARCHAR(25),
    is_churned    SMALLINT,
    gender        VARCHAR(10),
    age           INT,
    age_group     VARCHAR(10),
    city          VARCHAR(30)
);

CREATE INDEX idx_tx_customer ON transactions (customer_id);
CREATE INDEX idx_tx_date     ON transactions (order_date);
CREATE INDEX idx_tx_category ON transactions (product_category);
