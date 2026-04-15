#!/usr/bin/env python3
"""
SOW Generator v2 — Main Pipeline

Usage:
    python3 pipeline.py --requirements spec.json
    python3 pipeline.py --requirements spec.json --section S7  # Regenerate one section
    python3 pipeline.py --requirements spec.json --no-gdoc     # Skip Google Doc
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add v2 dir to path
sys.path.insert(0, str(Path(__file__).parent))

from config import SOW_SECTIONS, MAX_COST_PER_SOW
from schema import RequirementsSpec, ModuleCatalog
from llm import ClaudeClient
from retriever import RagRetriever
from generators import SECTION_GENERATORS
from validator import assemble_document, validate_structure, compute_quality_score
from output import DocxGenerator, GoogleDocGenerator
from logger import GenerationLogger


class SowPipeline:
    """Full SOW generation pipeline: input → context → generate → validate → output."""

    def __init__(self):
        print("[Pipeline] Initializing SOW Generator v2...")
        self.llm = ClaudeClient()
        self.retriever = RagRetriever()
        self.catalog = ModuleCatalog()
        self.docx_gen = DocxGenerator()
        self.gdoc_gen = GoogleDocGenerator()

    def generate(self, spec, skip_gdoc=False, section_override=None, existing_sections=None):
        """
        Run the full pipeline.

        Args:
            spec: RequirementsSpec object
            skip_gdoc: Skip Google Doc creation
            section_override: If set, only regenerate this section ID (e.g., "S7")
            existing_sections: Dict of previously generated sections (for regeneration)

        Returns: dict with document, quality score, file paths, and metadata
        """
        gen_log = GenerationLogger(
            opportunity_name=spec.customer.name,
            pm="cli",
            trigger="pipeline",
        )
        gen_log.set_opportunity(spec.sf_opportunity)

        # ---------------------------------------------------
        # Stage 2: Context Enrichment (RAG)
        # ---------------------------------------------------
        print("\n[Stage 2] Context Enrichment — searching similar SOWs...")
        rag_start = time.time()

        similar_sows = self.retriever.find_similar(spec, top_k=5)
        if similar_sows:
            print(f"  Found {len(similar_sows)} similar SOWs:")
            for s in similar_sows:
                print(f"    - {s['customer']} ({s.get('industry', '?')}) — score: {s['score']}")
            # Attach to spec for reference
            spec.similar_sows = similar_sows
        else:
            print("  No similar SOWs found — generating without historical context")

        gen_log.log_stage("stage_2_context", {
            "duration_ms": int((time.time() - rag_start) * 1000),
            "similar_count": len(similar_sows),
            "qdrant_status": self.retriever.stats().get("status", "unknown"),
        })

        # ---------------------------------------------------
        # Stage 3: Module matching (if not already done)
        # ---------------------------------------------------
        if not spec.modules:
            print("\n[Stage 3] Auto-matching modules from SF products...")
            products = spec.sf_opportunity.get("Products__c", "")
            description = spec.sf_opportunity.get("Description", "")
            spec.modules = self.catalog.match_from_products(products, description)
            print(f"  Matched {sum(len(v) for v in spec.modules.values())} modules across {len(spec.modules)} categories")

        gen_log.log_stage("stage_3_requirements", {
            "modules_matched": sum(len(v) for v in spec.modules.values()),
            "categories": list(spec.modules.keys()),
        })

        # ---------------------------------------------------
        # Stage 4: Section-by-Section Generation
        # ---------------------------------------------------
        sections = existing_sections.copy() if existing_sections else {}
        sections_to_generate = [section_override] if section_override else [s["id"] for s in SOW_SECTIONS]

        print(f"\n[Stage 4] Generating {len(sections_to_generate)} sections...")
        total_cost = 0.0

        for sid in sections_to_generate:
            gen_config = SECTION_GENERATORS.get(sid)
            if not gen_config:
                print(f"  [{sid}] Unknown section — skipping")
                continue

            # Template-fill sections (no LLM)
            if "template_fn" in gen_config:
                print(f"  [{sid}] Template fill... ", end="", flush=True)
                start = time.time()
                sections[sid] = gen_config["template_fn"](spec)
                dur = int((time.time() - start) * 1000)
                print(f"done ({dur}ms)")
                gen_log.log_section(sid, "template", 0, 0, dur, "ok")
                continue

            # LLM-generated sections
            model = gen_config.get("model", "flash")
            max_tokens = gen_config.get("max_tokens", 3000)
            prompt_fn = gen_config["prompt_fn"]

            # Get section-specific context from similar SOWs
            section_name = next((s["name"] for s in SOW_SECTIONS if s["id"] == sid), sid)
            similar_contexts = self.retriever.get_section_context(similar_sows, section_name)

            prompt = prompt_fn(spec, similar_contexts)

            print(f"  [{sid}] {section_name} ({model})... ", end="", flush=True)

            try:
                text, tokens_in, tokens_out, duration_ms = self.llm.generate(
                    prompt, model=model, max_output_tokens=max_tokens,
                )
                sections[sid] = text
                print(f"done ({duration_ms}ms, {tokens_in}+{tokens_out} tokens)")
                gen_log.log_section(sid, model, tokens_in, tokens_out, duration_ms, "ok")

            except Exception as e:
                print(f"FAILED: {e}")
                sections[sid] = f"## {section_name}\n\n[GENERATION FAILED — MANUAL INPUT REQUIRED]\n\nError: {e}\n"
                gen_log.log_section(sid, model, 0, 0, 0, "failed", error=e)

            # Cost check
            total_cost = gen_log.estimate_cost()
            if total_cost > MAX_COST_PER_SOW:
                print(f"\n  [ABORT] Cost limit exceeded: ${total_cost:.2f} > ${MAX_COST_PER_SOW:.2f}")
                break

        # ---------------------------------------------------
        # Stage 5: Assembly & Validation
        # ---------------------------------------------------
        print("\n[Stage 5] Assembly & Validation...")
        document = assemble_document(sections, spec)
        validation = validate_structure(document, spec)
        quality = compute_quality_score(document, spec, validation)

        print(f"  Sections: {validation['sections_present']}/{validation['sections_total']}")
        print(f"  Quality:  {quality['total']}/100 (Grade: {quality['grade']})")
        print(f"  Words:    {quality['breakdown'].get('word_count_actual', 0):,}")
        print(f"  [VERIFY]: {validation['verify_count']}  |  [TBD]: {validation['tbd_count']}  |  Failed: {validation['failed_sections']}")

        if validation["issues"]:
            for issue in validation["issues"][:5]:
                print(f"  Issue: {issue['type']} — {issue.get('section', issue.get('text', ''))}")

        gen_log.log_stage("stage_5_validation", {
            "sections_present": validation["sections_present"],
            "placeholders_remaining": validation["placeholder_count"],
            "quality_score": quality["total"],
            "verify_count": validation["verify_count"],
        })
        gen_log.set_quality_score(quality["total"])

        # ---------------------------------------------------
        # Stage 6: Output Generation
        # ---------------------------------------------------
        print("\n[Stage 6] Generating outputs...")
        result = {
            "document": document,
            "sections": sections,
            "quality": quality,
            "validation": validation,
            "files": {},
        }

        # DOCX
        try:
            docx_path = self.docx_gen.generate(document, spec)
            result["files"]["docx"] = docx_path
            print(f"  DOCX: {docx_path}")
        except Exception as e:
            print(f"  DOCX generation failed: {e}")

        # Google Doc
        if not skip_gdoc:
            try:
                gdoc_url = self.gdoc_gen.create(document, spec)
                if gdoc_url:
                    result["files"]["google_doc"] = gdoc_url
                    print(f"  Google Doc: {gdoc_url}")
            except Exception as e:
                print(f"  Google Doc creation failed: {e}")

        gen_log.log_stage("stage_6_output", {
            "docx_path": result["files"].get("docx", ""),
            "google_doc_url": result["files"].get("google_doc", ""),
        })

        # Save log
        log_path = gen_log.save()
        result["log_path"] = log_path
        result["cost_usd"] = gen_log.estimate_cost()

        print(f"\n[Done] SOW generated in {gen_log.log['total_duration_ms'] / 1000:.1f}s")
        print(f"  Cost: ${result['cost_usd']:.4f}")
        print(f"  Log:  {log_path}")

        return result


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="SOW Generator v2 Pipeline")
    parser.add_argument("--requirements", "-r", type=str, required=True,
                        help="Path to RequirementsSpec JSON file")
    parser.add_argument("--section", "-s", type=str, default=None,
                        help="Regenerate a specific section (e.g., S7)")
    parser.add_argument("--no-gdoc", action="store_true",
                        help="Skip Google Doc creation")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Override output directory")
    args = parser.parse_args()

    # Load requirements
    with open(args.requirements) as f:
        spec_data = json.load(f)
    spec = RequirementsSpec.from_dict(spec_data)

    print(f"Customer: {spec.customer.name}")
    print(f"Industry: {spec.customer.industry}")
    print(f"Use Case: {spec.use_case_type}")
    print(f"Modules:  {sum(len(v) for v in spec.modules.values())} across {len(spec.modules)} categories")

    # Run pipeline
    pipeline = SowPipeline()
    result = pipeline.generate(
        spec,
        skip_gdoc=args.no_gdoc,
        section_override=args.section,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("  SOW Generation Complete")
    print("=" * 60)
    print(f"  Customer:    {spec.customer.name}")
    print(f"  Quality:     {result['quality']['total']}/100 ({result['quality']['grade']})")
    print(f"  Cost:        ${result['cost_usd']:.4f}")
    for fmt, path in result["files"].items():
        print(f"  {fmt.upper()}: {path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
