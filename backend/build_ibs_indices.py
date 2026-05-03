import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ----------------------------
# Paths
# ----------------------------

RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
INDICES_DIR = Path("indices")

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
INDICES_DIR.mkdir(exist_ok=True)

JSON_PATH = RAW_DATA_DIR / "IOM_KIT001_raw_data_processed_IBS.json"

# ----------------------------
# Load JSON
# ----------------------------

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

tokens = data["tokens"]

# ======================================================
# BACTERIA CHUNKS (IBS)
# ======================================================

bacteria_chunks = []

for token_id, token_value in tokens.items():

    if isinstance(token_value, str) and token_value.strip().startswith("["):
        try:
            parsed = json.loads(token_value)
        except json.JSONDecodeError:
            continue

        for item in parsed:
            if item.get("Category") == "Bacteria":
                chunk = {
                    "chunk_type": "bacteria",
                    "bacteria_name": item.get("Token_name"),
                    "direction": item.get("Type"),
                    "current_abundance": item.get("Initial_Abundance"),
                    "optimal_abundance": item.get("Optimised_abundance"),
                    "report_scope": "IBS",
                    "metadata": {"source_token": token_id},
                }

                if chunk["bacteria_name"]:
                    bacteria_chunks.append(chunk)

print(f"Extracted {len(bacteria_chunks)} IBS bacteria chunks")

# ======================================================
# SCORE CHUNKS (IBS)
# ======================================================

score_chunks = []

for token_id, token_value in tokens.items():

    if isinstance(token_value, dict):
        category = token_value.get("Category")
        metric = token_value.get("Token_name")

        value = (
            token_value.get("Value")
            or token_value.get("Score")
            or token_value.get("Numeric_Value")
        )

        status = token_value.get("Status")

        if category and metric and value is not None:
            score_chunks.append({
                "chunk_type": "score",
                "category": category,
                "metric": metric,
                "current_value": value,
                "report_scope": "IBS",
                "metadata": {"source_token": token_id},
            })

print(f"Extracted {len(score_chunks)} IBS score chunks")

# ======================================================
# Save chunks (NO embeddings yet)
# ======================================================

with open(PROCESSED_DATA_DIR / "ibs_bacteria_chunks.json", "w", encoding="utf-8") as f:
    json.dump(bacteria_chunks, f, indent=2)

with open(PROCESSED_DATA_DIR / "ibs_score_chunks.json", "w", encoding="utf-8") as f:
    json.dump(score_chunks, f, indent=2)

print("Saved IBS chunks.")
