"""
NorthStar Retail - Bronze Sales Lakehouse Loader
Loads raw transactional sales CSV from S3 raw/ into the Bronze Lakehouse layer,
preserving raw audit trail and generating Bronze metadata.
"""

import os
import sys
import io
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
LOCAL_SALES_PATH = PROJECT_ROOT / "data" / "sales.csv"
LOCAL_LAKEHOUSE_BRONZE = PROJECT_ROOT / "data" / "lakehouse" / "bronze" / "sales_raw"


def get_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)


def load_raw_sales_dataframe(s3_client=None) -> pd.DataFrame:
    """Read raw sales CSV either from S3 or local data fallback."""
    if s3_client:
        try:
            print(f"Fetching s3://{BUCKET_NAME}/raw/sales.csv...")
            obj = s3_client.get_object(Bucket=BUCKET_NAME, Key="raw/sales.csv")
            return pd.read_csv(io.BytesIO(obj["Body"].read()))
        except Exception as e:
            print(f"Could not read from S3 ({e}), attempting local fallback...")

    if LOCAL_SALES_PATH.exists():
        print(f"Loading local source: {LOCAL_SALES_PATH}")
        return pd.read_csv(LOCAL_SALES_PATH)

    raise FileNotFoundError("Could not find sales.csv on S3 or locally.")


def stage_bronze_sales(df: pd.DataFrame, s3_client=None):
    """
    Stage raw sales into the Bronze Lakehouse layer.
    Saves locally and syncs to s3://<bucket>/bronze/sales_raw/sales_raw.parquet
    """
    LOCAL_LAKEHOUSE_BRONZE.mkdir(parents=True, exist_ok=True)
    local_parquet = LOCAL_LAKEHOUSE_BRONZE / "sales_raw.parquet"

    # Save to high-performance Parquet format using safe engine
    save_parquet(df, local_parquet)
    print(f"Saved Bronze Parquet locally: {local_parquet} ({len(df)} rows)")

    if s3_client:
        try:
            s3_key = "bronze/sales_raw/sales_raw.parquet"
            s3_client.upload_file(
                str(local_parquet),
                BUCKET_NAME,
                s3_key,
                ExtraArgs={"ServerSideEncryption": "AES256"},
            )
            print(f"Synced to S3 Bronze layer: s3://{BUCKET_NAME}/{s3_key}")
        except Exception as e:
            print(f"Note: S3 sync skipped or encountered warning: {e}")


def main():
    print("=" * 60)
    print("NorthStar Retail - Bronze Layer Lakehouse Ingestion")
    print("=" * 60)

    s3 = None
    try:
        s3 = get_s3_client()
        # Verify credentials
        s3.head_bucket(Bucket=BUCKET_NAME)
    except (NoCredentialsError, ClientError) as e:
        print(f"[INFO] AWS live connection not active ({e}). Operating in local lakehouse mode.")
        s3 = None

    df = load_raw_sales_dataframe(s3)
    stage_bronze_sales(df, s3)
    print("\nBronze sales ingestion completed successfully.")


if __name__ == "__main__":
    main()
