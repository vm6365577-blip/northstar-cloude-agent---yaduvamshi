"""
NorthStar Retail - Policy Documents Lakehouse Ingestion & Parsing
Extracts unstructured text from PDF, JSON, CSV, and TXT policy files,
indexes metadata, and loads them into the Gold Policy Document Store (S3 & Parquet).
"""

import os
import sys
import io
import csv
import json
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from pypdf import PdfReader
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.utils.parquet_io import save_parquet

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("AWS_S3_BUCKET", "northstar-retail-lakehouse")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOCAL_DOCS_DIR = PROJECT_ROOT / "data" / "product_docs"
LOCAL_LAKEHOUSE_GOLD = PROJECT_ROOT / "data" / "lakehouse" / "gold" / "product_documents"


def get_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)


# ============================================================
# MULTI-FORMAT EXTRACTION LOGIC
# ============================================================

def extract_pdf(content: bytes) -> str:
    """Extract clean text from PDF bytes."""
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def extract_json(content: bytes) -> str:
    """Extract formatted text representation from JSON bytes."""
    data = json.loads(content.decode("utf-8"))
    return json.dumps(data, indent=2, ensure_ascii=False)


def extract_txt(content: bytes) -> str:
    """Extract UTF-8 text from raw bytes."""
    return content.decode("utf-8", errors="replace")


def extract_csv(content: bytes) -> str:
    """Convert tabular CSV rows into pipe-delimited searchable text."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = []
    for row in reader:
        rows.append(" | ".join(row))
    return "\n".join(rows)


def extract_document(file_name: str, content: bytes) -> str:
    """Route document to format-specific text extractor."""
    ext = file_name.lower().split(".")[-1]
    if ext == "pdf":
        return extract_pdf(content)
    elif ext == "json":
        return extract_json(content)
    elif ext == "txt":
        return extract_txt(content)
    elif ext == "csv":
        return extract_csv(content)
    else:
        print(f"Skipping unsupported format: {file_name}")
        return ""


# ============================================================
# DOCUMENT HARVESTING (S3 & LOCAL FALLBACK)
# ============================================================

def read_documents_from_s3(s3_client) -> list:
    """Read and extract all policy documents stored under S3 raw/product_docs/."""
    prefix = "raw/product_docs/"
    documents = []

    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        objects = response.get("Contents", [])

        for obj in objects:
            key = obj["Key"]
            if key.endswith("/"):
                continue

            print(f"Downloading & Parsing: s3://{BUCKET_NAME}/{key}")
            resp = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            content = resp["Body"].read()

            text = extract_document(key, content)
            if not text.strip():
                continue

            file_name = key.split("/")[-1]
            documents.append({
                "source_name": file_name,
                "s3_uri": f"s3://{BUCKET_NAME}/{key}",
                "document_type": file_name.split(".")[-1].lower(),
                "content": text.strip(),
            })
    except Exception as e:
        print(f"S3 reading encountered error: {e}")

    return documents


def read_documents_locally() -> list:
    """Fallback reader that harvests directly from local data/product_docs/."""
    documents = []
    if not LOCAL_DOCS_DIR.exists():
        print(f"Local document folder not found: {LOCAL_DOCS_DIR}")
        return documents

    for file_path in LOCAL_DOCS_DIR.iterdir():
        if file_path.is_file() and not file_path.name.startswith("."):
            print(f"Parsing local file: {file_path.name}")
            content = file_path.read_bytes()
            text = extract_document(file_path.name, content)
            if not text.strip():
                continue

            documents.append({
                "source_name": file_path.name,
                "s3_uri": f"s3://{BUCKET_NAME}/raw/product_docs/{file_path.name}",
                "document_type": file_path.suffix.lstrip(".").lower(),
                "content": text.strip(),
            })

    return documents


def stage_gold_documents(documents: list, s3_client=None):
    """Save extracted documents to Parquet & JSON in the Gold Lakehouse layer."""
    if not documents:
        print("No documents found to stage.")
        return

    LOCAL_LAKEHOUSE_GOLD.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(documents)

    # Save to Gold Parquet
    parquet_path = LOCAL_LAKEHOUSE_GOLD / "product_documents.parquet"
    save_parquet(df, parquet_path)
    print(f"Saved Gold Documents Parquet: {parquet_path} ({len(df)} documents)")

    # Save to Gold JSON index for ultra-fast local loading
    json_path = LOCAL_LAKEHOUSE_GOLD / "product_documents.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    print(f"Saved Gold Documents JSON index: {json_path}")

    if s3_client:
        try:
            s3_key = "gold/product_documents/product_documents.parquet"
            s3_client.upload_file(
                str(parquet_path),
                BUCKET_NAME,
                s3_key,
                ExtraArgs={"ServerSideEncryption": "AES256"},
            )
            print(f"Synced to S3 Gold layer: s3://{BUCKET_NAME}/{s3_key}")
        except Exception as e:
            print(f"Note: S3 sync skipped or encountered warning: {e}")


def main():
    print("=" * 60)
    print("NorthStar Retail - Gold Policy Documents Lakehouse Ingestion")
    print("=" * 60)

    s3 = None
    try:
        s3 = get_s3_client()
        s3.head_bucket(Bucket=BUCKET_NAME)
        docs = read_documents_from_s3(s3)
        if not docs:
            print("No documents on S3 yet, reading from local data folder...")
            docs = read_documents_locally()
    except Exception:
        print("Reading directly from local data/product_docs directory...")
        docs = read_documents_locally()

    stage_gold_documents(docs, s3)
    print(f"\nCompleted Gold documents ingestion ({len(docs)} documents indexed).")


if __name__ == "__main__":
    main()
