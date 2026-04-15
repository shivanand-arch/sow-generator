"""
SOW Generator v2 — Section Generators (13 sections)

Each section has:
- A prompt template that takes RequirementsSpec + RAG context
- Template-fill sections (S2, S5, S11) are generated without LLM
- LLM sections use Gemini Flash (most) or Pro (Section 7)
"""

import json
from datetime import datetime, timedelta


# ============================================================
# Template-fill sections (no LLM needed)
# ============================================================

def generate_s2_versioning(spec):
    """S2: Document Versioning — pure template fill."""
    today = datetime.now().strftime("%d-%b-%Y")
    pm_name = "[PM Name]"
    customer = spec.customer.name or "[Customer Name]"

    return f"""## 2. Document Versioning

| Version | Date | Author | Reviewed By | Description |
|---------|------|--------|-------------|-------------|
| 1.0.0 | {today} | {pm_name} | Amit Singhla | Initial draft — AI-generated, pending PM review |

### Document Control

- **Document Title:** Statement of Work — {customer} ECC Implementation
- **Project ID:** {spec.customer.project_id or '[TBD]'}
- **Classification:** Confidential
- **Distribution:** Internal (Exotel) + {customer} project stakeholders
"""


def generate_s5_licenses(spec):
    """S5: License Components Table — from Salesforce OpportunityLineItems."""
    if not spec.licenses:
        return """## 5. License Components

| # | Component | Quantity | Type | Notes |
|---|-----------|----------|------|-------|
| | [PRODUCTS NOT FOUND IN SALESFORCE — PM TO FILL] | | | |

> **[VERIFY]** License data could not be extracted from Salesforce. Please fill in manually.
"""

    rows = []
    for i, lic in enumerate(spec.licenses, 1):
        component = lic.component if isinstance(lic, object) and hasattr(lic, 'component') else lic.get("component", "")
        count = lic.count if hasattr(lic, 'count') else lic.get("count", 0)
        lic_type = lic.type if hasattr(lic, 'type') else lic.get("type", "")
        retention = lic.retention_days if hasattr(lic, 'retention_days') else lic.get("retention_days", 0)
        notes = f"{retention}-day retention" if retention else ""
        rows.append(f"| {i} | {component} | {count} | {lic_type} | {notes} |")

    table = "\n".join(rows)
    return f"""## 5. License Components

The following ECC license components are provisioned as part of this engagement, per the Salesforce Opportunity record:

| # | Component | Quantity | Type | Notes |
|---|-----------|----------|------|-------|
{table}

> License quantities are sourced from the Salesforce Opportunity. Any changes require a revised PO.
"""


def generate_s11_data_purging(spec):
    """S11: Data Purging Policy — standard boilerplate with parameterized retention."""
    return """## 11. Data Purging Policy

### Retention Periods

| Data Type | Retention Period | Storage Location | Purge Method |
|-----------|-----------------|------------------|--------------|
| Voice Recordings | 90 days | Exotel Cloud Storage | Auto-purge |
| CDR (Call Detail Records) | 90 days | ECC Database | Auto-purge |
| Agent Activity Logs | 90 days | ECC Database | Auto-purge |
| Custom Reports Data | 90 days | ECC Reporting DB | Auto-purge |
| IVR Interaction Logs | 30 days | ECC Database | Auto-purge |
| Chat Transcripts | 90 days | ECC Database | Auto-purge |

### Notes

1. All retention periods begin from the date of data creation.
2. Extended retention is available as an add-on (subject to additional storage charges).
3. Customer may request data export before purge by raising a support ticket with 15 business days' notice.
4. Data purging is irreversible. Exotel is not liable for data loss after the retention period.
5. Retention periods are configurable during implementation. Changes after go-live require a change request.
"""


# ============================================================
# LLM-generated sections — prompt builders
# ============================================================

def _build_context_block(similar_contexts):
    """Build a reference block from similar SOW section excerpts."""
    if not similar_contexts:
        return ""
    parts = ["### Reference Examples from Similar Past SOWs:\n"]
    for i, ctx in enumerate(similar_contexts, 1):
        parts.append(f"**Example {i} ({ctx['customer']} — {ctx.get('industry', 'N/A')}):**")
        parts.append(ctx["text"])
        parts.append("")
    return "\n".join(parts)


