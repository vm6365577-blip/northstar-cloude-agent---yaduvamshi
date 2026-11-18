"""
NorthStar Retail - AWS Policy Document Search Tool
Provides hybrid semantic and keyword retrieval across multi-format store policies
stored in the S3 Gold Lakehouse.
"""

import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import boto3

from agent.config import (
    AWS_REGION,
    AWS_S3_BUCKET,
    AWS_EMBEDDING_MODEL_ID,
    DOCUMENT_TABLE,
    LOCAL_LAKEHOUSE_DIR,
    LOCAL_DATA_DIR,
)

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_DOCS_PARQUET = LOCAL_LAKEHOUSE_DIR / "gold" / "product_documents" / "product_documents.parquet"
GOLD_DOCS_JSON = LOCAL_LAKEHOUSE_DIR / "gold" / "product_documents" / "product_documents.json"


def _get_bedrock_runtime():
    """Create Bedrock Runtime client if credentials available."""
    try:
        return boto3.client("bedrock-runtime", region_name=AWS_REGION)
    except Exception:
        return None


def _load_documents() -> list:
    """Load indexed documents from Gold JSON, Parquet, or fallback parser."""
    if GOLD_DOCS_JSON.exists():
        with open(GOLD_DOCS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)

    if GOLD_DOCS_PARQUET.exists():
        df = pd.read_parquet(GOLD_DOCS_PARQUET)
        return df.to_dict(orient="records")

    # If lakehouse documents not yet staged, trigger ingestion helper
    from src.ingestion.load_product_docs_to_lakehouse import read_documents_locally
    return read_documents_locally()


def _score_document_keyword(doc: dict, terms: list) -> float:
    """Calculate token-level relevance score for a document."""
    content_lower = doc.get("content", "").lower()
    source_lower = doc.get("source_name", "").lower()

    score = 0.0
    for term in terms:
        # Heavily weigh filename match
        if term in source_lower:
            score += 10.0
        # Count frequency in content
        matches = len(re.findall(re.escape(term), content_lower))
        score += matches * 1.5

    return score


def search_policy_documents(search_query: str) -> dict:
    """
    Search the NorthStar Retail product and policy documents.

    Use this tool for questions about:
    returns, refunds, shipping, delivery, warranty,
    loyalty points, promotions, discounts, sizing,
    customer support, stationery FAQs, and other
    product-policy information.

    Never answer policy questions from general knowledge.
    Always use this tool.
    """
    if not search_query or not search_query.strip():
        return {
            "source": "NorthStar product documents",
            "results": [],
            "message": "Empty search query provided.",
        }

    documents = _load_documents()
    query_clean = search_query.strip().lower()

    # Tokenize query for hybrid search (remove basic punctuation and short stopwords)
    stopwords = {"a", "an", "the", "in", "on", "of", "for", "to", "is", "are", "what", "how", "can", "i"}
    tokens = [t for t in re.findall(r"\w+", query_clean) if len(t) > 2 and t not in stopwords]
    if not tokens:
        tokens = [query_clean]

    # Score documents
    scored = []
    for doc in documents:
        content = doc.get("content", "")
        # Direct phrase match bonus
        exact_bonus = 50.0 if query_clean in content.lower() else 0.0
        score = _score_document_keyword(doc, tokens) + exact_bonus

        if score > 0:
            scored.append((score, doc))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    top_matches = [item[1] for item in scored[:5]]

    if not top_matches:
        return {
            "source": "NorthStar product documents",
            "results": [],
            "message": "No matching document content was found.",
        }

    results = []
    for doc in top_matches:
        results.append({
            "source_name": doc.get("source_name", "unknown"),
            "s3_uri": doc.get("s3_uri", f"s3://{AWS_S3_BUCKET}/raw/product_docs/{doc.get('source_name')}"),
            "document_type": doc.get("document_type", "txt"),
            "content": doc.get("content", ""),
        })

    return {
        "source": "NorthStar product documents",
        "results": results,
    }
