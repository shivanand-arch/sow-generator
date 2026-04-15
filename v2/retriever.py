"""
SOW Generator v2 — RAG Retriever (Qdrant-backed)
"""

import json
import google.generativeai as genai
from config import (
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION,
    EMBEDDING_DIM, GEMINI_API_KEY, EMBEDDING_MODEL,
)

# Try Qdrant — gracefully degrade if unavailable
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


class RagRetriever:
    """Retrieves similar historical SOWs from Qdrant vector DB."""

    def __init__(self):
        self.qdrant = None
        self.available = False

        if not QDRANT_AVAILABLE:
            print("[RAG] qdrant-client not installed — RAG disabled")
            return

        try:
            self.qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=5)
            # Verify collection exists
            collections = [c.name for c in self.qdrant.get_collections().collections]
            if QDRANT_COLLECTION in collections:
                info = self.qdrant.get_collection(QDRANT_COLLECTION)
                self.available = True
                print(f"[RAG] Connected to Qdrant — {info.points_count} SOWs indexed")
            else:
                print(f"[RAG] Collection '{QDRANT_COLLECTION}' not found — RAG disabled. Run index_sows.py first.")
        except Exception as e:
            print(f"[RAG] Qdrant unreachable ({e}) — generating without historical context")

    def embed_text(self, text):
        """Generate embedding using Gemini text-embedding-004."""
        genai.configure(api_key=GEMINI_API_KEY)
        result = genai.embed_content(
            model=f"models/{EMBEDDING_MODEL}",
            content=text,
            task_type="RETRIEVAL_QUERY",
        )
        return result["embedding"]

    def find_similar(self, requirements_spec, top_k=5):
        """
        Find top-K similar SOWs from Qdrant.
        Returns list of dicts with: doc_id, customer, industry, score, modules, text_excerpt
        """
        if not self.available:
            return []

        # Build query from requirements
        query_parts = []
        customer = requirements_spec.customer
        if customer.industry:
            query_parts.append(customer.industry)
        if customer.country:
            query_parts.append(customer.country)
        if requirements_spec.use_case_type:
            query_parts.append(requirements_spec.use_case_type)
        if requirements_spec.deployment.type:
            query_parts.append(f"{requirements_spec.deployment.type} deployment")

        # Add module names
        for category, mod_ids in requirements_spec.modules.items():
            query_parts.append(category)
            for mid in mod_ids[:5]:  # Limit to avoid huge query
                query_parts.append(mid)

        if requirements_spec.additional_requirements:
            query_parts.append(requirements_spec.additional_requirements[:200])

        query_text = " ".join(query_parts)
        if not query_text.strip():
            query_text = "ECC contact center IVR implementation"

        try:
            query_vector = self.embed_text(query_text)
            results = self.qdrant.query_points(
                collection_name=QDRANT_COLLECTION,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )

            similar = []
            for point in results.points:
                payload = point.payload or {}
                similar.append({
                    "doc_id": payload.get("doc_id", str(point.id)),
                    "customer": payload.get("customer", "Unknown"),
                    "industry": payload.get("industry", ""),
                    "score": round(point.score, 3),
                    "modules": payload.get("modules", []),
                    "text_excerpt": payload.get("text", "")[:3000],  # Limit excerpt size
                })
            return similar

        except Exception as e:
            print(f"[RAG] Search failed: {e}")
            return []

    def get_section_context(self, similar_sows, section_name, max_sows=3):
        """
        Extract section-relevant text from similar SOWs.
        Used to provide few-shot examples for each section generator.
        """
        contexts = []
        for sow in similar_sows[:max_sows]:
            text = sow.get("text_excerpt", "")
            if not text:
                continue

            # Try to extract the relevant section
            section_lower = section_name.lower()
            lines = text.split("\n")
            capturing = False
            section_text = []

            for line in lines:
                line_lower = line.lower().strip()
                # Start capturing when we find the section header
                if section_lower in line_lower and (line_lower.startswith("#") or line_lower.startswith("**")):
                    capturing = True
                    continue
                # Stop at next section header
                if capturing and (line_lower.startswith("# ") or line_lower.startswith("## ")):
                    break
                if capturing:
                    section_text.append(line)

            excerpt = "\n".join(section_text).strip()
            if excerpt:
                contexts.append({
                    "customer": sow["customer"],
                    "industry": sow.get("industry", ""),
                    "text": excerpt[:2000],  # Limit per-section context
                })

        return contexts

    def stats(self):
        """Get index statistics."""
        if not self.available:
            return {"status": "unavailable", "count": 0}
        try:
            info = self.qdrant.get_collection(QDRANT_COLLECTION)
            return {
                "status": "connected",
                "count": info.points_count,
                "collection": QDRANT_COLLECTION,
            }
        except Exception as e:
            return {"status": f"error: {e}", "count": 0}
