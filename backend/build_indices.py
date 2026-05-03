import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

"""
build_indices.py

Purpose:
- Ingest structured JSON data
- Extract ONLY bacteria facts
- Build FAISS index for factual retrieval

Reads ONLY from data/raw/
Writes ONLY to data/processed/ and indices/

Raw files are immutable.
Processed files and indices can be safely deleted and regenerated.
"""

# ----------------------------
# Directory setup
# ----------------------------

RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
INDICES_DIR = Path("indices")

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
INDICES_DIR.mkdir(exist_ok=True)

JSON_PATH = RAW_DATA_DIR / "IOMVNLOFSZOBFF_raw_data_processed_SEnS.json"

# ----------------------------
# Load JSON
# ----------------------------

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

print("Top-level keys in JSON:")
for key in data.keys():
    print("-", key)

tokens = data["tokens"]

# ======================================================
# BACTERIA CHUNKS (FACTUAL, STRUCTURED)
# ======================================================

bacteria_chunks = []

for token_id, token_value in tokens.items():

    # Bacteria appear as stringified JSON lists
    if isinstance(token_value, str) and token_value.strip().startswith("["):
        try:
            parsed = json.loads(token_value)
        except json.JSONDecodeError:
            continue

        if not isinstance(parsed, list):
            continue

        for item in parsed:
            if not isinstance(item, dict):
                continue

            if item.get("Category") == "Bacteria":
                chunk = {
                    "chunk_type": "bacteria",
                    "bacteria_name": item.get("Token_name"),
                    "direction": item.get("Type"),
                    "current_abundance": item.get("Initial_Abundance"),
                    "optimal_abundance": item.get("Optimised_abundance"),
                    "report_scope": "SEnS",
                    "metadata": {
                        "source_token": token_id
                    }
                }

                if chunk["bacteria_name"]:
                    bacteria_chunks.append(chunk)

print(f"\nExtracted {len(bacteria_chunks)} bacteria chunks")

if bacteria_chunks:
    print("Sample bacteria chunk:")
    print(bacteria_chunks[0])

# ----------------------------
# Chunk → text (for embeddings)
# ----------------------------

def bacteria_chunk_to_text(chunk):
    parts = [
        f"Bacteria: {chunk['bacteria_name']}",
        f"Direction: {chunk['direction']}"
    ]

    if chunk.get("current_abundance") is not None:
        parts.append(f"Current abundance: {chunk['current_abundance']}")

    if chunk.get("optimal_abundance") is not None:
        parts.append(f"Optimal abundance: {chunk['optimal_abundance']}")

    return ". ".join(parts)

bacteria_texts = [bacteria_chunk_to_text(c) for c in bacteria_chunks]

# ----------------------------
# Embeddings + FAISS
# ----------------------------

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

embeddings = model.encode(bacteria_texts)
embeddings = np.array(embeddings).astype("float32")

dimension = embeddings.shape[1]
bacteria_index = faiss.IndexFlatL2(dimension)
bacteria_index.add(embeddings)

print("\nBacteria FAISS index size:", bacteria_index.ntotal)

# ----------------------------
# Save outputs
# ----------------------------

faiss.write_index(
    bacteria_index,
    str(INDICES_DIR / "bacteria.index")
)

with open(PROCESSED_DATA_DIR / "bacteria_chunks.json", "w", encoding="utf-8") as f:
    json.dump(bacteria_chunks, f, indent=2)

print("Saved bacteria index and chunks.")
