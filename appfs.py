from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()
app = FastAPI()

app.state.DB = None
app.state.CHAT = []


@app.get("/")
def home():
    return {"ok": True, "hint": "POST /ingest then /ask"}


@app.post("/ingest")
def ingest(files: list[UploadFile] = File(...)):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150)
    docs = []
    for f in files:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(f.file.read())
            tmp_path = tmp.name
        chunks = PyPDFLoader(tmp_path).load_and_split(text_splitter=splitter)
        Path(tmp_path).unlink(missing_ok=True)

        current_page = 0
        for d in chunks:
            raw = d.metadata.get("page")
            if isinstance(raw, int):
                current_page = raw + 1
            else:
                current_page += 1
            d.metadata["page"] = current_page
            d.metadata["source"] = f.filename

        docs.extend(chunks)

    if not docs:
        return {"status": "no text found", "files": [f.filename for f in files]}

    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    if app.state.DB is None:
        app.state.DB = InMemoryVectorStore(embedding=emb)
    app.state.DB.add_documents(docs)

    return {
        "status": "indexed (memory)",
        "files": [f.filename for f in files],
        "chunks_added": len(docs)
    }


def _history(last_n=4):
    lines = []
    for u, a in app.state.CHAT[-last_n:]:
        lines.append(f"User: {u}")
        lines.append(f"Assistant: {a}")
    return "\n".join(lines)


@app.post("/ask")
def ask(question: str, k: int = 3):
    if app.state.DB is None:
        return {"status": "empty index — upload PDFs via /ingest first"}
    hist = _history(last_n=4)
    retrieval_query = f"{hist}\n\nCurrent question: {question}" if hist else question
    docs = app.state.DB.similarity_search(retrieval_query, k=k)
    context_lines, evidence, sources = [], [], []
    for d in docs:
        src = d.metadata.get("source", "unknown")
        page = d.metadata.get("page", "?")
        tag = f"[{src}, p.{page}]"
        context_lines.append(f"{d.page_content}\n(Source: {tag})")
        evidence.append({"text": d.page_content, "source": src, "page": page})
        if tag not in sources:
            sources.append(tag)
    context_text = "\n\n".join(context_lines)
    llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
    messages = [
        SystemMessage(
            content="Answer strictly using ONLY the provided context snippets. If the answer is not present, reply exactly: 'Not enough info in context.'"),
        HumanMessage(
            content=f"Context:\n{context_text}\n\nQuestion: {question}")
    ]
    answer = llm.invoke(messages).content.strip()
    app.state.CHAT.append((question, answer))
    return {"question": question, "answer": answer, "sources": sources, "evidence": evidence}


@app.post("/reset_index")
def reset_index():
    app.state.DB = None
    app.state.CHAT = []
    return {"status": "cleared (vectors + chat)"}


@app.post("/reset_chat")
def reset_chat():
    app.state.CHAT = []
    return {"status": "chat cleared"}
