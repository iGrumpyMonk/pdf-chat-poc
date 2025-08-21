from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

load_dotenv()

llm = ChatOpenAI(model="gpt-5-nano", temperature=0)

system_rule = "you are a concise tutor. reply in 2 or less short sentences."
user_prompt = ChatPromptTemplate.from_messages(["human", "{question}"])

history = [SystemMessage(content=system_rule)]


def trim_history(hist, max_turns=10):
    system = hist[:1]
    rest = hist[1:]
    recent = rest[-2*max_turns:]
    return system + recent


print("Type '/exit' to quit, '/sys' to change system rule, '/show' to see history.")
while True:
    q = input("\n Your Question: ").strip()
    if not q:
        continue
    if q == "/exit":
        break
    if q == "/show":
        print("\n_____HISTORY_______")
        for i, m in enumerate(history):
            role = "system" if isinstance(
                m, SystemMessage) else "Human" if isinstance(m, HumanMessage) else "AI"
            print(f"{i}: [{role}] {m.content}")
        print("---------------")
        continue
    if q == "/sys":
        new_sys = input("new system rule: ").strip()
        if new_sys:
            history[:] = [SystemMessage(content=new_sys)]
            print("history cleared and System message updated to: "+new_sys)
        continue

    turns = user_prompt.format_messages(question=q)
    ai = llm.invoke(history + turns)
    history.extend(turns)
    history.append(AIMessage(content=ai.content))
    history = trim_history(history)
    print("AI: ", ai.content)
