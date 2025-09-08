from fastapi import APIRouter, Query, Request, Depends
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
import urllib.parse
import random
from auth import require_admin, require_manager, get_current_active_user, require_admin_or_manager
from settings import DB_CONNECTION_STRING, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION

router = APIRouter()

_sql_db = None

GREETING_RESPONSES = [
    "Hello! I'm here to help you with questions about our products, orders, and company policies.",
    "Hi there! What can I help you find today?",
    "Welcome! I can assist you with product information, order details, and company documentation.",
    "Hey! Feel free to ask me about our products, sales data, or company policies."
]

FALLBACK_RESPONSES = [
    "I'm not sure I understand. Could you ask about our products, orders, or company policies?",
    "Could you rephrase that? I can help with product questions, order information, and company documentation.",
    "I didn't quite get that. Try asking about our products, sales data, or company policies.",
    "That's unclear to me. I'm here to help with product info, orders, and company documents."
]


def detect_intent(llm: AzureChatOpenAI, user_input: str) -> str:
    """
    Detect the intent of user input
    Returns: 'greeting', 'query', or 'unknown'
    """
    intent_prompt = SystemMessage(content=(
        "You are an intent classifier for MyShop customer service system.\n"
        "Classify the user input into ONE of these categories:\n\n"
        "- 'greeting': Greetings, hello, hi, how are you, thanks, goodbye, small talk\n"
        "- 'query': Real questions about products, orders, sales, policies, company info, documentation\n"
        "- 'unknown': Unclear input, gibberish, random words, unrelated topics\n\n"
        "Respond with ONLY the category name: greeting, query, or unknown"
    ))

    response = llm.invoke([intent_prompt, HumanMessage(
        content=f"User input: {user_input}")]).content.strip().lower()

    if 'greeting' in response:
        return 'greeting'
    elif 'query' in response:
        return 'query'
    else:
        return 'unknown'


def get_sql_database():
    global _sql_db
    if _sql_db is None:
        uri = "mssql+pyodbc:///?odbc_connect=" + \
            urllib.parse.quote_plus(DB_CONNECTION_STRING)
        _sql_db = SQLDatabase.from_uri(
            uri,
            include_tables=["Products", "Orders", "OrderItems"],
            sample_rows_in_table_info=3
        )
        print(" Connected to MyShop database")
    return _sql_db


def get_conversation_history(request: Request, session_id: str):
    if not hasattr(request.app.state, 'conversations'):
        request.app.state.conversations = {}
    if session_id not in request.app.state.conversations:
        request.app.state.conversations[session_id] = []
    return request.app.state.conversations[session_id]


def add_to_history(request: Request, session_id: str, question: str, answer: str, sql_query: str = None):
    history = get_conversation_history(request, session_id)
    entry = {"question": question, "answer": answer}
    if sql_query:
        entry["sql_query"] = sql_query
    history.append(entry)
    if len(history) > 10:
        history.pop(0)


def route_question(llm: AzureChatOpenAI, question: str) -> str:
    prompt = SystemMessage(content=(
        "You are a router for MyShop system. Answer with ONE WORD: 'sql' or 'docs'.\n"
        "Choose 'sql' for: products, orders, customers, sales, prices, quantities, order items, revenue, dates, totals.\n"
        "Choose 'docs' for: policies, procedures, guidelines, manuals, company information, help documents.\n"
    ))
    response = llm.invoke([prompt, HumanMessage(
        content=f"Question: {question}")]).content.strip().lower()
    return "sql" if "sql" in response else "docs"


