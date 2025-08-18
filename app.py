from fastapi import FastAPI
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

load_dotenv()
app = FastAPI()

@app.post("/ingest")
def ingest():
    reader = PdfReader("data/sample.pdf")
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = splitter.split_text(text)

    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.from_texts(chunks, emb)
    db.save_local("faiss_pdf_index")

    return {"chunks": len(chunks), "status": "index saved"}

@app.post("/ask")
def ask(question: str):
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.load_local("faiss_pdf_index", emb, allow_dangerous_deserialization=True)

    docs = db.similarity_search(question, k=3)
    context = "\n\n".join(d.page_content for d in docs)

    llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
    msgs = [
        {"role": "system", "content": "Answer ONLY from context. If missing, say: 'Not enough info in context.'"},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ]
    resp = llm.invoke(msgs)

    return {"question": question, "answer": resp.content}
