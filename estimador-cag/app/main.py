"""Aplicación FastAPI — Estimador de software con arquitectura CAG."""

from fastapi import FastAPI

from app.routers import estimations, sessions

app = FastAPI(
    title="Estimador",
    description=(
        "Servicio de estimación de software. Estimación por formulario (parámetros "
        "tipados) y estimación conversacional con memoria de sesión y adjuntos."
    ),
    version="0.2.0",
)

app.include_router(estimations.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health():
    """Estado del servicio."""
    return {"status": "ok"}
