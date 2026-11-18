"""
Mock implementation of AWS S3 / Athena policy search tools.
Extracts text from local data/product_docs/ without requiring active AWS credentials.
"""

import csv
import io
import json
from pathlib import Path
from typing import List, Dict

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "product_docs"


def _extract_mock_file(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    try:
        if ext == "pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                pages = [p.extract_text() for p in reader.pages if p.extract_text()]
                return "\n".join(pages)
            except Exception:
                return f"[PDF Document: {path.name}]"
        elif ext == "json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return json.dumps(data, indent=2, ensure_ascii=False)
        elif ext == "txt":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        elif ext == "csv":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                return "\n".join(" | ".join(row) for row in reader)
    except Exception:
        pass
    return ""


def _load_mock_documents() -> List[Dict[str, str]]:
    if not DOCS_DIR.exists():
        return []

    docs = []
    for f in DOCS_DIR.iterdir():
        if not f.is_file():
            continue
        text = _extract_mock_file(f)
        if text.strip():
            docs.append({
                "source_name": f.name,
                "s3_uri": f"s3://northstar-retail-lakehouse/raw/product_docs/{f.name}",
                "document_type": f.suffix.lower().lstrip("."),
                "content": text,
            })
    return docs


def search_mock_policy_documents(search_query: str) -> dict:
    """Mock implementation of search_policy_documents tool."""
    docs = _load_mock_documents()
    query_lower = search_query.lower().strip()
    matching_docs = []

    for d in docs:
        if query_lower in d["content"].lower() or query_lower in d["source_name"].lower():
            matching_docs.append(d)

    matching_docs = matching_docs[:5]

    if not matching_docs:
        for d in docs:
            matching_docs.append(d)
            if len(matching_docs) >= 3:
                break

    return {
        "source": "Mock Product Documents (Local S3 Store)",
        "results": matching_docs,
        "message": "Results served via isolated local mock document store." if matching_docs else "No matching document content found.",
    }
