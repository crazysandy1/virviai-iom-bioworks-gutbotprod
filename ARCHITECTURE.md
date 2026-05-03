# GutBot — System Architecture

## Overview

GutBot is a stateful RAG chatbot. Each user maintains an isolated conversation session identified by a `conversationId`. Within a session, users can upload multiple PDFs that are chunked, embedded, and stored in a per-session in-memory FAISS index. Queries are routed through a multi-stage pipeline before an LLM response is generated.

---

## High-Level Component Diagram

```
Browser / Frontend App
        |
        | HTTP (JSON)
        v
  ┌─────────────────────────────────────────────────────────┐
  │  Nginx (port 80/443)  ← reverse proxy + static files   │
  └────────────────────┬────────────────────────────────────┘
                       |
                       | proxy_pass :8000
                       v
  ┌─────────────────────────────────────────────────────────┐
  │  Gunicorn (1 worker, gevent)  ← production WSGI        │
  │                                                         │
  │  ┌───────────────────────────────────────────────────┐  │
  │  │  Flask app  (app.py)                              │  │
  │  │                                                   │  │
  │  │  /upload ──► MedicalDocumentValidator             │  │
  │  │               └─► PyPDF2 text extract             │  │
  │  │               └─► Heuristic scoring               │  │
  │  │               └─► Reject / Accept                 │  │
  │  │               └─► SentenceTransformer embed        │  │
  │  │               └─► Per-session FAISS index         │  │
  │  │                                                   │  │
  │  │  /chat  ──► SecurityGuard (injection check)       │  │
  │  │              └─► InferenceEngine (strategy)       │  │
  │  │              └─► FAISS search (if doc query)      │  │
  │  │              └─► call_llm()                       │  │
  │  │                   └─► AWS Bedrock / LLAMA         │  │
  │  │                                                   │  │
  │  │  In-memory store: conversation_indices {}         │  │
  │  │    keyed by conversationId                        │  │
  │  └───────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────┘
                       |
           ┌───────────┴────────────┐
           |                        |
           v                        v
  ┌─────────────────┐    ┌─────────────────────────┐
  │  AWS Bedrock    │    │  Pre-built FAISS indices │
  │  (Claude/Mistr) │    │  bacteria, food, score,  │
  │                 │    │  ibs_*, gutheal_*        │
  └─────────────────┘    └─────────────────────────┘
```

---

## Request Flow — /upload

```
POST /upload  (multipart: file, conversationId)
  │
  ├─ 1. Validate: file is PDF, size < 50 MB, conversationId present
  │
  ├─ 2. Save to backend/uploads/<filename>
  │
  ├─ 3. Extract text (PyPDF2, page by page)
  │
  ├─ 4. MedicalDocumentValidator.validate(text)
  │       ├─ Score lab values, ref ranges, patient headers,
  │       │  report headers, microbiome terms, test abbreviations,
  │       │  medical keyword density
  │       ├─ Penalise invoice/legal/code patterns
  │       └─ Score < 4 → 400 "Not a medical document"
  │
  ├─ 5. Chunk text (500-char chunks)
  │
  ├─ 6. SentenceTransformer.encode(chunks)
  │
  ├─ 7. Build / update FAISS IndexFlatL2 for this conversationId
  │
  └─ 8. Return { docId, chunks, filename, status }
```

---

## Request Flow — /chat

```
POST /chat  (JSON: message, conversationId, chatHistory)
  │
  ├─ 1. Input validation (length, conversationId present)
  │
  ├─ 2. SecurityGuard.check(message)
  │       └─ 40+ regex patterns for injection / jailbreak
  │       └─ Blocked → polite deflection (no 4xx)
  │
  ├─ 3. InferenceEngine.classify(query, has_documents, chat_history)
  │       ├─ GREETING        → skip FAISS, short greeting response
  │       ├─ OUT_OF_DOMAIN   → skip FAISS, deflect politely
  │       ├─ CONTEXT_ONLY    → FAISS search, document-only answer
  │       ├─ GENERAL_MEDICAL → skip FAISS (no doc) or use knowledge
  │       └─ HYBRID          → FAISS + general knowledge blend
  │
  ├─ 4. (If strategy needs FAISS)
  │       FAISS.search(query_embedding, k=5)
  │       Build context string from top chunks
  │
  ├─ 5. HealthcarePromptBuilder.build_system_prompt(strategy)
  │      HealthcarePromptBuilder.build_user_prompt(question, context)
  │
  ├─ 6. LLMClient.call(user_prompt, system_prompt)
  │       ├─ Bedrock: Claude / Mistral / Llama via AWS API
  │       └─ LLAMA: POST to local/remote LLAMA server
  │
  └─ 7. Return { response, sources, chunks_used, status }
```

