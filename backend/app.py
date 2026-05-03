from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import torch

# -------------------------
# Load Environment Variables
# -------------------------
load_dotenv()

# -------------------------
# GPU/Device Detection
# -------------------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("[GPU Detection] Using device: " + DEVICE)
if DEVICE == "cuda":
    print("[GPU Detection] GPU: " + torch.cuda.get_device_name(0))

# -------------------------
# Import Centralized LLM Config
# -------------------------
from llm_config import call_llm, LLMConfig, get_llm_client, InferenceEngine, SecurityGuard
from medical_doc_validator import MedicalDocumentValidator

LLMConfig.validate()

# -------------------------
# Flask Setup
# -------------------------
app = Flask(__name__)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
]

EC2_DOMAIN = os.getenv("EC2_DOMAIN", "")
if EC2_DOMAIN:
    ALLOWED_ORIGINS.extend([
        "http://" + EC2_DOMAIN,
        "https://" + EC2_DOMAIN,
        "http://www." + EC2_DOMAIN,
        "https://www." + EC2_DOMAIN,
    ])

if os.getenv("FLASK_ENV") == "production":
    CORS(app, resources={
        r"/*": {
            "origins": ALLOWED_ORIGINS,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "max_age": 3600,
        }
    })
else:
    CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------
# Embedding Model
# -------------------------
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
print("[Embedding Model] Loading: " + EMBEDDING_MODEL_NAME)
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
print("[Embedding Model] Loaded on: " + DEVICE)

# -------------------------
# Conversation Store
# -------------------------
# Format: { conversationId: {
#   "documents": { doc_id: { "chunks", "filename", "size", "selected" } },
#   "combined_index": faiss_index | None,
#   "doc_to_chunk_mapping": { global_idx: (doc_id, local_idx) }
# }}
conversation_indices = {}


def rebuild_combined_index(conv_data):
    """Rebuild FAISS index from all selected documents.
    Returns: (combined_index, doc_to_chunk_mapping)
    """
    if not conv_data.get("documents"):
        return None, {}

    all_embeddings = []
    doc_to_chunk_mapping = {}
    chunk_idx = 0

    for doc_id in sorted(conv_data["documents"].keys()):
        doc_info = conv_data["documents"][doc_id]
        if not doc_info.get("selected", True):
            continue
        chunks = doc_info["chunks"]
        embeddings = embedding_model.encode(chunks)
        all_embeddings.append(embeddings)
        for local_idx in range(len(chunks)):
            doc_to_chunk_mapping[chunk_idx] = (doc_id, local_idx)
            chunk_idx += 1

    if not all_embeddings:
        return None, {}

    combined_embeddings = np.vstack(all_embeddings)
    dimension = combined_embeddings.shape[1]
    combined_index = faiss.IndexFlatL2(dimension)
    combined_index.add(combined_embeddings)

    return combined_index, doc_to_chunk_mapping


# -------------------------
# OPTIONS handler
# -------------------------
@app.route("/chat", methods=["OPTIONS"])
def chat_options():
    response = app.make_default_options_response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# -------------------------
