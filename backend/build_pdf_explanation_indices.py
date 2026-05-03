import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ----------------------------
# Paths
# ----------------------------

EXPLANATION_CHUNKS_PATH = Path("data/processed/pdf_explanation_chunks.json")
INDICES_DIR = Path("indices")

INDICES_DIR.mkdir(exist_ok=True)

# ----------------------------
# Load chunks
# ----------------------------

with open(EXPLANATION_CHUNKS_PATH, "r", encoding="utf-8") as f:
    explanation_chunks = json.load(f)

print(f"Loaded {len(explanation_chunks)} explanation chunks")

if not explanation_chunks:
    raise ValueError("No explanation chunks found.")

# ----------------------------
# Chunk → text
# ----------------------------

def explanation_chunk_to_text(chunk):
    return chunk["text"]

texts = [explanation_chunk_to_text(c) for c in explanation_chunks]

print("Sample explanation text:")
print(texts[0][:300], "...")

# ----------------------------
# Embeddings
# ----------------------------

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

embeddings = model.encode(texts)
embeddings = np.array(embeddings).astype("float32")

# ----------------------------
# FAISS index
# ----------------------------

dimension = embeddings.shape[1]
pdf_index = faiss.IndexFlatL2(dimension)
pdf_index.add(embeddings)

print("PDF explanation FAISS index size:", pdf_index.ntotal)

# ----------------------------
# Save index
# ----------------------------

faiss.write_index(
    pdf_index,
    str(INDICES_DIR / "pdf_explanation.index")
)

print("Saved PDF explanation FAISS index.")
