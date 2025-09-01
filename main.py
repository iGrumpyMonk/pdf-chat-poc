import asyncio
from fastapi import FastAPI
from settings import *
from core.indexer import setup_vector_store
from core.watcher import file_watcher_task
from routers.api import router as api_router

app = FastAPI()

app.state.vs = None
app.state.sql_db = None
app.state.seen_files = {}
app.state.CHAT_MODEL = CHAT_MODEL

@app.on_event("startup")
async def startup():
    print("Starting RAG System...")
    app.state.vs = setup_vector_store()
    asyncio.create_task(file_watcher_task(
        app.state.vs, 
        app.state.seen_files, 
        DOCS_DIR
    ))
    app.include_router(api_router)