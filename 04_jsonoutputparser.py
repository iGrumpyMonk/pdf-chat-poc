from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.json import JsonOutputParser
from dotenv import load_dotenv
load_dotenv()


llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
parser = JsonOutputParser()
formatting = parser.get_format_instructions()

prompt = ChatPromptTemplate.from_messages([
    ("system", "return valid JSON only"),
    ("human",  "Topic: {topic}\n"
               "Make an object with keys 'answer' (string) and 'bullets' (list of strings).\n"
               "{formatting}")
])


def qa():
    topic = input("please enter the topic you want to ask about:  ").strip()
    msgs = prompt.format_messages(topic=topic, formatting=formatting)
    resp = llm.invoke(msgs)
    # print(resp.content)
    data = parser.parse(resp.content)
    # print("\nParsed dict:", data)
    print("Answer:", data.get("answer"))
    print("Bullets:", data.get("bullets"))


if __name__ == "__main__":
    qa()