def build_s1_prompt(spec, similar_contexts=None):
    """S1: Executive Summary / Document Scope"""
    context = _build_context_block(similar_contexts)
    return f"""You are an expert technical writer for Exotel, a cloud communications platform company.

Write the Executive Summary / Document Scope section for an ECC (Exotel Contact Center) Statement of Work.

## Customer Details
- **Customer:** {spec.customer.name}
- **Industry:** {spec.customer.industry}
- **Country/Region:** {spec.customer.country} / {spec.customer.region}
- **Use Case:** {spec.use_case_type}
- **Deployment:** {spec.deployment.type} ({spec.deployment.infrastructure or 'Exotel Cloud'})
- **Deal Value:** {spec.customer.deal_value}

## Project Context
{spec.additional_requirements or 'Standard ECC implementation project.'}

{context}

## Instructions
- Write 2-3 paragraphs covering: document purpose, business context for the customer, high-level project scope, and expected outcome
- Reference the customer's industry and business needs specifically
- Mention the deployment type and key capabilities being delivered
- Keep professional, concise tone suitable for a contractual document
- Use Markdown formatting with ## header

Output ONLY the section content in Markdown (starting with ## 1. Executive Summary)."""


def build_s3_prompt(spec, similar_contexts=None):
    """S3: Stakeholder Registry & Escalation Matrix"""
    context = _build_context_block(similar_contexts)
    return f"""You are writing the Stakeholder Registry & Escalation Matrix for an Exotel ECC SOW.

## Customer: {spec.customer.name}
## Project ID: {spec.customer.project_id or '[TBD]'}

{context}

## Instructions
Generate two tables:

1. **Stakeholder Registry** with columns: Name, Role, Organization, Email, Phone
   - Exotel side: Project Manager, Technical Lead, Solution Architect, Account Manager (use placeholder names like [Exotel PM Name])
   - Customer side: Project Sponsor, IT Lead, Business Owner, Operations Manager (use [Customer] prefix)

2. **Escalation Matrix** with columns: Level, Exotel Contact, Customer Contact, SLA, Trigger
   - L1: PM to PM — 4 business hours — task delays
   - L2: Delivery Manager to IT Head — 8 business hours — milestone miss
   - L3: VP Delivery to CTO/COO — 16 business hours — project at risk

Output ONLY Markdown starting with ## 3. Stakeholder Registry & Escalation Matrix."""


def build_s4_prompt(spec, similar_contexts=None):
    """S4: Project Overview & Key Deliverables"""
    context = _build_context_block(similar_contexts)
    modules_summary = json.dumps(spec.modules, indent=2)
    return f"""You are writing the Project Overview & Key Deliverables for an Exotel ECC SOW.

## Customer: {spec.customer.name} ({spec.customer.industry})
## Use Case: {spec.use_case_type}
## Deployment: {spec.deployment.type}
## Modules: {modules_summary}

{context}

## Instructions
Write:
1. **Project Overview** (2-3 paragraphs): Business context, why the customer needs ECC, what business problem this solves
2. **Key Deliverables** table with columns: #, Deliverable, Description, Category
   - Map each module category to concrete deliverables
   - Categories: IVR Setup, Integration, Campaign Management, Queue/Routing, Reporting, Training, Documentation

Be specific to the customer's industry ({spec.customer.industry}) and use case ({spec.use_case_type}).

Output ONLY Markdown starting with ## 4. Project Overview & Key Deliverables."""


