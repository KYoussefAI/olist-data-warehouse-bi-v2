from __future__ import annotations

import streamlit as st

from charts import bar_chart, histogram, horizontal_bar_chart
from components import (
    render_business_context,
    render_data_warning,
    render_kpi_row,
    render_page_header,
    render_questions,
    render_section,
)
from db import run_query, sql_escape, table_exists


st.set_page_config(page_title="Delivery & Satisfaction", layout="wide")

REQUIRED_TABLES = [
    "fact_order_performance",
    "dim_customer",
    "dim_product_category",
]
missing_tables = [table for table in REQUIRED_TABLES if not table_exists(table)]
if missing_tables:
    render_data_warning(
        "Tables manquantes dans le Data Warehouse: " + ", ".join(f"`{table}`" for table in missing_tables)
    )
    st.stop()

render_page_header("Delivery & Satisfaction", "Analyse des délais de livraison et des avis clients.")

render_section("Objectif métier")
render_business_context(
    "Évaluer l'effet des retards de livraison sur la satisfaction et localiser les zones ou catégories à surveiller. "
    "Les avis sont agrégés au niveau commande, tandis que la table de faits est au grain article de commande; "
    "les comptages de commandes utilisent donc COUNT(DISTINCT order_id)."
)

render_section("Questions traitées")
render_questions(
    [
        "Les retards de livraison impactent-ils la satisfaction ?",
        "Quels États ont les délais moyens les plus élevés ?",
        "Quelles catégories ont les notes moyennes les plus faibles ?",
        "Quelle est la distribution des notes clients ?",
    ]
)

states = run_query(
    """
    SELECT DISTINCT customer_state
    FROM dim_customer
    WHERE customer_state IS NOT NULL
    ORDER BY customer_state;
    """
)
state_options = ["Tous"] + [state for state in states.get("customer_state", []) if state]
selected_state = st.sidebar.selectbox("État client", state_options)
state_filter = "" if selected_state == "Tous" else f"AND c.customer_state = '{sql_escape(selected_state)}'"

render_section("Indicateurs principaux")
kpis = run_query(
    f"""
    SELECT
        ROUND(AVG(f.review_score_avg), 2) AS avg_review_score,
        ROUND(AVG(f.delivery_delay_days), 2) AS avg_delivery_days,
        ROUND(AVG(f.is_late_delivery) * 100, 2) AS late_rate,
        COUNT(DISTINCT f.order_id) AS orders_count
    FROM fact_order_performance f
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE f.is_late_delivery IS NOT NULL {state_filter};
    """
)
if not kpis.empty:
    row = kpis.iloc[0]
    render_kpi_row(
        [
            {"label": "Note moyenne", "value": row["avg_review_score"], "format": "{:.2f}/5"},
            {"label": "Délai moyen", "value": row["avg_delivery_days"], "format": "{:.1f} jours"},
            {"label": "Taux de retard", "value": row["late_rate"], "format": "{:.2f}%"},
            {"label": "Commandes", "value": int(row["orders_count"] or 0), "format": "{:,}"},
        ]
    )

render_section("Visualisations")
late_vs_review = run_query(
    f"""
    SELECT
        CASE WHEN f.is_late_delivery = 1 THEN 'En retard' ELSE 'À temps / en avance' END AS delivery_status,
        COUNT(DISTINCT f.order_id) AS orders_count,
        ROUND(AVG(f.review_score_avg), 2) AS avg_review_score
    FROM fact_order_performance f
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE f.is_late_delivery IS NOT NULL {state_filter}
    GROUP BY delivery_status;
    """
)
bar_chart(late_vs_review, "delivery_status", "avg_review_score", "Note moyenne: livraison en retard vs à temps")

delivery_by_state = run_query(
    """
    SELECT
        COALESCE(c.customer_state, 'unknown') AS customer_state,
        COUNT(DISTINCT f.order_id) AS orders_count,
        ROUND(AVG(f.delivery_delay_days), 2) AS avg_delivery_days
    FROM fact_order_performance f
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE f.delivery_delay_days IS NOT NULL
    GROUP BY COALESCE(c.customer_state, 'unknown')
    HAVING COUNT(DISTINCT f.order_id) >= 20
    ORDER BY avg_delivery_days DESC;
    """
)
bar_chart(delivery_by_state, "customer_state", "avg_delivery_days", "Délai moyen de livraison par État client")

late_by_state = run_query(
    """
    SELECT
        COALESCE(c.customer_state, 'unknown') AS customer_state,
        COUNT(DISTINCT f.order_id) AS orders_count,
        ROUND(AVG(f.is_late_delivery) * 100, 2) AS late_rate
    FROM fact_order_performance f
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE f.is_late_delivery IS NOT NULL
    GROUP BY COALESCE(c.customer_state, 'unknown')
    HAVING COUNT(DISTINCT f.order_id) >= 20
    ORDER BY late_rate DESC;
    """
)
bar_chart(late_by_state, "customer_state", "late_rate", "Taux de retard par État client")

reviews = run_query(
    f"""
    SELECT f.review_score_avg
    FROM fact_order_performance f
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE f.review_score_avg IS NOT NULL {state_filter};
    """
)
histogram(reviews, "review_score_avg", "Distribution des notes clients")

low_categories = run_query(
    f"""
    SELECT
        COALESCE(pc.product_category_name_english, 'unknown') AS category,
        COUNT(DISTINCT f.order_id) AS orders_count,
        ROUND(AVG(f.review_score_avg), 2) AS avg_review_score
    FROM fact_order_performance f
    LEFT JOIN dim_product_category pc ON f.category_key = pc.category_key
    LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE f.review_score_avg IS NOT NULL {state_filter}
    GROUP BY COALESCE(pc.product_category_name_english, 'unknown')
    HAVING COUNT(DISTINCT f.order_id) >= 20
    ORDER BY avg_review_score ASC
    LIMIT 15;
    """
)
horizontal_bar_chart(
    low_categories.sort_values("avg_review_score", ascending=False),
    "avg_review_score",
    "category",
    "Catégories avec les notes moyennes les plus faibles",
)
