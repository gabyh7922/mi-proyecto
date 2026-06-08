import os

# Cargar variables de entorno desde .env si está disponible.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Importar clientes si están instalados.
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

anthropic_client = None
if Anthropic and ANTHROPIC_API_KEY:
    anthropic_client = Anthropic()

openai_client = None
if OpenAI and OPENAI_API_KEY:
    openai_client = OpenAI()

if __name__ == "__main__":
    if not anthropic_client:
        print("Error: ANTHROPIC_API_KEY no configurada o librería no instalada.")
    else:
        response = anthropic_client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "Hola, ¿cómo estás?"}
            ],
        )
        print(response.content[0].text)
