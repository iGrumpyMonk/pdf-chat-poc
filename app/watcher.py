import asyncio
from .document_loader import sync_new_or_changed_files



async def watcher_loop(vs, seen_files, docs_dir, chunk_size, chunk_overlap, poll_seconds: int):
    while True:
        try:
            sync_new_or_changed_files(vs, seen_files, docs_dir, chunk_size, chunk_overlap)
        except Exception:
            pass
        await asyncio.sleep(poll_seconds)
