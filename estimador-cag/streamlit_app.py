"""Interfaz de PRODUCTO (Streamlit) para el Estimador.

Sesión 4 — "del chat a la interfaz de producto": el usuario rellena un
formulario (st.form) que produce un EstimationRequest tipado; el backend compone
el prompt con plantillas Jinja2 versionadas. La salida sigue siendo texto libre.

Ejecutar desde la raíz del proyecto:
    uv run streamlit run streamlit_app.py
"""

import streamlit as st
from pydantic import ValidationError

from app.config import get_settings
from app.prompts.loader import render_estimation_prompt
from app.schemas import DetailLevel, EstimationRequest, OutputFormat, ProjectType
from app.services.llm_service import run_estimation

st.set_page_config(page_title="Estimador", page_icon="🧮", layout="wide")

settings = get_settings()
active_model = (
    settings.anthropic_model
    if settings.llm_provider == "anthropic"
    else settings.openai_model
)

# Etiqueta legible -> enum
PROJECT_TYPE_LABELS = {
    "Aplicación móvil": ProjectType.MOBILE_APP,
    "Web / SaaS": ProjectType.WEB_SAAS,
    "Herramienta interna": ProjectType.INTERNAL_TOOL,
    "Pipeline de datos": ProjectType.DATA_PIPELINE,
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

st.title("🧮 Estimador de Software")
st.caption(
    "Rellena el formulario y genera la estimación. El prompt lo compone el backend "
    "a partir de tus parámetros (interfaz de producto, no chat libre)."
)

with st.form("estimation_form"):
    description = st.text_area(
        "Descripción del proyecto",
        height=160,
        placeholder="Describe el proyecto: alcance, integraciones, plazos… (mín. 20 caracteres)",
    )
    c1, c2, c3 = st.columns(3)
    project_label = c1.selectbox("Tipo de proyecto", list(PROJECT_TYPE_LABELS))
    detail_label = c2.selectbox("Nivel de detalle", list(DETAIL_LABELS), index=1)
    format_label = c3.selectbox("Formato de salida", list(FORMAT_LABELS))
    submitted = st.form_submit_button("⚡ Generar estimación", type="primary")

if submitted:
    try:
        request = EstimationRequest(
            description=description or "",
            project_type=PROJECT_TYPE_LABELS[project_label],
            detail_level=DETAIL_LABELS[detail_label],
            output_format=FORMAT_LABELS[format_label],
        )
    except ValidationError:
        st.warning("⚠️ La descripción debe tener entre 20 y 2000 caracteres.")
    else:
        with st.spinner("Generando estimación…"):
            try:
                response = run_estimation(request)
            except Exception as exc:  # noqa: BLE001
                st.error(f"⚠️ Error al generar la estimación: {exc}")
            else:
                st.subheader("Estimación")
                st.markdown(response.text)
                st.caption(f"prompt_version: `{response.prompt_version}`")

# Panel lateral: vista previa del prompt compuesto según las selecciones
with st.sidebar:
    st.header("⚙️ Prompt (backend)")
    st.write(f"Proveedor: **{settings.llm_provider}** · `{active_model}`")
    preview = EstimationRequest.model_construct(
        description="(vista previa)",
        project_type=PROJECT_TYPE_LABELS[project_label],
        detail_level=DETAIL_LABELS[detail_label],
        output_format=FORMAT_LABELS[format_label],
    )
    system_preview, user_preview = render_estimation_prompt(preview)
    with st.expander("system.j2 (renderizado)"):
        st.code(system_preview)
    with st.expander("user.j2 (renderizado)"):
        st.code(user_preview)
