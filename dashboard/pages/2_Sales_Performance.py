from __future__ import annotations

import streamlit as st

from charts import bar_chart, horizontal_bar_chart, pie_chart
from components import (
    render_business_context,
    render_data_warning,
    render_kpi_row,
    render_page_header,
    render_questions,
    render_section,
)
from db import run_query, sql_escape, table_exists, view_exists


st.set_page_config(page_title="Sales Performance", layout="wide")

REQUIRED_TABLES = [
    "fact_order_performance",
    "dim_date",
    "dim_customer",
    "dim_seller",
    "dim_payment_type",
    "dim_product_category",
]
missing_tables = [table for table in REQUIRED_TABLES if not table_exists(table)]
if missing_tables:
    render_data_warning(
        "Tables manquantes dans le Data Warehouse: " + ", ".join(f"`{table}`" for table in missing_tables)
    )
    st.stop()

render_page_header("Sales Performance", "Analyse des revenus, catégories, vendeurs, clients et paiements.")

render_section("Objectif métier")
render_business_context(
    "Identifier les principaux moteurs de chiffre d'affaires et les zones de concentration des commandes."
)

render_section("Questions traitées")
render_questions(
    [
        "Quelles catégories génèrent le plus de revenus ?",
        "Quels vendeurs génèrent le plus de revenus ?",
        "Quels États clients concentrent le plus de commandes ?",
        "Quels modes de paiement sont les plus utilisés ?",
    ]
)

years = run_query(
    """
    SELECT DISTINCT d.year
    FROM fact_order_performance f
    LEFT JOIN dim_date d ON f.purchase_date_key = d.date_key
    WHERE d.year IS NOT NULL
    ORDER BY d.year;
    """
)
year_options = ["Toutes"] + [str(int(year)) for year in years.get("year", [])]
selected_year = st.sidebar.selectbox("Année", year_options)
year_filter = "" if selected_year == "Toutes" else f"AND d.year = {int(selected_year)}"

states = run_query(
    """
    SELECT DISTINCT c.customer_state
    FROM fact_order_performance f
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE c.customer_state IS NOT NULL
    ORDER BY c.customer_state;
    """
)
state_options = ["Tous"] + [state for state in states.get("customer_state", []) if state]
selected_state = st.sidebar.selectbox("État client", state_options)
state_filter = "" if selected_state == "Tous" else f"AND c.customer_state = '{sql_escape(selected_state)}'"

render_section("Indicateurs principaux")
kpis = run_query(
    f"""
    SELECT
        ROUND(SUM(f.item_total_value), 2) AS revenue,
        COUNT(DISTINCT f.order_id) AS orders_count,
        COUNT(DISTINCT f.seller_key) AS sellers_count,
        ROUND(AVG(f.payment_value_total), 2) AS avg_payment
    FROM fact_order_performance f
    LEFT JOIN dim_date d ON f.purchase_date_key = d.date_key
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE 1 = 1 {year_filter} {state_filter};
    """
)
if not kpis.empty:
    row = kpis.iloc[0]
    render_kpi_row(
        [
            {"label": "Revenu", "value": row["revenue"], "format": "{:,.0f}"},
            {"label": "Commandes", "value": int(row["orders_count"] or 0), "format": "{:,}"},
            {"label": "Vendeurs actifs", "value": int(row["sellers_count"] or 0), "format": "{:,}"},
            {"label": "Paiement moyen", "value": row["avg_payment"], "format": "{:,.2f}"},
        ]
    )

render_section("Visualisations")
if selected_year == "Toutes" and selected_state == "Tous" and view_exists("vw_category_performance"):
    categories = run_query("SELECT * FROM vw_category_performance LIMIT 15;")
else:
    categories = run_query(
        f"""
        SELECT
            COALESCE(pc.product_category_name_english, 'unknown') AS category,
            COUNT(DISTINCT f.order_id) AS orders_count,
            ROUND(SUM(f.item_total_value), 2) AS revenue
        FROM fact_order_performance f
        LEFT JOIN dim_product_category pc ON f.category_key = pc.category_key
        LEFT JOIN dim_date d ON f.purchase_date_key = d.date_key
        LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
        WHERE 1 = 1 {year_filter} {state_filter}
        GROUP BY COALESCE(pc.product_category_name_english, 'unknown')
        ORDER BY revenue DESC
        LIMIT 15;
        """
    )
horizontal_bar_chart(categories.sort_values("revenue"), "revenue", "category", "Top catégories par revenu")

seller_revenue = run_query(
    f"""
    SELECT
        COALESCE(s.seller_id, 'unknown') AS seller_id,
        ROUND(SUM(f.item_total_value), 2) AS revenue
    FROM fact_order_performance f
    LEFT JOIN dim_seller s ON f.seller_key = s.seller_key
    LEFT JOIN dim_date d ON f.purchase_date_key = d.date_key
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE 1 = 1 {year_filter} {state_filter}
    GROUP BY COALESCE(s.seller_id, 'unknown')
    ORDER BY revenue DESC
    LIMIT 10;
    """
)
horizontal_bar_chart(seller_revenue.sort_values("revenue"), "revenue", "seller_id", "Top 10 vendeurs par revenu")

orders_by_state = run_query(
    f"""
    SELECT
        COALESCE(c.customer_state, 'unknown') AS customer_state,
        COUNT(DISTINCT f.order_id) AS orders_count
    FROM fact_order_performance f
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    LEFT JOIN dim_date d ON f.purchase_date_key = d.date_key
    WHERE 1 = 1 {year_filter}
    GROUP BY COALESCE(c.customer_state, 'unknown')
    ORDER BY orders_count DESC;
    """
)
bar_chart(orders_by_state, "customer_state", "orders_count", "Commandes par État client")

payments = run_query(
    f"""
    SELECT
        COALESCE(p.payment_type, 'unknown') AS payment_type,
        COUNT(DISTINCT f.order_id) AS orders_count
    FROM fact_order_performance f
    LEFT JOIN dim_payment_type p ON f.payment_type_key = p.payment_type_key
    LEFT JOIN dim_date d ON f.purchase_date_key = d.date_key
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE 1 = 1 {year_filter} {state_filter}
    GROUP BY COALESCE(p.payment_type, 'unknown')
    ORDER BY orders_count DESC;
    """
)
pie_chart(payments, "payment_type", "orders_count", "Distribution des modes de paiement")
