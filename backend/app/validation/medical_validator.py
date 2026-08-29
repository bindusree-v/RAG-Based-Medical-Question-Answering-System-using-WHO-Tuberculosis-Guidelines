"""
MediRAG AI – Medical Document Validation Engine

Validates whether an uploaded document belongs to the healthcare domain
before it enters the RAG pipeline. Uses keyword analysis, metadata inspection,
and (optionally) LLM-based classification.

Allowed: Medical Research Papers, Clinical Guidelines, Drug Databases,
         Treatment Protocols, Medical Journals, Hospital SOP Documents,
         Medical Books, Medical Reports, Healthcare PDFs, Clinical Case Studies.

Rejected: Resumes, Marketing Files, Bank Statements, Invoices, Academic Notes
          unrelated to healthcare, Entertainment Content, General Business Documents.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models.schemas import DocumentCategory, ValidationResult
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Domain keyword dictionaries
# ---------------------------------------------------------------------------

MEDICAL_KEYWORDS: Dict[str, List[str]] = {
    "clinical_terms": [
        "diagnosis", "treatment", "therapy", "patient", "clinical", "medical",
        "disease", "disorder", "syndrome", "symptom", "prognosis", "etiology",
        "pathology", "pathophysiology", "pharmacology", "pharmaceutical",
        "prescription", "dosage", "contraindication", "adverse effect",
        "drug interaction", "side effect", "efficacy", "placebo",
        "randomized controlled trial", "rct", "cohort study", "meta-analysis",
        "systematic review", "evidence-based", "clinical trial", "protocol",
        "guideline", "standard of care", "best practice",
    ],
    "anatomy_physiology": [
        "cardiovascular", "pulmonary", "respiratory", "gastrointestinal",
        "neurological", "musculoskeletal", "endocrine", "renal", "hepatic",
        "hematological", "immunological", "oncological", "dermatological",
        "ophthalmological", "otolaryngology", "orthopedic", "pediatric",
        "geriatric", "obstetric", "gynecological", "psychiatric",
        "blood pressure", "heart rate", "oxygen saturation", "glucose",
        "cholesterol", "hemoglobin", "white blood cell", "platelet",
    ],
    "medical_procedures": [
        "surgery", "procedure", "intervention", "biopsy", "endoscopy",
        "catheterization", "intubation", "ventilation", "dialysis",
        "chemotherapy", "radiation", "immunotherapy", "transplant",
        "resection", "excision", "anastomosis", "laparoscopy",
        "echocardiogram", "electrocardiogram", "mri", "ct scan", "x-ray",
        "ultrasound", "laboratory", "specimen", "culture", "sensitivity",
    ],
    "drug_terms": [
        "antibiotic", "antiviral", "antifungal", "anticoagulant",
        "antihypertensive", "analgesic", "anti-inflammatory", "nsaid",
        "corticosteroid", "immunosuppressant", "vaccine", "insulin",
        "statin", "beta-blocker", "ace inhibitor", "diuretic",
        "mg", "mcg", "iv", "oral", "subcutaneous", "intravenous",
        "half-life", "bioavailability", "pharmacokinetics",
    ],
    "document_types": [
        "abstract", "introduction", "methodology", "results", "discussion",
        "conclusion", "references", "bibliography", "doi", "pubmed",
        "case report", "case study", "clinical case", "hospital", "clinic",
        "emergency", "icu", "intensive care", "ward", "outpatient",
        "inpatient", "discharge", "admission", "nursing", "physician",
        "surgeon", "specialist", "healthcare provider",
    ],
}

REJECTION_KEYWORDS: Dict[str, List[str]] = {
    "resume_cv": [
        "curriculum vitae", "work experience", "skills summary",
        "objective statement", "professional summary", "employment history",
        "references available", "linkedin", "portfolio",
    ],
    "financial": [
        "invoice", "bank statement", "account balance", "transaction history",
        "credit card", "bank account", "routing number", "tax return",
        "financial statement", "balance sheet", "profit and loss",
        "accounts payable", "accounts receivable",
    ],
    "marketing": [
        "buy now", "limited time offer", "promotional offer",
        "discount code", "call to action", "brand awareness",
        "marketing campaign", "click here", "unsubscribe",
        "advertisement", "sponsored content",
    ],
    "entertainment": [
        "movie review", "album review", "concert tour",
        "celebrity news", "entertainment weekly", "box office",
        "streaming service", "playlist", "game review",
    ],
    "business_general": [
        "quarterly earnings", "board of directors", "shareholder",
        "annual report", "merger acquisition", "stock price",
        "employee handbook", "vacation policy", "hr policy",
    ],
}

MEDICAL_SPECIALTIES: Dict[str, List[str]] = {
    "Cardiology": ["cardiac", "heart", "coronary", "arrhythmia", "hypertension", "atherosclerosis"],
    "Oncology": ["cancer", "tumor", "malignant", "chemotherapy", "oncology", "carcinoma"],
    "Neurology": ["neurological", "brain", "seizure", "epilepsy", "stroke", "dementia"],
    "Pulmonology": ["pulmonary", "respiratory", "asthma", "copd", "pneumonia", "lung"],
    "Endocrinology": ["diabetes", "thyroid", "insulin", "hormone", "endocrine", "glucose"],
    "Gastroenterology": ["gastrointestinal", "liver", "hepatic", "colon", "bowel", "gastric"],
    "Infectious Disease": ["infection", "antibiotic", "bacterial", "viral", "pathogen", "antimicrobial"],
    "Pharmacology": ["drug", "pharmacokinetics", "dosage", "adverse", "interaction", "pharmaceutical"],
    "Psychiatry": ["psychiatric", "mental health", "depression", "anxiety", "psychosis", "behavioral"],
    "Pediatrics": ["pediatric", "neonatal", "child", "infant", "adolescent", "congenital"],
    "Orthopedics": ["orthopedic", "fracture", "bone", "joint", "musculoskeletal", "spine"],
    "Dermatology": ["dermatology", "skin", "rash", "lesion", "dermatitis", "melanoma"],
    "General Medicine": ["clinical", "diagnosis", "treatment", "therapy", "patient", "guideline"],
}


def _count_keyword_matches(text: str, keywords: List[str]) -> int:
    """Count how many keywords appear in lowercase text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def _detect_medical_specialty(text: str) -> Optional[str]:
    """Heuristically determine the primary medical specialty of a text."""
    scores: Dict[str, int] = {}
    for specialty, terms in MEDICAL_SPECIALTIES.items():
        scores[specialty] = _count_keyword_matches(text, terms)
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] >= 2 else "General Medicine"


