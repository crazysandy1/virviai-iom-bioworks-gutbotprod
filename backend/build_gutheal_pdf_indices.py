from pathlib import Path
import pdfplumber
import json

# ----------------------------
# Paths
# ----------------------------

PDF_PATH = Path("data/raw/KIT001_GutHeal_Report (1).pdf")
OUTPUT_PATH = Path("data/processed/gutheal_pdf_explanation_chunks.json")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ----------------------------
# Extract explanation chunks
# ----------------------------

explanation_chunks = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_num, page in enumerate(pdf.pages, start=1):
        text = page.extract_text()

        if not text:
            continue

        cleaned = " ".join(
            line.strip()
            for line in text.split("\n")
            if line.strip()
        )

        # Skip very short / cover / noise pages
        if len(cleaned) < 300:
            continue

        explanation_chunks.append({
            "chunk_type": "pdf_explanation",
            "section": f"GutHeal PDF explanation page {page_num}",
            "text": cleaned,
            "report_scope": "GutHeal",
            "source_page": page_num
        })

print(f"Extracted {len(explanation_chunks)} GutHeal explanation chunks")

# ----------------------------
# Save
# ----------------------------

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(explanation_chunks, f, indent=2)

print("Saved GutHeal PDF explanation chunks.")

# Preview
if explanation_chunks:
    print("\nSample chunk:")
    print(explanation_chunks[0])
