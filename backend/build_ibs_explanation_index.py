import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ----------------------------
# Paths
# ----------------------------

CHUNKS_PATH = Path("data/processed/ibs_pdf_explanation_chunks.json")
INDICES_DIR = Path("indices")

INDICES_DIR.mkdir(exist_ok=True)

# ----------------------------
# Load chunks
# ----------------------------

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded {len(chunks)} IBS explanation chunks")

if not chunks:
    raise ValueError("No IBS explanation chunks found.")

# ----------------------------
# Chunk → text
# ----------------------------

def explanation_chunk_to_text(chunk):
    return chunk["text"]

texts = [explanation_chunk_to_text(c) for c in chunks]

print("Sample embedding text:")
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
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

print("IBS explanation FAISS index size:", index.ntotal)

# ----------------------------
# Save index
# ----------------------------

faiss.write_index(
    index,
    str(INDICES_DIR / "ibs_explanation.index")
)

print("Saved IBS explanation FAISS index.")