def _classify_document_category(text: str, filename: str) -> DocumentCategory:
    """Assign a document category based on text and filename signals."""
    lower_text = text.lower()
    lower_name = filename.lower()

    if any(w in lower_text or w in lower_name for w in
           ["drug", "pharmaceutical", "pharmacology", "medication", "formulary"]):
        return DocumentCategory.DRUG_DATABASE
    if any(w in lower_text or w in lower_name for w in
           ["guideline", "recommendation", "consensus statement", "best practice"]):
        return DocumentCategory.TREATMENT_GUIDELINE
    if any(w in lower_text or w in lower_name for w in
           ["protocol", "sop", "standard operating", "clinical pathway"]):
        return DocumentCategory.CLINICAL_PROTOCOL
    if any(w in lower_text or w in lower_name for w in
           ["research", "study", "trial", "cohort", "meta-analysis", "systematic review",
            "randomized", "doi", "pubmed", "journal"]):
        return DocumentCategory.RESEARCH_ARTICLE
    if any(w in lower_text or w in lower_name for w in
           ["textbook", "chapter", "edition", "handbook", "atlas"]):
        return DocumentCategory.MEDICAL_BOOK
    return DocumentCategory.MEDICAL_PDF


class MedicalDocumentValidator:
    """
    Validates documents for medical domain membership using keyword scoring.
    """

    # Thresholds
    MEDICAL_SCORE_THRESHOLD = 3       # Min medical keyword category hits
    REJECTION_SCORE_THRESHOLD = 3     # Rejection triggers at this many rejection hits
    MIN_TEXT_LENGTH = 50              # Characters

    def validate(
        self,
        text: str,
        filename: str,
        mime_type: Optional[str] = None,
    ) -> ValidationResult:
        """
        Run validation pipeline and return a ValidationResult.
        """
        if not text or len(text.strip()) < self.MIN_TEXT_LENGTH:
            return ValidationResult(
                is_valid=False,
                status="rejected",
                message="Document contains insufficient text content for analysis.",
                confidence_score=0.0,
                rejection_reason="insufficient_content",
            )

        # Score medical keywords across all categories
        medical_category_scores = {
            cat: _count_keyword_matches(text, keywords)
            for cat, keywords in MEDICAL_KEYWORDS.items()
        }
        total_medical_score = sum(medical_category_scores.values())
        categories_with_hits = sum(1 for v in medical_category_scores.values() if v > 0)

        # Score rejection keywords
        rejection_scores = {
            cat: _count_keyword_matches(text, keywords)
            for cat, keywords in REJECTION_KEYWORDS.items()
        }
        total_rejection_score = sum(rejection_scores.values())
        rejection_category = max(rejection_scores, key=lambda k: rejection_scores[k])

        # Compute confidence: ratio of medical to total signal
        total_signal = total_medical_score + total_rejection_score
        confidence = (
            total_medical_score / total_signal if total_signal > 0 else 0.0
        )
        confidence = min(1.0, confidence)

        # Decision logic
        is_medical = (
            categories_with_hits >= self.MEDICAL_SCORE_THRESHOLD
            and total_medical_score > total_rejection_score
            and confidence >= 0.5
        )

        is_rejected = (
            total_rejection_score >= self.REJECTION_SCORE_THRESHOLD
            and total_rejection_score > total_medical_score
        )

        if is_rejected and not is_medical:
            return ValidationResult(
                is_valid=False,
                status="rejected",
                message="Only healthcare-related documents are permitted.",
                confidence_score=round(1.0 - confidence, 3),
                rejection_reason=f"non_medical_content:{rejection_category}",
            )

        if not is_medical:
            return ValidationResult(
                is_valid=False,
                status="rejected",
                message=(
                    "Document does not appear to contain sufficient "
                    "healthcare or medical domain content."
                ),
                confidence_score=round(confidence, 3),
                rejection_reason="insufficient_medical_content",
            )

        # Accepted – classify further
        detected_category = _classify_document_category(text, filename)
        specialty = _detect_medical_specialty(text)

        return ValidationResult(
            is_valid=True,
            status="accepted",
            message="Document validated as healthcare-related content.",
            confidence_score=round(confidence, 3),
            detected_category=detected_category,
            medical_specialty=specialty,
        )


