from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import CharacterTextSplitter

# import the necessary libraries for RAG (Retrieval-Augmented Generation) workflow
# split the text into chunks, create embeddings
texts = [
    "San Francisco is a beautiful city in California, famous for the Golden Gate Bridge.",
    "New York is a bustling metropolis in the United States, well-known for Times Square and Central Park.", 
    "Los Angeles is known for its entertainment industry and sunny weather."
]
splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = splitter.create_documents(texts)
embedding = OllamaEmbeddings(model="llama3.1:8b")

# create a vector database (vdb) using Chroma and the generated embeddings
vdb = Chroma.from_documents(docs, embedding)

# vdb -> retriever wrapper, which will be used in the RAG chain
# make sure to set the search_kwargs to limit the number of retrieved documents (k) for each query
retriever = vdb.as_retriever(search_kwargs={"k": 3})

prompt = ChatPromptTemplate.from_template(
    "Please answer the question based on the provided context. "
    "If the context provides a basic description, use it. If the context doesn't contain enough detail, "
    "you can state what's in the context first, and then briefly supplement it with your own knowledge.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}"
)
model = ChatOllama(model="llama3.1:8b", base_url="http://localhost:11434")

# ==================== 新版 RAG Chain 代替之前的RetrievalQA ====================
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)

#print("---------Try New Rag--------")
#print(rag_chain.invoke("What's the weather in San Francisco?"))

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气。"""
    print(f"获取 {city} 的天气信息...")
    return f"{city}总是阳光明媚！"

# wrapper rag_chain as a tool for querying special databases
@tool
def query_special_db(query: str) -> str:
    """
    当你需要查询关于城市（如旧金山、纽约、洛杉矶）的本地文档、背景知识、天气描述或特定信息时，调用此工具。
    """
    # 显式声明这是一个母类/基础检索动作
    return rag_chain.invoke(query)

tools=[get_weather,query_special_db]

agent = create_agent(
    model=model,
    tools=tools,
)


result = agent.stream(
    {"messages": [{"role": "user", "content": "What's special about San Francisco and NewYork?"}]}
)
for chunk in result:
    for node_name, node_output in chunk.items():
        if "messages" in node_output:
            # get node output and print the latest message content
            latest_msg = node_output["messages"]
            for msg in latest_msg:
                print(f"\n[{node_name} 节点输出]: {msg.content}")
