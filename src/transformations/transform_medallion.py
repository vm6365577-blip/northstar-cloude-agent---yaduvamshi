"""
NorthStar Retail - Medallion Lakehouse Transformation Pipeline
Transforms Bronze raw sales data into:
- Silver: Cleansed, validated, typed, and deduplicated sales (sales_enriched).
- Gold: Star schema dimensional model (fact_sales, dim_product, dim_date).
Stores output in high-performance Snappy Parquet on S3 and local lakehouse cache.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.utils.parquet_io import save_parquet, read_parquet

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("AWS_S3_BUCKET", "northstar-retail-lakehouse")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOCAL_DATA_DIR = PROJECT_ROOT / "data"
LOCAL_LAKEHOUSE = LOCAL_DATA_DIR / "lakehouse"

BRONZE_PARQUET = LOCAL_LAKEHOUSE / "bronze" / "sales_raw" / "sales_raw.parquet"
SILVER_DIR = LOCAL_LAKEHOUSE / "silver" / "sales_enriched"
GOLD_FACT_DIR = LOCAL_LAKEHOUSE / "gold" / "fact_sales"
GOLD_PROD_DIR = LOCAL_LAKEHOUSE / "gold" / "dim_product"
GOLD_DATE_DIR = LOCAL_LAKEHOUSE / "gold" / "dim_date"


def get_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)


def load_bronze_data() -> pd.DataFrame:
    """Load bronze data from local parquet cache or raw CSV source."""
    if BRONZE_PARQUET.exists():
        print(f"Loading Bronze data from: {BRONZE_PARQUET}")
        return read_parquet(BRONZE_PARQUET)

    csv_path = LOCAL_DATA_DIR / "sales.csv"
    if csv_path.exists():
        print(f"Bronze Parquet not found. Bootstrapping directly from: {csv_path}")
        return pd.read_csv(csv_path)

    raise FileNotFoundError("Neither Bronze Parquet nor raw sales.csv could be found.")


def transform_silver(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Silver Layer Transformation:
    - Trims string columns.
    - Validates mandatory fields (order_id, order_date, product_id, category, region).
    - Filters invalid rows (quantity <= 0 or unit_price < 0).
    - Computes exact revenue = quantity * unit_price.
    - Formats category and region with Title/Initcap casing.
    - Removes duplicate records.
    """
    df = df_raw.copy()

    # Drop nulls across mandatory columns
    mandatory = ["order_id", "order_date", "product_id", "product_name", "category", "quantity", "unit_price", "region"]
    df = df.dropna(subset=mandatory)

    # String sanitization & casing
    df["order_id"] = df["order_id"].astype(str).str.strip()
    df["order_date"] = pd.to_datetime(df["order_date"], format="mixed", errors="coerce").dt.date
    df["store_id"] = df["store_id"].astype(str).str.strip()
    df["product_id"] = df["product_id"].astype(str).str.strip()
    df["product_name"] = df["product_name"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip().str.title()
    df["region"] = df["region"].astype(str).str.strip().str.title()

    # Numerical type validation
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0.0).round(2)

    # Quality filters
    df = df[
        (df["order_id"] != "")
        & (df["product_id"] != "")
        & (df["product_name"] != "")
        & (df["category"] != "")
        & (df["region"] != "")
        & (df["quantity"] > 0)
        & (df["unit_price"] >= 0)
    ]

    # Revenue measure computation
    df["revenue"] = (df["quantity"] * df["unit_price"]).round(2)

    # Deduplication
    df_silver = df.drop_duplicates().reset_index(drop=True)
    return df_silver


def transform_gold_fact_sales(df_silver: pd.DataFrame) -> pd.DataFrame:
    """
    Gold Layer Fact Table:
    Star schema central fact table mapping dimensions and revenue measures.
    """
    fact = pd.DataFrame({
        "order_id": df_silver["order_id"],
        "date_key": df_silver["order_date"].astype(str),
        "store_id": df_silver["store_id"],
        "product_id": df_silver["product_id"],
        "category": df_silver["category"],
        "region": df_silver["region"],
        "quantity": df_silver["quantity"],
        "unit_price": df_silver["unit_price"],
        "revenue": df_silver["revenue"],
    })
    return fact.drop_duplicates().reset_index(drop=True)


