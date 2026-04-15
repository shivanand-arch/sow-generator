#!/usr/bin/env python3
"""
SOW Generator v2 — Delivery Team Streamlit UI

Usage:
    streamlit run streamlit_app.py --server.port 8502
"""

import json
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

import streamlit as st

# Add v2 dir to path
V2_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(V2_DIR))

from schema import (
    RequirementsSpec, CustomerInfo, DeploymentInfo,
    IvrSpec, IntegrationSpec, LicenseComponent, ModuleCatalog,
)
from pipeline import SowPipeline
from config import SOW_SECTIONS

# ============================================================
# Page Config
# ============================================================

st.set_page_config(
    page_title="Delivery SOW Generator",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Sidebar — Config & Module Catalog
# ============================================================

with st.sidebar:
    st.title("⚙️ Configuration")

    st.markdown("**Pipeline:** Claude Sonnet 4.6 + Opus 4.6")
    st.markdown("**Template:** 13-Section (Jan 2026)")
    st.markdown("**Cost ceiling:** $5.00/SOW")

    st.divider()
    skip_gdoc = st.checkbox("Skip Google Doc creation", value=False)

    st.divider()
    with st.expander("📦 Module Catalog", expanded=False):
        try:
            catalog = ModuleCatalog()
            for cat_name, modules in catalog.catalog.items():
                st.markdown(f"**{cat_name}** ({len(modules)} modules)")
                for mod_id, mod_info in list(modules.items())[:5]:
                    name = mod_info if isinstance(mod_info, str) else mod_info.get("name", mod_id)
                    st.caption(f"  `{mod_id}` — {name}")
                if len(modules) > 5:
                    st.caption(f"  ... +{len(modules) - 5} more")
        except Exception as e:
            st.warning(f"Module catalog unavailable: {e}")

    st.divider()
    st.caption("SOW Generator v2 — Delivery Team")
    st.caption(f"Built for Amit Singhla's ECC Delivery PMs")

# ============================================================
# Helper Functions
# ============================================================

def _infer_region(country):
    """Infer region from country name."""
    region_map = {
        "India": "South Asia", "Bangladesh": "South Asia",
        "UAE": "Middle East", "Saudi Arabia": "Middle East",
        "Singapore": "Southeast Asia", "Malaysia": "Southeast Asia",
        "Indonesia": "Southeast Asia", "Philippines": "Southeast Asia",
    }
    return region_map.get(country, "Asia Pacific")

# ============================================================
# Main Content
# ============================================================

st.title("📋 Delivery SOW Generator")
st.markdown("Generate a **13-section Statement of Work** for ECC Delivery projects. Fill in the customer details below and click **Generate**.")

# ============================================================
# Input Form
# ============================================================

with st.form("sow_form"):

    st.subheader("1️⃣ Customer Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        customer_name = st.text_input("Customer Name *", placeholder="e.g., HDFC Bank")
        industry = st.selectbox("Industry *", [
            "Banking & Financial Services", "Insurance", "E-Commerce",
            "Healthcare", "Telecom", "EdTech", "Logistics",
            "Real Estate", "Fintech", "SaaS", "Automotive",
            "Retail", "Government", "Other",
        ])
    with col2:
        country = st.selectbox("Country", [
            "India", "UAE", "Saudi Arabia", "Singapore", "Malaysia",
            "Indonesia", "Philippines", "Bangladesh", "Other",
        ])
        deal_value = st.text_input("Deal Value", placeholder="e.g., ₹15,00,000 or $18,000")
    with col3:
        project_id = st.text_input("Project ID", placeholder="e.g., PRJ-2026-HDFC-001")
        mrr = st.text_input("MRR", placeholder="e.g., ₹1,25,000 or $1,500")

    st.divider()

    # -------------------------------------------------------
    # Deployment
    # -------------------------------------------------------
    st.subheader("2️⃣ Deployment")
    col1, col2 = st.columns(2)
    with col1:
        deployment_type = st.selectbox("Deployment Type *", [
            "Cloud (Exotel-hosted)", "On-Premise", "Hybrid", "Emerge",
        ])
        sip_integration = st.text_input("SIP Integration", placeholder="e.g., Standard SIP, Cisco CUBE, AudioCodes")
    with col2:
        use_case_type = st.selectbox("Use Case Type *", [
            "Inbound Voice", "Outbound Dialer", "Inbound + Outbound",
            "Omnichannel", "Migration", "DR Setup", "POC",
        ])
        infrastructure = st.text_input("Infrastructure", placeholder="e.g., Exotel Cloud, Customer DC Mumbai")

    st.divider()

    # -------------------------------------------------------
    # IVR Configuration
    # -------------------------------------------------------
    st.subheader("3️⃣ IVR Configuration")
    col1, col2, col3 = st.columns(3)
    with col1:
        ivr_complexity = st.selectbox("IVR Complexity *", ["Low", "Medium", "High", "Custom"])
        languages = st.multiselect("Languages", [
            "English", "Hindi", "Tamil", "Telugu", "Kannada",
            "Malayalam", "Bengali", "Marathi", "Gujarati", "Arabic",
        ], default=["English"])
    with col2:
        inbound_dids = st.text_area("Inbound DIDs (one per line)", placeholder="+91-80-XXXX-1001\n+91-80-XXXX-1002")
        csat = st.checkbox("Post-call CSAT survey")
    with col3:
        callback = st.checkbox("Callback queue")
        vip_routing = st.checkbox("VIP / priority routing")
        ivr_description = st.text_area("IVR Menu Description", placeholder="Describe the IVR menu structure, options, and routing logic...", height=120)

    st.divider()

    # -------------------------------------------------------
    # Integrations
    # -------------------------------------------------------
    st.subheader("4️⃣ Integrations")
    col1, col2 = st.columns(2)
    with col1:
        crm_system = st.selectbox("CRM Integration", [
            "None", "Salesforce", "Zoho CRM", "Freshdesk",
            "LeadSquared", "HubSpot", "Custom URL / API",
        ])
        crm_features = st.multiselect("CRM Features", [
            "Screen Pop", "Click-to-Dial", "Call Disposition",
            "Contact Lookup", "Case Creation", "Recording URL Sync",
        ], default=["Screen Pop", "Click-to-Dial"] if crm_system != "None" else [])
    with col2:
        other_integrations = st.text_area(
            "Other Integrations (one per line)",
            placeholder="e.g., Core Banking (Finacle) — bidirectional\nPayment Gateway — outbound",
            height=100,
        )

    st.divider()

    # -------------------------------------------------------
    # Licenses
    # -------------------------------------------------------
    st.subheader("5️⃣ Licenses")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        agent_count = st.number_input("ECC Agent Licenses", min_value=0, value=10, step=5)
    with col2:
        voice_channels = st.number_input("Voice Channels", min_value=0, value=5, step=5)
    with col3:
        voice_logger = st.number_input("Voice Logger Licenses", min_value=0, value=0, step=5)
    with col4:
        retention_days = st.number_input("Retention (days)", min_value=30, value=90, step=30)

    additional_licenses = st.text_area(
        "Additional Licenses (one per line: name, count, type)",
        placeholder="e.g., Predictive Dialer License, 20, Per Agent\nCQA License, 10, Per Seat",
        height=80,
    )

    st.divider()

    # -------------------------------------------------------
    # Additional Context
    # -------------------------------------------------------
    st.subheader("6️⃣ Additional Context")
    sf_products = st.text_input("SF Products (for auto module matching)", placeholder="e.g., ECC Agent License, IVR, Zoho Integration, CSAT, Reporting")
    additional_requirements = st.text_area(
        "Additional Requirements / Notes",
        placeholder="Any special requirements, constraints, or context the SOW should address...",
        height=100,
    )

    st.divider()

    # -------------------------------------------------------
    # Submit
    # -------------------------------------------------------
    submitted = st.form_submit_button("🚀 Generate 13-Section SOW", type="primary", use_container_width=True)


# ============================================================
# Build RequirementsSpec & Generate
# ============================================================

if submitted:
    # Validation
    if not customer_name.strip():
        st.error("Customer Name is required.")
        st.stop()

    # Build spec
    spec = RequirementsSpec()
    spec.customer = CustomerInfo(
        name=customer_name.strip(),
        industry=industry,
        country=country,
        region=_infer_region(country),
        project_id=project_id.strip() or f"PRJ-{datetime.now().strftime('%Y')}-{customer_name[:3].upper()}-001",
        deal_value=deal_value.strip(),
        mrr=mrr.strip(),
    )

    deploy_type_map = {
        "Cloud (Exotel-hosted)": "cloud",
        "On-Premise": "on-premise",
        "Hybrid": "hybrid",
        "Emerge": "emerge",
    }
    spec.deployment = DeploymentInfo(
        type=deploy_type_map.get(deployment_type, "cloud"),
        infrastructure=infrastructure.strip() or ("Exotel Cloud" if "Cloud" in deployment_type else "Customer Data Center"),
        platform="ECC",
        sip_integration=sip_integration.strip() or "Standard SIP",
    )

    # Licenses
    spec.licenses = []
    if agent_count > 0:
        spec.licenses.append(LicenseComponent(component="ECC Agent License", count=agent_count, type="Concurrent", retention_days=retention_days))
    if voice_channels > 0:
        spec.licenses.append(LicenseComponent(component="Voice Channel", count=voice_channels, type="Channel", retention_days=retention_days))
    if voice_logger > 0:
        spec.licenses.append(LicenseComponent(component="Voice Logger", count=voice_logger, type="Per Agent", retention_days=retention_days))

    # Parse additional licenses
    if additional_licenses.strip():
        for line in additional_licenses.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                spec.licenses.append(LicenseComponent(
                    component=parts[0], count=int(parts[1]) if parts[1].isdigit() else 0,
                    type=parts[2], retention_days=retention_days,
                ))

    # IVR
    dids = [d.strip() for d in inbound_dids.strip().split("\n") if d.strip()] if inbound_dids.strip() else []
    spec.ivr_spec = IvrSpec(
        complexity=ivr_complexity.lower(),
        inbound_dids=dids,
        languages=languages,
        menus=[],
        csat=csat,
        callback=callback,
        vip_routing=vip_routing,
        custom_description=ivr_description.strip(),
    )

    # Integrations
    spec.integrations = []
    if crm_system != "None":
        feature_map = {
            "Screen Pop": "screen_pop", "Click-to-Dial": "click_to_dial",
            "Call Disposition": "call_disposition", "Contact Lookup": "contact_lookup",
            "Case Creation": "case_creation", "Recording URL Sync": "recording_url",
        }
        spec.integrations.append(IntegrationSpec(
            type="CRM", system=crm_system, direction="bidirectional",
            features=[feature_map.get(f, f.lower().replace(" ", "_")) for f in crm_features],
        ))

    if other_integrations.strip():
        for line in other_integrations.strip().split("\n"):
            parts = [p.strip() for p in line.split("—")]
            if parts:
                spec.integrations.append(IntegrationSpec(
                    type="Custom", system=parts[0],
                    direction=parts[1] if len(parts) > 1 else "bidirectional",
                ))

    spec.use_case_type = use_case_type
    spec.additional_requirements = additional_requirements.strip()
    spec.sf_opportunity = {
        "Name": f"{customer_name} ECC",
        "Products__c": sf_products.strip(),
    }

    # Auto-match modules from SF products
    try:
        catalog = ModuleCatalog()
        spec.modules = catalog.match_from_products(
            sf_products.strip(),
            additional_requirements.strip(),
        )
    except Exception:
        spec.modules = {}

    # -------------------------------------------------------
    # Show spec summary before generating
    # -------------------------------------------------------
    with st.expander("📋 RequirementsSpec (review before generation)", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Customer:** {spec.customer.name} ({spec.customer.industry})")
            st.markdown(f"**Country:** {spec.customer.country} | **Deal:** {spec.customer.deal_value}")
            st.markdown(f"**Deployment:** {spec.deployment.type} — {spec.deployment.infrastructure}")
            st.markdown(f"**Use Case:** {spec.use_case_type}")
        with col2:
            st.markdown(f"**IVR:** {spec.ivr_spec.complexity} complexity, {len(spec.ivr_spec.languages)} language(s)")
            st.markdown(f"**Integrations:** {len(spec.integrations)} system(s)")
            st.markdown(f"**Licenses:** {len(spec.licenses)} component(s), {sum(l.count for l in spec.licenses)} total seats")
            mod_count = sum(len(v) for v in spec.modules.values())
            st.markdown(f"**Modules matched:** {mod_count} across {len(spec.modules)} categories")

    # -------------------------------------------------------
    # Generate SOW
    # -------------------------------------------------------
    st.divider()
    st.subheader("🔄 Generating SOW...")

    progress_bar = st.progress(0, text="Initializing pipeline...")
    status_area = st.empty()
    section_status = st.container()

    try:
        # Initialize pipeline
        pipeline = SowPipeline()
        progress_bar.progress(5, text="Pipeline initialized. Starting generation...")

        # Run generation
        start_time = time.time()
        result = pipeline.generate(spec, skip_gdoc=skip_gdoc)
        elapsed = time.time() - start_time

        progress_bar.progress(100, text=f"✅ SOW generated in {elapsed:.0f}s")

        # -------------------------------------------------------
        # Results Display
        # -------------------------------------------------------
        st.divider()
        st.subheader("✅ SOW Generated Successfully")

        # Metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        quality = result.get("quality", {})
        col1.metric("Quality Score", f"{quality.get('total', 0)}/100", quality.get("grade", ""))
        col2.metric("Word Count", f"{len(result.get('document', '').split()):,}")
        col3.metric("Sections", f"{result.get('validation', {}).get('sections_present', 0)}/13")
        col4.metric("Cost", f"${result.get('cost_usd', 0):.2f}")
        col5.metric("Duration", f"{elapsed:.0f}s")

        # Tabs
        tab_doc, tab_quality, tab_spec, tab_raw = st.tabs(["📄 SOW Document", "📊 Quality Report", "🔧 RequirementsSpec", "📝 Raw Markdown"])

        with tab_doc:
            st.markdown(result.get("document", "No document generated."))

            # Download buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                docx_path = result.get("files", {}).get("docx")
                if docx_path and Path(docx_path).exists():
                    with open(docx_path, "rb") as f:
                        st.download_button(
                            "📥 Download DOCX",
                            data=f.read(),
                            file_name=Path(docx_path).name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )
            with col2:
                st.download_button(
                    "📥 Download Markdown",
                    data=result.get("document", ""),
                    file_name=f"SOW_{customer_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with col3:
                st.download_button(
                    "📥 Download JSON (spec)",
                    data=spec.to_json(),
                    file_name=f"spec_{customer_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True,
                )

            # Google Doc link
            gdoc_url = result.get("files", {}).get("google_doc")
            if gdoc_url:
                st.success(f"📎 [Open in Google Docs]({gdoc_url})")

        with tab_quality:
            validation = result.get("validation", {})
            quality = result.get("quality", {})

            st.markdown(f"**Grade: {quality.get('grade', 'N/A')}** — {quality.get('total', 0)}/100")

            # Breakdown
            breakdown = quality.get("breakdown", {})
            if breakdown:
                st.markdown("#### Score Breakdown")
                for key, val in breakdown.items():
                    if isinstance(val, (int, float)):
                        st.markdown(f"- **{key.replace('_', ' ').title()}:** {val}")

            # Validation issues
            issues = validation.get("issues", [])
            if issues:
                st.markdown("#### ⚠️ Validation Issues")
                for issue in issues:
                    st.warning(f"{issue.get('type', 'unknown')}: {issue.get('section', issue.get('text', ''))}")

            # Verify flags
            verify_count = validation.get("verify_count", 0)
            if verify_count > 0:
                st.info(f"📝 {verify_count} `[VERIFY]` tags found — these mark items requiring PM review.")

        with tab_spec:
            st.json(spec.to_dict())

        with tab_raw:
            st.code(result.get("document", ""), language="markdown")

    except Exception as e:
        progress_bar.progress(0, text="❌ Generation failed")
        st.error(f"Pipeline error: {e}")
        st.exception(e)
