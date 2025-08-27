from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from .document_loader import upsert_file
from .db_loader import fetch_new_db_docs, current_max_ids

def create_embeddings(model: str):
    return OpenAIEmbeddings(model=model)

def open_vector_store(emb, persist_dir: str):
    return Chroma(embedding_function=emb, persist_directory=persist_dir)

def initial_file_ingest(vs, docs_dir: str, seen_files: dict, chunk_size: int, chunk_overlap: int):
    for pattern in ("*.txt", "*.pdf", "*.docx"):
        for f in Path(docs_dir).rglob(pattern):
            upsert_file(vs, f, chunk_size, chunk_overlap)
            try:
                seen_files[str(f.resolve())] = f.stat().st_mtime
            except FileNotFoundError:
                pass

def initial_db_ingest(vs, conn):
    for src in ("db/Products","db/Orders","db/OrderItems"):
        try:
            vs.delete(where={"source": src})
        except Exception:
            pass
    first_docs = fetch_new_db_docs(conn, {"Products":0,"Orders":0,"OrderItems":0})
    if first_docs:
        vs.add_documents(first_docs)
    return current_max_ids(conn)
