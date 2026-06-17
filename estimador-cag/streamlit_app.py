"""Interfaz conversacional (Streamlit) para el Estimador CAG.

Ejecutar desde la raíz del proyecto (estimador-cag/):

    uv run streamlit run streamlit_app.py

Reutiliza la lógica y el system prompt CAG del backend (app/services/llm_service.py).
La API key se lee desde .env (vía Pydantic Settings), nunca está en el código.
"""

import streamlit as st

from app.config import get_settings
from app.context.examples import ESTIMATION_EXAMPLES
from app.services.llm_service import build_system_prompt, stream_estimation

st.set_page_config(page_title="Estimador CAG", page_icon="🧮", layout="wide")

settings = get_settings()
active_model = (
    settings.anthropic_model
    if settings.llm_provider == "anthropic"
    else settings.openai_model
)

# --- Estado de la conversación (persiste durante la sesión) ---
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role": "user"|"assistant", "content": str}]
if "last_meta" not in st.session_state:
    st.session_state.last_meta = None


# --- NIVEL 3 (opcional): panel lateral con visibilidad del CAG ---
with st.sidebar:
    st.header("⚙️ Contexto CAG")
    st.write(f"Proveedor: **{settings.llm_provider}**")
    st.write(f"Modelo: `{active_model}`")

    with st.expander("🧠 System prompt (solo lectura)"):
        st.code(build_system_prompt(), language="markdown")

    with st.expander(f"📚 Contexto estático inyectado ({len(ESTIMATION_EXAMPLES)} ejemplos)"):
        for i, ex in enumerate(ESTIMATION_EXAMPLES, start=1):
            st.markdown(f"**Ejemplo {i} — resumen de la reunión:**")
            st.caption(ex["meeting_summary"])
            st.markdown(ex["estimation"])
            st.divider()

    st.subheader("📊 Última llamada")
    meta = st.session_state.last_meta
    if meta:
        c1, c2 = st.columns(2)
        c1.metric("Tokens entrada", meta.get("input_tokens", "—"))
        c2.metric("Tokens salida", meta.get("output_tokens", "—"))
        st.metric("Tiempo de respuesta", f"{meta.get('elapsed_s', '—')} s")
        st.caption(f"Modelo: {meta.get('model')} · Proveedor: {meta.get('provider')}")
    else:
        st.caption("Aún no hay llamadas en esta sesión.")

    if st.button("🗑️ Reiniciar conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_meta = None
        st.rerun()


# --- Cabecera ---
st.title("🧮 Estimador de Software — CAG")
st.caption(
    "Pega la transcripción de una reunión y recibe una estimación generada por un LLM. "
    "Puedes pedir ajustes en mensajes siguientes (el chat mantiene el contexto)."
)

# --- NIVEL 1: render del historial de la conversación ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- Entrada del usuario ---
prompt = st.chat_input("Pega aquí la transcripción de la reunión…")
if prompt:
    # Mostrar y guardar el mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- NIVEL 2: respuesta en streaming (token a token) ---
    with st.chat_message("assistant"):
        meta: dict = {}
        try:
            full_response = st.write_stream(
                stream_estimation(st.session_state.messages, metadata=meta)
            )
        except Exception as exc:  # noqa: BLE001
            full_response = f"⚠️ Error al generar la estimación: {exc}"
            st.error(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.session_state.last_meta = meta or None
    st.rerun()
