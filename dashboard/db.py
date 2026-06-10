from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


WAREHOUSE_PATH = Path(__file__).resolve().parents[1] / "data" / "warehouse" / "olist_dwh.sqlite"


def database_exists() -> bool:
    return WAREHOUSE_PATH.exists()


def get_connection() -> sqlite3.Connection | None:
    if not database_exists():
        st.error("Base de données introuvable. Lancez d'abord l'ETL.")
        return None
    return sqlite3.connect(WAREHOUSE_PATH)


def sql_escape(value: str) -> str:
    return value.replace("'", "''")


def _object_exists(name: str, object_type: str) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        result = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = ? AND name = ? LIMIT 1",
            (object_type, name),
        ).fetchone()
        return result is not None
    except sqlite3.Error as exc:
        st.warning(f"Vérification impossible pour {name}: {exc}")
        return False
    finally:
        conn.close()


def table_exists(table_name: str) -> bool:
    return _object_exists(table_name, "table")


def view_exists(view_name: str) -> bool:
    return _object_exists(view_name, "view")


@st.cache_data(show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        return pd.read_sql_query(sql, conn)
    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        st.warning(f"Données indisponibles pour cette analyse: {exc}")
        return pd.DataFrame()
    finally:
        conn.close()


def load_table(table_name: str) -> pd.DataFrame:
    if not table_exists(table_name):
        st.warning(f"La table `{table_name}` est absente du Data Warehouse.")
        return pd.DataFrame()
    return run_query(f'SELECT * FROM "{table_name}"')
