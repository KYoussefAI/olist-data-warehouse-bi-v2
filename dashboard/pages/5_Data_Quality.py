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
from db import load_table, run_query, table_exists


st.set_page_config(page_title="Data Quality", layout="wide")


def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def add_numeric_value(df):
    out = df.copy()
    out["value_num"] = out["value"].apply(to_number)
    return out


if not table_exists("etl_quality_report"):
    render_data_warning("La table `etl_quality_report` est absente. Relancez l'ETL.")
    st.stop()

render_page_header("Data Quality", "Contrôle de qualité et limites des données.")

render_section("Objectif métier")
render_business_context(
    "Cette page permet d'interpréter les indicateurs avec prudence. "
    "Un dashboard BI fiable doit toujours montrer les limites des données."
)

render_section("Questions traitées")
render_questions(
    [
        "Les sources attendues sont-elles chargées ?",
        "Existe-t-il des problèmes de relations entre tables ?",
        "Observe-t-on des doublons sur les identifiants clés ?",
        "Quelles valeurs manquantes peuvent limiter l'interprétation ?",
    ]
)

quality = load_table("etl_quality_report")

render_section("Indicateurs principaux")
total_checks = len(quality)
areas_count = quality["area"].nunique() if "area" in quality.columns else 0
if not quality.empty and {"area", "value"}.issubset(quality.columns):
    relationship_values = quality.loc[quality["area"].eq("relationships"), "value"]
    relationship_issues = sum(to_number(value) for value in relationship_values)
else:
    relationship_issues = 0
missing_checks = len(quality[quality["area"].eq("missing")]) if "area" in quality.columns else 0
render_kpi_row(
    [
        {"label": "Contrôles", "value": total_checks, "format": "{:,}"},
        {"label": "Domaines", "value": areas_count, "format": "{:,}"},
        {"label": "Issues relation", "value": relationship_issues, "format": "{:,.0f}"},
        {"label": "Contrôles missing", "value": missing_checks, "format": "{:,}"},
    ]
)

render_section("Visualisations")
if not quality.empty and {"area", "check_name", "value"}.issubset(quality.columns):
    by_area = quality.groupby("area", as_index=False).size().rename(columns={"size": "checks_count"})
    bar_chart(by_area, "area", "checks_count", "Nombre de contrôles par domaine")

    raw_rows = add_numeric_value(quality[quality["area"].eq("raw_rows")])
    horizontal_bar_chart(raw_rows.sort_values("value_num"), "value_num", "check_name", "Lignes par source brute")

    dimensional_rows = add_numeric_value(quality[quality["area"].isin(["dimension_rows", "fact_rows"])])
    horizontal_bar_chart(
        dimensional_rows.sort_values("value_num"),
        "value_num",
        "check_name",
        "Lignes par dimensions et faits",
    )

    relationship = add_numeric_value(quality[quality["area"].eq("relationships")])
    horizontal_bar_chart(relationship.sort_values("value_num"), "value_num", "check_name", "Problèmes de relations")

    duplicates = add_numeric_value(quality[quality["area"].eq("duplicates")])
    horizontal_bar_chart(duplicates.sort_values("value_num"), "value_num", "check_name", "Doublons détectés")

    missing = add_numeric_value(quality[quality["area"].eq("missing")])
    horizontal_bar_chart(missing.sort_values("value_num"), "value_num", "check_name", "Valeurs manquantes")

render_section("Table de contrôle ETL")
st.dataframe(quality, use_container_width=True)

render_section("Contrôles SQL complémentaires")
sql_checks = run_query(
    """
    SELECT 'orders_without_payment' AS check_name, COUNT(*) AS value
    FROM (
        SELECT DISTINCT order_id FROM fact_order_performance
        WHERE payment_value_total IS NULL
    )
    UNION ALL
    SELECT 'orders_without_review', COUNT(*)
    FROM (
        SELECT DISTINCT order_id FROM fact_order_performance
        WHERE review_count IS NULL
    )
    UNION ALL
    SELECT 'products_without_category', COUNT(*)
    FROM dim_product
    WHERE category_key IS NULL
    UNION ALL
    SELECT 'converted_leads_without_seller_key', COUNT(*)
    FROM fact_lead_conversion
    WHERE is_converted = 1 AND seller_key IS NULL;
    """
)
st.dataframe(sql_checks, use_container_width=True)
