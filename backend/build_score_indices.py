import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ----------------------------
# Paths
# ----------------------------

SCORE_CHUNKS_PATH = Path("data/processed/score_chunks.json")
INDICES_DIR = Path("indices")

INDICES_DIR.mkdir(exist_ok=True)

# ----------------------------
# Load score chunks
# ----------------------------

with open(SCORE_CHUNKS_PATH, "r", encoding="utf-8") as f:
    score_chunks = json.load(f)

print(f"Loaded {len(score_chunks)} score chunks")

if not score_chunks:
    raise ValueError("No score chunks found.")

# ----------------------------
# Chunk → text
# ----------------------------

def score_chunk_to_text(chunk):
    parts = [
        f"Category: {chunk['category']}",
        f"Metric: {chunk['metric']}",
        f"Current value: {chunk['current_value']}",
        f"Optimised value: {chunk['optimised_value']}",
    ]

    return ". ".join(parts)

texts = [score_chunk_to_text(c) for c in score_chunks]

print("Sample score embedding text:")
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

dimension = embeddings.shape[1]
score_index = faiss.IndexFlatL2(dimension)
score_index.add(embeddings)

print("Score FAISS index size:", score_index.ntotal)

# ----------------------------
# Save index
# ----------------------------

faiss.write_index(
    score_index,
    str(INDICES_DIR / "score.index")
)

print("Saved score FAISS index.")
