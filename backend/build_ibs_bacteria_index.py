import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ----------------------------
# Paths
# ----------------------------

CHUNKS_PATH = Path("data/processed/ibs_bacteria_chunks.json")
INDICES_DIR = Path("indices")
INDICES_DIR.mkdir(exist_ok=True)

# ----------------------------
# Load chunks
# ----------------------------

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded {len(chunks)} IBS bacteria chunks")

if not chunks:
    raise ValueError("No IBS bacteria chunks found.")

# ----------------------------
# Chunk → text
# ----------------------------

def bacteria_chunk_to_text(chunk):
    parts = [
        f"Bacteria: {chunk['bacteria_name']}",
        f"Direction: {chunk['direction']}",
    ]
    if chunk.get("current_abundance") is not None:
        parts.append(f"Current abundance: {chunk['current_abundance']}")
    if chunk.get("optimal_abundance") is not None:
        parts.append(f"Optimal abundance: {chunk['optimal_abundance']}")
    return ". ".join(parts)

texts = [bacteria_chunk_to_text(c) for c in chunks]

print("Sample embedding text:")
print(texts[0])

# ----------------------------
# Embeddings
# ----------------------------

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
embeddings = model.encode(texts)
embeddings = np.array(embeddings).astype("float32")

# ----------------------------
# FAISS index
# ----------------------------

dim = embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(embeddings)

print("IBS bacteria FAISS index size:", index.ntotal)

# ----------------------------
# Save
# ----------------------------

faiss.write_index(index, str(INDICES_DIR / "ibs_bacteria.index"))
print("Saved IBS bacteria FAISS index.")