class ValidationEngine:
    """
    High-level entry point for document validation.
    Wraps MedicalDocumentValidator and manages file-level concerns.
    """

    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".doc"}
    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
    }

    def __init__(self):
        self._validator = MedicalDocumentValidator()

    def validate_file_type(
        self,
        filename: str,
        mime_type: Optional[str],
    ) -> Tuple[bool, str]:
        """Check extension and MIME type before reading content."""
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return False, f"File type '{ext}' is not supported. Allowed: {self.ALLOWED_EXTENSIONS}"
        if mime_type and mime_type not in self.ALLOWED_MIME_TYPES:
            return False, f"MIME type '{mime_type}' is not permitted."
        return True, "File type valid."

    def validate_document(
        self,
        text: str,
        filename: str,
        mime_type: Optional[str] = None,
    ) -> ValidationResult:
        """
        Full validation: file type + content domain check.
        Returns a ValidationResult.
        """
        # Step 1: File type check
        ok, msg = self.validate_file_type(filename, mime_type)
        if not ok:
            return ValidationResult(
                is_valid=False,
                status="rejected",
                message=msg,
                confidence_score=0.0,
                rejection_reason="invalid_file_type",
            )

        # Step 2: Content domain check
        result = self._validator.validate(text, filename, mime_type)
        logger.info(
            f"Validation result for '{filename}': "
            f"status={result.status} confidence={result.confidence_score}"
        )
        return result