def build_s6_prompt(spec, similar_contexts=None):
    """S6: Solution Architecture"""
    context = _build_context_block(similar_contexts)
    return f"""You are writing the Solution Architecture section for an Exotel ECC SOW.

## Customer: {spec.customer.name}
## Deployment Type: {spec.deployment.type}
## Infrastructure: {spec.deployment.infrastructure or 'Exotel Cloud'}
## Platform: {spec.deployment.platform or 'ECC'}
## SIP Integration: {spec.deployment.sip_integration or 'Standard'}

## Integrations:
{json.dumps([ig.__dict__ if hasattr(ig, '__dict__') else ig for ig in spec.integrations], indent=2)}

{context}

## Instructions
Write the Solution Architecture section covering:
1. **Architecture Overview**: High-level description of the deployment topology
2. **Component Diagram** (describe in text — the PM will add a visual later):
   - Customer network / SBC / SIP trunk
   - Exotel cloud platform (ECC, IVR engine, queue engine)
   - Integration layer (CRM connectors, API gateway)
   - Reporting layer
3. **Network Requirements**: Bandwidth, latency, codec requirements
4. **Security**: Encryption (TLS/SRTP), authentication, data residency
5. **Deployment Notes**: Specific to {spec.deployment.type} deployment

{"For on-premise: include hardware specs, VM requirements, and network architecture." if spec.deployment.type == "on-premise" else ""}
{"For hybrid: include cloud-to-premise connectivity, VPN/IPSEC requirements." if spec.deployment.type == "hybrid" else ""}

Output ONLY Markdown starting with ## 6. Solution Architecture."""


def build_s7_prompt(spec, similar_contexts=None):
    """S7: Scope Definition — the most complex section. Uses Gemini Pro."""
    context = _build_context_block(similar_contexts)
    modules_detail = json.dumps(spec.modules, indent=2)
    ivr_json = json.dumps(spec.ivr_spec.__dict__ if hasattr(spec.ivr_spec, '__dict__') else spec.ivr_spec, indent=2, default=str)
    integrations_json = json.dumps([ig.__dict__ if hasattr(ig, '__dict__') else ig for ig in spec.integrations], indent=2)

    return f"""You are an expert ECC (Exotel Contact Center) solution architect writing the Scope Definition for a Statement of Work. This is the MOST IMPORTANT section of the SOW — it defines exactly what Exotel will deliver.

## Customer: {spec.customer.name} ({spec.customer.industry}, {spec.customer.country})
## Use Case: {spec.use_case_type}

## Selected Modules:
{modules_detail}

## IVR Specification:
{ivr_json}

## Integrations:
{integrations_json}

## Additional Requirements:
{spec.additional_requirements or 'None specified.'}

{context}

## Instructions

Generate the COMPLETE Scope Definition section with ALL of the following sub-sections:

### 7.1 IVR Configuration & Call Flow
- Describe each IVR menu structure based on the IVR specification above
- For each DID/number: describe the menu tree (Level 1 options, Level 2 sub-menus, etc.)
- Include DTMF mapping (Press 1 for X, Press 2 for Y, etc.)
- Describe routing logic (time-based, skill-based, language-based)
- Include retry/error handling (invalid input → replay prompt, max retries → fallback)

### 7.2 Prompt Description Table
Create a detailed table with columns: Prompt ID, Prompt Name, Description, Script/Text, Language, Type (Static/Dynamic)
- Include ALL prompts: welcome, menu options, queue announcements, error messages, goodbye, CSAT
- If bilingual, include entries for each language

### 7.3 Queue & Routing Configuration
- Queue naming convention
- Routing strategy per queue (skill-based, round-robin, priority)
- Overflow handling
- Agent groups and skills mapping

### 7.4 Customization Scope
- Any custom development beyond standard configuration
- Custom IVR nodes, API integrations, reports

### 7.5 Integration Scope
- For each integration: system name, direction (inbound/outbound/bidirectional), protocol (REST/SOAP/webhook)
- Data fields exchanged
- Authentication method
- Error handling

### 7.6 Reports & Analytics Scope
- Standard reports included
- Custom reports (if any)
- Dashboard requirements
- Scheduled report delivery

### 7.7 Out of Scope
- Explicitly list what is NOT included in this engagement
- Use bullet points
- Be specific (e.g., "WhatsApp channel integration" not just "other channels")

## Formatting Rules
- Use Markdown tables for structured data
- Use bullet lists for configuration items
- Mark any assumptions or inferred items with [VERIFY]
- Be THOROUGH — this section is typically 3,000-5,000 words for a mid-complexity project
- Do NOT include modules that are not in the Selected Modules list above

Output ONLY Markdown starting with ## 7. Scope Definition."""


