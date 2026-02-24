# Exotel SOW Generator

AI-powered Statement of Work generator that learns from 1,800+ historical SOWs using RAG (Retrieval Augmented Generation).

## Features

- **RAG-Powered**: Finds similar past SOWs to inform new document generation
- **Multi-Format Input**: Accepts call transcripts (PDF, text), meeting notes, or structured requirements
- **Complete Output**: Generates both SOW documents (.docx) and flowcharts (.drawio)
- **Module Catalog**: 152 pre-defined ECC modules with descriptions and pricing
- **Cost Effective**: Uses Gemini Flash 2.0 (~$0.01 per SOW)

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Input     │───▶│  RAG        │───▶│   Gemini    │───▶│   Output    │
│  Transcript │    │  Retrieval  │    │  Flash 2.0  │    │  SOW+Flow   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                          │
                   ┌──────▼──────┐
                   │ Vector DB   │
                   │ (1800 SOWs) │
                   └─────────────┘
```

## Quick Start

### 1. Installation

```bash
git clone https://github.com/exotel/sow-generator.git
cd sow-generator
npm install
```

### 2. Configuration

```bash
cp .env.example .env
# Add your API keys:
# GEMINI_API_KEY=your_gemini_api_key
# QDRANT_URL=http://localhost:6333 (optional, for production)
```

### 3. Index Historical SOWs (One-time)

**Option A: From Google Drive (Recommended)**
```bash
# Index SOWs from ECC SoWs shared drive
# Folder ID: 0AFw1rcSDgqHiUk9PVA
npm run index-gdrive -- --folder-id "0AFw1rcSDgqHiUk9PVA" --output ./data/embeddings

# Note: First run will prompt for OAuth authorization
# Download credentials.json from Google Cloud Console
```

**Option B: From Local Folder**
```bash
# Point to your SOW folder
npm run index-sows -- --input ./sows --output ./data/embeddings
```

### 4. Generate SOW

```bash
# From CLI
npm run cli -- generate --transcript ./call_notes.pdf --output ./output/

# Or via API
npm run server
curl -X POST http://localhost:3000/generate \
  -F "transcript=@call_notes.pdf" \
  -o output.zip
```

## Project Structure

```
exotel-sow-generator/
├── src/
│   ├── index.js              # Main entry point
│   ├── cli.js                # Command-line interface
│   ├── server.js             # REST API server
│   ├── indexer/
│   │   └── sow-indexer.js    # Index SOWs into vector DB
│   ├── retriever/
│   │   └── rag-retriever.js  # Retrieve similar SOWs
│   ├── generators/
│   │   ├── sow-docx.js       # Generate Word documents
│   │   └── flowchart-drawio.js # Generate draw.io diagrams
│   ├── llm/
│   │   └── gemini.js         # Gemini API wrapper
│   └── utils/
│       ├── pdf-parser.js     # Parse PDF transcripts
│       └── logger.js         # Logging utility
├── data/
│   ├── module-catalog.json   # 152 ECC modules
│   ├── industry-patterns.json # Industry-specific patterns
│   └── embeddings/           # Generated embeddings (gitignored)
├── prompts/
│   ├── extract-requirements.md
│   ├── generate-sow.md
│   └── generate-flowchart.md
├── templates/
│   └── sow-structure.json    # SOW template structure
├── config/
│   └── default.json          # Default configuration
└── examples/
    ├── sample-transcript.pdf
    └── sample-output/
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `GEMINI_API_KEY` | Google AI API key | Required |
| `GEMINI_MODEL` | Model to use | `gemini-2.0-flash-exp` |
| `QDRANT_URL` | Vector DB URL | `memory` (in-memory) |
| `TOP_K_SIMILAR` | Number of similar SOWs to retrieve | `5` |
| `OUTPUT_FORMAT` | Output formats | `docx,drawio` |

## API Endpoints

### POST /generate

Generate SOW from transcript.

**Request:**
- `transcript` (file): PDF or text file of call transcript
- `customer_name` (string, optional): Customer name override
- `project_name` (string, optional): Project name override

**Response:**
- ZIP file containing:
  - `SOW_{customer}_{project}_v1.0.0.docx`
  - `{project}_flow.drawio`
  - `metadata.json`

### GET /modules

List all available modules.

### GET /health

Health check endpoint.

## Module Catalog

The system includes 152 pre-defined modules across categories:

| Category | Count | Examples |
|----------|-------|----------|
| IVR | 35 | Welcome message, DTMF input, language selection |
| Integration | 40 | CRM, Salesforce, Freshdesk, custom API |
| Blaster | 20 | OBD campaigns, voice blast, retry logic |
| Queue | 25 | Agent routing, callback, overflow |
| Data/Reporting | 32 | CDR, analytics, custom reports |

## Cost Estimation

| Volume | Gemini Cost | Embeddings | Total |
|--------|-------------|------------|-------|
| 10 SOWs/month | $0.10 | $0 | ~$0.10 |
| 100 SOWs/month | $1.00 | $0 | ~$1.00 |
| 1000 SOWs/month | $10.00 | $0 | ~$10.00 |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Support

For issues or questions, contact the PS team or open a GitHub issue.
