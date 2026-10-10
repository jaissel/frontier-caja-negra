import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise SystemExit("Falta la key: ábre el archivo .env y pega tu OPENROUTER_API_KEY.")

# OpenRouter usa la misma librería de OpenAI, solo cambia la dirección (base_url)
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

respuesta = client.chat.completions.create(
    model="anthropic/claude-sonnet-5.5",  # puedes cambiarlo por cualquier modelo de openrouter.ai/models
    messages=[{"role": "user", "content": "Hola, dime en una frase que funcionas."}],
)

print(respuesta.choices[0].message.content)
