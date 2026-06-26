""" LangGraph for log analysis """

# define message state
import ast

from langchain.messages import AnyMessage, HumanMessage
from typing_extensions import TypedDict, Annotated
import operator,json,re,uuid

class MessagesState(TypedDict):
    #define the structure of the state dictionary
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

from langchain.messages import SystemMessage
from tools import model_with_tools,model
# define model node
def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""
    system = SystemMessage(
        content="""
        You are a log analyst, tasked with analyzing log data and identifying potential threats.
        You have access to the following tools:
        1. parse_logs(log_path: str): read log file, then parse it, and write a summary of suspicious activities in a cache file.
        2. find_threat_from_logs(CACHE_PATH: str): it can read cache file by parse log, and then check whether ip is suspicious, output the threat information.
        3. map_threats_to_mitre(CACHE_PATH: str): it can read cache file and map them to MITRE ATT&CK techniques.
        If you want to call a tool as the next step, please add this to response "Calling tool: <tool_name>, parameters: <parameters>. 
        You are ONLY allowed to call ONE tool per response. And you must do parse logs first before calling any other tools.
        Do NOT predict or fabricate tool results.
        When you get enough information, please output a final summary of the log data and any potential threats you have identified."
        Your final summary should be in the following json format:
        {
            "summary": "<summary of the log data>",
            "potential_threats": "<list of potential threats identified>"
        }
        """
    )

    return {
        "messages": [
            model_with_tools.invoke([system]+ state["messages"])
        ],
        "llm_calls": state.get('llm_calls', 0) + 1
    }


# define tool node
from langchain.messages import ToolMessage
from tools import tools_by_name

def tool_node(state: dict):
    """Performs the tool call"""

    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}

from langchain_core.messages import AIMessage

def summary_node(state: MessagesState):
    """Generates a summary of the log analysis"""
    
    instruction = HumanMessage(
        content="""
        Stop calling tools or creating any dialogue. 
        Based on all the log evidence and analysis history above, organize everything into the required JSON format perfectly.
        Response MUST be a valid JSON only:
        {
            "summary": "Overall log summary.",
            "potential_threats": "List of threats found."
        }
        """
    )
    response = model.invoke(state["messages"] + [instruction])
    return {"messages": [response]}

def intent_node(state: MessagesState):
    """
    intent extract through LLM, and then translate to tool call if valid
    """
    last_message = state["messages"][-1]
    content = last_message.content if isinstance(last_message, AIMessage) else ""

    response = model.invoke([
        SystemMessage(content="""You are a precise tool-intent extraction parser.
Extract which tool the input text wants to call and its arguments.

Allowed tools:
1. parse_logs            - argument: log_path
2. find_threat_from_logs - argument: CACHE_PATH
3. map_threats_to_mitre  - argument: CACHE_PATH

You MUST respond with a valid JSON object only. No markdown, no extra text.
Success: {"tool_name": "actual_tool_name", "parameters": {"arg": "value"}}
Failure: {"tool_name": "none", "parameters": {}}"""),
        HumanMessage(content=content)   
    ])
    
    try:
        clean_json = response.content.strip().replace("```json", "").replace("```", "")
        parsed_intent = json.loads(clean_json)
        tool_name = parsed_intent.get("tool_name", "Invalid tool name")
        parameters = parsed_intent.get("parameters", {})
    except Exception:
        tool_name = "Invalid tool name"
        parameters = {}
        
    if tool_name in tools_by_name:
        translated = AIMessage(
            content="",
            tool_calls=[{
                "name": tool_name, 
                "args": parameters,
                "id": uuid.uuid4().hex[:12]
            }],
        )
        return {"messages": [translated]}
    
    fallback_msg = AIMessage(content="The user intent could not be mapped to any valid system tools. Proceeding to final summary.")
    return {"messages": [fallback_msg]}

# define graph logic
from typing import Literal
from langgraph.graph import END

def after_llm(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"
    
    content = last_message.content if isinstance(last_message, AIMessage) else ""
    
    # if find invalid tool
    if content == "INVALID_INTENT_TRIGGERED":
        return "summary_node"
        
    # check keyword
    if any(keyword in content for keyword in ["Calling tool", "parameters", "python_tag", "CACHE_PATH"]):
        return "intent_node"

    if "summary" in content and "potential_threats" in content:
        return END

    return "summary_node"

def after_intent(state: MessagesState) -> Literal["tool_node", "summary_node"]:
    last = state["messages"][-1]
    
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tool_node"
    
    return "summary_node"
