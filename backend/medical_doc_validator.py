"""
Medical Document Validator for GutBot RAG System.

Determines whether an uploaded PDF is a medical or health-related document
before it enters the processing pipeline.

Strategy: multi-signal heuristic scoring — no LLM calls, no external requests.
Handles all document types this system processes:
  IOM SEnS/IBS microbiome reports, blood/lab reports, prescriptions,
  discharge summaries, clinical notes, health certificates, research papers.

Score >= THRESHOLD -> accepted
Score <  THRESHOLD -> rejected with a clear user-facing message
"""

import re


# Minimum confidence score to classify a document as medical/health-related
MEDICAL_SCORE_THRESHOLD = 4

# How much of the document to analyse (chars). Enough to cover any header/first page.
ANALYSIS_WINDOW = 8000


# =============================================================================
# PATTERN DEFINITIONS
# =============================================================================

# Lab values: a number immediately followed by a recognised medical unit
_LAB_VALUE_PATTERN = re.compile(
    r'\b\d+\.?\d*\s*'
    r'(?:mg\/d[Ll]|mmol\/[Ll]|g\/d[Ll]|g\/[Ll]|ng\/m[Ll]'
    r'|[Mm][Cc][Gg]\/m[Ll]|µg\/m[Ll]|ug\/mL'
    r'|[Ii][Uu]\/[Ll]|[Uu]\/[Ll]|mIU\/[Ll]|mEq\/[Ll]'
    r'|cells\/µ[Ll]|cells\/uL'
    r'|[×xX]10[\^]?\d'
    r'|µ[Mm]ol\/[Ll]|pmol\/[Ll]|nmol\/[Ll]'
    r'|m[Mm]Hg|bpm|cm\/s|mL\/min'
    r')',
)

# Reference / normal range markers
_REF_RANGE_PATTERN = re.compile(
    r'(?:normal|ref(?:erence)?|range|ref\.?|low|high|optimal)\s*[:\s]+'
    r'[\d\.]+\s*[-–—to]+\s*[\d\.]+',
    re.IGNORECASE,
)

# Patient or sample identifier lines
_PATIENT_ID_PATTERN = re.compile(
    r'(?:patient\s*(?:id|name|no\.?|#|identifier|ref)'
    r'|date\s+of\s+birth|dob\s*[:\-]'
    r'|mrn\b|medical\s+record\s+(?:no|number|#)'
    r'|sample\s+(?:id|no\.?|date|type|ref)'
    r'|report\s+(?:id|no\.?|date|ref)'
    r'|requisition\s+(?:no|#)'
    r'|accession\s+(?:no|number|#)'
    r'|specimen\s+(?:id|no\.?|type)'
    r'|collection\s+date)',
    re.IGNORECASE,
)

# Report / document type headers
_REPORT_HEADER_PATTERN = re.compile(
    r'(?:lab(?:oratory)?\s+report'
    r'|pathology\s+report'
    r'|medical\s+(?:report|record|summary|certificate|history|certificate)'
    r'|discharge\s+summary'
    r'|clinical\s+(?:report|summary|note|record|assessment)'
    r'|diagnostic\s+report'
    r'|radiology\s+report'
    r'|health\s+(?:report|record|summary|profile|assessment)'
    r'|patient\s+(?:report|summary|record|history)'
    r'|test\s+results?'
    r'|blood\s+(?:test|work|panel|report)'
    r'|gut\s+health\s+(?:report|analysis|score|assessment)'
    r'|microbiome\s+(?:report|analysis|profile|test|assessment)'
    r'|stool\s+(?:analysis|test|report|culture)'
    r'|iom\s+(?:report|kit|test|score|results?)'
    r'|sens\s+(?:report|score|kit|results?)'
    r'|ibs\s+(?:report|score|kit|results?|assessment)'
    r'|gutheal\s+(?:report|results?|score)'
    r'|comprehensive\s+(?:metabolic|blood|stool|gut)\s+panel)',
    re.IGNORECASE,
)

