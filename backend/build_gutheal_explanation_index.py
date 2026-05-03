import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ----------------------------
# Paths
# ----------------------------

CHUNKS_PATH = Path("data/processed/gutheal_pdf_explanation_chunks.json")
INDICES_DIR = Path("indices")

INDICES_DIR.mkdir(exist_ok=True)

# ----------------------------
# Load chunks
# ----------------------------

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded {len(chunks)} GutHeal explanation chunks")

if not chunks:
    raise ValueError("No GutHeal explanation chunks found.")

# ----------------------------
# Chunk → text
# ----------------------------

texts = [c["text"] for c in chunks]

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

print("GutHeal explanation FAISS index size:", index.ntotal)

# ----------------------------
# Save index
# ----------------------------

faiss.write_index(
    index,
    str(INDICES_DIR / "gutheal_explanation.index")
)

print("Saved GutHeal explanation FAISS index.")