# Upload PDF
# -------------------------
@app.route("/upload", methods=["POST"])
def upload():
    global conversation_indices
    try:
        file            = request.files.get("file")
        conversation_id = request.form.get("conversationId")

        if not file:
            return jsonify({"error": "No file provided"}), 400
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF files are supported"}), 400
        if not conversation_id:
            return jsonify({"error": "Conversation ID required"}), 400
        if file.content_length and file.content_length > 50 * 1024 * 1024:
            return jsonify({"error": "File size exceeds 50MB limit"}), 400

        safe_name = secure_filename(file.filename)
        if not safe_name:
            return jsonify({"error": "Invalid filename"}), 400
        filepath = os.path.join(UPLOAD_FOLDER, safe_name)
        file.save(filepath)

        text = ""
        try:
            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if len(reader.pages) == 0:
                    return jsonify({"error": "PDF is empty or corrupted"}), 400
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            return jsonify({"error": "Failed to read PDF: " + str(e)}), 400

        if not text.strip():
            return jsonify({"error": "No text could be extracted from PDF"}), 400

        # Validate document is medical/health-related before indexing
        validation = MedicalDocumentValidator.validate(text)
        if not validation["is_medical"]:
            try:
                os.remove(filepath)
            except Exception:
                pass
            print("[Upload] Rejected non-medical document: " + file.filename)
            return jsonify({"error": validation["message"]}), 400

        chunks = [text[i:i + 500] for i in range(0, len(text), 500)]

        if conversation_id not in conversation_indices:
            conversation_indices[conversation_id] = {
                "documents": {},
                "combined_index": None,
                "doc_to_chunk_mapping": {},
            }

        from uuid import uuid4
        doc_id = str(uuid4())

        conversation_indices[conversation_id]["documents"][doc_id] = {
            "chunks": chunks,
            "filename": file.filename,
            "size": len(text.encode("utf-8")),
            "selected": True,
        }

        combined_index, doc_to_chunk_mapping = rebuild_combined_index(
            conversation_indices[conversation_id]
        )
        conversation_indices[conversation_id]["combined_index"]      = combined_index
        conversation_indices[conversation_id]["doc_to_chunk_mapping"] = doc_to_chunk_mapping

        return jsonify({
            "message": "File uploaded and indexed successfully",
            "chunks": len(chunks),
            "source": file.filename,
            "docId": doc_id,
            "status": "success",
        }), 200

    except Exception as e:
        print("ERROR in /upload: " + str(e))
        import traceback; traceback.print_exc()
        return jsonify({"error": "Failed to upload file", "details": str(e)}), 500