def build_s8_prompt(spec, similar_contexts=None):
    """S8: Requirements Traceability Matrix"""
    modules_detail = json.dumps(spec.modules, indent=2)
    return f"""You are writing the Requirements Traceability Matrix (RTM) for an Exotel ECC SOW.

## Customer: {spec.customer.name}
## Modules: {modules_detail}

## Instructions
Generate an RTM table with columns:
| Req ID | Requirement | Module ID | Design Reference | Test Case ID | Status |

Rules:
- One row per selected module
- Req ID format: REQ-001, REQ-002, etc.
- Requirement: describe what the module delivers in business terms
- Module ID: the exact module ID from the catalog (e.g., IVR-001, INT-004)
- Design Reference: "SOW Section 7.X" pointing to the relevant scope sub-section
- Test Case ID: TC-001, TC-002, etc.
- Status: "Planned" for all rows

Output ONLY Markdown starting with ## 8. Requirements Traceability Matrix."""


def build_s9_prompt(spec, similar_contexts=None):
    """S9: Project Prerequisites"""
    context = _build_context_block(similar_contexts)
    return f"""You are writing the Project Prerequisites section for an Exotel ECC SOW.

## Customer: {spec.customer.name}
## Deployment: {spec.deployment.type}
## Integrations: {json.dumps([ig.__dict__ if hasattr(ig, '__dict__') else ig for ig in spec.integrations], indent=2)}

{context}

## Instructions
Generate a prerequisites table with columns: #, Prerequisite, Owner (Exotel/Customer/Joint), Due By (Phase), Status

Include prerequisites for:
1. **Infrastructure**: Network connectivity, firewall rules, VPN setup (if on-prem/hybrid), SIP trunk provisioning
2. **Integrations**: CRM API credentials, endpoint URLs, test environment access, documentation
3. **Customer Readiness**: Call flow finalization, prompt recordings, agent skill mapping, queue structure approval
4. **Data**: Agent list with skills, customer DID numbers, business hours schedule
5. **Access**: Admin portal access, test phone numbers, staging environment

Be specific to the deployment type ({spec.deployment.type}) and integrations.

Output ONLY Markdown starting with ## 9. Project Prerequisites."""


def build_s10_prompt(spec, similar_contexts=None):
    """S10: Deliverables Descoped"""
    modules_detail = json.dumps(spec.modules, indent=2)
    return f"""You are writing the Deliverables Descoped section for an Exotel ECC SOW.

## Customer: {spec.customer.name} ({spec.customer.industry})
## Use Case: {spec.use_case_type}
## Included Modules: {modules_detail}
## IVR Complexity: {spec.ivr_spec.complexity if hasattr(spec.ivr_spec, 'complexity') else 'medium'}

## Instructions
List items explicitly NOT included in this engagement. Be specific and actionable.

Typical descoped items (include relevant ones):
- Channels not included (e.g., WhatsApp, SMS, email, social media — if not in modules)
- Advanced features not selected (e.g., speech recognition, AI chatbot, workforce management)
- Custom development beyond X hours
- Third-party software licenses
- On-site training (if remote-only engagement)
- Data migration from legacy system (unless Migration type)
- Custom report development beyond standard reports
- Hardware procurement (for on-prem)
- Network infrastructure changes at customer premises

Format as a bullet list with brief explanations for each item.

Output ONLY Markdown starting with ## 10. Deliverables Descoped."""


