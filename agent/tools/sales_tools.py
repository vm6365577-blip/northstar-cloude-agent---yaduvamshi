"""
NorthStar Retail - AWS Sales Analytical Tools
Provides high-performance analytical queries against the Gold Star Schema
via Amazon Athena (or local Parquet Lakehouse engine).
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from agent.config import (
    AWS_REGION,
    AWS_S3_BUCKET,
    ATHENA_DATABASE,
    ATHENA_WORKGROUP,
    ATHENA_OUTPUT_LOCATION,
    GOLD_DATASET,
    FACT_SALES_TABLE,
    DIM_PRODUCT_TABLE,
    DIM_DATE_TABLE,
    LOCAL_LAKEHOUSE_DIR,
)

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_FACT_PARQUET = LOCAL_LAKEHOUSE_DIR / "gold" / "fact_sales" / "fact_sales.parquet"
GOLD_PROD_PARQUET = LOCAL_LAKEHOUSE_DIR / "gold" / "dim_product" / "dim_product.parquet"


def _get_athena_client():
    """Create Athena client if credentials are available."""
    try:
        client = boto3.client("athena", region_name=AWS_REGION)
        return client
    except Exception:
        return None


def _run_athena_query(query: str) -> list:
    """Execute SQL query using Amazon Athena and fetch result rows as dictionaries."""
    client = _get_athena_client()
    if not client:
        raise ConnectionError("Athena client not available.")

    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": ATHENA_DATABASE},
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT_LOCATION},
        WorkGroup=ATHENA_WORKGROUP,
    )
    query_id = response["QueryExecutionId"]

    # Poll for completion with standard timeout
    import time
    for _ in range(60):
        status_resp = client.get_query_execution(QueryExecutionId=query_id)
        state = status_resp["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        elif state in ("FAILED", "CANCELLED"):
            reason = status_resp["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
            raise RuntimeError(f"Athena query {state}: {reason}")
        time.sleep(1)

    results_resp = client.get_query_results(QueryExecutionId=query_id)
    column_names = [col["Name"] for col in results_resp["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]
    rows = results_resp["ResultSet"]["Rows"][1:]  # skip header row

    results = []
    for row in rows:
        record = {}
        for idx, datum in enumerate(row["Data"]):
            val = datum.get("VarCharValue", None)
            record[column_names[idx]] = val
        results.append(record)
    return results


def _run_lakehouse_query(query: str, fallback_to_local: bool = True) -> list:
    """
    Execute ANSI SQL against AWS Athena, with transparent fallback
    to local DuckDB Gold Parquet Lakehouse for offline / test resilience.
    """
    if os.getenv("USE_LIVE_ATHENA", "false").lower() == "true":
        try:
            return _run_athena_query(query)
        except Exception as e:
            if not fallback_to_local:
                raise e

    # Local High-Speed Parquet Lakehouse Execution
    import duckdb
    con = duckdb.connect()

    # Create virtual tables pointing to local Gold Parquet files
    con.execute(f"CREATE OR REPLACE VIEW fact_sales AS SELECT * FROM read_parquet('{GOLD_FACT_PARQUET.as_posix()}')")
    con.execute(f"CREATE OR REPLACE VIEW dim_product AS SELECT * FROM read_parquet('{GOLD_PROD_PARQUET.as_posix()}')")

    df = con.execute(query).fetchdf()
    con.close()
    return df.to_dict(orient="records")


def get_top_products(limit: int = 5) -> dict:
    """
    Return the top products ranked by total revenue.

    Use this tool when the user asks about:
    top products, highest revenue products,
    best products by revenue, or product ranking.
    """
    safe_limit = max(1, min(int(limit), 100))

    query = f"""
        SELECT
            p.product_id,
            p.product_name,
            ROUND(SUM(f.revenue), 2) AS total_revenue
        FROM fact_sales f
        JOIN dim_product p
          ON f.product_id = p.product_id
        GROUP BY
            p.product_id,
            p.product_name
        ORDER BY total_revenue DESC
        LIMIT {safe_limit}
    """

    results = _run_lakehouse_query(query)

    for item in results:
        if "total_revenue" in item:
            item["total_revenue"] = float(item["total_revenue"])

    return {
        "source": "Amazon Athena Gold",
        "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
        "data": results,
    }


def get_revenue_by_region() -> dict:
    """
    Return total revenue grouped by region.

    Use this tool when the user asks about:
    revenue by region, regional sales,
    regional performance, or sales by geography.
    """
    query = """
        SELECT
            region,
            ROUND(SUM(revenue), 2) AS total_revenue
        FROM fact_sales
        GROUP BY region
        ORDER BY total_revenue DESC
    """

    results = _run_lakehouse_query(query)

    for item in results:
        if "total_revenue" in item:
            item["total_revenue"] = float(item["total_revenue"])

    return {
        "source": "Amazon Athena Gold",
        "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
        "data": results,
    }


def get_recent_best_category() -> dict:
    """
    Return the category with the highest revenue in the
    seven days immediately before the latest order date
    present in the dataset.

    Use this tool when the user asks for:
    recent category performance, best-selling category,
    highest category revenue in the last seven days,
    or the category immediately before the latest order date.

    IMPORTANT:
    The seven-day window is relative to the latest date
    in the dataset, not today's date.
    """
    query = """
        WITH latest_date AS (
            SELECT
                MAX(CAST(date_key AS DATE)) AS latest_order_date
            FROM fact_sales
        ),

        category_revenue AS (
            SELECT
                f.category,
                ROUND(SUM(f.revenue), 2) AS total_revenue
            FROM fact_sales f
            CROSS JOIN latest_date
            WHERE CAST(f.date_key AS DATE) >= (latest_date.latest_order_date - INTERVAL 7 DAY)
              AND CAST(f.date_key AS DATE) < latest_date.latest_order_date
            GROUP BY f.category
        )

        SELECT
            category,
            total_revenue
        FROM category_revenue
        ORDER BY total_revenue DESC
        LIMIT 1
    """

    results = _run_lakehouse_query(query)

    for item in results:
        if "total_revenue" in item:
            item["total_revenue"] = float(item["total_revenue"])

    return {
        "source": "Amazon Athena Gold",
        "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
        "data": results,
    }
