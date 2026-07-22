import io

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = (".pdf", ".txt")


class UnsupportedFileTypeError(Exception):
    pass


class EmptyDocumentError(Exception):
    pass


def _extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_txt_text(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        text = _extract_pdf_text(file_bytes)
    elif lower_name.endswith(".txt"):
        text = _extract_txt_text(file_bytes)
    else:
        raise UnsupportedFileTypeError(
            f"Unsupported file type for '{filename}'. Supported: {SUPPORTED_EXTENSIONS}"
        )

    if not text.strip():
        raise EmptyDocumentError(f"No extractable text found in '{filename}'.")

    return text


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            chunks.append(paragraph)
            continue

        start = 0
        while start < len(paragraph):
            end = start + chunk_size
            chunks.append(paragraph[start:end])
            if end >= len(paragraph):
                break
            start = end - overlap

    return chunks
