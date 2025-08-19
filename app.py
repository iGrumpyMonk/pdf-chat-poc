from fastapi import UploadFile, File
from fastapi import FastAPI
from dotenv import load_dotenv
from pypdf import PdfReader
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
import shutil

load_dotenv()
app = FastAPI()

INDEX_DIR = "faiss_pdf_index"


def extract_chunks(files):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, chunk_overlap=200)
    chunks = []
    metas = []
    for f in files:
        reader = PdfReader(f.file)
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if not text:
                continue
            parts = splitter.split_text(text)
            for p in parts:
                chunks.append(p)
                metas.append({"source": f.filename, "page": i})
    return chunks, metas


@app.post("/ingest")
def ingest(files: list[UploadFile] = File(...)):
    chunks, metas = extract_chunks(files)
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    path = Path(INDEX_DIR)
    if path.exists():
        db = FAISS.load_local(
            INDEX_DIR, emb, allow_dangerous_deserialization=True)
        db.add_texts(chunks, metadatas=metas)
    else:
        db = FAISS.from_texts(chunks, emb, metadatas=metas)
    db.save_local(INDEX_DIR)
    total = len(db.index_to_docstore_id)
    return {
        "files_ingested": [f.filename for f in files],
        "added_chunks": len(chunks),
        "total_chunks": total,
        "status": "index saved"
    }


@app.post("/ask")
def ask(question: str, k: int = 3):
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.load_local(INDEX_DIR, emb, allow_dangerous_deserialization=True)
    docs = db.similarity_search(question, k=k)

    # build evidence list step by step
    evidence = []
    for d in docs:
        item = {
            "text": d.page_content,
            "source": d.metadata.get("source", "unknown"),
            "page": d.metadata.get("page", "?")
        }
        evidence.append(item)

    # List + join is faster than += because the latter creates a new string each time
    context_parts = []
    for e in evidence:
        piece = f"{e['text']}\n(Source: [{e['source']}, p.{e['page']}])"
        context_parts.append(piece)

    context = "\n\n".join(context_parts)

    # call the chat model
    llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
    msgs = [
        {"role": "system", "content": "Answer ONLY from context. If missing, say: 'Not enough info in context.'"},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ]
    resp = llm.invoke(msgs)

    # build unique sources
    all_sources = []
    for e in evidence:
        source_string = f"[{e['source']}, p.{e['page']}]"
        all_sources.append(source_string)

    unique_sources = []
    for s in all_sources:
        if s not in unique_sources:
            unique_sources.append(s)

    return {
        "question": question,
        "answer": resp.content,
        "sources": unique_sources,
        "evidence": evidence
    }


@app.post("/reset_index")
def reset_index():
    path = Path(INDEX_DIR)
    if path.exists():
        shutil.rmtree(INDEX_DIR)
        return {"status": "deleted", "index_dir": INDEX_DIR}
    return {"status": "not_found", "index_dir": INDEX_DIR}
