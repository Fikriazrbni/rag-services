"""File parsers for PDF, DOCX, and TXT documents."""

import os
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF
from docx import Document as DocxDocument


@dataclass
class PageContent:
    page_number: int
    text: str
    headings: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    pages: list[PageContent]
    skipped_pages: list[int] = field(default_factory=list)
    total_text: str = ""

    def __post_init__(self):
        if not self.total_text:
            self.total_text = "\n\n".join(p.text for p in self.pages if p.text.strip())


class FileParser:
    """Parses PDF, DOCX, and TXT files into structured text content."""

    def parse(self, file_path: str, mime_type: str) -> ParseResult:
        """Route to the correct parser based on mime type."""
        if mime_type == "application/pdf":
            return self._parse_pdf(file_path)
        elif mime_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            return self._parse_docx(file_path)
        elif mime_type.startswith("text/"):
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported mime type: {mime_type}")

    def _parse_pdf(self, file_path: str) -> ParseResult:
        """Parse PDF using PyMuPDF. Handles mixed-content pages."""
        pages = []
        skipped_pages = []

        doc = fitz.open(file_path)
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()

                if not text:
                    skipped_pages.append(page_num + 1)
                    continue

                pages.append(PageContent(
                    page_number=page_num + 1,
                    text=text,
                ))
        finally:
            doc.close()

        if not pages:
            raise ValueError(
                "No extractable text found in PDF. "
                "The document may contain only images or be password-protected."
            )

        return ParseResult(pages=pages, skipped_pages=skipped_pages)

    def _parse_docx(self, file_path: str) -> ParseResult:
        """Parse DOCX using python-docx."""
        doc = DocxDocument(file_path)
        paragraphs_text = []

        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs_text.append(para.text.strip())

        if not paragraphs_text:
            raise ValueError("No extractable text found in DOCX document.")

        full_text = "\n\n".join(paragraphs_text)
        pages = [PageContent(page_number=1, text=full_text)]

        return ParseResult(pages=pages)

    def _parse_txt(self, file_path: str) -> ParseResult:
        """Parse plain text files."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()

        if not content:
            raise ValueError("No text content found in file.")

        pages = [PageContent(page_number=1, text=content)]
        return ParseResult(pages=pages)
