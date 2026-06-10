-- Logical schema for the Olist BI Data Warehouse.
-- The Python ETL creates the physical SQLite tables automatically.

CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE,
    day INTEGER,
    month INTEGER,
    month_name TEXT,
    quarter INTEGER,
    year INTEGER,
    week_of_year INTEGER
);

CREATE TABLE dim_customer (
    customer_key INTEGER PRIMARY KEY,
    customer_id TEXT,
    customer_unique_id TEXT,
    customer_zip_code_prefix INTEGER,
    customer_city TEXT,
    customer_state TEXT
);

CREATE TABLE dim_seller (
    seller_key INTEGER PRIMARY KEY,
    seller_id TEXT,
    seller_zip_code_prefix INTEGER,
    seller_city TEXT,
    seller_state TEXT
);

CREATE TABLE dim_product_category (
    category_key INTEGER PRIMARY KEY,
    product_category_name TEXT,
    product_category_name_english TEXT
);

CREATE TABLE dim_product (
    product_key INTEGER PRIMARY KEY,
    product_id TEXT,
    category_key INTEGER,
    product_name_length REAL,
    product_description_length REAL,
    product_photos_qty REAL,
    product_weight_g REAL,
    product_length_cm REAL,
    product_height_cm REAL,
    product_width_cm REAL
);

CREATE TABLE dim_payment_type (
    payment_type_key INTEGER PRIMARY KEY,
    payment_type TEXT
);

CREATE TABLE dim_order_status (
    order_status_key INTEGER PRIMARY KEY,
    order_status TEXT
);

CREATE TABLE fact_order_performance (
    order_item_key INTEGER PRIMARY KEY,
    order_id TEXT,
    order_item_id INTEGER,
    customer_key INTEGER,
    seller_key INTEGER,
    product_key INTEGER,
    category_key INTEGER,
    payment_type_key INTEGER,
    order_status_key INTEGER,
    purchase_date_key INTEGER,
    approved_date_key INTEGER,
    delivered_carrier_date_key INTEGER,
    delivered_customer_date_key INTEGER,
    estimated_delivery_date_key INTEGER,
    shipping_limit_date_key INTEGER,
    price REAL,
    freight_value REAL,
    item_total_value REAL,
    payment_value_total REAL,
    allocated_payment_value REAL,
    payment_installments_max REAL,
    payment_method_count INTEGER,
    review_score_avg REAL,
    review_score_min REAL,
    review_score_max REAL,
    review_count INTEGER,
    delivery_delay_days REAL,
    delivery_difference_days REAL,
    is_late_delivery INTEGER,
    approval_delay_hours REAL
);

CREATE TABLE fact_lead_conversion (
    lead_key INTEGER PRIMARY KEY,
    mql_id TEXT,
    seller_key INTEGER,
    origin_key INTEGER,
    business_segment_key INTEGER,
    lead_type_key INTEGER,
    lead_profile_key INTEGER,
    sales_team_key INTEGER,
    first_contact_date_key INTEGER,
    won_date_key INTEGER,
    is_converted INTEGER,
    conversion_delay_days REAL,
    declared_monthly_revenue REAL,
    declared_product_catalog_size REAL,
    average_stock REAL,
    has_company TEXT,
    has_gtin TEXT
);
