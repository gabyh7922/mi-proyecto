import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

client = Anthropic()
app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {"mensaje": "Servidor funcionando. Usa POST /chat para hablar con Claude."}


@app.post("/chat")
def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": body.message}],
    )
    return {"respuesta": response.content[0].text}


MENSAJE = "Hola, ¿qué es la inteligencia artificial?"

SYSTEM_PROMPT = """Eres un experto en estimación de software con 20 años de experiencia
en proyectos de inteligencia artificial y machine learning. Respondes de forma técnica
y precisa, orientada a equipos de desarrollo. Usas métricas, referencias a metodologías
ágiles y ejemplos concretos del sector."""

# Precios por millón de tokens (claude-opus-4-8)
PRECIO_INPUT_POR_MILLON  = 5.00   # USD
PRECIO_OUTPUT_POR_MILLON = 25.00  # USD


def imprimir_metadatos(response):
    tokens_input  = response.usage.input_tokens
    tokens_output = response.usage.output_tokens
    modelo        = response.model

    coste_input  = (tokens_input  / 1_000_000) * PRECIO_INPUT_POR_MILLON
    coste_output = (tokens_output / 1_000_000) * PRECIO_OUTPUT_POR_MILLON
    coste_total  = coste_input + coste_output

    print("\n--- Metadatos ---")
    print(f"  Modelo:          {modelo}")
    print(f"  Tokens entrada:  {tokens_input}")
    print(f"  Tokens salida:   {tokens_output}")
    print(f"  Coste estimado:  ${coste_total:.6f} USD"
          f"  (input ${coste_input:.6f} + output ${coste_output:.6f})")


if __name__ == "__main__":
    print("=" * 60)
    print("NIVEL 1 — Sin system prompt")
    print("=" * 60)
    r1 = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": MENSAJE}],
    )
    print(r1.content[0].text)
    imprimir_metadatos(r1)

    print("\n" + "=" * 60)
    print("NIVEL 2 — Con system prompt (experto en estimación de software)")
    print("=" * 60)
    r2 = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": MENSAJE}],
    )
    print(r2.content[0].text)
    imprimir_metadatos(r2)
