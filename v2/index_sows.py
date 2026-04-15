#!/usr/bin/env python3
"""
SOW Generator v2 — Qdrant Indexing Pipeline

Crawls historical SOWs from Google Drive, chunks them, generates embeddings,
and upserts into Qdrant for RAG retrieval.

Usage:
    # Index from a list of Google Doc IDs
    python3 index_sows.py --doc-ids ids.json

    # Index a single document for testing
    python3 index_sows.py --doc-id "1zzJfgpRmaMX..."

    # Show index stats
    python3 index_sows.py --stats
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION,
    EMBEDDING_DIM, GEMINI_API_KEY, EMBEDDING_MODEL, GOOGLE_AUTH_SCRIPT,
)

import google.generativeai as genai

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError:
    print("qdrant-client required: pip install qdrant-client")
    sys.exit(1)


def get_access_token():
    """Get Google OAuth access token."""
    result = subprocess.run(
        ["bash", "-c", f"source {GOOGLE_AUTH_SCRIPT} && echo $GOOGLE_ACCESS_TOKEN"],
        capture_output=True, text=True, timeout=15,
    )
    token = result.stdout.strip()
    if token and len(token) > 20:
        return token
    raise RuntimeError("Failed to get Google access token")


def fetch_google_doc(doc_id, token):
    """Fetch Google Doc content as plain text."""
    import requests
    url = f"https://docs.googleapis.com/v1/documents/{doc_id}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    resp.raise_for_status()
    doc = resp.json()

    # Extract text from document body
    text_parts = []
    for element in doc.get("body", {}).get("content", []):
        if "paragraph" in element:
            for elem in element["paragraph"].get("elements", []):
                if "textRun" in elem:
                    text_parts.append(elem["textRun"]["content"])

    return "".join(text_parts), doc.get("title", "")


def chunk_document(text, title, doc_id, chunk_size=2000, overlap=200):
    """Split document into overlapping chunks for embedding."""
    chunks = []
    words = text.split()

    if len(words) <= chunk_size:
        chunks.append({
            "doc_id": doc_id,
            "title": title,
            "chunk_index": 0,
            "text": text,
        })
        return chunks

    i = 0
    chunk_idx = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)
        chunks.append({
            "doc_id": doc_id,
            "title": title,
            "chunk_index": chunk_idx,
            "text": chunk_text,
        })
        i += chunk_size - overlap
        chunk_idx += 1

    return chunks


def embed_text(text):
    """Generate embedding using Gemini."""
    genai.configure(api_key=GEMINI_API_KEY)
    result = genai.embed_content(
        model=f"models/{EMBEDDING_MODEL}",
        content=text[:5000],  # Limit input size
        task_type="RETRIEVAL_DOCUMENT",
    )
    return result["embedding"]


def extract_metadata(text, title):
    """Extract basic metadata from SOW text."""
    text_lower = text.lower()

    # Try to extract customer name from title
    customer = title.split("-")[0].strip() if "-" in title else title.split("_")[0].strip()

    # Detect industry keywords
    industry = "Unknown"
    industry_keywords = {
        "Insurance": ["insurance", "underwriting", "claims", "policy"],
        "Banking": ["banking", "bank", "financial", "loan", "account"],
        "Healthcare": ["healthcare", "hospital", "medical", "patient"],
        "E-commerce": ["ecommerce", "e-commerce", "shopping", "cart", "order"],
        "Telecom": ["telecom", "telecommunications", "broadband", "mobile"],
        "Automotive": ["automotive", "vehicle", "car", "dealer"],
        "Real Estate": ["real estate", "property", "housing"],
        "Education": ["education", "university", "school", "student"],
        "Logistics": ["logistics", "delivery", "shipping", "warehouse"],
        "BFSI": ["bfsi", "mutual fund", "investment", "trading"],
    }
    for ind, keywords in industry_keywords.items():
        if any(kw in text_lower for kw in keywords):
            industry = ind
            break

    # Detect modules mentioned
    modules = []
    module_keywords = {
        "IVR": ["ivr", "interactive voice"],
        "CRM Integration": ["crm", "salesforce", "zoho", "freshdesk"],
        "Blaster": ["blaster", "outbound campaign", "dialer"],
        "CSAT": ["csat", "satisfaction survey"],
        "WhatsApp": ["whatsapp"],
        "Queue": ["queue", "routing", "acd"],
        "Reporting": ["report", "dashboard", "analytics"],
    }
    for mod, keywords in module_keywords.items():
        if any(kw in text_lower for kw in keywords):
            modules.append(mod)

    return {
        "customer": customer,
        "industry": industry,
        "modules": modules,
    }


def ensure_collection(client):
    """Create Qdrant collection if it doesn't exist."""
    collections = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"Created collection: {QDRANT_COLLECTION}")
    else:
        info = client.get_collection(QDRANT_COLLECTION)
        print(f"Collection exists: {info.points_count} points")


