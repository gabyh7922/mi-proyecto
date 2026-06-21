"""Extracción de texto de adjuntos — Camino B (extracción local).

Elegimos el Camino B (pypdf / python-docx) frente al multimodal directo porque:
- Es independiente del proveedor (mismo código para OpenAI o Anthropic).
- Da control sobre qué texto entra al prompt.
- Prepara el terreno para el chunking de RAG (módulo 3).
"""

from io import BytesIO


def extract_text(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _from_pdf(data)
    if name.endswith(".docx"):
        return _from_docx(data)
    # txt u otros: intento utf-8
    return data.decode("utf-8", errors="ignore")


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _from_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)


def build_attachments_text(files: list[tuple[str, bytes]]) -> str:
    """Concatena el texto de los adjuntos con un separador claro por archivo."""
    parts = []
    for filename, data in files:
        text = extract_text(filename, data).strip()
        if text:
            parts.append(f"--- attachment: {filename} ---\n{text}")
    return "\n\n".join(parts)