# -------------------------
# Chat
# -------------------------
@app.route("/chat", methods=["POST"])
def chat():
    global conversation_indices
    try:
        data            = request.json
        question        = data.get("message", "").strip()
        conversation_id = data.get("conversationId")
        chat_history    = data.get("chatHistory", [])

        # Basic validation
        if not conversation_id:
            return jsonify({"error": "Conversation ID required", "status": "error"}), 400
        if not question:
            return jsonify({"error": "Message cannot be empty", "status": "error"}), 400
        if len(question) > 5000:
            return jsonify({"error": "Message too long (max 5000 chars)", "status": "error"}), 400

        # Security check — runs before anything else
        security = SecurityGuard.check(question)
        if not security["safe"]:
            print("[Security] Blocked from conversation " + conversation_id)
            return jsonify({
                "response": (
                    "I noticed something in your message I cannot process. "
                    "Feel free to ask me any health or wellness question!"
                ),
                "sources": [],
                "chunks_used": 0,
                "documents_used": 0,
                "status": "success",
            }), 200

        question = security["sanitized"]

        # Check documents
        conv_data     = conversation_indices.get(conversation_id, {})
        has_documents = bool(conv_data.get("documents"))

        # Run inference engine with actual document state
        # This correctly routes greetings/general questions away from FAISS
        # and document-intent questions toward FAISS
        pre_decision = InferenceEngine.classify(
            user_query=question,
            has_context=has_documents,
            chat_history=chat_history,
        )
        strategy = pre_decision["strategy"]
        print("[Chat] Strategy: " + strategy + " | has_documents: " + str(has_documents))

        # Strategies that skip FAISS entirely
        SKIP_FAISS = {
            InferenceEngine.STRATEGY_GREETING,
            InferenceEngine.STRATEGY_OUT_OF_DOMAIN,
        }
        # Also skip FAISS for pure general questions when no doc is uploaded
        if strategy == InferenceEngine.STRATEGY_GENERAL_MEDICAL and not has_documents:
            SKIP_FAISS.add(InferenceEngine.STRATEGY_GENERAL_MEDICAL)

        # ── Path A: Skip FAISS ────────────────────────────────────────────────
        if strategy in SKIP_FAISS:
            try:
                answer = call_llm(
                    question=question,
                    context=None,
                    sources_list=None,
                    chat_history=chat_history,
                )
            except Exception as e:
                print("LLM error (direct): " + str(e))
                return jsonify({
                    "response": "Something went wrong. Please try again.",
                    "error": True,
                    "status": "llm_error",
                    "details": str(e),
                }), 500

            return jsonify({
                "response": answer,
                "sources": [],
                "chunks_used": 0,
                "documents_used": 0,
                "status": "success",
            }), 200

        # ── Path B: Use FAISS ─────────────────────────────────────────────────
        # Reaches here only when documents exist and question is doc-intent or hybrid

        selected_docs = [
            (doc_id, doc_info)
            for doc_id, doc_info in conv_data["documents"].items()
            if doc_info.get("selected", True)
        ]

        if not selected_docs:
            return jsonify({
                "response": (
                    "No documents are selected right now. Select one to search, "
                    "or ask me a general health question!"
                ),
                "error": True,
                "status": "no_selected_documents",
            }), 400

        combined_index       = conv_data.get("combined_index")
        doc_to_chunk_mapping = conv_data.get("doc_to_chunk_mapping", {})

        if combined_index is None or len(doc_to_chunk_mapping) == 0:
            return jsonify({
                "response": "Document index missing. Please re-upload your document.",
                "error": True,
                "status": "index_error",
            }), 400

        # FAISS search
        try:
            query_embedding = embedding_model.encode([question])
            k = min(5, len(doc_to_chunk_mapping))
            D, I = combined_index.search(np.array(query_embedding), k=k)
        except Exception as e:
            print("Search error: " + str(e))
            return jsonify({
                "response": "Failed to search documents. Please try again.",
                "error": True,
                "status": "search_error",
            }), 500

        # Build context
        context_parts = []
        sources = set()

        for chunk_idx in I[0]:
            mapping = doc_to_chunk_mapping.get(chunk_idx)
            if not mapping:
                continue
            doc_id, local_chunk_idx = mapping
            if doc_id not in conv_data["documents"]:
                continue
            doc_info = conv_data["documents"][doc_id]
            if not doc_info.get("selected", True):
                continue
            chunks = doc_info["chunks"]
            if 0 <= local_chunk_idx < len(chunks):
                context_parts.append(
                    "[From: " + doc_info["filename"] + "]\n" + chunks[local_chunk_idx]
                )
                sources.add(doc_info["filename"])

        context      = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant information found in documents."
        sources_list = sorted(list(sources))

        # Call LLM
        try:
            answer = call_llm(
                question=question,
                context=context,
                sources_list=sources_list,
                chat_history=chat_history,
            )
        except Exception as e:
            print("LLM error: " + str(e))
            return jsonify({
                "response": "Failed to generate response. Please try again.",
                "error": True,
                "status": "llm_error",
                "details": str(e),
            }), 500

        return jsonify({
            "response": answer,
            "sources": sources_list,
            "chunks_used": len(I[0]),
            "documents_used": len(sources_list),
            "status": "success",
        }), 200

    except Exception as e:
        print("ERROR in /chat: " + str(e))
        import traceback; traceback.print_exc()
        return jsonify({
            "response": "An unexpected error occurred.",
            "error": True,
            "status": "server_error",
            "details": str(e),
        }), 500


