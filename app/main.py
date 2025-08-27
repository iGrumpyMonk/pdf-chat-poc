import asyncio
from fastapi import FastAPI
from .settings import DOCS_DIR, CHROMA_DIR, POLL_SECONDS, EMBED_MODEL, CHAT_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, DB_CONNECTION_STRING
from .indexer import create_embeddings, open_vector_store, initial_file_ingest, initial_db_ingest
from .db_loader import db_connect
from .watcher import watcher_loop
from .routers.api import router as api_router

app = FastAPI()
app.state.emb = None
app.state.vs = None
app.state.conn = None
app.state.seen_files = {}
app.state.last_seen_ids = {"Products":0,"Orders":0,"OrderItems":0}
app.state.CHAT_MODEL = CHAT_MODEL

@app.on_event("startup")
async def startup():
    app.state.conn = db_connect(DB_CONNECTION_STRING)
    app.state.emb = create_embeddings(EMBED_MODEL)
    app.state.vs = open_vector_store(app.state.emb, CHROMA_DIR)
    initial_file_ingest(app.state.vs, DOCS_DIR, app.state.seen_files, CHUNK_SIZE, CHUNK_OVERLAP)
    app.state.last_seen_ids = initial_db_ingest(app.state.vs, app.state.conn)
    app.include_router(api_router)
    asyncio.create_task(watcher_loop(app.state.vs, app.state.conn, app.state.seen_files, app.state.last_seen_ids, DOCS_DIR, CHUNK_SIZE, CHUNK_OVERLAP, POLL_SECONDS))

def get_app():
    return app
