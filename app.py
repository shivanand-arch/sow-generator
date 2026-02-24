"""
Exotel SOW Generator - Streamlit UI
AI-powered Statement of Work generator using Gemini 3 Flash
"""

import streamlit as st
import google.generativeai as genai
import json
import tempfile
import os
from datetime import datetime
from io import BytesIO

# Page config
st.set_page_config(
    page_title="Exotel SOW Generator",
    page_icon="📄",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #D1FAE5;
        border: 1px solid #10B981;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #DBEAFE;
        border: 1px solid #3B82F6;
    }
</style>
""", unsafe_allow_html=True)

# Module catalog
MODULE_CATALOG = {
    "IVR": {
        "IVR-001": "Welcome Message",
        "IVR-002": "Language Selection",
        "IVR-003": "Main Menu",
        "IVR-007": "DTMF Input Capture",
        "IVR-010": "PIN Verification",
        "IVR-011": "OTP Generation & Validation",
        "IVR-015": "Consent Capture",
        "IVR-019": "Self-Service Balance Inquiry",
        "IVR-020": "Order Status Check",
        "IVR-023": "Callback Request",
        "IVR-029": "Time-Based Routing",
        "IVR-033": "Appointment Booking"
    },
    "Integration": {
        "INT-001": "REST API Outbound",
        "INT-002": "Webhook Configuration",
        "INT-004": "Salesforce Integration",
        "INT-007": "Zoho CRM Integration",
        "INT-008": "Freshdesk Integration",
        "INT-013": "Payment Gateway Integration",
        "INT-014": "SMS Gateway Integration",
        "INT-017": "Custom CRM Integration",
        "INT-021": "Screen Pop",
        "INT-023": "Post-Call Data Push"
    },
    "Blaster": {
        "BLA-002": "Outbound Campaign Setup",
        "BLA-003": "Auto Callback",
        "BLA-004": "Collections Campaign",
        "BLA-007": "Click-to-Dial",
        "BLA-010": "Progressive Dialer",
        "BLA-011": "Predictive Dialer",
        "BLA-018": "Retry Logic Configuration"
    },
    "Queue": {
        "QUE-001": "Basic Queue",
        "QUE-002": "Skill-Based Routing",
        "QUE-003": "Priority Queue",
        "QUE-007": "Sticky Agent",
        "QUE-012": "Callback from Queue",
        "QUE-019": "Multi-Queue Agent",
        "QUE-020": "Supervisor Monitor"
    },
    "Data": {
        "DAT-001": "CDR Export",
        "DAT-007": "Custom Reports",
        "DAT-009": "Real-Time Dashboard",
        "DAT-010": "Survey Responses",
        "DAT-011": "Agent Performance Reports"
    }
}

def init_gemini(api_key):
    """Initialize Gemini client"""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')

def extract_requirements(model, transcript):
    """Extract structured requirements from transcript"""
    prompt = f"""You are an expert at analyzing call transcripts for Exotel, a cloud communications platform.

## Task
Extract structured requirements from this call transcript.

## Call Transcript:
{transcript}

## Output Format:
Return a valid JSON object with:
{{
    "customer": "Customer Name",
    "project": "Project Name",
    "industry": "Industry type",
    "attendees": [{{"name": "Name", "role": "Role"}}],
    "requirements": ["Requirement 1", "Requirement 2"],
    "modules_needed": ["Module descriptions"],
    "integrations": ["Integration needs"],
    "timeline": "Expected timeline",
    "notes": ["Additional notes"]
}}

Return ONLY the JSON, no other text."""

    response = model.generate_content(prompt)
    text = response.text

    # Extract JSON
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())

def generate_sow_content(model, requirements):
    """Generate full SOW content"""
    prompt = f"""You are an expert technical writer for Exotel.

## Task
Generate a detailed Statement of Work based on these requirements.

## Requirements:
{json.dumps(requirements, indent=2)}

## Available Modules:
{json.dumps(MODULE_CATALOG, indent=2)}

## Output Format:
Return a JSON object with:
{{
    "title": "SOW Title",
    "customer": "Customer Name",
    "project": "Project Name",
    "version": "1.0.0",
    "date": "{datetime.now().strftime('%Y-%m-%d')}",
    "executive_summary": "Brief summary of the project",
    "business_goals": ["Goal 1", "Goal 2"],
    "scope": {{
        "in_scope": ["Item 1", "Item 2"],
        "out_of_scope": ["Item 1"]
    }},
    "modules": [
        {{
            "id": "MODULE-ID",
            "name": "Module Name",
            "description": "Detailed description",
            "configuration": "Specific configuration"
        }}
    ],
    "prerequisites": [
        {{"item": "Description", "owner": "Client/Exotel", "status": "Required"}}
    ],
    "timeline": [
        {{"phase": "Phase 1", "activities": "Description", "duration": "X days"}}
    ],
    "total_duration": "X days",
    "assumptions": ["Assumption 1"],
    "dependencies": ["Dependency 1"],
    "acceptance_criteria": ["Criteria 1"],
    "escalation_matrix": [
        {{"level": "L1", "contact": "Name", "response_time": "X hours"}}
    ]
}}

