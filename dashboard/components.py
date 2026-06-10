from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render_page_header(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def render_business_context(text: str) -> None:
    st.info(text)


def render_questions(questions: list[str]) -> None:
    st.markdown("**Questions traitées**")
    for question in questions:
        st.markdown(f"- {question}")


def _format_value(value: Any, value_format: str | None = None) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    if value_format:
        try:
            return value_format.format(value)
        except (ValueError, TypeError):
            return str(value)
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def render_kpi_row(kpis: list[dict]) -> None:
    if not kpis:
        render_empty_state("Aucun indicateur disponible.")
        return
    columns = st.columns(min(len(kpis), 4))
    for index, kpi in enumerate(kpis):
        with columns[index % len(columns)]:
            st.metric(
                kpi.get("label", "Indicateur"),
                _format_value(kpi.get("value"), kpi.get("format")),
                delta=kpi.get("delta"),
            )


def render_section(title: str) -> None:
    st.divider()
    st.subheader(title)


def render_empty_state(message: str) -> None:
    st.info(message)


def render_data_warning(message: str) -> None:
    st.warning(message)
