from pathlib import Path
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


def split_docs(docs, chunk_size, chunk_overlap):
    if not docs:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(docs)


def load_one_file(path: Path, chunk_size: int, chunk_overlap: int):
    ext = path.suffix.lower()
    loader = TextLoader if ext == ".txt" else PyPDFLoader if ext == ".pdf" else Docx2txtLoader if ext == ".docx" else None
    if not loader:
        return []
    try:
        raw = loader(str(path)).load()
        for d in raw:
            d.metadata = {**d.metadata, "source": str(path.resolve())}
        return split_docs(raw, chunk_size, chunk_overlap)
    except Exception:
        return []


def upsert_file(vs, path: Path, chunk_size: int, chunk_overlap: int) -> int:
    src = str(path.resolve())
    try:
        vs.delete(where={"source": src})
    except Exception:
        pass
    chunks = load_one_file(path, chunk_size, chunk_overlap)
    if chunks:
        vs.add_documents(chunks)
    return len(chunks)


def sync_new_or_changed_files(vs, seen_files: dict, docs_dir: str, chunk_size: int, chunk_overlap: int) -> int:
    added = 0
    for pattern in ("*.txt", "*.pdf", "*.docx"):
        for f in Path(docs_dir).rglob(pattern):
            try:
                mtime = f.stat().st_mtime
            except FileNotFoundError:
                continue
            key = str(f.resolve())
            last = seen_files.get(key)
            if (last is None) or (mtime > last):
                added += upsert_file(vs, f, chunk_size, chunk_overlap)
                try:
                    seen_files[key] = mtime
                except FileNotFoundError:
                    pass
    return added
