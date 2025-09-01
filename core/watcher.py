import asyncio
from pathlib import Path
from core.document_loader import load_documents_from_directory
from settings import WATCH_INTERVAL

async def file_watcher_task(vector_store, seen_files: dict, docs_dir: str):
    print(f" Starting file watcher (checking every {WATCH_INTERVAL}s)")
    while True:
        try:
            added = load_documents_from_directory(vector_store, docs_dir, 800, 200)
            if added > 0:
                print(f"Auto-updated: {added} new document chunks")
            await cleanup_deleted_files(vector_store, docs_dir)
        except Exception as e:
            print(f"File watcher error: {e}")
        await asyncio.sleep(WATCH_INTERVAL)

async def cleanup_deleted_files(vector_store, docs_dir: str):
    try:
        existing_data = vector_store.get(include=["metadatas"])
        if not existing_data or not existing_data.get("metadatas"):
            return
        docs_path = Path(docs_dir).resolve()
        deleted_count = 0
        sources_to_remove = set()
        for metadata in existing_data["metadatas"]:
            if not metadata or "source" not in metadata:
                continue
            source_path = Path(metadata["source"])
            try:
                if str(source_path).startswith(str(docs_path)) and not source_path.exists():
                    sources_to_remove.add(metadata["source"])
            except:
                continue
        for source in sources_to_remove:
            try:
                vector_store.delete(where={"source": source})
                deleted_count += 1
                print(f" Removed chunks for deleted file: {Path(source).name}")
            except:
                continue
        if deleted_count > 0:
            print(f" Cleaned up {deleted_count} deleted files")
    except Exception as e:
        print(f"Cleanup error: {e}")
