import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ----------------------------
# Paths
# ----------------------------

INDICES_DIR = Path("indices")
DATA_DIR = Path("data/processed")

# ----------------------------
# Index configuration
# ----------------------------

INDEX_CONFIG = {
    # -------- SEnS --------
    "bacteria": {
        "index_path": INDICES_DIR / "bacteria.index",
        "chunks_path": DATA_DIR / "bacteria_chunks.json",
    },
    "food": {
        "index_path": INDICES_DIR / "food.index",
        "chunks_path": DATA_DIR / "food_chunks.json",
    },
    "score": {
        "index_path": INDICES_DIR / "score.index",
        "chunks_path": DATA_DIR / "score_chunks.json",
    },
    "explanation": {
        "index_path": INDICES_DIR / "pdf_explanation.index",
        "chunks_path": DATA_DIR / "pdf_explanation_chunks.json",
    },

    # -------- IBS --------
    "ibs_bacteria": {
        "index_path": INDICES_DIR / "ibs_bacteria.index",
        "chunks_path": DATA_DIR / "ibs_bacteria_chunks.json",
    },
    "ibs_explanation": {
        "index_path": INDICES_DIR / "ibs_explanation.index",
        "chunks_path": DATA_DIR / "ibs_pdf_explanation_chunks.json",
    },
    "gutheal_explanation": {
    "index_path": INDICES_DIR / "gutheal_explanation.index",
    "chunks_path": DATA_DIR / "gutheal_pdf_explanation_chunks.json",
},

}

TOP_K = 3

# ----------------------------
# Load embedding model
# ----------------------------

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# ----------------------------
# Load indices + chunks
# ----------------------------

indices = {}
chunks = {}

for name, cfg in INDEX_CONFIG.items():
    if not cfg["index_path"].exists() or not cfg["chunks_path"].exists():
        print(f"Skipping {name} (missing index or chunks)")
        continue

    indices[name] = faiss.read_index(str(cfg["index_path"]))

    with open(cfg["chunks_path"], "r", encoding="utf-8") as f:
        chunks[name] = json.load(f)

    print(
        f"{name}: index size={indices[name].ntotal}, "
        f"chunks={len(chunks[name])}"
    )

print("\nLoaded sources:", list(indices.keys()))

# ----------------------------
# Retriever
# ----------------------------

def retrieve(question: str, top_k: int = TOP_K):
    query_embedding = model.encode([question])
    query_embedding = np.array(query_embedding).astype("float32")

    results = []

    for source_name, index in indices.items():
        distances, ids = index.search(query_embedding, top_k)

        for rank, idx in enumerate(ids[0]):
            if idx < 0 or idx >= len(chunks[source_name]):
                continue

            results.append({
                "source": source_name,
                "rank": rank + 1,
                "distance": float(distances[0][rank]),
                "chunk": chunks[source_name][idx],
            })

    results.sort(key=lambda x: x["distance"])
    return results

# ----------------------------
# Test CLI
# ----------------------------

if __name__ == "__main__":
    while True:
        q = input("\nAsk GutBot (or 'exit'): ").strip()
        if q.lower() == "exit":
            break

        evidence = retrieve(q)

        print("\nTop evidence:")
        for e in evidence[:5]:
            print(f"\n[{e['source'].upper()} | distance={e['distance']:.3f}]")
            print(e["chunk"])
