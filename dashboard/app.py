from __future__ import annotations

import streamlit as st

from components import render_business_context, render_page_header, render_section
from db import database_exists


st.set_page_config(page_title="Olist BI", layout="wide")

render_page_header(
    "Olist E-commerce BI Pipeline",
    "Projet BI simple: sources de données, ETL, Data Warehouse SQLite et reporting Streamlit.",
)

render_business_context(
    "Olist souhaite suivre la performance commerciale, la qualité de livraison, "
    "la satisfaction client et l'efficacité de l'acquisition de vendeurs à partir "
    "de ses données opérationnelles."
)

render_section("Problématique")
st.write(
    "Comment Olist peut-elle exploiter ses données de commandes, paiements, avis clients, "
    "produits, vendeurs et leads marketing pour suivre la performance commerciale, "
    "la qualité de livraison, la satisfaction client et l'efficacité de l'acquisition "
    "de vendeurs ?"
)

render_section("Architecture décisionnelle")
st.code(
    """Sources CSV Olist
↓
ETL Python
↓
Data Warehouse SQLite
↓
Rapport BI Streamlit""",
    language="text",
)

render_section("Tables de faits")
st.markdown("- `fact_order_performance`: ventes, livraison et satisfaction au grain article de commande.")
st.markdown("- `fact_lead_conversion`: conversion marketing au grain MQL.")

render_section("Pages du rapport")
st.markdown("- Executive Overview")
st.markdown("- Sales Performance")
st.markdown("- Delivery & Satisfaction")
st.markdown("- Marketing Funnel")
st.markdown("- Data Quality")

render_section("État du Data Warehouse")
if database_exists():
    st.success("La base SQLite est disponible dans `data/warehouse/olist_dwh.sqlite`.")
else:
    st.error("Base de données introuvable. Lancez d'abord l'ETL.")
    st.code(
        "python -m src.run_etl --raw-data-dir data/raw --warehouse-path data/warehouse/olist_dwh.sqlite",
        language="bash",
    )