# -------------------------
# Manage Documents (Toggle Selection)
# -------------------------
@app.route("/manage-documents", methods=["POST"])
def manage_documents():
    global conversation_indices
    try:
        data            = request.json
        conversation_id = data.get("conversationId")
        doc_id          = data.get("docId")
        selected        = data.get("selected")

        if not conversation_id or not doc_id:
            return jsonify({"error": "Conversation ID and Document ID required"}), 400
        if conversation_id not in conversation_indices:
            return jsonify({"error": "Conversation not found"}), 404
        if doc_id not in conversation_indices[conversation_id]["documents"]:
            return jsonify({"error": "Document not found"}), 404

        conversation_indices[conversation_id]["documents"][doc_id]["selected"] = selected

        conv_data = conversation_indices[conversation_id]
        combined_index, doc_to_chunk_mapping = rebuild_combined_index(conv_data)
        conv_data["combined_index"]      = combined_index
        conv_data["doc_to_chunk_mapping"] = doc_to_chunk_mapping

        selected_count = sum(
            1 for doc in conv_data["documents"].values() if doc.get("selected", True)
        )

        return jsonify({
            "message": "Document selection updated",
            "docId": doc_id,
            "selected": selected,
            "selectedCount": selected_count,
        })

    except Exception as e:
        print("ERROR in /manage-documents: " + str(e))
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -------------------------
# Remove Document
# -------------------------
@app.route("/remove-document", methods=["POST"])
def remove_document():
    global conversation_indices
    try:
        data            = request.json
        conversation_id = data.get("conversationId")
        doc_id          = data.get("docId")

        if not conversation_id or not doc_id:
            return jsonify({"error": "Conversation ID and Document ID required"}), 400
        if conversation_id not in conversation_indices:
            return jsonify({"error": "Conversation not found"}), 404
        if doc_id not in conversation_indices[conversation_id]["documents"]:
            return jsonify({"error": "Document not found"}), 404

        del conversation_indices[conversation_id]["documents"][doc_id]

        conv_data = conversation_indices[conversation_id]
        if conv_data["documents"]:
            combined_index, doc_to_chunk_mapping = rebuild_combined_index(conv_data)
            conv_data["combined_index"]      = combined_index
            conv_data["doc_to_chunk_mapping"] = doc_to_chunk_mapping
        else:
            conv_data["combined_index"]      = None
            conv_data["doc_to_chunk_mapping"] = {}

        return jsonify({
            "message": "Document removed successfully",
            "docId": doc_id,
            "remainingDocuments": len(conv_data["documents"]),
        })

    except Exception as e:
        print("ERROR in /remove-document: " + str(e))
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -------------------------
# Get Document List
# -------------------------
@app.route("/documents", methods=["POST"])
def get_documents():
    global conversation_indices
    try:
        data            = request.json
        conversation_id = data.get("conversationId")

        if not conversation_id:
            return jsonify({"error": "Conversation ID required"}), 400
        if conversation_id not in conversation_indices:
            return jsonify({"documents": []})

        docs = []
        for doc_id, doc_info in conversation_indices[conversation_id]["documents"].items():
            docs.append({
                "id": doc_id,
                "filename": doc_info["filename"],
                "size": doc_info["size"],
                "selected": doc_info.get("selected", True),
                "chunks": len(doc_info["chunks"]),
            })

        return jsonify({"documents": docs})

    except Exception as e:
        print("ERROR in /documents: " + str(e))
        return jsonify({"error": str(e)}), 500


# -------------------------
# Debug: Conversation Isolation Check
# -------------------------
@app.route("/debug/isolation-check", methods=["POST"])
def isolation_check():
    global conversation_indices
    try:
        data            = request.json
        conversation_id = data.get("conversationId")

        if not conversation_id:
            return jsonify({"error": "Conversation ID required"}), 400

        if conversation_id not in conversation_indices:
            return jsonify({
                "conversation_id": conversation_id,
                "exists": False,
                "isolation_status": "ISOLATED - No data for this conversation",
                "documents": [],
            })

        conv_data = conversation_indices[conversation_id]
        doc_to_chunk_mapping = conv_data.get("doc_to_chunk_mapping", {})

        report = {
            "conversation_id": conversation_id,
            "exists": True,
            "documents_count": len(conv_data.get("documents", {})),
            "selected_documents_count": sum(
                1 for d in conv_data.get("documents", {}).values() if d.get("selected", True)
            ),
            "mapping_status": (
                str(len(doc_to_chunk_mapping)) + " chunk mappings"
                if doc_to_chunk_mapping else "No chunk mappings"
            ),
            "total_conversations": len(conversation_indices),
            "documents": [
                {
                    "doc_id": doc_id[:8] + "...",
                    "filename": doc_info.get("filename"),
                    "chunks": len(doc_info.get("chunks", [])),
                    "selected": doc_info.get("selected", True),
                }
                for doc_id, doc_info in conv_data.get("documents", {}).items()
            ],
        }

        return jsonify(report)

    except Exception as e:
        print("ERROR in /debug/isolation-check: " + str(e))
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.after_request
def after_request(response):
    # In development, allow all origins for convenience.
    # In production, Flask-CORS already enforces ALLOWED_ORIGINS — do not override it.
    if os.getenv("FLASK_ENV") != "production":
        response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


if __name__ == "__main__":
    app.run(port=8000)
