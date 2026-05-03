from pathlib import Path
import pdfplumber
import json
import re

PDF_PATH = Path("data/raw/IOM_KIT_SEnS.pdf")
OUTPUT_PATH = Path("data/processed/food_chunks.json")

FOOD_GROUPS = {
    "GRAINS & PULSES",
    "SPICES",
    "FRUITS",
    "VEGETABLES",
    "DRY FRUITS AND NUTS",
    "DAIRY AND SUBSTITUTES",
    "MEAT, FISH & POULTRY",
    "BEVERAGES",
    "SEEDS",
    "OTHERS",
}

def clean_list(text):
    return [x.strip() for x in re.split(r",|\n", text) if x.strip()]

food_chunks = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_num in range(16, 25):  # food section pages
        page = pdf.pages[page_num]
        text = page.extract_text()

        if not text:
            continue

        # Detect list type
        if "The “YES” List" in text or 'The "YES" List' in text:
            list_type = "YES"
        elif "The “Reduce” List" in text or 'The "Reduce" List' in text:
            list_type = "Reduce"
        else:
            continue

        lines = [l.strip() for l in text.split("\n") if l.strip()]

        current_group = None
        foods_buffer = []
        increased = []
        reduced = []

        for line in lines:

            # Detect food group
            if line in FOOD_GROUPS:
                # Flush previous group
                if current_group and foods_buffer:
                    food_chunks.append({
                        "chunk_type": "food",
                        "list_type": list_type,
                        "food_group": current_group,
                        "foods": foods_buffer,
                        "increases_bacteria": increased,
                        "reduces_bacteria": reduced,
                        "report_scope": "SEnS",
                        "source_page": page_num + 1
                    })

                current_group = line
                foods_buffer = []
                increased = []
                reduced = []
                continue

            # Detect bacteria rules
            if line.startswith("Increased:"):
                increased = clean_list(line.replace("Increased:", ""))
                continue

            if line.startswith("Reduced:"):
                reduced = clean_list(line.replace("Reduced:", ""))
                continue

            # Skip headers / noise
            if any(x in line for x in [
                "Foods that",
                "microbiome",
                "Name:",
                "Iom ID"
            ]):
                continue

            # Treat as food line
            if current_group:
                foods_buffer.extend(clean_list(line))

        # Flush last group on page
        if current_group and foods_buffer:
            food_chunks.append({
                "chunk_type": "food",
                "list_type": list_type,
                "food_group": current_group,
                "foods": foods_buffer,
                "increases_bacteria": increased,
                "reduces_bacteria": reduced,
                "report_scope": "SEnS",
                "source_page": page_num + 1
            })

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(food_chunks, f, indent=2)

print(f"Extracted {len(food_chunks)} clean food chunks")
print("Sample chunk:")
print(food_chunks[0] if food_chunks else "None")
