from fastapi import APIRouter, Query, Request
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
import urllib.parse                                                                       

router = APIRouter()

                                                    
_SQL_DB = None


                                                                               
def to_sqlalchemy_uri(odbc_conn_str: str) -> str:
    return "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc_conn_str)


                                                                    
def get_sql_db(odbc_conn_str: str) -> SQLDatabase:
    global _SQL_DB
    if _SQL_DB is None:
        uri = to_sqlalchemy_uri(odbc_conn_str)
                                                                                              
        _SQL_DB = SQLDatabase.from_uri(
            uri,
            include_tables=["Products", "Orders", "OrderItems"],
                                                                      
            sample_rows_in_table_info=2,
        )
    return _SQL_DB


                                                                               
def choose_path_with_llm(llm: ChatOpenAI, question: str) -> str:
    msgs = [
        SystemMessage(
            content=(
                "You are a strict router. Decide if the question should be answered "
                "from SQL tables (Products, Orders, OrderItems) or from documents. "
                "Answer with ONE WORD ONLY: sql or docs.\n\n"
                "Pick 'sql' for things like rows, totals, counts, prices, orders, products, quantities, "
                "customers, dates. Pick 'docs' for policies, procedures, guides, office info."
            )
        ),
        HumanMessage(
            content=f"Question: {question}\n\nRespond with exactly one word: sql or docs"),
    ]
    word = llm.invoke(msgs).content.strip().lower()
                                                      
    return "sql" if "sql" in word and "docs" not in word else "docs"


                                               
def llm_write_select(llm: ChatOpenAI, db: SQLDatabase, question: str) -> str:
    prompt = f"""You write one read-only T-SQL SELECT for Microsoft SQL Server.

Rules:
- SELECT-only. Never INSERT/UPDATE/DELETE/ALTER/DROP/TRUNCATE.
- Use SELECT TOP 100 ... (not LIMIT).
- Only select relevant columns. Use correct table/column names.

Available tables:
{db.get_table_info()}

Question: {question}

Return only the SQL (no explanation).
"""
    sql = llm.invoke(prompt).content.strip()

                                                                         
    if sql.startswith("```"):
        sql = sql.replace("```sql", "").replace("```", "").strip()

                                       
    BAD = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE")
    upper_sql = sql.upper()
    if any(b in upper_sql for b in BAD):
        raise ValueError("Refusing to run non-read-only SQL.")

                                                               
    if upper_sql.startswith("SELECT ") and " TOP " not in upper_sql[:30]:
                                                                
        sql = "SELECT TOP 100 " + sql[7:]

    return sql


def run_select_with_tool(db: SQLDatabase, sql: str) -> str:
    tool = QuerySQLDatabaseTool(db=db)
    return tool.invoke(sql)


def llm_explain_result(llm: ChatOpenAI, question: str, sql: str, result_text: str) -> str:
    prompt = (
        "Answer the user's question using ONLY the SQL result below. "
        "If the result is insufficient, say you don't know.\n\n"
        f"Question:\n{question}\n\nSQL:\n{sql}\n\nResult:\n{result_text}"
    )
    return llm.invoke(prompt).content


                                                                       
def answer_from_docs(llm: ChatOpenAI, vs, question: str, k: int = 3) -> dict:
    hits = vs.similarity_search(question, k=k)
    if not hits:
        return {"answer": "I don't know from the current documents.", "sources": []}

    context = "\n---\n".join(d.page_content for d in hits)
    sources = [d.metadata for d in hits]

    msgs = [
        SystemMessage(
            content="Answer strictly from the provided context. If it's not there, say you don't know."),
        HumanMessage(content=f"Question: {question}\n\nContext:\n{context}"),
    ]
    answer = llm.invoke(msgs).content
    return {"answer": answer, "sources": sources}


                                                              
@router.get("/api/ask")
def ask(request: Request, question: str = Query(...), k: int = 6):
    llm = ChatOpenAI(model=request.app.state.CHAT_MODEL, temperature=0)

                               
    route = choose_path_with_llm(llm, question)

    if route == "sql":
                                                                        
        from ..settings import DB_CONNECTION_STRING
        db = get_sql_db(DB_CONNECTION_STRING)

                                                
        sql = llm_write_select(llm, db, question)
        rows_text = run_select_with_tool(db, sql)
        answer = llm_explain_result(llm, question, sql, rows_text)
        return {"answer": answer, "sources": [{"source": "db", "sql": sql}]}

                                  
    return answer_from_docs(llm, request.app.state.vs, question, k=k)
