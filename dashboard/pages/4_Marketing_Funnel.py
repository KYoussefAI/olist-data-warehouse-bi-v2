from __future__ import annotations

import streamlit as st

from charts import bar_chart, horizontal_bar_chart
from components import (
    render_business_context,
    render_data_warning,
    render_kpi_row,
    render_page_header,
    render_questions,
    render_section,
)
from db import run_query, sql_escape, table_exists, view_exists


st.set_page_config(page_title="Marketing Funnel", layout="wide")

REQUIRED_TABLES = [
    "fact_lead_conversion",
    "dim_lead_origin",
    "dim_business_segment",
    "dim_sales_team",
]
missing_tables = [table for table in REQUIRED_TABLES if not table_exists(table)]
if missing_tables:
    render_data_warning(
        "Tables manquantes dans le Data Warehouse: " + ", ".join(f"`{table}`" for table in missing_tables)
    )
    st.stop()

render_page_header("Marketing Funnel", "Analyse des MQL, conversions, segments et équipes commerciales.")

render_section("Objectif métier")
render_business_context(
    "Comprendre l'efficacité de l'acquisition de vendeurs en conservant les leads non convertis dans le calcul. "
    "Le taux de conversion correspond aux leads convertis divisés par le total des MQL."
)

render_section("Questions traitées")
render_questions(
    [
        "Combien de MQL sont générés ?",
        "Quel est le taux de conversion global ?",
        "Quels canaux d'origine convertissent le mieux ?",
        "Quels segments business convertissent le mieux ?",
        "Quel est le délai moyen de conversion ?",
        "Quels commerciaux ferment le plus de deals ?",
    ]
)

origins = run_query(
    """
    SELECT DISTINCT origin
    FROM dim_lead_origin
    WHERE origin IS NOT NULL
    ORDER BY origin;
    """
)
origin_options = ["Toutes"] + [origin for origin in origins.get("origin", []) if origin]
selected_origin = st.sidebar.selectbox("Origine lead", origin_options)
origin_filter = "" if selected_origin == "Toutes" else f"AND o.origin = '{sql_escape(selected_origin)}'"

render_section("Indicateurs principaux")
kpis = run_query(
    f"""
    SELECT
        COUNT(*) AS mql_count,
        SUM(f.is_converted) AS converted_count,
        ROUND(100.0 * SUM(f.is_converted) / NULLIF(COUNT(*), 0), 2) AS conversion_rate,
        ROUND(AVG(f.conversion_delay_days), 2) AS avg_conversion_delay
    FROM fact_lead_conversion f
    LEFT JOIN dim_lead_origin o ON f.origin_key = o.origin_key
    WHERE 1 = 1 {origin_filter};
    """
)
if not kpis.empty:
    row = kpis.iloc[0]
    render_kpi_row(
        [
            {"label": "MQL", "value": int(row["mql_count"] or 0), "format": "{:,}"},
            {"label": "Deals gagnés", "value": int(row["converted_count"] or 0), "format": "{:,}"},
            {"label": "Taux conversion", "value": row["conversion_rate"], "format": "{:.2f}%"},
            {"label": "Délai conversion", "value": row["avg_conversion_delay"], "format": "{:.1f} jours"},
        ]
    )

render_section("Visualisations")
mql_by_origin = run_query(
    f"""
    SELECT
        COALESCE(o.origin, 'unknown') AS origin,
        COUNT(*) AS mql_count
    FROM fact_lead_conversion f
    LEFT JOIN dim_lead_origin o ON f.origin_key = o.origin_key
    WHERE 1 = 1 {origin_filter}
    GROUP BY COALESCE(o.origin, 'unknown')
    ORDER BY mql_count DESC;
    """
)
bar_chart(mql_by_origin, "origin", "mql_count", "MQL par origine")

if selected_origin == "Toutes" and view_exists("vw_lead_funnel"):
    lead_funnel = run_query("SELECT * FROM vw_lead_funnel;")
else:
    lead_funnel = run_query(
        f"""
        SELECT
            COALESCE(o.origin, 'unknown') AS origin,
            COUNT(*) AS mql_count,
            SUM(f.is_converted) AS converted_count,
            ROUND(100.0 * SUM(f.is_converted) / NULLIF(COUNT(*), 0), 2) AS conversion_rate_pct,
            ROUND(AVG(f.conversion_delay_days), 2) AS avg_conversion_delay_days
        FROM fact_lead_conversion f
        LEFT JOIN dim_lead_origin o ON f.origin_key = o.origin_key
        WHERE 1 = 1 {origin_filter}
        GROUP BY COALESCE(o.origin, 'unknown')
        ORDER BY mql_count DESC;
        """
    )
bar_chart(lead_funnel, "origin", "conversion_rate_pct", "Taux de conversion par origine")
bar_chart(lead_funnel, "origin", "avg_conversion_delay_days", "Délai moyen de conversion par origine")

segments = run_query(
    f"""
    SELECT
        COALESCE(s.business_segment, 'unknown') AS business_segment,
        COUNT(*) AS mql_count,
        SUM(f.is_converted) AS converted_count,
        ROUND(100.0 * SUM(f.is_converted) / NULLIF(COUNT(*), 0), 2) AS conversion_rate_pct,
        ROUND(AVG(f.declared_monthly_revenue), 2) AS avg_declared_monthly_revenue
    FROM fact_lead_conversion f
    LEFT JOIN dim_business_segment s ON f.business_segment_key = s.business_segment_key
    LEFT JOIN dim_lead_origin o ON f.origin_key = o.origin_key
    WHERE 1 = 1 {origin_filter}
    GROUP BY COALESCE(s.business_segment, 'unknown')
    HAVING COUNT(*) >= 5
    ORDER BY conversion_rate_pct DESC
    LIMIT 15;
    """
)
horizontal_bar_chart(
    segments.sort_values("conversion_rate_pct"),
    "conversion_rate_pct",
    "business_segment",
    "Taux de conversion par segment business",
)
horizontal_bar_chart(
    segments.sort_values("avg_declared_monthly_revenue"),
    "avg_declared_monthly_revenue",
    "business_segment",
    "Revenu mensuel déclaré moyen par segment",
)

sales_team = run_query(
    f"""
    SELECT
        COALESCE(t.sr_id, 'unknown') AS sr_id,
        SUM(f.is_converted) AS converted_count
    FROM fact_lead_conversion f
    LEFT JOIN dim_sales_team t ON f.sales_team_key = t.sales_team_key
    LEFT JOIN dim_lead_origin o ON f.origin_key = o.origin_key
    WHERE 1 = 1 {origin_filter}
    GROUP BY COALESCE(t.sr_id, 'unknown')
    ORDER BY converted_count DESC
    LIMIT 15;
    """
)
horizontal_bar_chart(sales_team.sort_values("converted_count"), "converted_count", "sr_id", "Deals gagnés par commercial SR")
