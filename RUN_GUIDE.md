# GutBot — Run Guide

Three supported modes:

| Mode | Backend | Frontend | Use when |
|---|---|---|---|
| **Local Dev** | Flask dev server (port 8000) | Vite dev server (port 3000) | Development, testing |
| **Local Build** | Gunicorn (port 8000) | Vite build served by Nginx or Gunicorn static | Pre-production testing |
| **EC2 Production** | Gunicorn + systemd (port 8000) | Nginx serves built frontend (port 80/443) | Live deployment |

For EC2 production, see [EC2_SETUP_GUIDE.md](EC2_SETUP_GUIDE.md).

---

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.10 or higher | `python3 --version` |
| pip | latest | `pip --version` |
| Node.js | 18 or higher | `node --version` |
| npm | 9 or higher | `npm --version` |

---

## Step 1 — Fill in Your Credentials

This is required before any mode works.

```bash
cd backend
cp .env.example .env
```

Open `backend/.env` and fill in these fields:

```env
# Choose your LLM backend
LLM_BACKEND=bedrock          # or: llama

# AWS Bedrock (required if LLM_BACKEND=bedrock)
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=AKIA...    # your IAM key
AWS_SECRET_ACCESS_KEY=...    # your IAM secret
BEDROCK_MODEL_ID=anthropic.claude-haiku-4-5-20251001-v1:0

# Deployment mode
FLASK_ENV=development        # keep this for local dev
EC2_DOMAIN=                  # leave empty for local
```

**AWS IAM minimum permissions required:**
```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel"],
  "Resource": "arn:aws:bedrock:*::foundation-model/*"
}
```

**Supported Bedrock model IDs** (must be enabled in AWS Console → Bedrock → Model Access):
- `anthropic.claude-haiku-4-5-20251001-v1:0` — recommended, fast and cheap
- `anthropic.claude-3-5-sonnet-20241022-v2:0` — more capable, higher cost
- `mistral.mistral-7b-instruct-v0:2` — open-source alternative

---

## Mode 1 — Local Development

Both backend and frontend run as hot-reload dev servers.

### Backend

```bash
cd backend

# Create virtual environment (first time only)
python3 -m venv venv

# Activate
source venv/bin/activate          # Linux / Mac
venv\Scripts\activate             # Windows

# Install dependencies
pip install -r requirements.txt

# Start backend
python app.py
# Running on http://localhost:8000
```

### Frontend

Open a second terminal:

```bash
cd frontend
npm install          # first time only
npm run dev
# Running on http://localhost:3000
```

Or use the combined startup script (Linux/Mac only):

```bash
cd backend
chmod +x start.sh
./start.sh
```

### Verify it works

```bash
curl http://localhost:8000/documents \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-123"}'
# Expected: {"documents": []}
```

---

## Mode 2 — Local Build (Gunicorn)

Tests the production server locally before deploying.

### Backend with Gunicorn

```bash
cd backend
source venv/bin/activate

# Install gunicorn if not already in venv
pip install gunicorn gevent

# Start with gevent worker (single process, concurrent connections)
gunicorn \
  --bind 0.0.0.0:8000 \
  --workers 1 \
  --worker-class gevent \
  --worker-connections 100 \
  --timeout 120 \
  app:app
```

### Frontend build

```bash
cd frontend
npm run build
# Creates frontend/dist/

# Serve the built files (quick local check)
npx serve dist -p 3000
```

### FLASK_ENV for local build test

Keep `FLASK_ENV=development` in `.env` while testing locally so CORS does not restrict you. Switch to `production` only on EC2 with `EC2_DOMAIN` set.

---

## Configuration Reference

All configuration lives in `backend/.env`. The table below covers every field.

| Variable | Default | Description |
|---|---|---|
| `LLM_BACKEND` | `bedrock` | `bedrock` or `llama` |
| `AWS_REGION` | `ap-south-1` | AWS region with Bedrock enabled |
| `AWS_ACCESS_KEY_ID` | — | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | — | IAM secret key |
| `BEDROCK_MODEL_ID` | `mistral...` | Model to invoke on Bedrock |
| `BEDROCK_MAX_TOKENS` | `512` | Max tokens in LLM response |
| `BEDROCK_TEMPERATURE` | `0.2` | Response randomness (0–1) |
| `LLAMA_SERVER_URL` | `http://localhost:8000/chat` | LLAMA server URL |
| `LLAMA_MODEL_NAME` | `qwen` | Model name on LLAMA server |
| `REQUEST_TIMEOUT` | `30` | LLM request timeout (seconds) |
| `MAX_RETRIES` | `3` | LLM call retry count |
| `RETRY_DELAY` | `1` | Seconds between retries |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformers model |
| `FLASK_ENV` | `development` | `development` or `production` |
| `EC2_DOMAIN` | _(empty)_ | EC2 IP/domain for CORS (production only) |

---

## Rebuilding FAISS Indices

Only needed if you update the raw data in `backend/data/raw/`.

```bash
cd backend
source venv/bin/activate

# Run the appropriate build script for the data you changed
python build_indices.py                      # SEnS bacteria + score
python build_food_indices.py                 # food chunks
python build_pdf_explanation_indices.py      # SEnS PDF explanations
python build_ibs_bacteria_index.py           # IBS bacteria
python build_ibs_explanation_index.py        # IBS PDF explanations
python build_gutheal_explanation_index.py    # GutHeal explanations
```

Each script writes updated `.index` files to `backend/indices/` and updated chunk JSONs to `backend/data/processed/`.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `LLM_BACKEND must be 'bedrock' or 'llama'` | `.env` not loaded or typo | Check `.env` exists in `backend/` and `LLM_BACKEND` is set |
| `botocore.exceptions.NoCredentialsError` | AWS keys missing or wrong | Verify `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in `.env` |
| `AccessDeniedException` from Bedrock | Model not enabled | Go to AWS Console → Bedrock → Model Access → enable your model |
| `ModuleNotFoundError: faiss` | venv not activated | Run `source venv/bin/activate` first |
| `CORS error in browser` | Wrong FLASK_ENV or EC2_DOMAIN | Set `EC2_DOMAIN` to your IP/domain when in production mode |
| Port 8000 already in use | Another process | `lsof -i :8000` then kill it, or change port in `app.py` line `app.run(port=8000)` |
