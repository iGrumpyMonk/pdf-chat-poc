from pathlib import Path
from langchain_openai import AzureOpenAIEmbeddings
from langchain_chroma import Chroma
from core.document_loader import load_documents_from_directory
from settings import (
    EMBED_MODEL,
    CHROMA_DIR,
    DOCS_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    OPENAI_API_VERSION
)


def setup_vector_store():
    print(" Setting up vector store...")

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=EMBED_MODEL,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=OPENAI_API_VERSION,
        api_key=AZURE_OPENAI_API_KEY,
    )

    vector_store = Chroma(
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )

    added_count = load_documents_from_directory(
        vector_store, DOCS_DIR, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"Processed {added_count} new document chunks")
    return vector_store