def handle_sql_question(llm: AzureChatOpenAI, question: str, history: list = None) -> dict:
    db = get_sql_database()

    previous_filters = ""
    if history:
        for entry in reversed(history):
            if "sql_query" in entry:
                prev_sql = entry["sql_query"]
                if "WHERE" in prev_sql.upper():
                    where_part = prev_sql.upper().split("WHERE", 1)[1]
                    if "GROUP BY" in where_part:
                        where_part = where_part.split("GROUP BY")[0]
                    if "ORDER BY" in where_part:
                        where_part = where_part.split("ORDER BY")[0]
                    previous_filters = f"Previous filters used: WHERE {where_part.strip()}"
                break

    sql_prompt = f"""Write a SELECT query for Microsoft SQL Server to query the MyShop database.

Available tables and schema:
{db.get_table_info()}

Question: {question}

{previous_filters}

Requirements:
- SELECT-only queries (no INSERT/UPDATE/DELETE)
- Use TOP 100 to limit results  
- Use correct table names: Products, Orders, OrderItems
- Use correct column names: product_id, name, price, order_id, customer_name, order_date, order_item_id, quantity, unit_price
- If asking for totals/aggregates and there were previous filters, reuse those filters
- For totals/sums, calculate (quantity * unit_price) and use SUM()
- Return only the SQL query, no explanation

SQL:"""

    sql_query = llm.invoke(sql_prompt).content.strip()
    if "```" in sql_query:
        sql_query = sql_query.split("```sql")[-1].split("```")[0].strip()

    dangerous_words = ["INSERT", "UPDATE",
                       "DELETE", "DROP", "ALTER", "TRUNCATE"]
    if any(word in sql_query.upper() for word in dangerous_words):
        return {"answer": "Security error: Only SELECT queries are allowed.", "sources": []}

    try:
        query_tool = QuerySQLDatabaseTool(db=db)
        result = query_tool.invoke(sql_query)
        answer_prompt = f"""Based on the SQL query results, provide a CONCISE and DIRECT answer to the user's question.

User's Question: {question}
Query Results: {result}

Requirements:
- Be PRECISE and BRIEF
- Don't add extra explanations unless asked
- If it's a number/total question, give the number clearly
- Don't make assumptions about customer names unless specified in the question

Answer:"""
        answer = llm.invoke(answer_prompt).content
        return {
            "answer": answer,
            "sources": [{"type": "database", "sql_query": sql_query}],
            "sql_query": sql_query
        }
    except Exception as e:
        return {"answer": f"Database error: {str(e)}", "sources": []}


def handle_docs_question(llm: AzureChatOpenAI, vs, question: str) -> dict:
    try:
        docs = vs.similarity_search(question, k=4)
    except Exception as e:
        return {"answer": f"Document search error: {str(e)}", "sources": []}

    if not docs:
        return {"answer": "I couldn't find relevant information in the documents.", "sources": []}

    context = "\n---\n".join([doc.page_content for doc in docs])
    sources = [{"type": "document", "source": doc.metadata.get(
        "source", "unknown")} for doc in docs]

    docs_prompt = f"""Answer the user's question using ONLY the provided context. If the context doesn't contain enough information to answer the question, say so clearly.
Be CONCISE and DIRECT.

Question: {question}

Context from documents:
{context}

Answer:"""
    answer = llm.invoke(docs_prompt).content
    return {"answer": answer, "sources": sources}


def create_azure_llm(model_name: str) -> AzureChatOpenAI:
    """Create AzureChatOpenAI instance with proper configuration"""
    return AzureChatOpenAI(
        azure_deployment=model_name,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=OPENAI_API_VERSION,
        api_key=AZURE_OPENAI_API_KEY,
        temperature=0
    )


@router.get("/api/ask", dependencies=[Depends(require_admin)])
async def ask_question(
    request: Request,
    question: str = Query(..., description="Your question"),
    session_id: str = Query(
        "default", description="Session ID for conversation history")
):
    if not question.strip():
        return {"error": "Please provide a question"}

    llm = create_azure_llm(request.app.state.CHAT_MODEL)

    try:
        history = get_conversation_history(request, session_id)

        intent = detect_intent(llm, question)
        print(f" Intent detected: {intent} for question: '{question}'")

        if intent == "greeting":
            answer = random.choice(GREETING_RESPONSES)
            add_to_history(request, session_id, question, answer)
            return {
                "answer": answer,
                "sources": [{"type": "greeting", "intent": "greeting"}]
            }

        elif intent == "unknown":
            answer = random.choice(FALLBACK_RESPONSES)
            add_to_history(request, session_id, question, answer)
            return {
                "answer": answer,
                "sources": [{"type": "fallback", "intent": "unknown"}]
            }
        route = route_question(llm, question)
        print(f" Question: '{question}' → Route: {route}")

        if route == "sql":
            result = handle_sql_question(llm, question, history)
        else:
            result = handle_docs_question(llm, request.app.state.vs, question)

        sql_query = result.get("sql_query")
        add_to_history(request, session_id, question,
                       result["answer"], sql_query)
        return result

    except Exception as e:
        return {"error": f"System error: {str(e)}"}
