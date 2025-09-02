from pathlib import Path
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def get_file_loader(file_path: Path):
    ext = file_path.suffix.lower()
    if ext == '.txt':
        return TextLoader
    elif ext == '.pdf':
        return PyPDFLoader
    elif ext == '.docx':
        return Docx2txtLoader
    return None

def load_single_file(file_path: Path, chunk_size: int, chunk_overlap: int):
    loader_class = get_file_loader(file_path)
    if not loader_class:
        return []
    try:
        loader = loader_class(str(file_path))
        documents = loader.load()
        for doc in documents:
            doc.metadata.update({
                "source": str(file_path.resolve()),
                "filename": file_path.name,
                "file_type": file_path.suffix
            })
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        chunks = text_splitter.split_documents(documents)
        return chunks
    except Exception as e:
        print(f" Error loading {file_path.name}: {e}")
        return []

def load_documents_from_directory(vector_store, docs_dir: str, chunk_size: int, chunk_overlap: int) -> int:
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        print(f" Created documents directory: {docs_dir}")
        return 0
    try:
        existing_data = vector_store.get(include=["metadatas"])
        existing_files = set()
        if existing_data and "metadatas" in existing_data:
            for metadata in existing_data["metadatas"] or []:
                if metadata and "source" in metadata:
                    existing_files.add(metadata["source"])
    except:
        existing_files = set()
    total_added = 0
    supported_extensions = ['.txt', '.pdf', '.docx']
    for ext in supported_extensions:
        for file_path in docs_path.rglob(f"*{ext}"):
            file_key = str(file_path.resolve())
            if file_key in existing_files:
                continue
            chunks = load_single_file(file_path, chunk_size, chunk_overlap)
            if chunks:
                try:
                    vector_store.delete(where={"source": file_key})
                except:
                    pass
                vector_store.add_documents(chunks)
                total_added += len(chunks)
                print(f" Added {len(chunks)} chunks from {file_path.name}")
    return total_added
