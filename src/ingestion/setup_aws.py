"""
NorthStar Retail - AWS Infrastructure Setup
Provisions Amazon S3 Lakehouse Bucket, enables encryption,
enforces Block Public Access, and creates Medallion folder prefixes.
"""

import os
import sys
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("AWS_S3_BUCKET", "northstar-retail-lakehouse")

REQUIRED_PREFIXES = [
    "raw/",
    "raw/product_docs/",
    "bronze/sales_raw/",
    "silver/sales_enriched/",
    "gold/fact_sales/",
    "gold/dim_product/",
    "gold/dim_date/",
    "gold/product_documents/",
    "athena-results/",
]


def get_s3_client():
    """Create a configured Boto3 S3 client."""
    return boto3.client("s3", region_name=AWS_REGION)


def create_bucket_if_not_exists(s3_client, bucket_name: str, region: str):
    """
    Create S3 bucket if not exists, handling us-east-1 constraint rules.
    Enforces server-side encryption and blocks public access.
    """
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket already exists and is accessible: s3://{bucket_name}")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchBucket"):
            print(f"Creating S3 Bucket: s3://{bucket_name} in {region}...")
            if region == "us-east-1":
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
            print(f"Successfully created bucket: s3://{bucket_name}")
        elif error_code == "403":
            print(f"Access forbidden: Bucket s3://{bucket_name} exists but owned by another account or lacks permissions.")
            return False
        else:
            print(f"AWS Error checking bucket: {e}")
            return False

    # Apply Default Server-Side Encryption (SSE-S3 / AES256)
    try:
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            },
        )
        print("Enabled default SSE-S3 encryption.")
    except Exception as e:
        print(f"Note on encryption setting: {e}")

    # Enforce Block Public Access
    try:
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        print("Enforced Block Public Access.")
    except Exception as e:
        print(f"Note on public access block: {e}")

    return True


def provision_lakehouse_prefixes(s3_client, bucket_name: str):
    """Create placeholder zero-byte keys to establish folder hierarchy."""
    print("Provisioning Medallion Lakehouse prefixes...")
    for prefix in REQUIRED_PREFIXES:
        try:
            s3_client.put_object(Bucket=bucket_name, Key=prefix, Body=b"")
            print(f"  + s3://{bucket_name}/{prefix}")
        except Exception as e:
            print(f"  - Warning for {prefix}: {e}")


def main():
    print("=" * 60)
    print("NorthStar Retail - AWS S3 Lakehouse Provisioning")
    print("=" * 60)
    print(f"Region: {AWS_REGION}")
    print(f"Bucket: {BUCKET_NAME}")

    try:
        s3 = get_s3_client()
        success = create_bucket_if_not_exists(s3, BUCKET_NAME, AWS_REGION)
        if success:
            provision_lakehouse_prefixes(s3, BUCKET_NAME)
            print("\nAWS Lakehouse storage provisioned successfully.")
    except NoCredentialsError:
        print("\n[WARNING] AWS credentials not found.")
        print("Please configure AWS CLI via 'aws configure' or set AWS_ACCESS_KEY_ID in .env.")
        print("For offline local execution, run the mock suite.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Failed to provision AWS storage: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
