# Estimador CAG — Proyecto 1 (FastAPI + Cache-Augmented Generation)

Servicio FastAPI que recibe la **transcripción de una reunión** y devuelve una
**estimación de software** generada por un LLM.

Arquitectura **CAG (Cache-Augmented Generation)**: todo el contexto que necesita
el modelo (unos pocos ejemplos de estimaciones previas) viaja **dentro del prompt
en cada llamada**. No hay base de datos, ni retrieval, ni persistencia.

## Estructura

```
estimador-cag/
├── app/
│   ├── main.py              # App FastAPI + /health + router
│   ├── config.py            # Configuración con Pydantic BaseSettings (.env)
│   ├── routers/
│   │   └── estimations.py   # POST /api/v1/estimate (schemas request/response)
│   ├── services/
│   │   └── llm_service.py   # Lógica CAG: system prompt + ejemplos + llamada al LLM
│   └── context/
│       └── examples.py      # Contexto estático: ejemplos de estimaciones previas
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

## Probar el endpoint

```bash
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": "En la reunión con el equipo de marketing, el cliente explicó que necesita una landing page con formulario de contacto, integración con su CRM actual (HubSpot), y una sección de blog con editor WYSIWYG. El plazo ideal sería 4 semanas. El diseño ya existe en Figma."
  }'
```

(También puedes usar el contenido de [`transcripcion_ejemplo.txt`](transcripcion_ejemplo.txt).)

### Respuesta de ejemplo

```json
{
  "estimation": "## Estimación: ...",
  "model": "claude-haiku-4-5",
  "provider": "anthropic",
  "input_tokens": 812,
  "output_tokens": 430,
  "estimated_cost_usd": 0.002962
}
```

## Cómo funciona la arquitectura CAG aquí

1. `context/examples.py` define ejemplos de estimaciones previas (el "conocimiento").
2. `services/llm_service.py` los inyecta en el **system prompt** (few-shot).
3. La **transcripción** del usuario va como mensaje `user`.
4. El LLM devuelve la estimación, que el endpoint retorna como JSON.

```
[system]    -> instrucciones + ejemplos de estimaciones previas
[user]      -> transcripción de la reunión a estimar
[assistant] -> estimación generada
```
