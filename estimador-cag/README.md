# Estimador CAG — Proyecto 1 (FastAPI + Cache-Augmented Generation)

Servicio FastAPI que recibe **parámetros tipados de un proyecto** y devuelve una
**estimación de software** generada por un LLM.

Arquitectura **CAG (Cache-Augmented Generation)**: todo el contexto que necesita
el modelo (unos pocos ejemplos de estimaciones previas) viaja **dentro del prompt
en cada llamada**. No hay base de datos, ni retrieval, ni persistencia.

**Interfaz de producto (Sesión 4):** el usuario ya no escribe un prompt en un
textarea libre. Rellena un formulario con parámetros tipados (`project_type`,
`detail_level`, `output_format`, `description`) y **el prompt se compone en el
backend** con una plantilla Jinja2 versionada. *El prompt es un artefacto de
software: vive en el repo, se versiona y se testea.*

## Estructura

```
estimador-cag/
├── app/
│   ├── main.py              # App FastAPI + /health + router
│   ├── config.py            # Configuración con Pydantic BaseSettings (.env)
│   ├── routers/
│   │   └── estimations.py   # POST /api/v1/estimate (parámetros tipados)
│   ├── schemas/
│   │   └── estimation.py    # EstimationRequest/Response (Pydantic + Enums)
│   ├── prompts/
│   │   └── estimation.py    # Plantilla Jinja2 versionada (build_system_prompt)
│   ├── services/
│   │   └── llm_service.py   # Llamada al LLM (genera y stream) + coste
│   └── context/
│       └── examples.py      # Contexto estático: ejemplos de estimaciones previas
├── streamlit_app.py         # Interfaz de producto (formulario + streaming)
├── transcripcion_ejemplo.txt
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## Requisitos

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Una API key de OpenAI **o** Anthropic con créditos.

## Configuración

1. Copia el ejemplo de variables y rellena tus valores reales:

   ```bash
   cp .env.example .env
   ```

2. Edita `.env`:

   ```env
   LLM_PROVIDER=anthropic        # o "openai"
   ANTHROPIC_API_KEY=sk-ant-...  # tu key real
   OPENAI_API_KEY=sk-...         # (si usas openai)
   ```

   > `.env` está en `.gitignore`: las keys nunca se suben al repo.

## Ejecutar

```bash
uv run uvicorn app.main:app --reload
```

- Documentación Swagger: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Probar el endpoint (parámetros tipados)

```bash
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Plataforma web de reservas para restaurantes: gestión de mesas, pagos online y panel de administración. Diseño en Figma. Plazo 6 semanas.",
    "project_type": "web_saas",
    "detail_level": "medium",
    "output_format": "phases_table"
  }'
```

Valores admitidos:
- `project_type`: `mobile_app` · `web_saas` · `internal_tool` · `data_pipeline` · `other`
- `detail_level`: `summary` · `medium` · `detailed`
- `output_format`: `phases_table` · `line_items` · `narrative`

### Respuesta de ejemplo

```json
{
  "estimation": "# Estimación: ...",
  "model": "claude-haiku-4-5",
  "provider": "anthropic",
  "input_tokens": 922,
  "output_tokens": 1232,
  "estimated_cost_usd": 0.007082
}
```

## Interfaz de producto (Streamlit)

Interfaz web con **formulario** (no chat libre) que reutiliza la misma lógica y
plantilla de prompt, con respuesta en **streaming** (token a token):

```bash
uv run streamlit run streamlit_app.py
```

Se abre en http://localhost:8501. Funcionalidades:

- **Formulario**: descripción + selectores de tipo de proyecto, nivel de detalle y formato de salida → el backend compone el prompt.
- **Streaming**: la estimación se "escribe" en tiempo real con `st.write_stream`.
- **Panel lateral** con visibilidad del CAG: vista previa del system prompt activo según las selecciones, ejemplos de contexto y métricas de la última llamada.

> La API key se lee desde `.env` (vía Pydantic Settings), nunca está en el código.

## Cómo funciona (interfaz de producto + CAG)

1. El usuario aporta **parámetros tipados** (`EstimationRequest`), no un prompt.
2. `prompts/estimation.py` compone el **system prompt** con una plantilla Jinja2
   versionada, inyectando los parámetros + los ejemplos de referencia (CAG).
3. La **descripción** del proyecto va como mensaje `user`.
4. El LLM devuelve la estimación, que el endpoint retorna como JSON.

```
[system]    -> plantilla (rol + nivel/formato) + ejemplos de referencia (CAG)
[user]      -> descripción del proyecto
[assistant] -> estimación generada
```
