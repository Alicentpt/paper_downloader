"""Helpers for extracting stable titles and filenames from downloaded PDFs."""

from __future__ import annotations

import re
from pathlib import Path

import PyPDF2
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar, LTTextContainer, LTTextLine


def extract_largest_text_from_pdf(pdf_path: str | Path) -> str:
    """Return the text line with the largest average font size in a PDF."""
    largest_text = ""
    largest_size = 0.0

    for page_layout in extract_pages(pdf_path):
        for element in page_layout:
            if not isinstance(element, LTTextContainer):
                continue

            for text_line in element:
                if not isinstance(text_line, LTTextLine):
                    continue

                char_sizes = [
                    character.size for character in text_line if isinstance(character, LTChar)
                ]
                if not char_sizes:
                    continue

                font_size = sum(char_sizes) / len(char_sizes)
                if font_size > largest_size:
                    largest_size = font_size
                    largest_text = text_line.get_text().strip()

    return largest_text


def extract_pdf_metadata_title(pdf_path: str | Path) -> str:
    """Return the `/Title` metadata entry from a PDF when it is available."""
    with Path(pdf_path).open("rb") as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        if pdf_reader.metadata and pdf_reader.metadata.get("/Title"):
            return str(pdf_reader.metadata["/Title"]).strip()
    return ""


def extract_pdf_title(pdf_path: str | Path) -> str:
    """Return the best available human-readable title for a PDF."""
    title = extract_pdf_metadata_title(pdf_path)
    if not title or "doi" in title.lower():
        title = extract_largest_text_from_pdf(pdf_path)
    return title.strip()


def sanitize_filename(
    value: str,
    fallback: str = "downloaded_paper",
    max_length: int = 120,
) -> str:
    """Convert arbitrary text into a filesystem-safe file stem."""
    sanitized = re.sub(r"\s+", " ", (value or "")).strip()
    sanitized = "".join(
        character
        for character in sanitized
        if character.isalnum() or character in (" ", "-", "_", ".")
    )
    sanitized = sanitized.strip(" ._-")
    if not sanitized:
        sanitized = fallback
    return sanitized[:max_length]
