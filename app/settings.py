import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING", "")
DOCS_DIR = os.getenv("DOCS_DIR", "./documents")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_index")
POLL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5-nano")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

Path(DOCS_DIR).mkdir(parents=True, exist_ok=True)
Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)

if not OPENAI_API_KEY or not DB_CONNECTION_STRING:
    raise RuntimeError("Set OPENAI_API_KEY and DB_CONNECTION_STRING in .env")
