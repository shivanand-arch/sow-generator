"""
SOW Generator v2 — Configuration
"""

import os
from pathlib import Path

# Load .env from ~/.claude/.env if present (for ANTHROPIC_API_KEY etc.)
_dotenv_path = Path.home() / ".claude" / ".env"
if _dotenv_path.exists():
    with open(_dotenv_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                _k, _v = _key.strip(), _val.strip()
                if not os.environ.get(_k):  # override empty values too
                    os.environ[_k] = _v

# Paths
BASE_DIR = Path(__file__).parent
PROJECT_DIR = BASE_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
MODULE_CATALOG_PATH = DATA_DIR / "module-catalog.json"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Google auth
GOOGLE_AUTH_SCRIPT = Path.home() / ".claude" / "scripts" / "google-auth.sh"

# Qdrant
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "exotel_sows")
EMBEDDING_DIM = 1024  # Voyage AI via Anthropic (or adjust for your embedding model)

# Anthropic / Claude
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

# Claude models
CLAUDE_FAST_MODEL = "claude-sonnet-4-6"       # Fast + cheap — used for 9 sections
CLAUDE_STRONG_MODEL = "claude-opus-4-6"       # Strong — used for Section 7 (IVR/Scope)

# Embeddings — still use Gemini for embeddings (free/cheap, Anthropic doesn't offer embeddings)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-004"

# Generation limits
MAX_RETRIES = 3
SECTION_TIMEOUT_SECONDS = 120
MAX_TOKENS_PER_SOW = 100_000
MAX_COST_PER_SOW = 5.00  # USD — Claude is pricier than Gemini

# SOW template — 13 sections (Jan 2026 standard)
SOW_SECTIONS = [
    {"id": "S1",  "name": "Executive Summary",                     "template_fill": False, "model": "fast"},
    {"id": "S2",  "name": "Document Versioning",                   "template_fill": True,  "model": None},
    {"id": "S3",  "name": "Stakeholder Registry & Escalation",     "template_fill": False, "model": "fast"},
    {"id": "S4",  "name": "Project Overview & Key Deliverables",   "template_fill": False, "model": "fast"},
    {"id": "S5",  "name": "License Components",                    "template_fill": True,  "model": None},
    {"id": "S6",  "name": "Solution Architecture",                 "template_fill": False, "model": "fast"},
    {"id": "S7",  "name": "Scope Definition",                      "template_fill": False, "model": "strong"},
    {"id": "S8",  "name": "Requirements Traceability Matrix",      "template_fill": False, "model": "fast"},
    {"id": "S9",  "name": "Project Prerequisites",                 "template_fill": False, "model": "fast"},
    {"id": "S10", "name": "Deliverables Descoped",                 "template_fill": False, "model": "fast"},
    {"id": "S11", "name": "Data Purging Policy",                   "template_fill": True,  "model": None},
    {"id": "S12", "name": "Implementation Plan",                   "template_fill": False, "model": "fast"},
    {"id": "S13", "name": "Approvals, UAT & Change Management",    "template_fill": False, "model": "fast"},
]
