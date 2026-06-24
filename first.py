from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain.tools import tool

model = ChatOllama(
    model="llama3.1:8b", # qwen 2.5-coder:7b don't support tool calls
    base_url="http://localhost:11434", # 显式指向映射出来的本地端口
)

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气。"""
    print(f"获取 {city} 的天气信息...")
    return f"{city}总是阳光明媚！"

tools=[get_weather]

agent = create_agent(
    model=model,
    tools=tools,
)


result = agent.stream(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
for chunk in result:
    for node_name, node_output in chunk.items():
        if "messages" in node_output:
            # get node output and print the latest message content
            latest_msg = node_output["messages"]
            for msg in latest_msg:
                print(f"\n[{node_name} 节点输出]: {msg.content}")

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in New York?"}]}
)
print(result["messages"][-1].content_blocks)

"""
try deep agent instead of simple agent, I found it costs more time to run deep agent
I don't recommend using deep agent for now, but I will keep it here for future reference
"""

"""
from deepagents import create_deep_agent

deep_agent = create_deep_agent(
    model=model,
    tools=tools,
)

print("\n=== 开始追踪重型 Deep Agent 的一举一动 ===")

deep_agent_stream = deep_agent.stream(
    {"messages": [{"role": "user", "content": "What's the weather in Los Angeles?"}]}
)

for chunk in deep_agent_stream:
    for node_name, node_output in chunk.items():
        if node_output and isinstance(node_output, dict) and "messages" in node_output:
            latest_msg = node_output["messages"][-1]
            print(f"\n[{node_name} node working]: {latest_msg.content}")
        else:
            print(f"[{node_name} node done with no messages]")
"""
