"""
MediRAG AI – Medical Text Chunker
Uses RecursiveCharacterTextSplitter with medical-aware separators.
Preserves medical terminology, section hierarchy, tables, and references.
"""

from typing import Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.utils.logger import logger


class MedicalChunk:
    """Represents a single text chunk with metadata."""

    def __init__(
        self,
        content: str,
        chunk_index: int,
        document_id: str,
        page_number: Optional[int] = None,
        section: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.content = content
        self.chunk_index = chunk_index
        self.document_id = document_id
        self.page_number = page_number
        self.section = section
        self.metadata = metadata or {}


class MedicalTextChunker:
    """
    Chunks medical text using RecursiveCharacterTextSplitter with
    medical-domain separators to preserve section integrity.
    """

    # Medical section separators in priority order
    MEDICAL_SEPARATORS = [
        # Section headers
        "\n## ", "\n### ", "\n#### ",
        # Numbered sections
        "\n1. ", "\n2. ", "\n3. ",
        # Common medical section headers
        "\nAbstract\n", "\nIntroduction\n", "\nMethods\n",
        "\nResults\n", "\nDiscussion\n", "\nConclusion\n",
        "\nReferences\n", "\nBackground\n",
        "\nTreatment\n", "\nDiagnosis\n", "\nDosage\n",
        # Standard paragraph separators
        "\n\n",
        "\n",
        ". ",
        " ",
        "",
    ]

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.MEDICAL_SEPARATORS,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk_document(
        self,
        text: str,
        document_id: str,
        page_number: Optional[int] = None,
    ) -> List[MedicalChunk]:
        """
        Split text into MedicalChunk objects.

        Args:
            text: Full document text.
            document_id: UUID of the parent Document record.
            page_number: Optional page hint.

        Returns:
            List of MedicalChunk objects, each with index and metadata.
        """
        if not text or not text.strip():
            logger.warning(f"Empty text provided for document {document_id}")
            return []

        raw_chunks = self._splitter.split_text(text)

        chunks: List[MedicalChunk] = []
        for idx, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue

            section = self._detect_section(chunk_text)
            chunks.append(
                MedicalChunk(
                    content=chunk_text,
                    chunk_index=idx,
                    document_id=document_id,
                    page_number=page_number,
                    section=section,
                )
            )

        logger.debug(
            f"Chunked document {document_id} into {len(chunks)} chunks "
            f"(size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        return chunks

    def _detect_section(self, text: str) -> Optional[str]:
        """Heuristically detect the medical section a chunk belongs to."""
        medical_sections = [
            "abstract", "introduction", "background", "methods",
            "results", "discussion", "conclusion", "references",
            "treatment", "diagnosis", "dosage", "pharmacology",
            "contraindications", "indications", "adverse effects",
            "clinical trials", "guidelines",
        ]
        first_line = text.split("\n")[0].lower().strip()
        for section in medical_sections:
            if section in first_line:
                return section.title()
        return None
