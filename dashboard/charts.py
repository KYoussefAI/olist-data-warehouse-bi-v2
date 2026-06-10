from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components import render_empty_state


def _can_plot(df: pd.DataFrame, columns: list[str]) -> bool:
    if df.empty:
        render_empty_state("Aucune donnée disponible pour cette visualisation.")
        return False
    missing = [column for column in columns if column and column not in df.columns]
    if missing:
        render_empty_state(f"Colonnes manquantes : {', '.join(missing)}")
        return False
    return True


def line_chart(df: pd.DataFrame, x: str, y: str, title: str, markers: bool = True):
    if not _can_plot(df, [x, y]):
        return None
    fig = px.line(df, x=x, y=y, markers=markers, title=title)
    st.plotly_chart(fig, use_container_width=True)
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str):
    if not _can_plot(df, [x, y]):
        return None
    fig = px.bar(df, x=x, y=y, title=title)
    st.plotly_chart(fig, use_container_width=True)
    return fig


def horizontal_bar_chart(df: pd.DataFrame, x: str, y: str, title: str):
    if not _can_plot(df, [x, y]):
        return None
    fig = px.bar(df, x=x, y=y, orientation="h", title=title)
    st.plotly_chart(fig, use_container_width=True)
    return fig


def pie_chart(df: pd.DataFrame, names: str, values: str, title: str):
    if not _can_plot(df, [names, values]):
        return None
    fig = px.pie(df, names=names, values=values, title=title)
    st.plotly_chart(fig, use_container_width=True)
    return fig


def histogram(df: pd.DataFrame, x: str, title: str):
    if not _can_plot(df, [x]):
        return None
    fig = px.histogram(df, x=x, title=title)
    st.plotly_chart(fig, use_container_width=True)
    return fig


def scatter_chart(df: pd.DataFrame, x: str, y: str, title: str, color: str | None = None):
    columns = [x, y] + ([color] if color else [])
    if not _can_plot(df, columns):
        return None
    fig = px.scatter(df, x=x, y=y, color=color, title=title)
    st.plotly_chart(fig, use_container_width=True)
    return fig