Return ONLY the JSON."""

    response = model.generate_content(prompt)
    text = response.text

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())

def generate_flowchart_structure(model, requirements):
    """Generate flowchart structure"""
    prompt = f"""You are an expert at creating IVR and call flow diagrams.

## Task
Generate a flowchart structure for these requirements.

## Requirements:
{json.dumps(requirements, indent=2)}

## Output Format:
Return a JSON object with:
{{
    "title": "Flowchart Title",
    "nodes": [
        {{
            "id": "node_1",
            "type": "start",
            "label": "Start"
        }},
        {{
            "id": "node_2",
            "type": "process",
            "label": "Process Step"
        }}
    ],
    "edges": [
        {{
            "from": "node_1",
            "to": "node_2",
            "label": ""
        }}
    ]
}}

Node types: start, end, process, decision, api, queue, disconnect

Return ONLY the JSON."""

    response = model.generate_content(prompt)
    text = response.text

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())

def generate_drawio_xml(flowchart):
    """Convert flowchart structure to draw.io XML"""
    node_styles = {
        "start": "ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
        "end": "ellipse;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;",
        "process": "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
        "decision": "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
        "api": "rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;",
        "queue": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8fc;strokeColor=#6c8ebf;",
        "disconnect": "ellipse;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;"
    }

    # Calculate positions
    nodes = flowchart.get("nodes", [])
    edges = flowchart.get("edges", [])

    cells = []
    node_positions = {}

    y_pos = 40
    for i, node in enumerate(nodes):
        node_id = node.get("id", f"node_{i}")
        node_type = node.get("type", "process")
        label = node.get("label", "")
        style = node_styles.get(node_type, node_styles["process"])

        width = 120 if node_type != "decision" else 100
        height = 60 if node_type != "decision" else 80
        x_pos = 300

        node_positions[node_id] = {"x": x_pos, "y": y_pos, "w": width, "h": height}

        cells.append(f'''      <mxCell id="{node_id}" value="{label}" style="{style}" vertex="1" parent="1">
        <mxGeometry x="{x_pos}" y="{y_pos}" width="{width}" height="{height}" as="geometry"/>
      </mxCell>''')

        y_pos += height + 60

    # Add edges
    for i, edge in enumerate(edges):
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")
        label = edge.get("label", "")

        cells.append(f'''      <mxCell id="edge_{i}" value="{label}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;" edge="1" parent="1" source="{from_id}" target="{to_id}">
        <mxGeometry relative="1" as="geometry"/>
      </mxCell>''')

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="{datetime.now().isoformat()}" agent="Exotel SOW Generator" version="1.0">
  <diagram name="Flow" id="flow-diagram">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{chr(10).join(cells)}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

    return xml

def format_sow_markdown(sow):
    """Format SOW as markdown for display"""
    md = f"""# {sow.get('title', 'Statement of Work')}

**Customer:** {sow.get('customer', 'N/A')}
**Project:** {sow.get('project', 'N/A')}
**Version:** {sow.get('version', '1.0.0')}
**Date:** {sow.get('date', datetime.now().strftime('%Y-%m-%d'))}

---

## Executive Summary

{sow.get('executive_summary', 'N/A')}

## Business Goals

