# Exotel SOW Generator

## Project Overview
AI-powered Statement of Work (SOW) generator that reduces SOW delivery time from 2 days to hours. Built for the Exotel Professional Services team.

## Stack
- **Frontend:** Streamlit (deployed on Streamlit Cloud)
- **AI Model:** Claude Sonnet (`claude-sonnet-4-5-20250929`) via Anthropic API
- **Document Generation:** python-docx for Word export
- **Flowchart:** matplotlib for PDF/PNG, draw.io XML for editable diagrams
- **Repo:** https://github.com/shivanand-arch/sow-generator

## Key Files
- `app.py` - Main Streamlit app (all logic in single file)
- `requirements.txt` - Python dependencies (streamlit, anthropic, python-docx, matplotlib, numpy, PyPDF2)
- `.streamlit/secrets.toml` - API key (NEVER commit this)

## API Configuration
- **Provider:** Anthropic
- **Model:** `claude-sonnet-4-5-20250929`
- **Secret Key Name:** `ANTHROPIC_API_KEY`
- **Console:** https://console.anthropic.com
- API key stored in Streamlit Secrets as `ANTHROPIC_API_KEY`

## SOW Template Format (Exotel Standard)
Generated Word documents follow this exact structure:
1. **Title Page** - "Scope of Work" + Customer short code + Document Properties table (Creation Date, Draft, Ticket ID, Created By) + Copyright notice
2. **Document History** - Version tracking table
3. **Table of Contents**
4. **Section 1: Business Goal Vs Deliverables** - Table with S.No, Business Goal/Use Case, Deliverables
5. **Section 2: Prerequisites & Licenses** - Dependencies on customer team (bullet list)
6. **Section 3: Details of Deliverables** - Detailed technical descriptions (multi-paragraph, subsections like 3.1, 3.2)
7. **Section 4: Deployment & UAT Instance** - Deployment specifics
8. **Section 5: Notes** - Scope validity, change management
9. **Section 6: Assumptions** - Standard deployment assumptions
10. **Section 7: Annexure** - Account Manager info, Escalation Matrix for Scoping (Level/Name/Phone/Email table), Escalation Matrix for Deployment (same format), SOW Approval Procedure

## Formatting Details
- Table headers: Light blue shading (#D9E2F3), bold text
- Title: Dark blue (#003366), 28pt bold, centered
- Customer name: Dark blue, 24pt bold, centered
- Page: US Letter (8.5" x 11"), margins 1" all sides
- Footer: "© {year} eXotel, All rights reserved. CONFIDENTIAL"

## Module Catalog (152 ECC Modules)
The app includes a hardcoded catalog of Exotel modules across categories:
- **IVR:** Welcome Message, Language Selection, Main Menu, DTMF, PIN Verification, OTP, Consent, Balance Inquiry, Order Status, Callback, Time-Based Routing, Appointment Booking
- **Integration:** REST API, Webhook, Salesforce, Zoho, Freshdesk, Payment Gateway, SMS Gateway, Custom CRM, Screen Pop, Post-Call Data Push
- **Blaster:** Outbound Campaign, Auto Callback, Collections, Click-to-Dial, Progressive Dialer, Predictive Dialer, Retry Logic
- **Queue:** Basic Queue, Skill-Based Routing, Priority Queue, Sticky Agent, Callback from Queue, Multi-Queue Agent, Supervisor Monitor
- **Data:** CDR Export, Custom Reports, Real-Time Dashboard, Survey Responses, Agent Performance Reports

## Google Drive - Historical SOWs
- **Folder:** ECC SoWs (Shared Drive)
- **Folder ID:** `0AFw1rcSDgqHiUk9PVA`
- **Volume:** ~1,800 historical SOWs
- **Status:** Identified but RAG pipeline NOT yet implemented
- **Industry breakdown:** Banking 17.8%, Insurance 13.6%, Healthcare 10%, E-commerce 8.5%, Telecom 7.2%, BFSI 6.8%

## Pending Features
1. **RAG Pipeline** - Connect to Google Drive, extract text from 1,800 SOWs, create vector embeddings (ChromaDB), retrieve similar SOWs as context for generation
2. **Exotel logo** on title page
3. **Auto-populate** escalation matrix from internal directory
4. **SOW versioning** - track revisions
5. **Salesforce integration** - auto-create ticket ID

## Cost (Anthropic Claude Sonnet)
- Input: $3.00 per million tokens
- Output: $15.00 per million tokens
- Estimated ~$0.05-0.10 per SOW (depending on transcript length)
- 100 SOWs/month: ~$5-10

## Security
- API key stored ONLY in Streamlit Secrets as `ANTHROPIC_API_KEY`
- Never commit keys to git
- Never share keys in chat
- Get keys from https://console.anthropic.com

## Commands to Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Sample SOW Reference
A sample SOW (SOW_Sample.docx) was analyzed to derive the template format. Key reference: TENB customer SOW by Surbhi Kumari.
