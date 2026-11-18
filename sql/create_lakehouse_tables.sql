-- ============================================================
-- NorthStar Retail - AWS Athena & Redshift Lakehouse DDL
-- Database & External Tables referencing S3 Medallion Parquet
-- ============================================================

-- 1. Create Glue Lakehouse Database
CREATE DATABASE IF NOT EXISTS northstar_lakehouse
LOCATION 's3://${AWS_S3_BUCKET}/';

-- 2. Bronze Layer: Raw Sales Table
CREATE EXTERNAL TABLE IF NOT EXISTS northstar_lakehouse.sales_raw (
    order_id STRING,
    order_date STRING,
    store_id STRING,
    product_id STRING,
    product_name STRING,
    category STRING,
    quantity INT,
    unit_price DOUBLE,
    region STRING
)
STORED AS PARQUET
LOCATION 's3://${AWS_S3_BUCKET}/bronze/sales_raw/'
TBLPROPERTIES ('parquet.compress'='SNAPPY');

-- 3. Silver Layer: Enriched & Cleansed Sales Table
CREATE EXTERNAL TABLE IF NOT EXISTS northstar_lakehouse.sales_enriched (
    order_id STRING,
    order_date DATE,
    store_id STRING,
    product_id STRING,
    product_name STRING,
    category STRING,
    quantity INT,
    unit_price DOUBLE,
    region STRING,
    revenue DOUBLE
)
STORED AS PARQUET
LOCATION 's3://${AWS_S3_BUCKET}/silver/sales_enriched/'
TBLPROPERTIES ('parquet.compress'='SNAPPY');

-- 4. Gold Layer: Fact Sales
CREATE EXTERNAL TABLE IF NOT EXISTS northstar_lakehouse.fact_sales (
    order_id STRING,
    date_key STRING,
    store_id STRING,
    product_id STRING,
    category STRING,
    region STRING,
    quantity INT,
    unit_price DOUBLE,
    revenue DOUBLE
)
STORED AS PARQUET
LOCATION 's3://${AWS_S3_BUCKET}/gold/fact_sales/'
TBLPROPERTIES ('parquet.compress'='SNAPPY');

-- 5. Gold Layer: Dimension Product
CREATE EXTERNAL TABLE IF NOT EXISTS northstar_lakehouse.dim_product (
    product_id STRING,
    product_name STRING,
    category STRING
)
STORED AS PARQUET
LOCATION 's3://${AWS_S3_BUCKET}/gold/dim_product/'
TBLPROPERTIES ('parquet.compress'='SNAPPY');

-- 6. Gold Layer: Dimension Date
CREATE EXTERNAL TABLE IF NOT EXISTS northstar_lakehouse.dim_date (
    date_key STRING,
    year INT,
    month INT,
    day INT,
    quarter INT,
    day_of_week STRING
)
STORED AS PARQUET
LOCATION 's3://${AWS_S3_BUCKET}/gold/dim_date/'
TBLPROPERTIES ('parquet.compress'='SNAPPY');

-- 7. Gold Layer: Product & Policy Documents
CREATE EXTERNAL TABLE IF NOT EXISTS northstar_lakehouse.product_documents (
    source_name STRING,
    s3_uri STRING,
    document_type STRING,
    content STRING
)
STORED AS PARQUET
LOCATION 's3://${AWS_S3_BUCKET}/gold/product_documents/'
TBLPROPERTIES ('parquet.compress'='SNAPPY');
