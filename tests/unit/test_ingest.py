from pathlib import Path

import pytest

from app.ingest import (
    UnsupportedFileTypeError,
    EmptyDocumentError,
    chunk_text,
    extract_text,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_text_from_pdf():
    pdf_bytes = (FIXTURES / "sample.pdf").read_bytes()

    text = extract_text(pdf_bytes, "sample.pdf")

    assert "refund policy" in text
    assert "30 days" in text


def test_extract_text_from_txt():
    txt_bytes = (FIXTURES / "sample.txt").read_bytes()

    text = extract_text(txt_bytes, "sample.txt")

    assert "refund policy" in text
    assert "Support is available" in text


def test_extract_text_from_txt_latin1_fallback():
    latin1_bytes = "café résumé".encode("latin-1")

    text = extract_text(latin1_bytes, "notes.txt")

    assert "caf" in text


def test_extract_text_rejects_unsupported_extension():
    with pytest.raises(UnsupportedFileTypeError):
        extract_text(b"whatever", "sample.docx")


def test_extract_text_rejects_empty_text():
    with pytest.raises(EmptyDocumentError):
        extract_text(b"   \n\n  ", "empty.txt")


def test_chunk_text_respects_size_and_overlap():
    text = "A" * 50 + " " + "B" * 50 + " " + "C" * 50

    chunks = chunk_text(text, chunk_size=60, overlap=10)

    assert len(chunks) >= 2
    assert all(len(c) <= 60 for c in chunks)


def test_chunk_text_splits_on_paragraphs_first():
    text = "First paragraph text.\n\nSecond paragraph text.\n\nThird paragraph text."

    chunks = chunk_text(text, chunk_size=1000, overlap=0)

    assert chunks == [
        "First paragraph text.",
        "Second paragraph text.",
        "Third paragraph text.",
    ]


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text("", chunk_size=100, overlap=10) == []
