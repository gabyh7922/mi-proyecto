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