# Microbiome and gut-health specific terms (core to this product)
_MICROBIOME_PATTERN = re.compile(
    r'(?:firmicutes|bacteroidetes|proteobacteria|actinobacteria|verrucomicrobia'
    r'|bifidobacterium|lactobacillus|akkermansia|faecalibacterium\s+prausnitzii'
    r'|ruminococcus|clostridium|prevotella|streptococcus|enterococcus'
    r'|blautia|roseburia|eubacterium|coprococcus'
    r'|microbiome|microbiota|gut\s+flora|gut\s+microb'
    r'|dysbiosis|eubiosis'
    r'|diversity\s+(?:score|index|ratio)'
    r'|ibs[-\s]?(?:score|c|d|m|u|ibs)'
    r'|gut\s+(?:health|permeability|lining|restoration|healing)'
    r'|short[- ]chain\s+fatty\s+acid|scfa'
    r'|butyrate|propionate|acetate'
    r'|leaky\s+gut|intestinal\s+permeability'
    r'|probiotic|prebiotic|postbiotic)',
    re.IGNORECASE,
)

# Common medical test abbreviations as standalone tokens
_TEST_ABBREV_PATTERN = re.compile(
    r'\b(?:CBC|BMP|CMP|HbA1c|eGFR|TSH|FT[34]|PSA|ESR|CRP'
    r'|WBC|RBC|HGB|HCT|MCV|MCH|MCHC|PLT'
    r'|ALT|AST|ALP|GGT|LDH|CK|BNP|NTproBNP'
    r'|HDL|LDL|VLDL|TG|TC|FBG|PP2BS'
    r'|INR|PT|aPTT|D[- ]?dimer'
    r'|uric\s+acid|creatinine|GFR|BUN)\b',
)

# Strong non-medical domain signals that should subtract from the score
_NON_MEDICAL_PATTERNS = [
    # Financial / invoice
    re.compile(
        r'(?:invoice\s+(?:no|number|#|date)'
        r'|total\s+amount\s+(?:due|payable)'
        r'|tax\s+invoice'
        r'|gst\s+(?:no|number|#)'
        r'|bank\s+account\s+(?:no|number)'
        r'|ifsc\s+code|swift\s+code'
        r'|bill\s+to\s*:|ship\s+to\s*:'
        r'|purchase\s+order\s+(?:no|#)'
        r'|payment\s+due\s+(?:date|by)'
        r'|subtotal|grand\s+total)',
        re.IGNORECASE,
    ),
    # Legal contracts
    re.compile(
        r'(?:(?:this\s+)?agreement\s+(?:is\s+)?(?:entered|made\s+and\s+entered)'
        r'|whereas,?\s+the\s+(?:parties|party)'
        r'|terms\s+and\s+conditions\s+of\s+(?:this|the)'
        r'|\bplaintiff\b|\bdefendant\b'
        r'|hereinafter\s+referred\s+to\s+as'
        r'|indemnif(?:y|ication)'
        r'|arbitration\s+clause'
        r'|intellectual\s+property\s+rights'
        r'|confidentiality\s+(?:clause|agreement))',
        re.IGNORECASE,
    ),
    # Source code / programming
    re.compile(
        r'(?:def\s+\w+\s*\('
        r'|class\s+\w+\s*[:\(]'
        r'|import\s+(?:os|sys|re|json|numpy|pandas|torch)'
        r'|function\s+\w+\s*\('
        r'|public\s+static\s+void'
        r'|private\s+(?:void|int|String|bool)'
        r'|SELECT\s+\*?\s+FROM\s+\w+'
        r'|CREATE\s+TABLE\s+\w+'
        r'|console\.log\s*\('
        r'|print\s*\([\"\'])',
        re.IGNORECASE,
    ),
]

# Medical keywords for density scoring (each hit = +1, capped)
_MEDICAL_KEYWORDS = [
    # Clinical
    "diagnosis", "diagnoses", "treatment", "prescription", "medication",
    "dosage", "dose", "symptom", "disease", "condition", "syndrome",
    "disorder", "therapy", "procedure", "surgery", "clinical",
    "laboratory", "specimen", "result", "finding", "assessment",
    "evaluation", "consultation", "referral", "prognosis",
    # Anatomical / biochemical
    "blood", "urine", "stool", "serum", "plasma", "biopsy",
    "hemoglobin", "haemoglobin", "glucose", "creatinine", "cholesterol",
    "sodium", "potassium", "calcium", "thyroid", "insulin", "cortisol",
    "bilirubin", "albumin", "platelet", "neutrophil", "lymphocyte",
    "eosinophil", "basophil", "monocyte", "ferritin", "transferrin",
    # Provider / setting
    "hospital", "clinic", "laboratory", "ward", "physician",
    "specialist", "pathologist", "radiologist", "nurse",
    "patient", "doctor",
    # Drug names
    "metformin", "insulin", "aspirin", "ibuprofen", "paracetamol",
    "acetaminophen", "atorvastatin", "omeprazole", "lisinopril",
    "amlodipine", "amoxicillin", "metoprolol", "levothyroxine",
    "prednisolone", "prednisone", "pantoprazole", "ranitidine",
    "salbutamol", "albuterol", "cetirizine",
    # Nutrition / gut
    "probiotic", "prebiotic", "dietary", "inflammation",
    "inflammatory", "antioxidant", "micronutrient", "supplement",
    # Specialties
    "cardiology", "neurology", "oncology", "gastroenterology",
    "endocrinology", "nephrology", "dermatology", "radiology",
    "hematology", "haematology", "immunology", "rheumatology",
]

