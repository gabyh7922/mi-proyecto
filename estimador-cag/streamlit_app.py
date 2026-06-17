"""Interfaz de PRODUCTO (Streamlit) para el Estimador CAG.

Sesión 4 — "del chat a la interfaz de producto": el usuario ya no escribe un
prompt en un textarea libre; rellena un formulario con parámetros tipados y el
backend compone el prompt (plantilla Jinja2 versionada + contexto CAG).

Ejecutar desde la raíz del proyecto:
    uv run streamlit run streamlit_app.py
"""

import streamlit as st
from pydantic import ValidationError

from app.config import get_settings
from app.context.examples import ESTIMATION_EXAMPLES
from app.prompts.estimation import PROMPT_VERSION, build_system_prompt
from app.schemas.estimation import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)
from app.services.llm_service import stream_estimation

st.set_page_config(page_title="Estimador CAG", page_icon="🧮", layout="wide")

settings = get_settings()
active_model = (
    settings.anthropic_model
    if settings.llm_provider == "anthropic"
    else settings.openai_model
)

# --- Mapeos etiqueta legible -> enum ---
PROJECT_TYPE_LABELS = {
    "Aplicación móvil": ProjectType.MOBILE_APP,
    "Web / SaaS": ProjectType.WEB_SAAS,
    "Herramienta interna": ProjectType.INTERNAL_TOOL,
    "Pipeline de datos": ProjectType.DATA_PIPELINE,
    "Otro": ProjectType.OTHER,
}
DETAIL_LABELS = {
    "Resumen": DetailLevel.SUMMARY,
    "Medio": DetailLevel.MEDIUM,
    "Detallado": DetailLevel.DETAILED,
}
FORMAT_LABELS = {
    "Tabla por fases": OutputFormat.PHASES_TABLE,
    "Lista de tareas": OutputFormat.LINE_ITEMS,
    "Narrativa": OutputFormat.NARRATIVE,
}

# --- Estado ---
st.session_state.setdefault("last_meta", None)
st.session_state.setdefault("last_estimation", None)

# --- Cabecera + formulario ---
st.title("🧮 Estimador de Software — CAG")
st.caption(
    "Rellena el formulario y genera la estimación. El prompt lo compone el backend "
    "a partir de tus parámetros (interfaz de producto, no chat libre)."
)

description = st.text_area(
    "Descripción del proyecto",
    height=160,
    placeholder="Describe el proyecto: alcance, integraciones, plazos, equipo… (mín. 20 caracteres)",
    key="description",
)
c1, c2 = st.columns(2)
c1.selectbox("Tipo de proyecto", list(PROJECT_TYPE_LABELS), key="project_label")
c2.selectbox("Formato de salida", list(FORMAT_LABELS), key="format_label")
st.radio("Nivel de detalle", list(DETAIL_LABELS), horizontal=True, key="detail_label")
generate = st.button("⚡ Generar estimación", type="primary", use_container_width=True)


def _selected(mapping: dict, key: str):
    return mapping[st.session_state.get(key, next(iter(mapping)))]


# --- Sidebar (Nivel 3): visibilidad del CAG ---
with st.sidebar:
    st.header("⚙️ Contexto CAG")
    st.write(f"Proveedor: **{settings.llm_provider}** · `{active_model}`")
    st.caption(f"Versión de prompt: `{PROMPT_VERSION}`")

    # Vista previa del system prompt según las selecciones actuales del formulario.
    preview = EstimationRequest.model_construct(
        description="",
        project_type=_selected(PROJECT_TYPE_LABELS, "project_label"),
        detail_level=_selected(DETAIL_LABELS, "detail_label"),
        output_format=_selected(FORMAT_LABELS, "format_label"),
    )
    with st.expander("🧠 System prompt activo (solo lectura)"):
        st.code(build_system_prompt(preview), language="markdown")

    with st.expander(f"📚 Contexto estático ({len(ESTIMATION_EXAMPLES)} ejemplos)"):
        for i, ex in enumerate(ESTIMATION_EXAMPLES, start=1):
            st.markdown(f"**Ejemplo {i}:**")
            st.caption(ex["meeting_summary"])
            st.markdown(ex["estimation"])
            st.divider()

    st.subheader("📊 Última llamada")
    meta = st.session_state.last_meta
    if meta:
        m1, m2 = st.columns(2)
        m1.metric("Tokens entrada", meta.get("input_tokens", "—"))
        m2.metric("Tokens salida", meta.get("output_tokens", "—"))
        st.metric("Tiempo de respuesta", f"{meta.get('elapsed_s', '—')} s")
        st.caption(f"Modelo: {meta.get('model')}")
    else:
        st.caption("Aún no hay llamadas en esta sesión.")

# --- Generación ---
if generate:
    try:
        request = EstimationRequest(
            description=description or "",
            project_type=_selected(PROJECT_TYPE_LABELS, "project_label"),
            detail_level=_selected(DETAIL_LABELS, "detail_label"),
            output_format=_selected(FORMAT_LABELS, "format_label"),
        )
    except ValidationError:
        st.warning("⚠️ La descripción debe tener al menos 20 caracteres.")
    else:
        st.subheader("Estimación")
        meta_out: dict = {}
        try:
            full = st.write_stream(stream_estimation(request, metadata=meta_out))
            st.session_state.last_estimation = full
            st.session_state.last_meta = meta_out or None
            st.rerun()  # refresca las métricas del sidebar
        except Exception as exc:  # noqa: BLE001
            st.error(f"⚠️ Error al generar la estimación: {exc}")
elif st.session_state.last_estimation:
    st.subheader("Última estimación")
    st.markdown(st.session_state.last_estimation)
