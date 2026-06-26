""" main executor of agent, use langgraph"""
from langgraph.graph import StateGraph, START, END
from graph import MessagesState, llm_call, tool_node, intent_node, summary_node, after_llm, after_intent

# Build workflow
agent_builder = StateGraph(MessagesState)

# Add nodes
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_node("intent_node", intent_node)
agent_builder.add_node("summary_node", summary_node)
# Add edges to connect nodes
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    after_llm,["tool_node", "intent_node","summary_node", END]
)
agent_builder.add_edge("tool_node", "llm_call")
agent_builder.add_conditional_edges(
    "intent_node",
    after_intent,
    ["tool_node", "summary_node"]
)
agent_builder.add_edge("summary_node", END)

# Compile the agent
agent = agent_builder.compile()

# Show the agent
from IPython.display import Image, display
display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

# Invoke
log_path = "logs\sample.json"
from langchain.messages import HumanMessage
messages = [HumanMessage(content=f"do log analysis for this log: {log_path}")]
messages = agent.stream({"messages": messages})
for chunk in messages:
    for node_name, node_output in chunk.items():
        if "messages" in node_output:
            # get node output and print the latest message content
            latest_msg = node_output["messages"]
            for msg in latest_msg:
                print(f"\n[{node_name} 节点输出]: {msg.content}")