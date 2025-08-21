from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

load_dotenv()

llm = ChatOpenAI(model="gpt-5-nano", temperature=0)

history = [SystemMessage(content="Be direct. 1–2 sentences only.")]

print("Type 'leave the chat' to exit.")
while True:
    q = input("\nmy question: ").strip()
    if not q:
        continue
    if q.lower() == "leave the chat":
        print("this is the history", history)
        break

    history.append(HumanMessage(content=q))
    ai = llm.invoke(history)
    history.append(AIMessage(content=ai.content))
    print("AI:", ai.content)
