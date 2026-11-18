import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# AWS & REGION CONFIGURATION
# ============================================================

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "northstar-retail-lakehouse")

# ============================================================
# ATHENA / REDSHIFT DATA LAKEHOUSE CONFIGURATION
# ============================================================

ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "northstar_lakehouse")
ATHENA_WORKGROUP = os.getenv("ATHENA_WORKGROUP", "primary")
ATHENA_OUTPUT_LOCATION = os.getenv(
    "ATHENA_OUTPUT_LOCATION",
    f"s3://{AWS_S3_BUCKET}/athena-results/"
)

# Medallion Layers
BRONZE_DATASET = os.getenv("BRONZE_DATASET", "bronze")
SILVER_DATASET = os.getenv("SILVER_DATASET", "silver")
GOLD_DATASET = os.getenv("GOLD_DATASET", "gold")

# Gold Tables
FACT_SALES_TABLE = os.getenv("FACT_SALES_TABLE", "fact_sales")
DIM_PRODUCT_TABLE = os.getenv("DIM_PRODUCT_TABLE", "dim_product")
DIM_DATE_TABLE = os.getenv("DIM_DATE_TABLE", "dim_date")
DOCUMENT_TABLE = os.getenv("DOCUMENT_TABLE", "product_documents")

# ============================================================
# AMAZON BEDROCK CONFIGURATION
# ============================================================

AWS_BEDROCK_MODEL_ID = os.getenv(
    "AWS_BEDROCK_MODEL_ID",
    "anthropic.claude-3-5-sonnet-20241022-v2:0"
)

AWS_EMBEDDING_MODEL_ID = os.getenv(
    "AWS_EMBEDDING_MODEL_ID",
    "amazon.titan-embed-text-v2:0"
)

# Local data cache paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DATA_DIR = PROJECT_ROOT / "data"
LOCAL_LAKEHOUSE_DIR = PROJECT_ROOT / "data" / "lakehouse"
