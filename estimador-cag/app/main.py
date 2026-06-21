"""Aplicación FastAPI — Estimador de software con arquitectura CAG."""

from fastapi import FastAPI

from app.routers import estimations

app = FastAPI(
    title="Estimador CAG",
    description=(
        "Servicio que recibe la transcripción de una reunión y devuelve una "
        "estimación de software generada por un LLM. Arquitectura CAG: el contexto "
        "estático (ejemplos de estimaciones previas) se inyecta en cada llamada."
    ),
    version="0.1.0",
)

app.include_router(estimations.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health():
    """Estado del servicio."""
    return {"status": "ok"}
