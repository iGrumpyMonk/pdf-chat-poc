import os
import asyncio
import pyodbc
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from langchain_core.documents import Document
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# ----------- config (env vars) -----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING", "")
DOCS_DIR = os.getenv("DOCS_DIR", "./documents")
POLL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

Path(DOCS_DIR).mkdir(parents=True, exist_ok=True)
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY")

# ----------- app state -----------
app = FastAPI()
app.state.emb = None
app.state.vs = None
app.state.conn = None

# ----------- helpers: DB -----------
def get_db_conn():
    if not DB_CONNECTION_STRING:
        raise RuntimeError("Set DB_CONNECTION_STRING")
    return pyodbc.connect(DB_CONNECTION_STRING, autocommit=True)

def load_db_documents(conn):
    docs = []
    cur = conn.cursor()

    # Products
    try:
        cur.execute("SELECT product_id, name, price FROM Products")
        for pid, name, price in cur.fetchall():
            docs.append(Document(
                page_content=f"DB Product: id={pid}, name={name}, price={price}",
                metadata={"source": "db", "table": "Products", "id": int(pid)}
            ))
    except Exception:
        pass

    # Orders
    try:
        cur.execute("SELECT order_id, customer_name, order_date FROM Orders")
        for oid, customer, odate in cur.fetchall():
            docs.append(Document(
                page_content=f"DB Order: id={oid}, customer={customer}, order_date={odate}",
                metadata={"source": "db", "table": "Orders", "id": int(oid)}
            ))
    except Exception:
        pass

    # OrderItems joined to Products for richer text
    try:
        cur.execute("""
            SELECT oi.order_id, oi.product_id, oi.quantity, p.name, p.price
            FROM OrderItems oi
            JOIN Products p ON p.product_id = oi.product_id
        """)
        for oid, pid, qty, pname, pprice in cur.fetchall():
            docs.append(Document(
                page_content=f"DB OrderItem: order_id={oid}, product_id={pid}, qty={qty}, product={pname}, price_each={pprice}",
                metadata={"source": "db", "table": "OrderItems", "order_id": int(oid), "product_id": int(pid)}
            ))
    except Exception:
        pass

    return docs

# ----------- helpers: files -----------
def load_file_documents():
    docs = []

    # .txt files
    try:
        txt_loader = DirectoryLoader(
            DOCS_DIR, glob="**/*.txt", loader_cls=TextLoader, show_progress=False
        )
        docs.extend(txt_loader.load())
    except Exception:
        pass

    # .pdf files (PyPDFLoader yields one Document per page)
    try:
        pdf_loader = DirectoryLoader(
            DOCS_DIR, glob="**/*.pdf", loader_cls=PyPDFLoader, show_progress=False
        )
        docs.extend(pdf_loader.load())
    except Exception:
        pass

    # .docx files
    try:
        docx_loader = DirectoryLoader(
            DOCS_DIR, glob="**/*.docx", loader_cls=Docx2txtLoader, show_progress=False
        )
        docs.extend(docx_loader.load())
    except Exception:
        pass

    if not docs:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    return splitter.split_documents(docs)

# ----------- indexing -----------
def rebuild_index():
    db_docs = load_db_documents(app.state.conn) if app.state.conn else []
    file_docs = load_file_documents()
    all_docs = db_docs + file_docs

    if not all_docs:
        app.state.vs = None
        return

    app.state.vs = InMemoryVectorStore.from_documents(
        all_docs,
        embedding=app.state.emb
    )
    print(f"[index] {len(all_docs)} docs indexed")

async def poll_changes_forever():
    while True:
        try:
            rebuild_index()
        except Exception as e:
            print("[poller] error:", e)
        await asyncio.sleep(POLL_SECONDS)

# ----------- startup -----------
@app.on_event("startup")
async def on_startup():
    app.state.conn = get_db_conn()
    app.state.emb = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    rebuild_index()
    asyncio.create_task(poll_changes_forever())
    print("[startup] ready; polling for DB/docs changes...")

# ----------- single endpoint -----------
@app.get("/api/ask")
def ask(
    question: str = Query(..., description="Your question"),
    k: int = 6,
):
    if app.state.vs is None:
        return {"answer": "I have no data yet.", "sources": []}

    hits = app.state.vs.similarity_search(question, k=k)
    if not hits:
        return {
            "answer": "I don't have enough information in the current data.",
            "sources": [],
        }

    context = "\n---\n".join(d.page_content for d in hits)
    sources = [d.metadata for d in hits]

    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)
    msgs = [
        SystemMessage(content="Answer strictly from the provided context. If it's not there, say you don't know."),
        HumanMessage(content=f"Question: {question}\n\nContext:\n{context}"),
    ]
    out = llm.invoke(msgs)
    answer = out.content if hasattr(out, "content") else str(out)

    return {"answer": answer, "sources": sources}

