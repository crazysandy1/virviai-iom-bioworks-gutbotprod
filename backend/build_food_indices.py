import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ----------------------------
# Paths
# ----------------------------

RAW_FOOD_CHUNKS_PATH = Path("data/processed/food_chunks.json")
INDEXED_FOOD_CHUNKS_PATH = Path("data/processed/food_indexed_chunks.json")
INDICES_DIR = Path("indices")

INDICES_DIR.mkdir(exist_ok=True)

# ----------------------------
# Load raw food chunks
# ----------------------------

with open(RAW_FOOD_CHUNKS_PATH, "r", encoding="utf-8") as f:
    raw_chunks = json.load(f)

print(f"Loaded {len(raw_chunks)} raw food chunks")

# ----------------------------
# Expand group chunks → per-food chunks
# ----------------------------

food_chunks = []

for chunk in raw_chunks:
    foods = chunk.get("foods", [])
    if not foods:
        continue

    for food in foods:
        food_chunks.append({
            "food_name": food,
            "recommendation": chunk.get("list_type"),
            "food_group": chunk.get("food_group"),
            "increases_bacteria": chunk.get("increases_bacteria", []),
            "reduces_bacteria": chunk.get("reduces_bacteria", []),
            "report_scope": chunk.get("report_scope"),
            "source_page": chunk.get("source_page"),
        })

print(f"Expanded to {len(food_chunks)} individual food entries")

if not food_chunks:
    raise ValueError("No food entries after expansion.")

# ----------------------------
# SAVE expanded chunks (CRITICAL)
# ----------------------------

with open(INDEXED_FOOD_CHUNKS_PATH, "w", encoding="utf-8") as f:
    json.dump(food_chunks, f, indent=2)

print("Saved expanded food chunks to food_indexed_chunks.json")

# ----------------------------
# Chunk → text
# ----------------------------

def food_chunk_to_text(chunk):
    parts = [
        f"Food: {chunk['food_name']}",
        f"Recommendation: {chunk['recommendation']}",
    ]

    if chunk.get("food_group"):
        parts.append(f"Food group: {chunk['food_group']}")

    if chunk.get("increases_bacteria"):
        parts.append(
            "Increases bacteria: " + ", ".join(chunk["increases_bacteria"])
        )

    if chunk.get("reduces_bacteria"):
        parts.append(
            "Reduces bacteria: " + ", ".join(chunk["reduces_bacteria"])
        )

    return ". ".join(parts)

texts = [food_chunk_to_text(c) for c in food_chunks]

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

dimension = embeddings.shape[1]
food_index = faiss.IndexFlatL2(dimension)
food_index.add(embeddings)

print("Food FAISS index size:", food_index.ntotal)

# ----------------------------
# Save index
# ----------------------------

faiss.write_index(
    food_index,
    str(INDICES_DIR / "food.index")
)

print("Saved food FAISS index.")
