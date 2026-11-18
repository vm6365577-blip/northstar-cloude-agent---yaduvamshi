"""
NorthStar Retail - Mock Ingestion Simulator (AWS S3 & Athena Lakehouse)
Runs the complete ingestion pipeline locally without live AWS credentials.
"""

import os
import sys
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mock.mock_policy_tools import _load_mock_documents

DATA_DIR = PROJECT_ROOT / "data"
SALES_PATH = DATA_DIR / "sales.csv"
DOCS_DIR = DATA_DIR / "product_docs"


def run_mock_s3_provisioning(bucket_name: str = "northstar-retail-lakehouse", region: str = "us-east-1"):
    print("=" * 60)
    print("MOCK AWS PROVISIONING: Amazon S3 Bucket")
    print("=" * 60)
    print(f"[MOCK] Simulated Bucket Provisioning: s3://{bucket_name}")
    print(f"[MOCK] Region: {region}")
    print("[MOCK] Encryption: AES256 (SSE-S3)")
    print("[MOCK] Block Public Access: Enabled")
    print("[MOCK] Provisioning status: SUCCESS (Simulated)\n")


def run_mock_s3_upload(bucket_name: str = "northstar-retail-lakehouse"):
    print("=" * 60)
    print("MOCK AWS INGESTION: Local to Amazon S3 Staging")
    print("=" * 60)
    count = 0
    for file_path in DATA_DIR.rglob("*"):
        if not file_path.is_file() or file_path.name.startswith(".") or "lakehouse" in file_path.parts:
            continue
        rel = file_path.relative_to(DATA_DIR)
        s3_dest = f"s3://{bucket_name}/raw/{rel.as_posix()}"
        print(f"  [MOCK UPLOAD] {file_path.name} -> {s3_dest}")
        count += 1
    print(f"[MOCK] Total files staged to Amazon S3: {count}\n")


def run_mock_athena_sales_load(database: str = "northstar_lakehouse"):
    print("=" * 60)
    print("MOCK ATHENA / LAKEHOUSE INGESTION: Bronze Sales Raw Table")
    print("=" * 60)
    target_table = f"{database}.sales_raw"
    with open(SALES_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = sum(1 for _ in reader)
    print(f"[MOCK] Target Table: {target_table}")
    print(f"[MOCK] Schema: {header}")
    print(f"[MOCK] Rows Loaded: {rows} records\n")


def run_mock_athena_docs_load(database: str = "northstar_lakehouse"):
    print("=" * 60)
    print("MOCK ATHENA / LAKEHOUSE INGESTION: Gold Product Documents Store")
    print("=" * 60)
    target_table = f"{database}.product_documents"
    docs = _load_mock_documents()
    for d in docs:
        print(f"  [MOCK EXTRACT & INDEX] {d['source_name']} ({d['document_type']}) - {len(d['content'])} characters")
    print(f"[MOCK] Total Documents Indexed into {target_table}: {len(docs)}\n")


def main():
    print("######################################################################")
    print("  NORTHSTAR RETAIL - END-TO-END MOCK PIPELINE EXECUTION (AWS)")
    print("######################################################################\n")
    run_mock_s3_provisioning()
    run_mock_s3_upload()
    run_mock_athena_sales_load()
    run_mock_athena_docs_load()
    print("All mock ingestion steps executed successfully without live AWS credentials.")


if __name__ == "__main__":
    main()
