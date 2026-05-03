from pathlib import Path
import pdfplumber
import json
import re

# ----------------------------
# Config
# ----------------------------

PDF_PATH = Path("data/raw/IOM_KIT_SEnS.pdf")
OUTPUT_PATH = Path("data/processed/score_chunks.json")

# Pages containing scores (1-based indexing)
SCORE_PAGES = {
    6: "Overall",
    7: "Sleep",
    8: "Stress",
    9: "Energy",
}

# ----------------------------
# Helpers
# ----------------------------

def extract_percentage(text, label):
    """
    Extract percentage following 'Current:' or 'Optimised:'
    """
    match = re.search(rf"{label}:\s*([0-9]+%)", text)
    return match.group(1) if match else None


# ----------------------------
# Extraction
# ----------------------------

score_chunks = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_num, category in SCORE_PAGES.items():
        page = pdf.pages[page_num - 1]
        text = page.extract_text()

        if not text:
            continue

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        current_metric = None
        current_value = None
        optimised_value = None

        for line in lines:

            # Metric name (usually title case, not percentage)
            if (
                "%" not in line
                and "Score" not in line
                and "Current:" not in line
                and "Optimised:" not in line
                and len(line.split()) <= 4
            ):
                current_metric = line
                continue

            if "Current:" in line:
                current_value = extract_percentage(line, "Current")

            if "Optimised:" in line:
                optimised_value = extract_percentage(line, "Optimised")

            # Once we have a full metric → save chunk
            if current_metric and current_value and optimised_value:
                score_chunks.append({
                    "chunk_type": "score",
                    "category": category,
                    "metric": current_metric,
                    "current_value": current_value,
                    "optimised_value": optimised_value,
                    "report_scope": "SEnS",
                    "source_page": page_num
                })

                # Reset for next metric
                current_metric = None
                current_value = None
                optimised_value = None

# ----------------------------
# Save
# ----------------------------

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(score_chunks, f, indent=2)

print(f"Extracted {len(score_chunks)} score chunks")
print("Sample score chunk:")
print(score_chunks[0] if score_chunks else "No score chunks found")
