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
    print("ANTHROPIC_API_KEY presente:", bool(ANTHROPIC_API_KEY))
    print("OPENAI_API_KEY presente:", bool(OPENAI_API_KEY))
    print("anthropic_client creado:", anthropic_client is not None)
    print("openai_client creado:", openai_client is not None)
