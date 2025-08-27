from fastapi import APIRouter, Query, Request
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

router = APIRouter()

@router.get("/api/ask")
def ask(request: Request, question: str = Query(...), k: int = 6):
    vs = request.app.state.vs
    hits = vs.similarity_search(question, k=k)
    if not hits:
        return {"answer":"I don't know from the current data.","sources":[]}
    context = "\n---\n".join(d.page_content for d in hits)
    sources = [d.metadata for d in hits]
    llm = ChatOpenAI(model=request.app.state.CHAT_MODEL, temperature=0)
    msgs = [
        SystemMessage(content="Answer strictly from the provided context. If it's not there, say you don't know."),
        HumanMessage(content=f"Question: {question}\n\nContext:\n{context}"),
    ]
    answer = llm.invoke(msgs).content
    return {"answer": answer, "sources": sources}
