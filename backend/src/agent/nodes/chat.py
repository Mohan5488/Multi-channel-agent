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

# def chat_node(state: Dict[str, Any]) -> Dict[str, Any]:
#     user_prompt = (state.get("user_prompt") or "").strip()
    
#     messages = state.get("messages", [])

#     search_tool = TavilySearchResults(max_results=3)
#     tools = [search_tool]

#     # llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
#     llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.1)
#     llm_with_tools = llm.bind_tools(tools=tools)

#     chat_messages = [
#         SystemMessage(content="""You are a helpful assistant with access to web search via Tavily.

# IMPORTANT: When you need to search for information, you MUST use the tavily_search_results_json tool with proper JSON format.

# Tool calling format:
# - Use the tool when users ask about current events, recent news, weather, facts that change, or any information that might be outdated
# - Always format tool calls as proper JSON: {"query": "your search query here"}
# - Be specific with your search queries
# - After getting search results, provide a clear, helpful response based on the results

# Be friendly and provide clear, helpful responses based on the search results.""")
#     ]
    
#     chat_messages.extend(messages)

#     chat_messages.append(HumanMessage(content=user_prompt))

#     response = llm_with_tools.invoke(chat_messages)
#     print(response)
    
#     if response.tool_calls:
#         tool_messages = []
#         for tool_call in response.tool_calls:
#             tool_name = tool_call["name"]
#             tool_args = tool_call["args"]
#             print(tool_name)
            
#             if tool_name == "tavily_search_results_json":
#                 tool_result = search_tool.invoke(tool_args)
#             else:
#                 tool_result = "Tool not found"
        
#             tool_messages.append(ToolMessage(
#                 content=str(tool_result),
#                 tool_call_id=tool_call["id"]
#             ))
#         final_messages = chat_messages + [response] + tool_messages
#         final_response = llm_with_tools.invoke(final_messages)
#         print(final_response)
#         answer = final_response.content or "Search completed."
#     else:
#         answer = response.content or "I'm here to help!"
    
#     updated_messages = messages + [HumanMessage(content=user_prompt), AIMessage(content=answer)]
    
#     state["preview"] = f"💬 CHAT REPLY\n{'='*40}\n{answer}\n{'='*40}"
#     state["result"] = {"status": "success", "type": "chat", "message": answer}
#     state["messages"] = updated_messages
    
#     return Command(goto=END, update=state)


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
            "Be friendly and provide clear, helpful responses based on results."
        )),
    )

    input_messages = messages + [HumanMessage(content=user_prompt)]

    response = react_agent.invoke({"messages" : input_messages})

    all_msgs = response.get("messages", [])
    ai_msgs = [m for m in all_msgs if isinstance(m, AIMessage)]
    answer = ai_msgs[-1].content if ai_msgs else "I'm here to help!"

    state["preview"] = f"💬 CHAT REPLY\n{'='*40}\n{answer}\n{'='*40}"
    state["result"] = {"status": "success", "type": "chat", "message": answer}
    state["messages"] = all_msgs

    return Command(goto=END, update=state)