"""
    for goal in sow.get('business_goals', []):
        md += f"- {goal}\n"

    md += "\n## Scope\n\n### In Scope\n\n"
    for item in sow.get('scope', {}).get('in_scope', []):
        md += f"- {item}\n"

    md += "\n### Out of Scope\n\n"
    for item in sow.get('scope', {}).get('out_of_scope', []):
        md += f"- {item}\n"

    md += "\n## Modules\n\n"
    md += "| Module ID | Name | Description |\n"
    md += "|-----------|------|-------------|\n"
    for module in sow.get('modules', []):
        md += f"| {module.get('id', '')} | {module.get('name', '')} | {module.get('description', '')} |\n"

    md += "\n## Prerequisites\n\n"
    md += "| Item | Owner | Status |\n"
    md += "|------|-------|--------|\n"
    for prereq in sow.get('prerequisites', []):
        md += f"| {prereq.get('item', '')} | {prereq.get('owner', '')} | {prereq.get('status', '')} |\n"

    md += "\n## Timeline\n\n"
    md += "| Phase | Activities | Duration |\n"
    md += "|-------|------------|----------|\n"
    for phase in sow.get('timeline', []):
        md += f"| {phase.get('phase', '')} | {phase.get('activities', '')} | {phase.get('duration', '')} |\n"

    md += f"\n**Total Duration:** {sow.get('total_duration', 'TBD')}\n"

    md += "\n## Assumptions\n\n"
    for assumption in sow.get('assumptions', []):
        md += f"- {assumption}\n"

    md += "\n## Acceptance Criteria\n\n"
    for criteria in sow.get('acceptance_criteria', []):
        md += f"- {criteria}\n"

    return md

# Main UI
st.markdown('<p class="main-header">📄 Exotel SOW Generator</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-powered Statement of Work generator using Gemini 3 Flash</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="Get your API key from Google AI Studio"
    )

    st.divider()

    st.header("📊 Module Catalog")
    with st.expander("View Available Modules"):
        for category, modules in MODULE_CATALOG.items():
            st.subheader(category)
            for mod_id, mod_name in modules.items():
                st.text(f"{mod_id}: {mod_name}")

    st.divider()

    st.markdown("""
    ### About
    This tool generates professional SOW documents from call transcripts using AI.

    **Powered by:**
    - Gemini 3 Flash
    - 1,800+ historical SOWs
    - 152 ECC modules
    """)

# Main content
if not api_key:
    st.info("👈 Enter your Gemini API key in the sidebar to get started")
    st.stop()

# Initialize model
try:
    model = init_gemini(api_key)
except Exception as e:
    st.error(f"Failed to initialize Gemini: {e}")
    st.stop()

# File upload
st.header("📤 Upload Call Transcript")

uploaded_file = st.file_uploader(
    "Upload a call transcript or meeting notes",
    type=["txt", "pdf", "md"],
    help="Supported formats: TXT, PDF, MD"
)

# Or paste text
transcript_text = st.text_area(
    "Or paste your transcript here:",
    height=200,
    placeholder="Paste your call transcript, meeting notes, or requirements here..."
)

# Process button
if st.button("🚀 Generate SOW", type="primary", use_container_width=True):
    # Get transcript
    transcript = ""

    if uploaded_file:
        if uploaded_file.type == "text/plain":
            transcript = uploaded_file.read().decode("utf-8")
        elif uploaded_file.type == "application/pdf":
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                transcript = "\n".join([page.extract_text() for page in pdf_reader.pages])
            except ImportError:
                st.error("PDF support requires PyPDF2. Please paste text instead.")
                st.stop()
        else:
            transcript = uploaded_file.read().decode("utf-8")
    elif transcript_text:
        transcript = transcript_text
    else:
        st.warning("Please upload a file or paste your transcript")
        st.stop()

    if len(transcript) < 50:
        st.warning("Transcript seems too short. Please provide more details.")
        st.stop()

    # Generate SOW
    with st.spinner("🔍 Analyzing transcript..."):
        try:
            requirements = extract_requirements(model, transcript)
            st.success("✅ Requirements extracted!")
        except Exception as e:
            st.error(f"Failed to extract requirements: {e}")
            st.stop()

    with st.spinner("📝 Generating SOW..."):
        try:
            sow_content = generate_sow_content(model, requirements)
            st.success("✅ SOW generated!")
        except Exception as e:
            st.error(f"Failed to generate SOW: {e}")
            st.stop()

    with st.spinner("📊 Creating flowchart..."):
        try:
            flowchart = generate_flowchart_structure(model, requirements)
            drawio_xml = generate_drawio_xml(flowchart)
            st.success("✅ Flowchart created!")
        except Exception as e:
            st.warning(f"Flowchart generation failed: {e}")
            flowchart = None
            drawio_xml = None

    # Display results
    st.divider()
    st.header("📋 Generated SOW")

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📄 SOW Document", "🔍 Requirements", "📊 Flowchart"])

    with tab1:
        st.markdown(format_sow_markdown(sow_content))

        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download SOW (JSON)",
                data=json.dumps(sow_content, indent=2),
                file_name=f"SOW_{sow_content.get('customer', 'Customer').replace(' ', '_')}_v1.0.0.json",
                mime="application/json"
            )
        with col2:
            st.download_button(
                "📥 Download SOW (Markdown)",
                data=format_sow_markdown(sow_content),
                file_name=f"SOW_{sow_content.get('customer', 'Customer').replace(' ', '_')}_v1.0.0.md",
                mime="text/markdown"
            )

    with tab2:
        st.subheader("Extracted Requirements")
        st.json(requirements)

    with tab3:
        if flowchart and drawio_xml:
            st.subheader("Flow Diagram")
            st.json(flowchart)

            st.download_button(
                "📥 Download Flowchart (.drawio)",
                data=drawio_xml,
                file_name=f"{sow_content.get('project', 'Flow').replace(' ', '_')}_flow.drawio",
                mime="application/xml"
            )
        else:
            st.info("Flowchart not available")

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #6B7280; font-size: 0.9rem;">
    Built with ❤️ by Exotel PS Team | Powered by Gemini 3 Flash
</div>
""", unsafe_allow_html=True)
