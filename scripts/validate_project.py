from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_PATH = ROOT / "data" / "warehouse" / "olist_dwh.sqlite"

REQUIRED_MODULES = [
    "dashboard.db",
    "dashboard.components",
    "dashboard.charts",
]

REQUIRED_TABLES = [
    "fact_order_performance",
    "fact_lead_conversion",
    "dim_date",
    "dim_customer",
    "dim_seller",
    "dim_product",
    "dim_product_category",
    "dim_payment_type",
    "dim_order_status",
    "etl_quality_report",
]

REQUIRED_VIEWS = [
    "vw_sales_monthly",
    "vw_category_performance",
    "vw_lead_funnel",
]


def check_imports() -> list[str]:
    errors = []
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "dashboard"))
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            errors.append(f"Import failed: {module_name} ({exc})")
    return errors


def check_sqlite_objects() -> list[str]:
    if not WAREHOUSE_PATH.exists():
        return [f"Warehouse not found: {WAREHOUSE_PATH}"]

    errors = []
    with sqlite3.connect(WAREHOUSE_PATH) as conn:
        existing_tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        existing_views = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'view'")
        }

    for table in REQUIRED_TABLES:
        if table not in existing_tables:
            errors.append(f"Missing table: {table}")
    for view in REQUIRED_VIEWS:
        if view not in existing_views:
            errors.append(f"Missing view: {view}")
    return errors


def main() -> int:
    errors = check_imports() + check_sqlite_objects()
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Validation succeeded.")
    print(f"Warehouse: {WAREHOUSE_PATH}")
    print(f"Tables checked: {len(REQUIRED_TABLES)}")
    print(f"Views checked: {len(REQUIRED_VIEWS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
