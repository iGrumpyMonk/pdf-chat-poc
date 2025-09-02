import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-12-01-preview")

# backwards compatibility
OPENAI_API_KEY = AZURE_OPENAI_API_KEY

DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING", "")

DOCS_DIR = os.getenv("DOCS_DIR", "./documents")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_index")

CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5-chat")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
WATCH_INTERVAL = int(os.getenv("WATCH_INTERVAL_SECONDS", "5"))

Path(DOCS_DIR).mkdir(parents=True, exist_ok=True)
Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)

if not AZURE_OPENAI_API_KEY or not DB_CONNECTION_STRING or not AZURE_OPENAI_ENDPOINT:
    raise RuntimeError(
        "Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and DB_CONNECTION_STRING in .env file")
