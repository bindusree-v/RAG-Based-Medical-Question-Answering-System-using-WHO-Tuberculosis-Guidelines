"""
MediRAG AI – Text Extraction Module
Supports PDF, DOCX, and TXT using PyPDF, pdfplumber, python-docx.
"""

import io
from pathlib import Path
from typing import List, Tuple

from app.utils.logger import logger


class PageContent:
    """Holds extracted content from a single page / block."""

    def __init__(self, text: str, page_number: int = 0, metadata: dict = None):
        self.text = text.strip()
        self.page_number = page_number
        self.metadata = metadata or {}


class TextExtractor:
    """
    Multi-format text extractor. Tries pdfplumber first for PDFs,
    falls back to pypdf on failure. Supports DOCX and plain TXT.
    """

    def extract(self, file_path: str) -> Tuple[str, List[PageContent]]:
        """
        Extract text from a file.

        Returns:
            full_text (str): Concatenated text of all pages/blocks.
            pages (List[PageContent]): Per-page content objects.
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext in (".docx", ".doc"):
            return self._extract_docx(file_path)
        elif ext == ".txt":
            return self._extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    def _extract_pdf(self, file_path: str) -> Tuple[str, List[PageContent]]:
        """Try pdfplumber, fall back to pypdf."""
        try:
            return self._extract_pdf_pdfplumber(file_path)
        except Exception as exc:
            logger.warning(f"pdfplumber failed for {file_path}: {exc}. Falling back to pypdf.")
            return self._extract_pdf_pypdf(file_path)

    def _extract_pdf_pdfplumber(self, file_path: str) -> Tuple[str, List[PageContent]]:
        import pdfplumber

        pages: List[PageContent] = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                # Attempt table extraction
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        row_text = " | ".join(cell or "" for cell in row if cell)
                        text += f"\n{row_text}"
                pages.append(PageContent(text=text, page_number=i))

        full_text = "\n\n".join(p.text for p in pages if p.text)
        return full_text, pages

    def _extract_pdf_pypdf(self, file_path: str) -> Tuple[str, List[PageContent]]:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        pages: List[PageContent] = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(PageContent(text=text, page_number=i))

        full_text = "\n\n".join(p.text for p in pages if p.text)
        return full_text, pages

    # ------------------------------------------------------------------
    # DOCX
    # ------------------------------------------------------------------

    def _extract_docx(self, file_path: str) -> Tuple[str, List[PageContent]]:
        from docx import Document

        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]

        # Tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)

        full_text = "\n\n".join(paragraphs)
        pages = [PageContent(text=full_text, page_number=1)]
        return full_text, pages

    # ------------------------------------------------------------------
    # TXT
    # ------------------------------------------------------------------

    def _extract_txt(self, file_path: str) -> Tuple[str, List[PageContent]]:
        text = Path(file_path).read_text(encoding="utf-8", errors="replace")
        pages = [PageContent(text=text, page_number=1)]
        return text, pages

    # ------------------------------------------------------------------
    # Bytes interface (for in-memory uploads)
    # ------------------------------------------------------------------

    def extract_from_bytes(
        self, content: bytes, filename: str
    ) -> Tuple[str, List[PageContent]]:
        """Extract text from raw bytes without saving to disk first."""
        import tempfile
        import os

        ext = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            return self.extract(tmp_path)
        finally:
            os.unlink(tmp_path)
