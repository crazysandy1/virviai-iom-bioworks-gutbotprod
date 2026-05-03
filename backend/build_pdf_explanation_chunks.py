from pathlib import Path
import pdfplumber
import json

# ----------------------------
# Config
# ----------------------------

PDF_PATH = Path("data/raw/IOM_KIT_SEnS.pdf")
OUTPUT_PATH = Path("data/processed/pdf_explanation_chunks.json")

# Pages containing explanatory text (1-based indexing)
EXPLANATION_PAGES = list(range(5, 17))  # pages 5–16 inclusive

# ----------------------------
# Extraction
# ----------------------------

explanation_chunks = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_num in EXPLANATION_PAGES:
        page = pdf.pages[page_num - 1]
        text = page.extract_text()

        if not text:
            continue

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        buffer = []

        for line in lines:
            # Skip obvious noise
            if any(x in line for x in [
                "Name:",
                "Iom ID",
                "Date:",
                "Your SEnS Food List",
                "Table of Content"
            ]):
                continue

            buffer.append(line)

        if buffer:
            explanation_chunks.append({
                "chunk_type": "pdf_explanation",
                "section": f"PDF explanation page {page_num}",
                "text": " ".join(buffer),
                "report_scope": "SEnS",
                "source_page": page_num
            })

# ----------------------------
# Save
# ----------------------------

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(explanation_chunks, f, indent=2)

print(f"Extracted {len(explanation_chunks)} explanation chunks")
print("Sample explanation chunk:")
print(explanation_chunks[0] if explanation_chunks else "No explanation chunks found")
