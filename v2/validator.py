"""
SOW Generator v2 — Assembly, Structural Validator & Quality Scorer
"""

import re
from config import SOW_SECTIONS


# ============================================================
# Assembly — merge 13 sections into one document
# ============================================================

def assemble_document(sections_dict, spec):
    """
    Merge all section outputs into a single Markdown document.
    sections_dict: {"S1": "markdown text", "S2": "...", ...}
    Returns: full Markdown string with TOC
    """
    customer = spec.customer.name or "[Customer]"
    project_id = spec.customer.project_id or "[Project ID]"

    header = f"""# Statement of Work
## {customer} — ECC Implementation
**Project ID:** {project_id}
**Date:** {__import__('datetime').datetime.now().strftime('%d %B %Y')}
**Classification:** Confidential

---

## Table of Contents

"""
    # Build TOC
    toc_lines = []
    for sec in SOW_SECTIONS:
        sid = sec["id"]
        name = sec["name"]
        num = sid.replace("S", "")
        toc_lines.append(f"{num}. [{name}](#{num.lower()}-{name.lower().replace(' ', '-').replace('&', '').replace(',', '')})")

    header += "\n".join(toc_lines)
    header += "\n\n---\n\n"

    # Append sections in order
    body_parts = []
    for sec in SOW_SECTIONS:
        sid = sec["id"]
        content = sections_dict.get(sid, "")
        if content:
            body_parts.append(content.strip())
        else:
            name = sec["name"]
            num = sid.replace("S", "")
            body_parts.append(f"## {num}. {name}\n\n[GENERATION FAILED — MANUAL INPUT REQUIRED]\n")
        body_parts.append("")  # blank line between sections

    return header + "\n\n".join(body_parts)


# ============================================================
# Structural Validator
# ============================================================

def validate_structure(document, spec):
    """
    Validate the assembled document for structural completeness.
    Returns: dict with pass/fail and details
    """
    issues = []

    # Check all 13 section headers present
    for sec in SOW_SECTIONS:
        name = sec["name"]
        # Look for the section header in various formats
        patterns = [
            name.lower(),
            name.split(" & ")[0].lower() if "&" in name else None,
            name.split(",")[0].lower() if "," in name else None,
        ]
        found = any(p and p in document.lower() for p in patterns if p)
        if not found:
            issues.append({"type": "missing_section", "section": sec["id"], "name": name})

    # Check for residual placeholders
    placeholders = ["<Customer Name>", "<customer_name>", "INSERT", "PLACEHOLDER", "Lorem ipsum"]
    for p in placeholders:
        if p in document:
            issues.append({"type": "placeholder_remaining", "text": p})

    # Check for allowed markers
    verify_count = document.count("[VERIFY]")
    failed_count = document.count("[GENERATION FAILED")
    tbd_count = document.count("[TBD]")

    # Check customer name consistency
    customer_name = spec.customer.name
    if customer_name and len(customer_name) > 2:
        name_count = document.lower().count(customer_name.lower())
        if name_count < 3:
            issues.append({"type": "customer_name_inconsistent", "count": name_count, "expected": ">= 3"})

    # Check tables exist (at least License, RTM, Implementation)
    table_count = len(re.findall(r'\|.*\|.*\|', document))
    if table_count < 10:  # Each table has header + separator + rows
        issues.append({"type": "insufficient_tables", "found": table_count, "expected": ">= 10"})

    sections_present = len(SOW_SECTIONS) - len([i for i in issues if i["type"] == "missing_section"])

    return {
        "passed": len([i for i in issues if i["type"] == "missing_section"]) == 0,
        "sections_present": sections_present,
        "sections_total": len(SOW_SECTIONS),
        "placeholder_count": len([i for i in issues if i["type"] == "placeholder_remaining"]),
        "verify_count": verify_count,
        "failed_sections": failed_count,
        "tbd_count": tbd_count,
        "issues": issues,
    }


# ============================================================
# Quality Scorer
# ============================================================

def compute_quality_score(document, spec, validation_result):
    """
    Compute quality score 0-100 based on structural validation.
    Returns: dict with total score and breakdown
    """
    breakdown = {}

    # 1. Sections present (40 points)
    sections_score = (validation_result["sections_present"] / validation_result["sections_total"]) * 40
    breakdown["sections_present"] = round(sections_score, 1)

    # 2. No bad placeholders (15 points)
    placeholder_count = validation_result["placeholder_count"]
    if placeholder_count == 0:
        breakdown["no_placeholders"] = 15
    elif placeholder_count <= 2:
        breakdown["no_placeholders"] = 8
    else:
        breakdown["no_placeholders"] = 0

    # 3. Word count in range (10 points)
    word_count = len(document.split())
    if 3000 <= word_count <= 20000:
        breakdown["word_count"] = 10
    elif 1000 <= word_count <= 30000:
        breakdown["word_count"] = 5
    else:
        breakdown["word_count"] = 0
    breakdown["word_count_actual"] = word_count

    # 4. Customer name consistency (10 points)
    customer_name = spec.customer.name
    if customer_name and len(customer_name) > 2:
        name_count = document.lower().count(customer_name.lower())
        if name_count >= 5:
            breakdown["customer_consistency"] = 10
        elif name_count >= 3:
            breakdown["customer_consistency"] = 6
        else:
            breakdown["customer_consistency"] = 0
    else:
        breakdown["customer_consistency"] = 5  # Can't check without name

    # 5. Tables present (10 points)
    table_rows = len(re.findall(r'\|.*\|.*\|', document))
    if table_rows >= 20:
        breakdown["tables"] = 10
    elif table_rows >= 10:
        breakdown["tables"] = 6
    else:
        breakdown["tables"] = 2

    # 6. Low VERIFY/TBD count (10 points)
    verify_total = validation_result["verify_count"] + validation_result["tbd_count"]
    if verify_total == 0:
        breakdown["completeness"] = 10
    elif verify_total <= 3:
        breakdown["completeness"] = 7
    elif verify_total <= 8:
        breakdown["completeness"] = 4
    else:
        breakdown["completeness"] = 0

    # 7. No failed sections (5 points)
    if validation_result["failed_sections"] == 0:
        breakdown["no_failures"] = 5
    else:
        breakdown["no_failures"] = 0

    total = sum(v for k, v in breakdown.items() if k != "word_count_actual")

    return {
        "total": round(total, 1),
        "max": 100,
        "breakdown": breakdown,
        "grade": "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D" if total >= 40 else "F",
    }
