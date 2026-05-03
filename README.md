# GutBot — AI Medical Chatbot

GutBot is a production-grade RAG (Retrieval-Augmented Generation) chatbot built for **VirviAI x IOM Bioworks**. It helps users understand their gut-health reports, microbiome analyses, lab results, and general medical documents through natural, conversational AI.

---

## Key Features

- **Document-aware chat** — upload a PDF (IOM SEnS, IBS, GutHeal, or any lab report) and ask questions about it directly
- **Medical document validation** — only accepts genuine medical/health PDFs; rejects resumes, invoices, and unrelated files with a clear message
- **Conversation isolation** — each user's session is fully isolated; no data crosses between users
- **Multi-index RAG** — pre-built FAISS indices for IOM SEnS, IBS, and GutHeal knowledge bases
- **Security guard** — blocks prompt injection, jailbreak attempts, and out-of-domain queries
- **Inference engine** — automatically routes queries to greeting / general medical / document-specific / hybrid response strategies
- **Production-ready** — Gunicorn + Nginx deployment, systemd service, configurable for AWS EC2

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 2.3, Gunicorn |
| LLM | AWS Bedrock (Claude Haiku / Mistral) or self-hosted LLAMA |
| Vector Search | FAISS (CPU) |
| Embeddings | SentenceTransformers `all-MiniLM-L6-v2` |
| PDF Parsing | PyPDF2 |
| Reverse Proxy | Nginx |
| OS (Production) | Ubuntu 22.04 LTS on AWS EC2 |

---

## Repository Layout

```
virviai-iom-bioworks-gutbotprod/
├── README.md                   ← this file
├── ARCHITECTURE.md             ← system design and data flow
├── RUN_GUIDE.md                ← run locally (dev + build modes)
├── EC2_SETUP_GUIDE.md          ← full EC2 deployment from scratch
├── .gitignore
└── backend/
    ├── app.py                  ← main Flask application (entry point)
    ├── llm_config.py           ← LLM client, inference engine, security guard
    ├── medical_doc_validator.py← PDF content validation layer
    ├── unified_retriever.py    ← multi-index FAISS retriever
    ├── orchestrator.py         ← CLI chat interface (dev/testing utility)
    ├── storage.py              ← file storage helper
    ├── backend_config.py       ← centralised config classes
    ├── requirements.txt        ← Python dependencies
    ├── start.sh                ← local dev startup script (Linux/Mac)
    ├── start.bat               ← local dev startup script (Windows)
    ├── run_flask.bat           ← Windows Flask-only runner
    ├── .env.example            ← environment variable template (FILL THIS)
    ├── .env                    ← your credentials (never commit)
    ├── indices/                ← pre-built FAISS vector indices
    │   ├── bacteria.index
    │   ├── food.index
    │   ├── score.index
    │   ├── pdf_explanation.index
    │   ├── ibs_bacteria.index
    │   ├── ibs_explanation.index
    │   └── gutheal_explanation.index
    ├── data/
    │   ├── processed/          ← chunked JSON datasets (used by indices)
    │   └── raw/                ← original IOM JSON + data dictionary
    ├── uploads/                ← user-uploaded PDFs (runtime, git-ignored)
    ├── interface/              ← optional FastAPI upload micro-service
    └── build_*.py              ← one-time scripts to rebuild FAISS indices
```

---

## Getting Started

### Local development
See [RUN_GUIDE.md](RUN_GUIDE.md) for step-by-step local setup including `.env` configuration.

### Production (AWS EC2)
See [EC2_SETUP_GUIDE.md](EC2_SETUP_GUIDE.md) for a complete guide from launching an EC2 instance to serving 100+ concurrent users.

### System design
See [ARCHITECTURE.md](ARCHITECTURE.md) for component diagrams, data flow, and key design decisions.

---

## Quick Credential Setup

Before running anything:

```bash
cd backend
cp .env.example .env
# Open .env and fill in:
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY
#   AWS_REGION
#   BEDROCK_MODEL_ID
```

See `.env.example` — every field is documented with options and instructions.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload a medical PDF; validates content before indexing |
| POST | `/chat` | Send a message; returns AI response with sources |
| POST | `/documents` | List all uploaded documents for a conversation |
| POST | `/manage-documents` | Toggle document selection on/off |
| POST | `/remove-document` | Delete an uploaded document |
| POST | `/debug/isolation-check` | Verify per-conversation data isolation |

All endpoints accept and return JSON. See [ARCHITECTURE.md](ARCHITECTURE.md) for request/response formats.

---

## Built by

VirviAI & IOM Bioworks
