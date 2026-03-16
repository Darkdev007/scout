import os
from dotenv import load_dotenv
from tools import get_african_news, get_wikipedia_summary, get_global_news, get_exchange_rates
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict

load_dotenv()
openai_api_key = os.environ.get("OPENAI_API_KEY")

# State
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# Tools
TOOLS = [
    get_wikipedia_summary,
    get_global_news,
    get_african_news,
    get_exchange_rates,
]

# System prompt 

SYSTEM_PROMPT = """You are Scout, an autonomous research agent specialized in 
African markets, finance, and technology.

When given a research goal, follow this approach:
1. For Wikipedia queries:
- Company names: 'Flutterwave', 'Kuda Bank', 'Paystack'
- Country context: 'Nigeria', 'Kenya' — not 'fintech in Nigeria'
- Let the news tools handle sector-level queries

2. Use get_african_news for Nigerian or African company queries
3. Use get_global_news for international coverage or if African news returns nothing
4. Always use get_exchange_rates for any query involving finance, investment, or African markets

Rules:
- Always use at least 2 tools per query — never answer from memory alone
- If a tool returns NO_RESULTS, try a broader search term or switch tools
- After gathering information, synthesize everything into a structured briefing
- Use ## headers to organize your final report
- Always include a currency/FX context section for African market queries
- Be specific — quote actual data points from tool results
- If information is missing, say so honestly rather than fabricating
- When the user mentions 'the company X' or 'startup X', always treat X as 
  a proper company name — never interpret it as a generic concept or 
  financial term
- For African startup names that look like common words (Divest, Carbon, 
  Wave, Grey, Mono, Brass), always add 'Nigerian fintech' or 'African startup' 
  to your search queries e.g. 'Divest Nigerian fintech' not just 'Divest'
"""

# LLM 
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    api_key=openai_api_key
).bind_tools(TOOLS)

# Nodes
def call_model(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(TOOLS)

# Graph 
graph = StateGraph(AgentState)

graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)

graph.set_entry_point("agent")
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "agent")

scout = graph.compile()

print("Scout agent ready")