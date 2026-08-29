"""
MediRAG AI – RAG Pipeline Tests
Tests the retrieval logic, prompt assembly, and citation generation.
These tests use mocking to avoid requiring a live Ollama instance.
"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document as LCDoc
from app.models.schemas import SourceCitation


class TestRAGPipeline:
    """Unit tests for the RAG pipeline (mocked LLM)."""

    def _make_mock_search_result(self):
        """Create a fake vector search result."""
        doc = LCDoc(
            page_content="Hypertension management includes ACE inhibitors as first-line therapy.",
            metadata={
                "document_id": "doc-001",
                "filename": "hypertension_guidelines.pdf",
                "title": "Hypertension Treatment Guidelines 2024",
                "category": "treatment_guidelines",
                "medical_specialty": "Cardiology",
                "page_number": 5,
                "section": "Treatment",
                "source": "AHA Guidelines",
            },
        )
        return [(doc, 0.87)]

    @patch("app.vectorstore.vector_store_manager.VectorStoreManager.search")
    @patch("app.rag.rag_pipeline.LLMChain")
    def test_medical_query_returns_response(self, mock_chain_cls, mock_search):
        """RAG pipeline assembles context and returns a structured response."""
        mock_search.return_value = self._make_mock_search_result()

        # Mock LLM chain run
        mock_chain = MagicMock()
        mock_chain.run.return_value = (
            "Based on the provided guidelines, ACE inhibitors are recommended "
            "as first-line therapy for hypertension in patients with diabetes."
        )
        mock_chain_cls.return_value = mock_chain

        from app.rag.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline()
        pipeline._llm = MagicMock()  # Skip Ollama loading

        response = pipeline.medical_query(
            query="What are treatment recommendations for hypertension?"
        )

        assert response.query == "What are treatment recommendations for hypertension?"
        assert len(response.answer) > 0
        assert len(response.sources) > 0
        assert response.confidence_score > 0.0
        assert response.disclaimer != ""
        assert "Not a substitute" in response.disclaimer

    @patch("app.vectorstore.vector_store_manager.VectorStoreManager.search")
    def test_empty_knowledge_base_returns_graceful_message(self, mock_search):
        """When no documents are indexed, the pipeline should return a clear message."""
        mock_search.return_value = []

        from app.rag.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline()

        context, citations = pipeline._retrieve_context("any medical query")

        assert "No relevant medical literature" in context
        assert citations == []

    @patch("app.vectorstore.vector_store_manager.VectorStoreManager.search")
    def test_confidence_score_computed_from_sources(self, mock_search):
        """Confidence score should reflect relevance scores of top sources."""
        mock_search.return_value = self._make_mock_search_result()

        from app.rag.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline()
        _, citations = pipeline._retrieve_context("hypertension treatment")

        confidence = pipeline._compute_confidence(citations)
        assert 0.0 <= confidence <= 1.0
        assert confidence == pytest.approx(0.87, abs=0.01)

    def test_compute_confidence_empty_citations(self):
        from app.rag.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline()
        assert pipeline._compute_confidence([]) == 0.0

    def test_compute_confidence_multiple_sources(self):
        from app.rag.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline()
        citations = [
            SourceCitation(
                document_id=f"doc-{i}",
                filename=f"doc{i}.pdf",
                excerpt="excerpt",
                relevance_score=score,
            )
            for i, score in enumerate([0.9, 0.8, 0.7, 0.5])
        ]
        confidence = pipeline._compute_confidence(citations)
        # Average of top 3: (0.9 + 0.8 + 0.7) / 3 = 0.8
        assert confidence == pytest.approx(0.8, abs=0.01)
