from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
load_dotenv()


llm = ChatOpenAI(model="gpt-5-nano", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You explain things to absolute beginners. Keep it simple."),
    ("human",  "Explain {topic} in exactly {n} short bullet points.")
])


def qa():
    topic = input("please enter the topic you want to ask about:  ").strip()
    n = int(input("how many bulletpoints do you need: ").strip())
    msgs = prompt.format_messages(topic=topic, n=n)
    resp = llm.invoke(msgs)
    print(resp.content)


if __name__ == "__main__":
    qa()
