"""
MediRAG AI – Text Chunker Tests
"""

import pytest
from app.ingestion.chunker import MedicalTextChunker


class TestMedicalTextChunker:
    def setup_method(self):
        self.chunker = MedicalTextChunker(chunk_size=500, chunk_overlap=50)

    def test_basic_chunking(self):
        text = "Medical text. " * 200  # ~2800 chars
        chunks = self.chunker.chunk_document(text, "doc-123")
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= 600  # chunk_size + some tolerance

    def test_empty_text_returns_empty(self):
        chunks = self.chunker.chunk_document("", "doc-456")
        assert chunks == []

    def test_chunk_indices_are_sequential(self):
        text = "Patient diagnosis treatment protocol. " * 100
        chunks = self.chunker.chunk_document(text, "doc-789")
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_document_id_preserved(self):
        text = "Clinical guidelines for hypertension management. " * 50
        chunks = self.chunker.chunk_document(text, "doc-999")
        for chunk in chunks:
            assert chunk.document_id == "doc-999"

    def test_section_detection(self):
        text = """
Abstract
This study evaluates treatment outcomes.

Introduction
Hypertension affects 1 billion people worldwide.

Methods
Randomized controlled trial design.

Results
Blood pressure reduced by 15mmHg.

Conclusion
ACE inhibitors are effective first-line agents.
"""
        chunks = self.chunker.chunk_document(text, "doc-sec")
        # At least one chunk should have a section detected
        sections = [c.section for c in chunks if c.section]
        assert len(sections) >= 1

    def test_short_text_single_chunk(self):
        text = "Patient has hypertension. Blood pressure 150/90."
        chunks = self.chunker.chunk_document(text, "doc-short")
        assert len(chunks) == 1
        assert chunks[0].content == text
