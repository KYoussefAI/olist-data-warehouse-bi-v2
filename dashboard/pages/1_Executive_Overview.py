from __future__ import annotations

import streamlit as st

from charts import bar_chart, line_chart
from components import (
    render_business_context,
    render_data_warning,
    render_kpi_row,
    render_page_header,
    render_questions,
    render_section,
)
from db import run_query, table_exists, view_exists


st.set_page_config(page_title="Executive Overview", layout="wide")

REQUIRED_TABLES = [
    "fact_order_performance",
    "fact_lead_conversion",
    "dim_date",
    "dim_customer",
    "dim_seller",
]
missing_tables = [table for table in REQUIRED_TABLES if not table_exists(table)]
if missing_tables:
    render_data_warning(
        "Tables manquantes dans le Data Warehouse: " + ", ".join(f"`{table}`" for table in missing_tables)
    )
    st.stop()

render_page_header(
    "Executive Overview",
    "Vue synthétique de la performance commerciale, logistique et marketing.",
)

render_section("Objectif métier")
render_business_context(
    "Donner une lecture rapide des résultats globaux: revenu, commandes, clients, "
    "vendeurs, satisfaction, retard de livraison et conversion des leads."
)

render_section("Questions traitées")
render_questions(
    [
        "Quel est le niveau global de revenu et de commandes ?",
        "Quelle est l'évolution mensuelle de la performance ?",
        "La satisfaction moyenne reste-t-elle stable dans le temps ?",
        "Quel est le niveau de conversion des leads marketing ?",
    ]
)

render_section("Indicateurs principaux")
kpis = run_query(
    """
    SELECT
        ROUND(SUM(f.item_total_value), 2) AS total_revenue,
        COUNT(DISTINCT f.order_id) AS orders_count,
        COUNT(DISTINCT c.customer_id) AS customers_count,
        COUNT(DISTINCT s.seller_id) AS sellers_count,
        ROUND(AVG(f.review_score_avg), 2) AS avg_review_score,
        ROUND(AVG(f.is_late_delivery) * 100, 2) AS late_delivery_rate_pct
    FROM fact_order_performance f
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    LEFT JOIN dim_seller s ON f.seller_key = s.seller_key;
    """
)
lead_kpis = run_query(
    """
    SELECT
        COUNT(*) AS mql_count,
        ROUND(100.0 * SUM(is_converted) / NULLIF(COUNT(*), 0), 2) AS conversion_rate_pct
    FROM fact_lead_conversion;
    """
)
if not kpis.empty and not lead_kpis.empty:
    row = kpis.iloc[0]
    lead_row = lead_kpis.iloc[0]
    render_kpi_row(
        [
            {"label": "Chiffre d'affaires", "value": row["total_revenue"], "format": "{:,.0f}"},
            {"label": "Commandes", "value": int(row["orders_count"] or 0), "format": "{:,}"},
            {"label": "Clients", "value": int(row["customers_count"] or 0), "format": "{:,}"},
            {"label": "Vendeurs", "value": int(row["sellers_count"] or 0), "format": "{:,}"},
        ]
    )
    render_kpi_row(
        [
            {"label": "Note moyenne", "value": row["avg_review_score"], "format": "{:.2f}/5"},
            {"label": "Taux de retard", "value": row["late_delivery_rate_pct"], "format": "{:.2f}%"},
            {"label": "MQL", "value": int(lead_row["mql_count"] or 0), "format": "{:,}"},
            {"label": "Conversion leads", "value": lead_row["conversion_rate_pct"], "format": "{:.2f}%"},
        ]
    )

render_section("Visualisations")
if view_exists("vw_sales_monthly"):
    monthly = run_query("SELECT * FROM vw_sales_monthly WHERE year_month IS NOT NULL ORDER BY year_month;")
    line_chart(monthly, "year_month", "revenue", "Évolution mensuelle du chiffre d'affaires")
    bar_chart(monthly, "year_month", "orders_count", "Volume mensuel des commandes")
    line_chart(monthly, "year_month", "avg_review_score", "Note moyenne par mois")
else:
    render_data_warning("La vue `vw_sales_monthly` est absente.")

lead_monthly = run_query(
    """
    SELECT
        printf('%04d-%02d', d.year, d.month) AS year_month,
        COUNT(*) AS mql_count,
        SUM(f.is_converted) AS converted_count,
        ROUND(100.0 * SUM(f.is_converted) / NULLIF(COUNT(*), 0), 2) AS conversion_rate_pct
    FROM fact_lead_conversion f
    LEFT JOIN dim_date d ON f.first_contact_date_key = d.date_key
    WHERE d.year IS NOT NULL
    GROUP BY d.year, d.month
    ORDER BY d.year, d.month;
    """
)
line_chart(lead_monthly, "year_month", "conversion_rate_pct", "Conversion des leads par mois")
