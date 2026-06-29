"""Bloque 3 — Corpus de adjuntos sintéticos.

Genera PDFs calibrados por **caracteres de texto extraído** (5, 20, 50, 100 KB de
texto plano ~ 5k/20k/50k/100k caracteres). Calibramos por caracteres extraídos y
no por bytes de archivo porque fpdf comprime los streams: un PDF de pocos KB en
disco puede contener cientos de miles de caracteres, y lo que de verdad estresa
al CAG es el texto que entra al prompt (~tokens), no el peso del fichero.

No se comitean: el runner los regenera porque son deterministas (mismo contenido
siempre).

Cada PDF empieza con un marcador único (``MARKER``) dentro de un requisito
concreto, para poder medir el *recall* del contenido del adjunto en la respuesta
del modelo (¿sobrevive el requisito clave al crecer el adjunto?). El resto es
relleno tipo Lorem Ipsum hasta alcanzar el objetivo de caracteres.

Uso directo:

    uv run python -m evals.stress.fixtures.build_pdfs
"""

from __future__ import annotations

import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent
TARGET_SIZES_KB = (5, 20, 50, 100)
# 1 KB de texto plano ~ 1000 caracteres extraídos.
CHARS_PER_KB = 1000

# Marcador que la estimación debería referenciar si "ve" el adjunto.
MARKER = "ACME-LEDGER-7"
MARKER_SENTENCE = (
    f"CRITICAL REQUIREMENT: the system must export every transaction in the "
    f"{MARKER} certified audit format, validated nightly."
)

_LOREM = (
    "The platform shall provide a robust and auditable workflow for every module. "
    "Each requirement is tracked, versioned and reviewed by the product team. "
    "Non-functional constraints include availability, latency and data retention. "
    "Stakeholders expect clear reporting and predictable delivery milestones. "
)


def _paragraph(i: int) -> str:
    return f"Section {i}. " + _LOREM * 3


def _render(n_paragraphs: int, path: Path) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 5, MARKER_SENTENCE)
    pdf.ln(3)
    for i in range(1, n_paragraphs + 1):
        pdf.multi_cell(0, 5, _paragraph(i))
        pdf.ln(1)
    pdf.output(str(path))


def _extracted_chars(path: Path) -> int:
    # Mide con el mismo extractor del producto (Camino B).
    from app.services.attachments import extract_text

    return len(extract_text(path.name, path.read_bytes()))


def build_pdf(target_kb: int, path: Path) -> Path:
    """Construye un PDF cuyo texto extraído ~ target_kb * 1000 caracteres."""
    target_chars = target_kb * CHARS_PER_KB
    # Cada párrafo aporta ~unos cientos de caracteres extraídos; empezamos bajo y
    # subimos hasta alcanzar el objetivo (determinista, pocos archivos).
    n_paragraphs = max(2, target_chars // 800)
    while True:
        _render(n_paragraphs, path)
        if _extracted_chars(path) >= target_chars or n_paragraphs > target_chars:
            break
        n_paragraphs = int(n_paragraphs * 1.3) + 1
    return path


def build_all() -> dict[int, Path]:
    """Regenera los cuatro PDFs y devuelve {kb: path}. (0 KB = ausencia de adjunto.)"""
    out: dict[int, Path] = {}
    for kb in TARGET_SIZES_KB:
        path = FIXTURES_DIR / f"attach_{kb}kb.pdf"
        build_pdf(kb, path)
        out[kb] = path
    return out


if __name__ == "__main__":
    for kb, path in build_all().items():
        print(
            f"{path.name}: {os.path.getsize(path) / 1024:.1f} KB en disco, "
            f"{_extracted_chars(path)} chars extraídos"
        )