def index_document(client, doc_id, token, point_id_start=0):
    """Index a single Google Doc into Qdrant."""
    print(f"  Fetching {doc_id}...", end=" ", flush=True)
    try:
        text, title = fetch_google_doc(doc_id, token)
    except Exception as e:
        print(f"FAILED: {e}")
        return 0

    if len(text.strip()) < 100:
        print(f"too short ({len(text)} chars) — skipping")
        return 0

    print(f"'{title}' ({len(text)} chars)")

    # Extract metadata
    metadata = extract_metadata(text, title)

    # Chunk
    chunks = chunk_document(text, title, doc_id)
    print(f"    {len(chunks)} chunks", end="", flush=True)

    # Embed and upsert
    points = []
    for chunk in chunks:
        try:
            embedding = embed_text(chunk["text"])
            point = PointStruct(
                id=point_id_start + chunk["chunk_index"],
                vector=embedding,
                payload={
                    "doc_id": doc_id,
                    "title": title,
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "customer": metadata["customer"],
                    "industry": metadata["industry"],
                    "modules": metadata["modules"],
                },
            )
            points.append(point)
            time.sleep(0.1)  # Rate limit embeddings API
        except Exception as e:
            print(f"\n    Embedding failed for chunk {chunk['chunk_index']}: {e}")

    if points:
        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        print(f" → {len(points)} points indexed")
    else:
        print(" → 0 points (all embeddings failed)")

    return len(points)


def main():
    parser = argparse.ArgumentParser(description="SOW Qdrant Indexer")
    parser.add_argument("--doc-id", type=str, help="Single Google Doc ID to index")
    parser.add_argument("--doc-ids", type=str, help="JSON file with list of doc IDs")
    parser.add_argument("--stats", action="store_true", help="Show index stats")
    args = parser.parse_args()

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=10)

    if args.stats:
        try:
            info = client.get_collection(QDRANT_COLLECTION)
            print(f"Collection: {QDRANT_COLLECTION}")
            print(f"Points:     {info.points_count}")
            print(f"Vectors:    {info.vectors_count}")
            print(f"Status:     {info.status}")
        except Exception as e:
            print(f"Error: {e}")
        return

    ensure_collection(client)
    token = get_access_token()
    total_points = 0

    if args.doc_id:
        # Index single document
        total_points = index_document(client, args.doc_id, token, point_id_start=0)
    elif args.doc_ids:
        # Index from file
        with open(args.doc_ids) as f:
            doc_ids = json.load(f)
        print(f"Indexing {len(doc_ids)} documents...")
        pid = 0
        for i, did in enumerate(doc_ids):
            doc_id = did if isinstance(did, str) else did.get("id", did.get("doc_id", ""))
            if not doc_id:
                continue
            print(f"\n[{i+1}/{len(doc_ids)}]", end=" ")
            n = index_document(client, doc_id, token, point_id_start=pid)
            pid += n + 10  # Leave gaps for re-indexing
            total_points += n
            time.sleep(0.5)  # Rate limit
    else:
        parser.print_help()
        return

    print(f"\nDone. Total points indexed: {total_points}")
    info = client.get_collection(QDRANT_COLLECTION)
    print(f"Collection now has {info.points_count} points")


if __name__ == "__main__":
    main()
