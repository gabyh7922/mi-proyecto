"""Interfaz conversacional con memoria (Streamlit) — Sesión 5.

- Crea una sesión al cargar y guarda el session_id en st.session_state.
- Campo de transcripción + selector múltiple de adjuntos (PDF/Word).
- Muestra el project_metadata actual en el sidebar (separación memoria/historial).
- Botón "Nueva conversación" que crea otra sesión y resetea el estado.

Llama al servicio de sesión en proceso (mismo proceso que Streamlit). Ejecutar:
    uv run streamlit run streamlit_app.py
"""

import streamlit as st

from app.config import get_settings
from app.services.session_service import estimate_in_session
from app.sessions import create_session, get_session

st.set_page_config(page_title="Estimador — memoria", page_icon="🧮", layout="wide")
settings = get_settings()
active_model = (
    settings.anthropic_model
    if settings.llm_provider == "anthropic"
    else settings.openai_model
)


def _new_session() -> str:
    return create_session().session_id


# Crear sesión al cargar
if "session_id" not in st.session_state:
    st.session_state.session_id = _new_session()

session = get_session(st.session_state.session_id)
if session is None:  # el proceso se reinició: creamos una nueva
    st.session_state.session_id = _new_session()
    session = get_session(st.session_state.session_id)

# --- Sidebar: memoria del proyecto ---
with st.sidebar:
    st.header("🧠 Memoria del proyecto")
    st.caption(f"session_id: `{session.session_id[:8]}…`")
    st.write(f"Proveedor: **{settings.llm_provider}** · `{active_model}`")

    md = session.metadata
    st.subheader("project_metadata")
    st.json(md.model_dump())

    st.caption(f"Turnos en historial: {len(session.history.windowed_messages()) // 2} "
               f"(ventana máx. {session.history.max_turns})")

    if st.button("🆕 Nueva conversación", use_container_width=True):
        st.session_state.session_id = _new_session()
        st.rerun()

# --- Cabecera ---
st.title("🧮 Estimador conversacional")
st.caption(
    "Pega una transcripción (y adjunta documentación si quieres). El sistema recuerda "
    "el proyecto en curso entre turnos y puedes ir refinando la estimación."
)

# --- Historial de la conversación ---
for m in session.history.windowed_messages():
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- Entrada ---
with st.form("turn_form", clear_on_submit=True):
    transcript = st.text_area(
        "Transcripción de la reunión / instrucción",
        height=140,
        placeholder="Ej.: El cliente quiere una app móvil de reservas… (o 'sube las horas de QA')",
    )
    files = st.file_uploader(
        "Adjuntos (PDF / Word, opcional)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )
    submitted = st.form_submit_button("⚡ Generar / refinar estimación", type="primary")

if submitted:
    if not transcript or not transcript.strip():
        st.warning("⚠️ Escribe una transcripción o instrucción.")
    else:
        attachments = [(f.name, f.getvalue()) for f in (files or [])]
        with st.spinner("Generando estimación y actualizando memoria…"):
            try:
                estimate_in_session(session, transcript, attachments)
            except Exception as exc:  # noqa: BLE001
                st.error(f"⚠️ Error: {exc}")
            else:
                st.rerun()  # refresca historial y project_metadata
