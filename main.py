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


if __name__ == "__main__":
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hola, ¿qué es la inteligencia artificial?"}],
    )
    print(response.content[0].text)
