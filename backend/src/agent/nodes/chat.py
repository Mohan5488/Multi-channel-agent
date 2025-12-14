# src/agent/nodes/chat.py
from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent

load_dotenv()

def chat_node(state):
    user_prompt = (state.get("user_prompt") or "").strip()
    messages = state.get("messages", [])

    search_tool = TavilySearchResults(max_results=3)
    tools = [search_tool]

    # llm = ChatOpenAI(model="gpt-4", temperature=0.7)
    llm = ChatGroq(model="openai/gpt-oss-120b",temperature=0.7)

    react_agent = create_react_agent(
        llm,
        tools=tools,
        prompt=SystemMessage(content=(
            "You are a helpful assistant with access to web search via Tavily. "
            "When a user asks for information that might benefit from up-to-date data "
            "(current events, recent news, facts that change), use the search tool. "
            "Be friendly and provide clear, helpful responses based on results. "
        )),
    )

    # Avoid duplicating the latest HumanMessage; it's already injected via workflow input
    if messages and isinstance(messages[-1], HumanMessage) and messages[-1].content == user_prompt:
        input_messages = messages
    else:
        input_messages = messages + [HumanMessage(content=user_prompt)]

    response = react_agent.invoke({"messages" : input_messages})

    all_msgs = response.get("messages", [])
    ai_msgs = [m for m in all_msgs if isinstance(m, AIMessage)]
    answer = ai_msgs[-1].content if ai_msgs else "I'm here to help!"

    state["preview"] = f"💬 CHAT REPLY\n{'='*40}\n{answer}\n{'='*40}"
    state["result"] = {"status": "success", "type": "chat", "message": answer}
    state["messages"] = all_msgs

    return Command(goto=END, update=state)