---

## Session Isolation Design

**How it works:**
```python
conversation_indices = {
    "conv-abc123": {
        "documents": {
            "doc-uuid-1": {
                "chunks": [...],
                "filename": "patient_report.pdf",
                "size": 42000,
                "selected": True
            }
        },
        "combined_index": faiss.IndexFlatL2,  # built from selected docs only
        "doc_to_chunk_mapping": { global_idx: (doc_id, local_chunk_idx) }
    },
    "conv-xyz789": { ... }   # completely separate
}
```

**Why single-worker Gunicorn:**
This store lives in Python process memory. With multiple Gunicorn workers (separate processes), User A's upload on worker-1 would be invisible on worker-2. GutBot runs **1 worker with gevent concurrency**, keeping all session data in a single process while handling many concurrent connections efficiently.

If you need horizontal scaling in future, replace `conversation_indices` with a Redis-backed store.

---

## Pre-built Knowledge Indices

These are loaded at startup by `unified_retriever.py` for answering general IOM/gut-health questions even without an uploaded document.

| Index name | Content |
|---|---|
| `bacteria` | Gut bacteria descriptions and associations (SEnS kit) |
| `food` | Food–bacteria interactions and dietary guidance (SEnS) |
| `score` | IOM SEnS score explanations |
| `explanation` | IOM SEnS PDF narrative explanations |
| `ibs_bacteria` | Bacteria data for IBS kit |
| `ibs_explanation` | IOM IBS PDF narrative explanations |
| `gutheal_explanation` | GutHeal report explanations |

To rebuild indices after updating source data, run the corresponding `build_*.py` script from `backend/`.

---

## Medical Document Validator — Scoring Logic

`medical_doc_validator.py` analyses the first 8 000 characters of extracted text.

| Signal | Points |
|---|---|
| Lab values with medical units (≥2 found) | +3 |
| Reference / normal range markers | +3 |
| Patient / sample identifier headers | +3 |
| Report type header (lab report, microbiome report, etc.) | +4 |
| Microbiome / gut-health terms (≥2 found) | +4 |
| Medical test abbreviations (CBC, HbA1c, eGFR…) | +1–+2 |
| Medical keyword density (per 100 words, capped at 6) | +1 each |
| Invoice / legal / source-code patterns | −3 each |

**Acceptance threshold: score ≥ 4**

---

## API Reference

### POST /upload

**Request** — multipart/form-data
```
file           : PDF file (max 50 MB)
conversationId : string (UUID)
```

**Response 200**
```json
{
  "message": "File uploaded and indexed successfully",
  "chunks": 42,
  "source": "patient_report.pdf",
  "docId": "3fa85f64-...",
  "status": "success"
}
```

**Response 400 (non-medical document)**
```json
{
  "error": "This does not appear to be a medical or health-related document. ..."
}
```

---

### POST /chat

**Request** — application/json
```json
{
  "message": "What does my Firmicutes level mean?",
  "conversationId": "3fa85f64-...",
  "chatHistory": [
    { "role": "user",      "content": "Hello" },
    { "role": "assistant", "content": "Hi! I am GutBot..." }
  ]
}
```

**Response 200**
```json
{
  "response": "Your Firmicutes level of 45% ...",
  "sources": ["IOM_SEnS_Report.pdf"],
  "chunks_used": 5,
  "documents_used": 1,
  "status": "success"
}
```

---

### POST /documents

```json
{ "conversationId": "3fa85f64-..." }
```
Returns list of uploaded documents with id, filename, size, selected state, chunk count.

---

### POST /manage-documents

```json
{ "conversationId": "...", "docId": "...", "selected": false }
```
Toggles a document in/out of the FAISS search index.

---

### POST /remove-document

```json
{ "conversationId": "...", "docId": "..." }
```
Permanently removes a document from the session.
