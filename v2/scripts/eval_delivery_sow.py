#!/usr/bin/env python3
"""
SOW Generator v2 — Delivery SOW Evaluation Harness

Defines 3 test scenarios (Simple, Mid-Market, Enterprise),
runs full 13-section pipeline for each, scores the output,
and saves results to eval_results.json.
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add v2 dir to path for imports
V2_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_DIR))

from schema import RequirementsSpec, CustomerInfo, DeploymentInfo, IvrSpec, IntegrationSpec, LicenseComponent
from pipeline import SowPipeline
from config import SOW_SECTIONS


# ============================================================
# 3 Test Scenarios
# ============================================================

def build_simple_inbound() -> RequirementsSpec:
    """Scenario A: Simple Inbound — Insurance, basic IVR, no CRM, cloud, 5 modules."""
    spec = RequirementsSpec()
    spec.customer = CustomerInfo(
        name="SafeGuard Insurance",
        industry="Insurance",
        country="India",
        region="South Asia",
        project_id="PRJ-2026-SG-001",
        deal_value="$18,000",
        mrr="$1,500",
    )
    spec.deployment = DeploymentInfo(
        type="cloud",
        infrastructure="Exotel Cloud",
        platform="ECC",
        sip_integration="Standard SIP",
    )
    spec.licenses = [
        LicenseComponent(component="ECC Agent License", count=10, type="Concurrent", retention_days=90),
        LicenseComponent(component="Voice Channel", count=5, type="Channel", retention_days=90),
    ]
    spec.modules = {
        "IVR": ["IVR-001", "IVR-003", "IVR-029", "IVR-030", "IVR-031"],
    }
    spec.ivr_spec = IvrSpec(
        complexity="low",
        inbound_dids=["+91-80-XXXX-1001"],
        languages=["English"],
        menus=[{
            "did": "+91-80-XXXX-1001",
            "levels": 1,
            "options": ["Claims", "Policy Inquiry", "Agent"],
            "sub_menus": [],
        }],
        csat=False,
        callback=False,
        vip_routing=False,
    )
    spec.integrations = []
    spec.use_case_type = "Inbound Voice"
    spec.additional_requirements = "Basic inbound IVR for policy inquiries and claims routing. No CRM integration needed initially."
    spec.sf_opportunity = {"Name": "SafeGuard Insurance ECC", "Products__c": "ECC Agent License, IVR"}
    return spec


def build_mid_market() -> RequirementsSpec:
    """Scenario B: Mid-Market — E-commerce, medium IVR with CSAT, Zoho CRM, 15 modules."""
    spec = RequirementsSpec()
    spec.customer = CustomerInfo(
        name="ShopEase India",
        industry="E-Commerce",
        country="India",
        region="South Asia",
        project_id="PRJ-2026-SE-042",
        deal_value="$65,000",
        mrr="$5,200",
    )
    spec.deployment = DeploymentInfo(
        type="cloud",
        infrastructure="Exotel Cloud",
        platform="ECC",
        sip_integration="Standard SIP",
    )
    spec.licenses = [
        LicenseComponent(component="ECC Agent License", count=50, type="Concurrent", retention_days=90),
        LicenseComponent(component="Voice Channel", count=25, type="Channel", retention_days=90),
        LicenseComponent(component="Voice Logger", count=50, type="Per Agent", retention_days=90),
    ]
    spec.modules = {
        "IVR": ["IVR-001", "IVR-002", "IVR-003", "IVR-004", "IVR-007", "IVR-018", "IVR-020", "IVR-029", "IVR-030", "IVR-031"],
        "Integration": ["INT-001", "INT-002", "INT-007", "INT-021", "INT-023"],
        "Queue": ["QUE-001", "QUE-002", "QUE-009"],
        "Data": ["DAT-001", "DAT-007", "DAT-009"],
    }
    spec.ivr_spec = IvrSpec(
        complexity="medium",
        inbound_dids=["+91-80-XXXX-2001", "+91-80-XXXX-2002"],
        languages=["English", "Hindi"],
        menus=[
            {
                "did": "+91-80-XXXX-2001",
                "levels": 2,
                "options": ["Order Status", "Returns & Refunds", "Product Inquiry", "Speak to Agent"],
                "sub_menus": [
                    {"parent": "Returns & Refunds", "options": ["Return Pickup", "Refund Status", "Exchange"]},
                ],
            },
            {
                "did": "+91-80-XXXX-2002",
                "levels": 1,
                "options": ["Seller Support", "Logistics Partner", "Other"],
            },
        ],
        csat=True,
        callback=False,
        vip_routing=False,
    )
    spec.integrations = [
        IntegrationSpec(type="CRM", system="Zoho CRM", direction="bidirectional",
                        features=["screen_pop", "call_disposition", "contact_lookup"]),
    ]
    spec.use_case_type = "Inbound Voice + Outbound Campaigns"
    spec.additional_requirements = (
        "E-commerce customer service platform with order status self-service, "
        "bilingual IVR (English/Hindi), Zoho CRM integration with screen pop, "
        "and post-call CSAT survey."
    )
    spec.sf_opportunity = {
        "Name": "ShopEase India ECC",
        "Products__c": "ECC Agent License, IVR, Zoho Integration, CSAT, Reporting",
    }
    return spec


def build_enterprise() -> RequirementsSpec:
    """Scenario C: Enterprise — Banking, high IVR, SF+custom CRM, on-prem, 30+ modules."""
    spec = RequirementsSpec()
    spec.customer = CustomerInfo(
        name="Meridian National Bank",
        industry="Banking & Financial Services",
        country="India",
        region="South Asia",
        project_id="PRJ-2026-MNB-007",
        deal_value="$220,000",
        mrr="$18,000",
    )
    spec.deployment = DeploymentInfo(
        type="on-premise",
        infrastructure="Customer Data Center (Mumbai + DR Chennai)",
        platform="ECC",
        sip_integration="Cisco CUBE SBC",
    )
    spec.licenses = [
        LicenseComponent(component="ECC Agent License", count=200, type="Concurrent", retention_days=180),
        LicenseComponent(component="Voice Channel", count=100, type="Channel", retention_days=180),
        LicenseComponent(component="Voice Logger", count=200, type="Per Agent", retention_days=365),
        LicenseComponent(component="Predictive Dialer License", count=50, type="Per Agent", retention_days=90),
        LicenseComponent(component="CQA License", count=20, type="Per Seat", retention_days=90),
    ]
    spec.modules = {
        "IVR": [
            "IVR-001", "IVR-002", "IVR-003", "IVR-004", "IVR-005", "IVR-006",
            "IVR-007", "IVR-009", "IVR-010", "IVR-011", "IVR-012", "IVR-013",
            "IVR-014", "IVR-015", "IVR-018", "IVR-019", "IVR-023", "IVR-026",
            "IVR-028", "IVR-029", "IVR-030", "IVR-031", "IVR-033", "IVR-034",
        ],
        "Integration": [
            "INT-001", "INT-002", "INT-003", "INT-004", "INT-010",
            "INT-011", "INT-013", "INT-018", "INT-019", "INT-020",
            "INT-021", "INT-022", "INT-023", "INT-024",
        ],
        "Blaster": ["BLA-002", "BLA-004", "BLA-010", "BLA-011", "BLA-018"],
        "Queue": [
            "QUE-001", "QUE-002", "QUE-003", "QUE-005", "QUE-006",
            "QUE-007", "QUE-009", "QUE-012", "QUE-020", "QUE-021", "QUE-022",
        ],
        "Data": ["DAT-001", "DAT-003", "DAT-007", "DAT-009", "DAT-011", "DAT-013", "DAT-014", "DAT-015"],
    }
    spec.ivr_spec = IvrSpec(
        complexity="high",
        inbound_dids=[
            "+91-22-XXXX-3001",  # Retail Banking
            "+91-22-XXXX-3002",  # Corporate Banking
            "+91-22-XXXX-3003",  # Credit Cards
            "+91-1800-XXXX-3000",  # Toll-free
        ],
        languages=["English", "Hindi", "Marathi"],
        menus=[
            {
                "did": "+91-22-XXXX-3001",
                "levels": 3,
                "options": ["Account Balance", "Fund Transfer", "Card Services", "Loans", "Speak to Agent"],
                "sub_menus": [
                    {"parent": "Card Services", "options": ["Block Card", "Card Limit", "Card Statement", "Rewards"]},
                    {"parent": "Loans", "options": ["Home Loan", "Personal Loan", "Loan Status"]},
                ],
            },
            {
                "did": "+91-22-XXXX-3002",
                "levels": 2,
                "options": ["Trade Finance", "Cash Management", "FX Rates", "Relationship Manager"],
            },
            {
                "did": "+91-22-XXXX-3003",
                "levels": 2,
                "options": ["Activate Card", "Dispute Transaction", "EMI Conversion", "Reward Points", "Agent"],
            },
        ],
        csat=True,
        callback=True,
        vip_routing=True,
        custom_description=(
            "Multi-language (EN/HI/MR) banking IVR with PIN verification, "
            "OTP for transactions, self-service balance/mini-statement, "
            "VIP routing for HNI customers (>50L balance), "
            "emergency card block bypass, and Salesforce + core banking integration."
        ),
    )
    spec.integrations = [
        IntegrationSpec(type="CRM", system="Salesforce", direction="bidirectional",
                        features=["screen_pop", "click_to_dial", "call_disposition", "recording_url", "case_creation"]),
        IntegrationSpec(type="CRM", system="Core Banking System (Finacle)", direction="bidirectional",
                        features=["account_lookup", "balance_inquiry", "mini_statement", "fund_transfer_status"]),
        IntegrationSpec(type="Payment", system="NPCI UPI Gateway", direction="outbound",
                        features=["upi_validation"]),
    ]
    spec.use_case_type = "Inbound Voice + Outbound Collections + Self-Service Banking"
    spec.additional_requirements = (
        "Full-scale banking contact center with multi-language IVR, self-service banking "
        "(balance, mini-statement, card block), Salesforce CRM + Finacle core banking integration, "
        "VIP/HNI routing, PCI-DSS compliant payment IVR, predictive dialer for collections, "
        "on-premise deployment in Mumbai DC with DR in Chennai, and CQA for quality audits."
    )
    spec.sf_opportunity = {
        "Name": "Meridian National Bank ECC",
        "Products__c": "ECC Agent License, IVR, Salesforce Integration, Predictive Dialer, CQA, Voice Logger",
    }
    return spec


# ============================================================
# Scoring Functions
# ============================================================

def score_output(document: str, result: dict, spec: RequirementsSpec) -> dict:
    """Score a pipeline run output across all metrics."""
    validation = result.get("validation", {})
    quality = result.get("quality", {})

    # sections_present
    sections_present = validation.get("sections_present", 0)

    # quality_score (from validator)
    quality_score = quality.get("total", 0)

    # word_count
    word_count = len(document.split())

    # placeholder_count — count [VERIFY], [TBD], [GENERATION FAILED]
    verify_count = document.count("[VERIFY]")
    tbd_count = document.count("[TBD]")
    failed_count = document.count("[GENERATION FAILED")
    placeholder_count = verify_count + tbd_count + failed_count

    # table_count — count Markdown tables (header + separator)
    table_matches = re.findall(r'^\|.+\|\s*\n\|[\s\-:|]+\|', document, re.MULTILINE)
    table_count = len(table_matches)

    # module_references — count occurrences of module IDs like IVR-001, INT-004, etc.
    module_id_pattern = re.compile(r'\b(IVR|INT|BLA|QUE|DAT)-\d{3}\b')
    module_refs = module_id_pattern.findall(document)
    # Count unique full IDs
    full_ids = re.findall(r'\b(?:IVR|INT|BLA|QUE|DAT)-\d{3}\b', document)
    module_references = len(full_ids)
    unique_module_ids = len(set(full_ids))

    # Expected modules from spec
    expected_module_count = sum(len(ids) for ids in spec.modules.values())

    return {
        "sections_present": sections_present,
        "sections_total": 13,
        "quality_score": quality_score,
        "word_count": word_count,
        "placeholder_count": placeholder_count,
        "verify_count": verify_count,
        "tbd_count": tbd_count,
        "failed_count": failed_count,
        "table_count": table_count,
        "module_references": module_references,
        "unique_module_ids": unique_module_ids,
        "expected_modules": expected_module_count,
        "module_coverage_pct": round(unique_module_ids / max(expected_module_count, 1) * 100, 1),
    }


# ============================================================
# Run Eval
# ============================================================

SCENARIOS = [
    ("simple_inbound", "Simple Inbound (Insurance)", build_simple_inbound),
    ("mid_market", "Mid-Market (E-Commerce)", build_mid_market),
    ("enterprise", "Enterprise (Banking)", build_enterprise),
]


def run_eval(scenarios=None, label="baseline"):
    """Run evaluation across all scenarios and return structured results."""
    if scenarios is None:
        scenarios = SCENARIOS

    pipeline = SowPipeline()
    results = {}
    all_scores = []

    for scenario_id, scenario_name, build_fn in scenarios:
        print(f"\n{'='*70}")
        print(f"  SCENARIO: {scenario_name}")
        print(f"{'='*70}")

        spec = build_fn()
        start = time.time()

        try:
            result = pipeline.generate(spec, skip_gdoc=True)
            duration_s = round(time.time() - start, 1)

            document = result.get("document", "")
            scores = score_output(document, result, spec)
            scores["duration_s"] = duration_s
            scores["cost_usd"] = round(result.get("cost_usd", 0), 4)
            scores["status"] = "ok"
            scores["error"] = None

        except Exception as e:
            duration_s = round(time.time() - start, 1)
            scores = {
                "sections_present": 0,
                "sections_total": 13,
                "quality_score": 0,
                "word_count": 0,
                "placeholder_count": 0,
                "verify_count": 0,
                "tbd_count": 0,
                "failed_count": 0,
                "table_count": 0,
                "module_references": 0,
                "unique_module_ids": 0,
                "expected_modules": sum(len(ids) for ids in spec.modules.values()),
                "module_coverage_pct": 0,
                "duration_s": duration_s,
                "cost_usd": 0,
                "status": "error",
                "error": str(e),
            }

        results[scenario_id] = scores
        all_scores.append(scores)

        print(f"\n  --- Scores for {scenario_name} ---")
        print(f"  Sections:     {scores['sections_present']}/13")
        print(f"  Quality:      {scores['quality_score']}/100")
        print(f"  Words:        {scores['word_count']:,}")
        print(f"  Placeholders: {scores['placeholder_count']} (VERIFY:{scores['verify_count']} TBD:{scores['tbd_count']} FAILED:{scores['failed_count']})")
        print(f"  Tables:       {scores['table_count']}")
        print(f"  Module Refs:  {scores['module_references']} ({scores['unique_module_ids']} unique / {scores['expected_modules']} expected = {scores['module_coverage_pct']}%)")
        print(f"  Duration:     {scores['duration_s']}s | Cost: ${scores['cost_usd']}")
        if scores.get("error"):
            print(f"  ERROR:        {scores['error']}")

    # Aggregate
    ok_scores = [s for s in all_scores if s["status"] == "ok"]
    aggregate = {}
    if ok_scores:
        aggregate = {
            "avg_sections": round(sum(s["sections_present"] for s in ok_scores) / len(ok_scores), 1),
            "avg_quality": round(sum(s["quality_score"] for s in ok_scores) / len(ok_scores), 1),
            "avg_words": round(sum(s["word_count"] for s in ok_scores) / len(ok_scores)),
            "avg_placeholders": round(sum(s["placeholder_count"] for s in ok_scores) / len(ok_scores), 1),
            "avg_tables": round(sum(s["table_count"] for s in ok_scores) / len(ok_scores), 1),
            "avg_module_refs": round(sum(s["module_references"] for s in ok_scores) / len(ok_scores), 1),
            "avg_module_coverage_pct": round(sum(s["module_coverage_pct"] for s in ok_scores) / len(ok_scores), 1),
            "total_cost": round(sum(s["cost_usd"] for s in ok_scores), 4),
            "total_duration_s": round(sum(s["duration_s"] for s in ok_scores), 1),
            "scenarios_ok": len(ok_scores),
            "scenarios_total": len(all_scores),
        }

    # Save results
    output = {
        "label": label,
        "timestamp": datetime.now().isoformat(),
        "scenarios": results,
        "aggregate": aggregate,
    }

    results_path = V2_DIR / "scripts" / "eval_results.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {results_path}")

    # Print summary table
    print(f"\n{'='*90}")
    print(f"  EVALUATION SUMMARY — {label}")
    print(f"{'='*90}")
    header = f"{'Scenario':<30} {'Sect':>5} {'Qual':>5} {'Words':>7} {'Plchld':>7} {'Tables':>7} {'ModRef':>7} {'ModCov':>7} {'Cost':>7}"
    print(header)
    print("-" * 90)
    for scenario_id, scenario_name, _ in scenarios:
        s = results.get(scenario_id, {})
        if s.get("status") == "error":
            print(f"{scenario_name:<30} {'ERROR':>5} {'--':>5} {'--':>7} {'--':>7} {'--':>7} {'--':>7} {'--':>7} {'--':>7}")
        else:
            print(f"{scenario_name:<30} {s['sections_present']:>4}/13 {s['quality_score']:>5.1f} {s['word_count']:>7,} {s['placeholder_count']:>7} {s['table_count']:>7} {s['module_references']:>7} {s['module_coverage_pct']:>6.1f}% ${s['cost_usd']:>6.4f}")
    print("-" * 90)
    if aggregate:
        print(f"{'AVERAGE':<30} {aggregate['avg_sections']:>4.0f}/13 {aggregate['avg_quality']:>5.1f} {aggregate['avg_words']:>7,} {aggregate['avg_placeholders']:>7.1f} {aggregate['avg_tables']:>7.1f} {aggregate['avg_module_refs']:>7.1f} {aggregate['avg_module_coverage_pct']:>6.1f}% ${aggregate['total_cost']:>6.4f}")
    print(f"{'='*90}")

    return output


# ============================================================
# TSV Logger
# ============================================================

def log_to_experiments_tsv(label: str, aggregate: dict, description: str = ""):
    """Append a row to experiments.tsv."""
    tsv_path = V2_DIR / "experiments.tsv"
    status = "ok" if aggregate.get("scenarios_ok", 0) == aggregate.get("scenarios_total", 0) else "partial"
    row = "\t".join([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        label,
        str(aggregate.get("avg_sections", 0)),
        str(aggregate.get("avg_quality", 0)),
        str(aggregate.get("avg_words", 0)),
        str(aggregate.get("avg_placeholders", 0)),
        status,
        description,
    ])
    with open(tsv_path, "a") as f:
        f.write(row + "\n")
    print(f"Logged to {tsv_path}")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    description = sys.argv[2] if len(sys.argv) > 2 else ""

    output = run_eval(label=label)

    if output.get("aggregate"):
        log_to_experiments_tsv(label, output["aggregate"], description)
    else:
        print("No successful scenarios — skipping TSV log.")
