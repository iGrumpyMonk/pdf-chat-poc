from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from .document_loader import upsert_file


def create_embeddings(model: str):
    return OpenAIEmbeddings(model=model)


def open_vector_store(emb, persist_dir: str):
    return Chroma(embedding_function=emb, persist_directory=persist_dir)


def initial_file_ingest(vs, docs_dir: str, seen_files: dict, chunk_size: int, chunk_overlap: int) -> int:
    added = 0
    for pattern in ("*.txt", "*.pdf", "*.docx"):
        for f in Path(docs_dir).rglob(pattern):
            try:
                added += upsert_file(vs, f, chunk_size, chunk_overlap)
                seen_files[str(f.resolve())] = f.stat().st_mtime
            except FileNotFoundError:
                pass
    return added
