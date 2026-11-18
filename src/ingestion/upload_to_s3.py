"""
NorthStar Retail - S3 Raw Data Upload Pipeline
Uploads local transactional sales CSV and multi-format policy documents
into Amazon S3 under the 'raw/' prefix, preserving directory structure.
"""

import os
import sys
import mimetypes
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("AWS_S3_BUCKET", "northstar-retail-lakehouse")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def get_s3_client():
    """Create a configured Boto3 S3 client."""
    return boto3.client("s3", region_name=AWS_REGION)


def upload_file_to_s3(s3_client, local_path: Path, bucket: str, s3_key: str):
    """Upload a single file to S3 with content-type detection."""
    content_type, _ = mimetypes.guess_type(str(local_path))
    content_type = content_type or "application/octet-stream"

    file_size_kb = local_path.stat().st_size / 1024.0

    extra_args = {
        "ContentType": content_type,
        "ServerSideEncryption": "AES256",
    }

    s3_client.upload_file(
        str(local_path),
        bucket,
        s3_key,
        ExtraArgs=extra_args,
    )
    print(f"Uploaded: {local_path.name} ({file_size_kb:.1f} KB)")
    print(f"       -> s3://{bucket}/{s3_key}")


def upload_all_raw_data(s3_client, bucket: str):
    """Recursively upload files from data/ into s3://<bucket>/raw/."""
    if not DATA_DIR.exists():
        print(f"Error: Data directory not found at {DATA_DIR}")
        return 0

    count = 0
    for file_path in DATA_DIR.rglob("*"):
        if not file_path.is_file():
            continue
        # Skip hidden files or lakehouse output if generated locally
        if file_path.name.startswith(".") or "lakehouse" in file_path.parts:
            continue

        relative_path = file_path.relative_to(DATA_DIR)
        s3_key = f"raw/{relative_path.as_posix()}"

        upload_file_to_s3(s3_client, file_path, bucket, s3_key)
        count += 1

    return count


def main():
    print("=" * 60)
    print("NorthStar Retail - S3 Raw Data Upload")
    print("=" * 60)
    print(f"Target Bucket: s3://{BUCKET_NAME}")
    print(f"Source Folder: {DATA_DIR}")

    try:
        s3 = get_s3_client()
        uploaded_count = upload_all_raw_data(s3, BUCKET_NAME)
        print("\n" + "=" * 60)
        print(f"Upload completed successfully. {uploaded_count} files stored in s3://{BUCKET_NAME}/raw/")
        print("=" * 60)
    except NoCredentialsError:
        print("\n[WARNING] AWS credentials not found.")
        print("Please configure AWS CLI via 'aws configure' or set AWS_ACCESS_KEY_ID in .env.")
        sys.exit(1)
    except ClientError as e:
        print(f"\n[ERROR] AWS ClientError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
