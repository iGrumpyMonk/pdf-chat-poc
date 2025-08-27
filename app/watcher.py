import asyncio
from .document_loader import sync_new_or_changed_files
from .db_loader import fetch_new_db_docs, current_max_ids

async def watcher_loop(vs, conn, seen_files, last_seen_ids, docs_dir, chunk_size, chunk_overlap, poll_seconds: int):
    while True:
        try:
            sync_new_or_changed_files(vs, seen_files, docs_dir, chunk_size, chunk_overlap)
            new_docs = fetch_new_db_docs(conn, last_seen_ids)
            if new_docs:
                vs.add_documents(new_docs)
                ids = current_max_ids(conn)
                last_seen_ids["Products"] = ids["Products"]
                last_seen_ids["Orders"] = ids["Orders"]
                last_seen_ids["OrderItems"] = ids["OrderItems"]
        except Exception:
            pass
        await asyncio.sleep(poll_seconds)