def transform_gold_dim_product(df_silver: pd.DataFrame) -> pd.DataFrame:
    """
    Gold Layer Product Dimension:
    Unique product master catalogue.
    """
    dim_product = df_silver[["product_id", "product_name", "category"]].drop_duplicates()
    return dim_product.sort_values("product_id").reset_index(drop=True)


def transform_gold_dim_date(df_silver: pd.DataFrame) -> pd.DataFrame:
    """
    Gold Layer Date Dimension:
    Calendar date breakdown for date_key filtering.
    """
    dates = pd.to_datetime(df_silver["order_date"].unique())
    dim_date = pd.DataFrame({
        "date_key": dates.strftime("%Y-%m-%d"),
        "year": dates.year,
        "month": dates.month,
        "day": dates.day,
        "quarter": dates.quarter,
        "day_of_week": dates.day_name(),
    })
    return dim_date.sort_values("date_key").reset_index(drop=True)


def sync_to_s3(s3_client, local_file: Path, s3_key: str):
    """Sync transformed parquet file to S3."""
    if s3_client:
        try:
            s3_client.upload_file(
                str(local_file),
                BUCKET_NAME,
                s3_key,
                ExtraArgs={"ServerSideEncryption": "AES256"},
            )
            print(f"  -> Synced to s3://{BUCKET_NAME}/{s3_key}")
        except Exception as e:
            print(f"  - S3 upload note ({s3_key}): {e}")


def run_pipeline():
    print("=" * 60)
    print("NorthStar Retail - Medallion Lakehouse Transformation Pipeline")
    print("=" * 60)

    s3 = None
    try:
        s3 = get_s3_client()
        s3.head_bucket(Bucket=BUCKET_NAME)
    except Exception:
        s3 = None

    # Step 1: Load Bronze
    df_bronze = load_bronze_data()
    print(f"Bronze Raw Records: {len(df_bronze)}")

    # Step 2: Transform Silver
    df_silver = transform_silver(df_bronze)
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    silver_file = SILVER_DIR / "sales_enriched.parquet"
    save_parquet(df_silver, silver_file)
    print(f"Silver Cleaned Records: {len(df_silver)} saved to {silver_file}")
    sync_to_s3(s3, silver_file, "silver/sales_enriched/sales_enriched.parquet")

    # Step 3: Transform Gold Fact Sales
    df_fact = transform_gold_fact_sales(df_silver)
    GOLD_FACT_DIR.mkdir(parents=True, exist_ok=True)
    fact_file = GOLD_FACT_DIR / "fact_sales.parquet"
    save_parquet(df_fact, fact_file)
    print(f"Gold Fact Sales Records: {len(df_fact)} saved to {fact_file}")
    sync_to_s3(s3, fact_file, "gold/fact_sales/fact_sales.parquet")

    # Step 4: Transform Gold Dim Product
    df_prod = transform_gold_dim_product(df_silver)
    GOLD_PROD_DIR.mkdir(parents=True, exist_ok=True)
    prod_file = GOLD_PROD_DIR / "dim_product.parquet"
    save_parquet(df_prod, prod_file)
    print(f"Gold Dim Product Records: {len(df_prod)} saved to {prod_file}")
    sync_to_s3(s3, prod_file, "gold/dim_product/dim_product.parquet")

    # Step 5: Transform Gold Dim Date
    df_date = transform_gold_dim_date(df_silver)
    GOLD_DATE_DIR.mkdir(parents=True, exist_ok=True)
    date_file = GOLD_DATE_DIR / "dim_date.parquet"
    save_parquet(df_date, date_file)
    print(f"Gold Dim Date Records: {len(df_date)} saved to {date_file}")
    sync_to_s3(s3, date_file, "gold/dim_date/dim_date.parquet")

    print("\n" + "=" * 60)
    print("All Medallion Lakehouse layers generated successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
