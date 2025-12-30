import ollama
from app.core.settings import settings

client = ollama.Client(host=settings.OLLAMA_HOST)
try:
    models = client.list()
    print(models)
except Exception as e:
    print(f"Error: {e}")
