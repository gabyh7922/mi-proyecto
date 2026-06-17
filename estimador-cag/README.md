# Estimador — Proyecto 1 (FastAPI + interfaz de producto)

Servicio FastAPI que recibe **parámetros tipados de un proyecto** y devuelve una
**estimación de software** generada por un LLM.

**Sesión 4 — del chat a la interfaz de producto:** el usuario ya no escribe un
prompt en un textarea libre. Rellena un **formulario** con parámetros tipados
(`project_type`, `detail_level`, `output_format`, `description`) y **el prompt se
compone en el backend** a partir de plantillas **Jinja2 versionadas**. El prompt
es un artefacto de software: vive en el repo, se versiona y se testea.

## Estructura

```
estimador-cag/
├── app/
│   ├── main.py                       # App FastAPI + /health + router
│   ├── config.py                     # Configuración Pydantic Settings (.env)
│   ├── schemas.py                    # EstimationRequest/Response (Pydantic + Enums)
│   ├── routers/
│   │   └── estimations.py            # POST /api/v1/estimate (parámetros tipados)
│   ├── services/
│   │   └── llm_service.py            # run_estimation: render prompt + llamada al LLM
│   └── prompts/
│       ├── loader.py                 # render_estimation_prompt(request, version)
│       └── estimation/v1/
│           ├── system.j2             # rol + bloques condicionales (formato/detalle)
│           ├── user.j2               # envuelve la descripción del usuario
│           └── examples.j2           # few-shot (incluido en system con {% include %})
├── tests/
│   └── prompts/
│       └── test_estimation_v1.py     # tests del template (sin tocar APIs)
├── streamlit_app.py                  # interfaz de producto (st.form)
├── .env.example
├── pyproject.toml
└── README.md
```

## Requisitos

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Una API key de OpenAI **o** Anthropic con créditos.

## Configuración

```bash
cp .env.example .env
```

Edita `.env`:

```env
LLM_PROVIDER=anthropic        # o "openai"
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

> `.env` está en `.gitignore`: las keys nunca se suben al repo.

## Levantar el servicio

```bash
uv run uvicorn app.main:app --reload
```

- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Probar el endpoint

```bash
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "App móvil interna para que ventas registre visitas, con login, sync offline y push.",
    "project_type": "mobile_app",
    "detail_level": "detailed",
    "output_format": "phases_table"
  }'
```

Valores admitidos:
- `project_type`: `mobile_app` · `web_saas` · `internal_tool` · `data_pipeline`
- `detail_level`: `summary` · `medium` · `detailed`
- `output_format`: `phases_table` · `line_items` · `narrative`

Respuesta: `{ "text": "...", "prompt_version": "v1" }`.

> Bonus: el endpoint acepta `?prompt_version=v2` (query param) para seleccionar versión.

## Interfaz (Streamlit)

```bash
uv run streamlit run streamlit_app.py
```

Formulario con descripción + selectores. Al enviar compone un `EstimationRequest`,
llama al servicio y muestra la estimación. El sidebar muestra el `system.j2` y
`user.j2` renderizados según las selecciones actuales.

## Ejecutar los tests

```bash
uv run pytest
```

Son **tests del template** (no del LLM): verifican que el prompt renderizado
contiene la descripción, que `phases_table` activa las columnas correctas (y
`narrative` no), y que `detailed` añade la instrucción de asunciones por fase (y
`summary` no). Corren en milisegundos, sin coste de API.

## Cómo funciona

```
[system]  -> system.j2 (rol + bloques condicionales por formato/detalle + examples.j2)
[user]    -> user.j2 (envuelve la descripción del proyecto)
[assistant] -> estimación generada (texto libre)
```

El usuario aporta parámetros tipados; `render_estimation_prompt()` los inyecta en
las plantillas; el endpoint llama al LLM con `system` y `user` **separados**.

## Sesión 5 — Memoria conversacional y contexto enriquecido

Estimación **conversacional** con memoria de sesión y adjuntos, además del endpoint por formulario.

### Endpoints nuevos
- `POST /api/v1/sessions` → crea una sesión y devuelve `{"session_id": "..."}` (UUID v4).
- `POST /api/v1/sessions/{session_id}/estimate` → `multipart/form-data` con:
  - `transcript` (texto)
  - `attachments` (lista opcional de PDF/Word)
  Devuelve la estimación + el `project_metadata` actualizado.

### Memoria: historial vs project_metadata
- **Historial** (`app/sessions.py::ConversationHistory`): el array de mensajes que viaja al LLM, con **ventana deslizante** (`MAX_TURNS=6` pares user+assistant). El system prompt es invariante y se regenera cada turno.
- **project_metadata** (`ProjectMetadata`): hechos del proyecto (`project_name`, `assumed_team_size`, `mentioned_technologies`, `agreed_scope`). Vive aparte del historial y se inyecta en `<project_metadata>` del system prompt en cada turno.
- Estado **en memoria del proceso** (dict por `session_id`), sin BBDD. Si el servicio se reinicia, las sesiones se pierden (volatilidad aceptada en esta fase).

### Adjuntos — Camino B (extracción local)
Elegido `pypdf` (PDF) + `python-docx` (Word) en `app/services/attachments.py`. Motivo: **independiente del proveedor**, control fino sobre qué texto entra al prompt, y prepara el chunking de RAG (módulo 3). El texto extraído se concatena al transcript con separador `--- attachment: nombre ---`.

### Extracción de project_metadata — extractor LLM
`app/services/metadata_extractor.py` hace una llamada extra (barata) que devuelve JSON y se **mergea** con la metadata actual (unión de tecnologías). Elegido frente a heurística regex por ser más robusto ante lenguaje natural variado y multilingüe. Si la extracción falla, se conserva la metadata previa.

### Cliente
`uv run streamlit run streamlit_app.py`: crea una sesión al cargar, campo de transcripción + selector múltiple de adjuntos, panel lateral con el `project_metadata` en vivo y botón "Nueva conversación".

### Tests
`uv run pytest` — incluye `tests/test_sessions.py`: (1) dos turnos enlazados actualizan el `project_metadata`, (2) el contenido de un adjunto llega al prompt, (3) la ventana deslizante nunca supera `MAX_TURNS`. Las llamadas al LLM se mockean (rápidos, sin coste).

> **Fuera de alcance** (sesión en vivo): resumen acumulativo / anclas, tier dinámico, persistencia entre reinicios, y **búsqueda web + function calling a BBDD** (mecanismos 2 y 3 del artículo de contexto dinámico).
