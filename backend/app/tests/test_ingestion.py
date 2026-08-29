"""
MediRAG AI – Document Ingestion Pipeline Tests
"""

import pytest
from unittest.mock import patch, MagicMock
from app.ingestion.text_extractor import TextExtractor, PageContent
from app.ingestion.chunker import MedicalTextChunker
from app.validation.medical_validator import ValidationEngine


SAMPLE_MEDICAL_TEXT = """
Abstract
This randomized controlled trial evaluated the efficacy of lisinopril in the
management of essential hypertension. Methods: 300 patients with systolic blood
pressure > 140 mmHg were enrolled. Results: Lisinopril 10mg daily reduced mean
systolic blood pressure by 18 mmHg (p<0.001). Adverse effects included dry cough
in 12% of patients and angioedema in 0.3%. Clinical guidelines recommend ACE
inhibitors as first-line antihypertensive therapy for patients with diabetes mellitus
and cardiovascular risk factors. Contraindications include bilateral renal artery
stenosis and pregnancy. Dosage: start at 5mg daily, titrate to 10-40mg based on
clinical response. Monitor renal function and electrolytes at 2-4 weeks.
References: JNC-8, ESH/ESC 2018 Hypertension Guidelines.
"""

SAMPLE_NON_MEDICAL_TEXT = """
INVOICE #2024-001
Bill To: ABC Corporation
Item: Marketing Services - Q1 2024
Total Amount Due: $5,000
Payment Due Date: 30 days
Bank Account: 1234567890
Routing Number: 987654321
Please send payment to our accounts payable department.
"""


class TestTextExtractor:
    def setup_method(self):
        self.extractor = TextExtractor()

    def test_extract_txt_file(self, tmp_path):
        """Test plain text extraction."""
        test_file = tmp_path / "medical.txt"
        test_file.write_text(SAMPLE_MEDICAL_TEXT)
        full_text, pages = self.extractor.extract(str(test_file))
        assert len(full_text) > 100
        assert len(pages) == 1
        assert "lisinopril" in full_text.lower()

    def test_extract_unsupported_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            self.extractor.extract("document.xlsx")

    def test_extract_from_bytes_txt(self):
        content = SAMPLE_MEDICAL_TEXT.encode("utf-8")
        full_text, pages = self.extractor.extract_from_bytes(content, "medical.txt")
        assert len(full_text) > 50
        assert "hypertension" in full_text.lower()


class TestFullIngestionPipeline:
    """Integration tests for validation → chunking pipeline."""

    def test_medical_document_accepted_and_chunked(self):
        validator = ValidationEngine()
        chunker = MedicalTextChunker(chunk_size=300, chunk_overlap=50)

        # Validate
        result = validator.validate_document(
            text=SAMPLE_MEDICAL_TEXT,
            filename="hypertension_trial.pdf",
            mime_type="application/pdf",
        )
        assert result.is_valid is True
        assert result.status == "accepted"
        assert result.detected_category is not None

        # Chunk
        chunks = chunker.chunk_document(SAMPLE_MEDICAL_TEXT, "doc-ingestion-test")
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_id == "doc-ingestion-test"
            assert len(chunk.content) > 0
            assert chunk.chunk_index >= 0

    def test_non_medical_document_rejected_before_chunking(self):
        validator = ValidationEngine()

        result = validator.validate_document(
            text=SAMPLE_NON_MEDICAL_TEXT,
            filename="invoice.pdf",
            mime_type="application/pdf",
        )
        assert result.is_valid is False
        assert result.status == "rejected"
        # Non-medical doc should NOT proceed to chunking
        assert result.rejection_reason is not None

    def test_pipeline_preserves_medical_terminology(self):
        chunker = MedicalTextChunker(chunk_size=500, chunk_overlap=100)
        chunks = chunker.chunk_document(SAMPLE_MEDICAL_TEXT, "doc-term-test")

        all_content = " ".join(c.content for c in chunks)
        # Key medical terms must survive chunking
        assert "lisinopril" in all_content.lower()
        assert "hypertension" in all_content.lower()
        assert "contraindications" in all_content.lower()

    def test_chunk_overlap_creates_context_continuity(self):
        """With overlap, adjacent chunks should share some content."""
        long_text = "Clinical trial data shows " + ("efficacy of treatment. " * 100)
        chunker = MedicalTextChunker(chunk_size=200, chunk_overlap=50)
        chunks = chunker.chunk_document(long_text, "doc-overlap-test")

        if len(chunks) >= 2:
            # Content from end of chunk N should appear in start of chunk N+1
            end_of_first = chunks[0].content[-30:]
            start_of_second = chunks[1].content[:100]
            # There should be at least some word overlap
            first_words = set(end_of_first.lower().split())
            second_words = set(start_of_second.lower().split())
            overlap = first_words & second_words
            assert len(overlap) >= 1

    def test_unsupported_file_type_rejected_at_validator(self):
        validator = ValidationEngine()
        ok, msg = validator.validate_file_type("document.exe", "application/octet-stream")
        assert ok is False
