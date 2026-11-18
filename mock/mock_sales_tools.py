"""
Mock implementation of AWS Athena Gold sales analytical tools.
Allows end-to-end execution without live AWS credentials by querying local lakehouse data.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sales.csv"


def _parse_date(date_str: str):
    """Parse date handling mixed dash and slash formats."""
    clean_str = date_str.strip().replace("/", "-")
    return datetime.strptime(clean_str, "%Y-%m-%d").date()


def _load_sales_records() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        return []

    records = []
    with open(DATA_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                qty = float(row.get("quantity", 0) or 0)
                price = float(row.get("unit_price", 0) or 0)
                order_date = _parse_date(row.get("order_date", ""))
                records.append({
                    "order_id": row.get("order_id", "").strip(),
                    "order_date": order_date,
                    "store_id": row.get("store_id", "").strip(),
                    "product_id": row.get("product_id", "").strip(),
                    "product_name": row.get("product_name", "").strip(),
                    "category": row.get("category", "").strip().title(),
                    "quantity": int(qty),
                    "unit_price": price,
                    "region": row.get("region", "").strip().title(),
                    "revenue": qty * price,
                })
            except Exception:
                continue
    return records


def get_mock_top_products(limit: int = 5) -> dict:
    """Mock implementation of get_top_products tool."""
    records = _load_sales_records()
    product_rev: Dict[str, Dict[str, Any]] = {}
    for r in records:
        pid = r["product_id"]
        if pid not in product_rev:
            product_rev[pid] = {
                "product_id": pid,
                "product_name": r["product_name"],
                "total_revenue": 0.0,
            }
        product_rev[pid]["total_revenue"] += r["revenue"]

    sorted_products = sorted(
        product_rev.values(),
        key=lambda x: x["total_revenue"],
        reverse=True
    )[:limit]

    for p in sorted_products:
        p["total_revenue"] = round(p["total_revenue"], 2)

    return {
        "source": "Mock Amazon Athena Gold (S3 Lakehouse)",
        "table": "gold.fact_sales",
        "data": sorted_products,
    }


def get_mock_revenue_by_region() -> dict:
    """Mock implementation of get_revenue_by_region tool."""
    records = _load_sales_records()
    region_rev: Dict[str, float] = {}
    for r in records:
        reg = r["region"]
        region_rev[reg] = region_rev.get(reg, 0.0) + r["revenue"]

    sorted_regions = [
        {"region": reg, "total_revenue": round(rev, 2)}
        for reg, rev in sorted(region_rev.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "source": "Mock Amazon Athena Gold (S3 Lakehouse)",
        "table": "gold.fact_sales",
        "data": sorted_regions,
    }


def get_mock_recent_best_category() -> dict:
    """Mock implementation of get_recent_best_category tool."""
    records = _load_sales_records()
    if not records:
        return {
            "source": "Mock Amazon Athena Gold (S3 Lakehouse)",
            "table": "gold.fact_sales",
            "data": [],
        }

    latest_date = max(r["order_date"] for r in records)
    start_date = latest_date - timedelta(days=7)

    cat_rev: Dict[str, float] = {}
    for r in records:
        if start_date <= r["order_date"] < latest_date:
            cat = r["category"]
            cat_rev[cat] = cat_rev.get(cat, 0.0) + r["revenue"]

    if not cat_rev:
        return {
            "source": "Mock Amazon Athena Gold (S3 Lakehouse)",
            "table": "gold.fact_sales",
            "data": [],
        }

    top_cat, rev = max(cat_rev.items(), key=lambda x: x[1])
    return {
        "source": "Mock Amazon Athena Gold (S3 Lakehouse)",
        "table": "gold.fact_sales",
        "data": [{"category": top_cat, "total_revenue": round(rev, 2)}],
    }