def build_s12_prompt(spec, similar_contexts=None):
    """S12: Implementation Plan"""
    # Estimate timeline based on complexity
    module_count = sum(len(mods) for mods in spec.modules.values())
    ivr_complexity = spec.ivr_spec.complexity if hasattr(spec.ivr_spec, 'complexity') else "medium"

    if module_count <= 10 and ivr_complexity == "low":
        total_weeks = 4
        project_size = "SMB"
    elif module_count <= 25 or ivr_complexity == "medium":
        total_weeks = 8
        project_size = "Mid-Market"
    else:
        total_weeks = 16
        project_size = "Enterprise"

    return f"""You are writing the Implementation Plan for an Exotel ECC SOW.

## Customer: {spec.customer.name}
## Project Size: {project_size}
## Total Estimated Duration: {total_weeks} weeks
## Module Count: {module_count}
## IVR Complexity: {ivr_complexity}

## Instructions
Generate a phased implementation plan as a table with columns:
| Phase | Activity | Duration | Start (Week) | End (Week) | Deliverable | Dependencies |

Standard 12-phase ECC implementation:
1. Project Kickoff & Planning (1 week)
2. Requirement Deep-Dive & Design (1-2 weeks)
3. Environment Setup & Provisioning (1 week)
4. IVR Development & Configuration (1-3 weeks based on complexity)
5. Queue & Routing Configuration (1 week)
6. Integration Development (1-3 weeks)
7. Custom Development (if any) (1-2 weeks)
8. System Integration Testing (SIT) (1 week)
9. User Acceptance Testing (UAT) (1-2 weeks)
10. Agent Training (0.5-1 week)
11. Go-Live & Cutover (0.5-1 week)
12. Hypercare & Stabilization (2 weeks)

Scale durations to fit the {total_weeks}-week total. Overlap phases where possible.

Also include:
- **Milestones** table: Key milestones with target dates (use Week N format)
- **Assumptions**: 2-3 key timeline assumptions

Output ONLY Markdown starting with ## 12. Implementation Plan."""


def build_s13_prompt(spec, similar_contexts=None):
    """S13: Approvals, UAT & Change Management"""
    return f"""You are writing the Approvals, UAT & Change Management section for an Exotel ECC SOW.

## Customer: {spec.customer.name}

## Instructions
Generate the following sub-sections:

### 13.1 Approval Process
- SOW sign-off process (customer + Exotel)
- Design approval gate (before development begins)
- UAT sign-off criteria

### 13.2 User Acceptance Testing
- UAT scope and duration
- UAT entry criteria (SIT complete, test cases prepared)
- UAT exit criteria (all P1/P2 defects resolved, sign-off from customer)
- Defect classification (P1: Blocker, P2: Major, P3: Minor, P4: Cosmetic)
- UAT environment details

### 13.3 Change Management
- Change request process
- Impact assessment (timeline, cost, scope)
- Change approval authority
- Change request form (table with fields: CR ID, Description, Requested By, Impact, Priority, Status)

### 13.4 Roles & Responsibilities
RACI matrix with columns: Activity, Exotel PM, Exotel Tech, Customer PM, Customer IT
Key activities: Requirements, Design, Development, Testing, Training, Go-Live, Support

Output ONLY Markdown starting with ## 13. Approvals, UAT & Change Management."""


# ============================================================
# Section generator registry
# ============================================================

SECTION_GENERATORS = {
    "S1":  {"prompt_fn": build_s1_prompt,  "model": "fast",   "max_tokens": 1500},
    "S2":  {"template_fn": generate_s2_versioning},
    "S3":  {"prompt_fn": build_s3_prompt,  "model": "fast",   "max_tokens": 2000},
    "S4":  {"prompt_fn": build_s4_prompt,  "model": "fast",   "max_tokens": 3000},
    "S5":  {"template_fn": generate_s5_licenses},
    "S6":  {"prompt_fn": build_s6_prompt,  "model": "fast",   "max_tokens": 3000},
    "S7":  {"prompt_fn": build_s7_prompt,  "model": "strong", "max_tokens": 8000},
    "S8":  {"prompt_fn": build_s8_prompt,  "model": "fast",   "max_tokens": 3000},
    "S9":  {"prompt_fn": build_s9_prompt,  "model": "fast",   "max_tokens": 2000},
    "S10": {"prompt_fn": build_s10_prompt, "model": "fast",   "max_tokens": 1500},
    "S11": {"template_fn": generate_s11_data_purging},
    "S12": {"prompt_fn": build_s12_prompt, "model": "fast",   "max_tokens": 3000},
    "S13": {"prompt_fn": build_s13_prompt, "model": "fast",   "max_tokens": 3000},
}
