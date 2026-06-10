"""Run the Olist BI ETL pipeline.

This script reads raw Olist CSV files, builds a small dimensional warehouse,
and writes the output to a SQLite database.

Usage:
    python -m src.run_etl --raw-data-dir data/raw --warehouse-path data/warehouse/olist_dwh.sqlite
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Dict, Iterable

import numpy as np
import pandas as pd


REQUIRED_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "mql": "olist_marketing_qualified_leads_dataset.csv",
    "closed_deals": "olist_closed_deals_dataset.csv",
}

OPTIONAL_FILES = {
    "categories": "product_category_name_translation.csv",
}

DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
    "mql": ["first_contact_date"],
    "closed_deals": ["won_date"],
}


def read_csv_files(raw_data_dir: Path) -> Dict[str, pd.DataFrame]:
    """Read required CSV sources and parse known date columns."""
    missing = [name for name in REQUIRED_FILES.values() if not (raw_data_dir / name).exists()]
    if missing:
        missing_list = "\n".join(f"- {name}" for name in missing)
        raise FileNotFoundError(
            f"Missing required CSV files in {raw_data_dir}:\n{missing_list}\n"
            "Copy the raw Olist CSV files into data/raw/ or pass --raw-data-dir."
        )

    dataframes: Dict[str, pd.DataFrame] = {}
    for key, file_name in REQUIRED_FILES.items():
        parse_dates = DATE_COLUMNS.get(key, [])
        dataframes[key] = pd.read_csv(raw_data_dir / file_name, parse_dates=parse_dates)

    categories_path = raw_data_dir / OPTIONAL_FILES["categories"]
    if categories_path.exists():
        dataframes["categories"] = pd.read_csv(categories_path)
    else:
        dataframes["categories"] = pd.DataFrame(
            columns=["product_category_name", "product_category_name_english"]
        )
    return dataframes


def make_surrogate_key(df: pd.DataFrame, key_name: str) -> pd.DataFrame:
    """Add a 1-based surrogate key as first column."""
    out = df.reset_index(drop=True).copy()
    out.insert(0, key_name, np.arange(1, len(out) + 1, dtype=np.int64))
    return out


def normalize_text_series(series: pd.Series) -> pd.Series:
    """Normalize text labels used in dimensions."""
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .replace({"": pd.NA, "nan": pd.NA, "none": pd.NA})
    )


def date_key_from_series(series: pd.Series) -> pd.Series:
    """Convert datetime/date series to integer date key YYYYMMDD with nullable values."""
    dt = pd.to_datetime(series, errors="coerce")
    return (dt.dt.strftime("%Y%m%d")).astype("Int64")


def build_dim_date(dataframes: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build a shared date dimension from every business date in the project."""
    date_values = []
    for table_name, columns in DATE_COLUMNS.items():
        df = dataframes.get(table_name)
        if df is None:
            continue
        for column in columns:
            if column in df.columns:
                date_values.append(pd.to_datetime(df[column], errors="coerce").dt.date)

    all_dates = pd.concat(date_values, ignore_index=True).dropna().drop_duplicates()
    dim = pd.DataFrame({"full_date": pd.to_datetime(all_dates).sort_values().reset_index(drop=True)})
    dim["date_key"] = dim["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim["day"] = dim["full_date"].dt.day
    dim["month"] = dim["full_date"].dt.month
    dim["month_name"] = dim["full_date"].dt.month_name()
    dim["quarter"] = dim["full_date"].dt.quarter
    dim["year"] = dim["full_date"].dt.year
    dim["week_of_year"] = dim["full_date"].dt.isocalendar().week.astype(int)
    return dim[["date_key", "full_date", "day", "month", "month_name", "quarter", "year", "week_of_year"]]


def build_dimensions(dataframes: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Create all dimension tables used by the two facts."""
    customers = dataframes["customers"].drop_duplicates("customer_id").copy()
    dim_customer = make_surrogate_key(
        customers[
            [
                "customer_id",
                "customer_unique_id",
                "customer_zip_code_prefix",
                "customer_city",
                "customer_state",
            ]
        ],
        "customer_key",
    )

    sellers_base = dataframes["sellers"].drop_duplicates("seller_id").copy()
    closed_sellers = dataframes["closed_deals"][["seller_id"]].dropna().drop_duplicates()
    sellers = closed_sellers.merge(sellers_base, on="seller_id", how="left")
    sellers = pd.concat([sellers_base, sellers], ignore_index=True).drop_duplicates("seller_id")
    dim_seller = make_surrogate_key(
        sellers[["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"]],
        "seller_key",
    )

    categories = dataframes["categories"].drop_duplicates("product_category_name").copy()
    product_categories = dataframes["products"][["product_category_name"]].drop_duplicates()
    categories = product_categories.merge(categories, on="product_category_name", how="left")
    categories["product_category_name"] = normalize_text_series(categories["product_category_name"])
    categories["product_category_name_english"] = normalize_text_series(categories["product_category_name_english"])
    categories["product_category_name_english"] = categories["product_category_name_english"].fillna(
        categories["product_category_name"]
    )
    dim_product_category = make_surrogate_key(
        categories.sort_values("product_category_name", na_position="last"),
        "category_key",
    )

    products = dataframes["products"].copy()
    products = products.rename(
        columns={
            "product_name_lenght": "product_name_length",
            "product_description_lenght": "product_description_length",
        }
    )
    products["product_category_name"] = normalize_text_series(products["product_category_name"])
    category_map = dim_product_category.set_index("product_category_name")["category_key"]
    products["category_key"] = products["product_category_name"].map(category_map).astype("Int64")
    dim_product = make_surrogate_key(
        products[
            [
                "product_id",
                "category_key",
                "product_name_length",
                "product_description_length",
                "product_photos_qty",
                "product_weight_g",
                "product_length_cm",
                "product_height_cm",
                "product_width_cm",
            ]
        ].drop_duplicates("product_id"),
        "product_key",
    )

    payment_types = dataframes["payments"][["payment_type"]].drop_duplicates().copy()
    payment_types["payment_type"] = normalize_text_series(payment_types["payment_type"])
    payment_types = pd.concat([payment_types, pd.DataFrame({"payment_type": ["mixed", "unknown"]})], ignore_index=True)
    payment_types = payment_types.drop_duplicates().sort_values("payment_type")
    dim_payment_type = make_surrogate_key(payment_types, "payment_type_key")

    order_statuses = dataframes["orders"][["order_status"]].drop_duplicates().copy()
    order_statuses["order_status"] = normalize_text_series(order_statuses["order_status"])
    dim_order_status = make_surrogate_key(order_statuses.sort_values("order_status"), "order_status_key")

    def simple_dim(source_df: pd.DataFrame, column: str, key_name: str) -> pd.DataFrame:
        dim = source_df[[column]].drop_duplicates().copy()
        dim[column] = normalize_text_series(dim[column]).fillna("unknown")
        dim = dim.drop_duplicates().sort_values(column)
        return make_surrogate_key(dim, key_name)

    dim_lead_origin = simple_dim(dataframes["mql"], "origin", "origin_key")
    dim_business_segment = simple_dim(dataframes["closed_deals"], "business_segment", "business_segment_key")
    dim_lead_type = simple_dim(dataframes["closed_deals"], "lead_type", "lead_type_key")
    dim_lead_profile = simple_dim(dataframes["closed_deals"], "lead_behaviour_profile", "lead_profile_key")

    sales_team = dataframes["closed_deals"][["sdr_id", "sr_id"]].drop_duplicates().copy()
    sales_team["sdr_id"] = sales_team["sdr_id"].fillna("unknown")
    sales_team["sr_id"] = sales_team["sr_id"].fillna("unknown")
    dim_sales_team = make_surrogate_key(sales_team.sort_values(["sdr_id", "sr_id"]), "sales_team_key")

    return {
        "dim_date": build_dim_date(dataframes),
        "dim_customer": dim_customer,
        "dim_seller": dim_seller,
        "dim_product_category": dim_product_category,
        "dim_product": dim_product,
        "dim_payment_type": dim_payment_type,
        "dim_order_status": dim_order_status,
        "dim_lead_origin": dim_lead_origin,
        "dim_business_segment": dim_business_segment,
        "dim_lead_type": dim_lead_type,
        "dim_lead_profile": dim_lead_profile,
        "dim_sales_team": dim_sales_team,
    }


def build_payment_summary(payments: pd.DataFrame) -> pd.DataFrame:
    """Aggregate payments at order level and derive a BI-friendly payment type."""
    p = payments.copy()
    p["payment_type"] = normalize_text_series(p["payment_type"]).fillna("unknown")

    payment_total = p.groupby("order_id", as_index=False).agg(
        payment_value_total=("payment_value", "sum"),
        payment_installments_max=("payment_installments", "max"),
        payment_method_count=("payment_type", "nunique"),
        payment_records_count=("payment_sequential", "count"),
    )

    type_by_order = (
        p.sort_values(["order_id", "payment_value"], ascending=[True, False])
        .groupby("order_id", as_index=False)
        .first()[["order_id", "payment_type"]]
        .rename(columns={"payment_type": "main_payment_type"})
    )
    payment_total = payment_total.merge(type_by_order, on="order_id", how="left")
    payment_total["payment_type_group"] = np.where(
        payment_total["payment_method_count"] > 1,
        "mixed",
        payment_total["main_payment_type"],
    )
    payment_total["payment_type_group"] = payment_total["payment_type_group"].fillna("unknown")
    return payment_total


def build_review_summary(reviews: pd.DataFrame) -> pd.DataFrame:
    """Aggregate reviews at order level."""
    return reviews.groupby("order_id", as_index=False).agg(
        review_score_avg=("review_score", "mean"),
        review_score_min=("review_score", "min"),
        review_score_max=("review_score", "max"),
        review_count=("review_id", "count"),
    )


def build_fact_order_performance(dataframes: Dict[str, pd.DataFrame], dimensions: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create the order performance fact at order-item grain."""
    orders = dataframes["orders"].copy()
    items = dataframes["order_items"].copy()

    fact = items.merge(orders, on="order_id", how="inner")
    fact = fact.merge(build_payment_summary(dataframes["payments"]), on="order_id", how="left")
    fact = fact.merge(build_review_summary(dataframes["reviews"]), on="order_id", how="left")

    fact["item_total_value"] = fact["price"].fillna(0) + fact["freight_value"].fillna(0)
    order_item_totals = fact.groupby("order_id", as_index=False)["item_total_value"].sum().rename(
        columns={"item_total_value": "order_items_total_value"}
    )
    fact = fact.merge(order_item_totals, on="order_id", how="left")
    fact["allocated_payment_value"] = np.where(
        fact["order_items_total_value"] > 0,
        fact["payment_value_total"] * fact["item_total_value"] / fact["order_items_total_value"],
        np.nan,
    )

    # Keys
    customer_map = dimensions["dim_customer"].set_index("customer_id")["customer_key"]
    seller_map = dimensions["dim_seller"].set_index("seller_id")["seller_key"]
    product_map = dimensions["dim_product"].set_index("product_id")["product_key"]
    product_category_map = dimensions["dim_product"].set_index("product_id")["category_key"]
    payment_map = dimensions["dim_payment_type"].set_index("payment_type")["payment_type_key"]
    status_map = dimensions["dim_order_status"].set_index("order_status")["order_status_key"]

    fact["customer_key"] = fact["customer_id"].map(customer_map).astype("Int64")
    fact["seller_key"] = fact["seller_id"].map(seller_map).astype("Int64")
    fact["product_key"] = fact["product_id"].map(product_map).astype("Int64")
    fact["category_key"] = fact["product_id"].map(product_category_map).astype("Int64")
    fact["payment_type_key"] = fact["payment_type_group"].map(payment_map).astype("Int64")
    fact["order_status_key"] = fact["order_status"].map(status_map).astype("Int64")

    for source_col, target_col in {
        "order_purchase_timestamp": "purchase_date_key",
        "order_approved_at": "approved_date_key",
        "order_delivered_carrier_date": "delivered_carrier_date_key",
        "order_delivered_customer_date": "delivered_customer_date_key",
        "order_estimated_delivery_date": "estimated_delivery_date_key",
        "shipping_limit_date": "shipping_limit_date_key",
    }.items():
        fact[target_col] = date_key_from_series(fact[source_col])

    # Measures
    fact["delivery_delay_days"] = (
        pd.to_datetime(fact["order_delivered_customer_date"], errors="coerce")
        - pd.to_datetime(fact["order_purchase_timestamp"], errors="coerce")
    ).dt.total_seconds() / 86400
    fact["delivery_difference_days"] = (
        pd.to_datetime(fact["order_delivered_customer_date"], errors="coerce")
        - pd.to_datetime(fact["order_estimated_delivery_date"], errors="coerce")
    ).dt.total_seconds() / 86400
    fact["is_late_delivery"] = np.where(fact["delivery_difference_days"] > 0, 1, 0)
    fact.loc[fact["delivery_difference_days"].isna(), "is_late_delivery"] = np.nan
    fact["approval_delay_hours"] = (
        pd.to_datetime(fact["order_approved_at"], errors="coerce")
        - pd.to_datetime(fact["order_purchase_timestamp"], errors="coerce")
    ).dt.total_seconds() / 3600

    fact = make_surrogate_key(fact, "order_item_key")

    columns = [
        "order_item_key",
        "order_id",
        "order_item_id",
        "customer_key",
        "seller_key",
        "product_key",
        "category_key",
        "payment_type_key",
        "order_status_key",
        "purchase_date_key",
        "approved_date_key",
        "delivered_carrier_date_key",
        "delivered_customer_date_key",
        "estimated_delivery_date_key",
        "shipping_limit_date_key",
        "price",
        "freight_value",
        "item_total_value",
        "payment_value_total",
        "allocated_payment_value",
        "payment_installments_max",
        "payment_method_count",
        "review_score_avg",
        "review_score_min",
        "review_score_max",
        "review_count",
        "delivery_delay_days",
        "delivery_difference_days",
        "is_late_delivery",
        "approval_delay_hours",
    ]
    return fact[columns]


def build_fact_lead_conversion(dataframes: Dict[str, pd.DataFrame], dimensions: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create the lead conversion fact at MQL grain."""
    mql = dataframes["mql"].copy()
    deals = dataframes["closed_deals"].copy()
    fact = mql.merge(deals, on="mql_id", how="left", indicator=True)

    seller_map = dimensions["dim_seller"].set_index("seller_id")["seller_key"]
    origin_map = dimensions["dim_lead_origin"].set_index("origin")["origin_key"]
    segment_map = dimensions["dim_business_segment"].set_index("business_segment")["business_segment_key"]
    type_map = dimensions["dim_lead_type"].set_index("lead_type")["lead_type_key"]
    profile_map = dimensions["dim_lead_profile"].set_index("lead_behaviour_profile")["lead_profile_key"]
    sales_team_map = dimensions["dim_sales_team"].set_index(["sdr_id", "sr_id"])["sales_team_key"]

    fact["origin"] = normalize_text_series(fact["origin"]).fillna("unknown")
    fact["business_segment"] = normalize_text_series(fact["business_segment"]).fillna("unknown")
    fact["lead_type"] = normalize_text_series(fact["lead_type"]).fillna("unknown")
    fact["lead_behaviour_profile"] = normalize_text_series(fact["lead_behaviour_profile"]).fillna("unknown")
    fact["sdr_id"] = fact["sdr_id"].fillna("unknown")
    fact["sr_id"] = fact["sr_id"].fillna("unknown")

    fact["seller_key"] = fact["seller_id"].map(seller_map).astype("Int64")
    fact["origin_key"] = fact["origin"].map(origin_map).astype("Int64")
    fact["business_segment_key"] = fact["business_segment"].map(segment_map).astype("Int64")
    fact["lead_type_key"] = fact["lead_type"].map(type_map).astype("Int64")
    fact["lead_profile_key"] = fact["lead_behaviour_profile"].map(profile_map).astype("Int64")
    fact["sales_team_key"] = fact.set_index(["sdr_id", "sr_id"]).index.map(sales_team_map).astype("Int64")

    fact["first_contact_date_key"] = date_key_from_series(fact["first_contact_date"])
    fact["won_date_key"] = date_key_from_series(fact["won_date"])
    fact["is_converted"] = np.where(fact["_merge"] == "both", 1, 0)
    fact["conversion_delay_days"] = (
        pd.to_datetime(fact["won_date"], errors="coerce")
        - pd.to_datetime(fact["first_contact_date"], errors="coerce")
    ).dt.total_seconds() / 86400

    fact = make_surrogate_key(fact, "lead_key")

    columns = [
        "lead_key",
        "mql_id",
        "seller_key",
        "origin_key",
        "business_segment_key",
        "lead_type_key",
        "lead_profile_key",
        "sales_team_key",
        "first_contact_date_key",
        "won_date_key",
        "is_converted",
        "conversion_delay_days",
        "declared_monthly_revenue",
        "declared_product_catalog_size",
        "average_stock",
        "has_company",
        "has_gtin",
    ]
    return fact[columns]


def build_quality_report(dataframes: Dict[str, pd.DataFrame], dimensions: Dict[str, pd.DataFrame], facts: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create a small data quality table for dashboard and documentation."""
    checks = []

    def add_check(area: str, check_name: str, value: int | float | str) -> None:
        checks.append({"area": area, "check_name": check_name, "value": value})

    for name, df in dataframes.items():
        add_check("raw_rows", name, len(df))

    category_translation_rows = len(dataframes["categories"])
    add_check(
        "source_notes",
        "product_category_name_translation",
        "available" if category_translation_rows > 0 else "missing_optional_using_original_category_names",
    )

    for name, df in dimensions.items():
        add_check("dimension_rows", name, len(df))

    for name, df in facts.items():
        add_check("fact_rows", name, len(df))

    orders = dataframes["orders"]
    items = dataframes["order_items"]
    payments = dataframes["payments"]
    reviews = dataframes["reviews"]
    mql = dataframes["mql"]
    deals = dataframes["closed_deals"]
    sellers = dataframes["sellers"]

    add_check("relationships", "orders_without_items", int((~orders["order_id"].isin(items["order_id"])).sum()))
    add_check("relationships", "orders_without_payments", int((~orders["order_id"].isin(payments["order_id"])).sum()))
    add_check("relationships", "orders_without_reviews", int((~orders["order_id"].isin(reviews["order_id"])).sum()))
    add_check("relationships", "items_without_order", int((~items["order_id"].isin(orders["order_id"])).sum()))
    add_check("relationships", "deals_without_mql", int((~deals["mql_id"].isin(mql["mql_id"])).sum()))
    add_check("relationships", "closed_deal_sellers_not_in_marketplace_sellers", int((~deals["seller_id"].isin(sellers["seller_id"])).sum()))

    add_check("duplicates", "duplicated_order_ids", int(orders.duplicated("order_id").sum()))
    add_check("duplicates", "duplicated_customer_ids", int(dataframes["customers"].duplicated("customer_id").sum()))
    add_check("duplicates", "duplicated_seller_ids", int(sellers.duplicated("seller_id").sum()))
    add_check("duplicates", "duplicated_mql_ids", int(mql.duplicated("mql_id").sum()))

    add_check("missing", "orders_missing_delivered_customer_date", int(orders["order_delivered_customer_date"].isna().sum()))
    add_check("missing", "products_missing_category", int(dataframes["products"]["product_category_name"].isna().sum()))
    add_check("missing", "reviews_missing_score", int(reviews["review_score"].isna().sum()))
    add_check("missing", "closed_deals_missing_declared_revenue", int(deals["declared_monthly_revenue"].isna().sum()))

    return pd.DataFrame(checks)


def write_sqlite(warehouse_path: Path, tables: Dict[str, pd.DataFrame]) -> None:
    """Write all warehouse tables to SQLite."""
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    if warehouse_path.exists():
        warehouse_path.unlink()

    with sqlite3.connect(warehouse_path) as conn:
        for table_name, df in tables.items():
            df.to_sql(table_name, conn, index=False, if_exists="replace")

        # Helpful SQL views for the Streamlit report.
        conn.executescript(
            """
            CREATE VIEW vw_sales_monthly AS
            SELECT
                d.year,
                d.month,
                printf('%04d-%02d', d.year, d.month) AS year_month,
                COUNT(DISTINCT f.order_id) AS orders_count,
                ROUND(SUM(f.item_total_value), 2) AS revenue,
                ROUND(AVG(f.review_score_avg), 2) AS avg_review_score,
                ROUND(AVG(f.delivery_delay_days), 2) AS avg_delivery_days,
                ROUND(AVG(f.is_late_delivery) * 100, 2) AS late_delivery_rate_pct
            FROM fact_order_performance f
            LEFT JOIN dim_date d ON f.purchase_date_key = d.date_key
            GROUP BY d.year, d.month
            ORDER BY d.year, d.month;

            CREATE VIEW vw_category_performance AS
            SELECT
                COALESCE(c.product_category_name_english, 'unknown') AS category,
                COUNT(DISTINCT f.order_id) AS orders_count,
                ROUND(SUM(f.item_total_value), 2) AS revenue,
                ROUND(AVG(f.review_score_avg), 2) AS avg_review_score,
                ROUND(AVG(f.is_late_delivery) * 100, 2) AS late_delivery_rate_pct
            FROM fact_order_performance f
            LEFT JOIN dim_product_category c ON f.category_key = c.category_key
            GROUP BY COALESCE(c.product_category_name_english, 'unknown')
            ORDER BY revenue DESC;

            CREATE VIEW vw_lead_funnel AS
            SELECT
                o.origin,
                COUNT(*) AS mql_count,
                SUM(f.is_converted) AS converted_count,
                ROUND(100.0 * SUM(f.is_converted) / COUNT(*), 2) AS conversion_rate_pct,
                ROUND(AVG(f.conversion_delay_days), 2) AS avg_conversion_delay_days,
                ROUND(AVG(f.declared_monthly_revenue), 2) AS avg_declared_monthly_revenue
            FROM fact_lead_conversion f
            LEFT JOIN dim_lead_origin o ON f.origin_key = o.origin_key
            GROUP BY o.origin
            ORDER BY mql_count DESC;
            """
        )


def write_markdown_quality_report(report_path: Path, quality_df: pd.DataFrame) -> None:
    """Write quality checks to a markdown file."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Data Quality Report", "", "Generated by `python -m src.run_etl`.", ""]

    for area, group in quality_df.groupby("area", sort=False):
        lines.append(f"## {area}")
        lines.append("")
        lines.append("| Check | Value |")
        lines.append("|---|---:|")
        for _, row in group.iterrows():
            lines.append(f"| {row['check_name']} | {row['value']} |")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def run_pipeline(raw_data_dir: Path, warehouse_path: Path, quality_report_path: Path) -> None:
    """Run complete ETL pipeline."""
    print(f"Reading raw data from: {raw_data_dir}")
    dataframes = read_csv_files(raw_data_dir)

    print("Building dimensions...")
    dimensions = build_dimensions(dataframes)

    print("Building facts...")
    facts = {
        "fact_order_performance": build_fact_order_performance(dataframes, dimensions),
        "fact_lead_conversion": build_fact_lead_conversion(dataframes, dimensions),
    }

    print("Building quality report...")
    quality_df = build_quality_report(dataframes, dimensions, facts)

    tables = {**dimensions, **facts, "etl_quality_report": quality_df}

    print(f"Writing warehouse to: {warehouse_path}")
    write_sqlite(warehouse_path, tables)

    print(f"Writing markdown quality report to: {quality_report_path}")
    write_markdown_quality_report(quality_report_path, quality_df)

    print("ETL completed successfully.")
    print(f"Created {len(tables)} tables/views-ready tables.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Olist BI ETL pipeline")
    parser.add_argument("--raw-data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--warehouse-path", type=Path, default=Path("data/warehouse/olist_dwh.sqlite"))
    parser.add_argument("--quality-report-path", type=Path, default=Path("docs/data_quality_report.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pipeline(args.raw_data_dir, args.warehouse_path, args.quality_report_path)


if __name__ == "__main__":
    main()