# Max keyword score contribution (prevents generic health-heavy articles from flooding the score)
_KEYWORD_SCORE_CAP = 6


# =============================================================================
# VALIDATOR
# =============================================================================

class MedicalDocumentValidator:
    """
    Validates whether extracted PDF text is from a medical / health document.
    Call MedicalDocumentValidator.validate(text) and check result["is_medical"].
    """

    @classmethod
    def validate(cls, text: str) -> dict:
        """
        Args:
            text: Full extracted text from the PDF.
        Returns:
            {
                "is_medical": bool,
                "score": int,
                "signals": list[str],
                "message": str,
            }
        """
        sample = text[:ANALYSIS_WINDOW]
        sample_lower = sample.lower()
        score = 0
        signals = []

        # ── Signal 1: Lab values with recognised units (weight +3) ────────────
        lab_hits = _LAB_VALUE_PATTERN.findall(sample)
        if len(lab_hits) >= 2:
            score += 3
            signals.append("lab_values:" + str(len(lab_hits)))
        elif len(lab_hits) == 1:
            score += 1
            signals.append("lab_value:1")

        # ── Signal 2: Reference / normal range markers (weight +3) ────────────
        ref_hits = _REF_RANGE_PATTERN.findall(sample)
        if ref_hits:
            score += 3
            signals.append("ref_ranges:" + str(len(ref_hits)))

        # ── Signal 3: Patient / sample identifier lines (weight +3) ──────────
        if _PATIENT_ID_PATTERN.search(sample):
            score += 3
            signals.append("patient_id_header")

        # ── Signal 4: Report / document type header (weight +4) ───────────────
        if _REPORT_HEADER_PATTERN.search(sample):
            score += 4
            signals.append("report_header")

        # ── Signal 5: Microbiome / gut-health specific terms (weight +4) ──────
        micro_hits = _MICROBIOME_PATTERN.findall(sample)
        if len(micro_hits) >= 2:
            score += 4
            signals.append("microbiome_terms:" + str(len(micro_hits)))
        elif len(micro_hits) == 1:
            score += 2
            signals.append("microbiome_term:1")

        # ── Signal 6: Medical test abbreviations (weight +2) ──────────────────
        abbrev_hits = _TEST_ABBREV_PATTERN.findall(sample)
        if len(abbrev_hits) >= 2:
            score += 2
            signals.append("test_abbreviations:" + str(len(abbrev_hits)))
        elif len(abbrev_hits) == 1:
            score += 1
            signals.append("test_abbreviation:1")

        # ── Signal 7: Medical keyword density (weight +1 each, capped) ────────
        keyword_count = sum(1 for kw in _MEDICAL_KEYWORDS if kw in sample_lower)
        keyword_contribution = min(keyword_count, _KEYWORD_SCORE_CAP)
        score += keyword_contribution
        if keyword_count > 0:
            signals.append("medical_keywords:" + str(keyword_count))

        # ── Signal 8: Non-medical domain patterns (weight -3 each) ────────────
        for pattern in _NON_MEDICAL_PATTERNS:
            if pattern.search(sample):
                score -= 3
                signals.append("non_medical_signal:-3")

        print(
            "[MedicalDocValidator] Score=" + str(score)
            + " threshold=" + str(MEDICAL_SCORE_THRESHOLD)
            + " signals=" + str(signals)
        )

        if score >= MEDICAL_SCORE_THRESHOLD:
            return {
                "is_medical": True,
                "score": score,
                "signals": signals,
                "message": "Document validated as medical/health content.",
            }

        return {
            "is_medical": False,
            "score": score,
            "signals": signals,
            "message": (
                "This does not appear to be a medical or health-related document. "
                "GutBot only accepts lab reports, microbiome reports, prescriptions, "
                "medical records, and health-related documents. "
                "Please upload a valid medical document and try again."
            ),
        }
