
"""
LangGraph workflow definition for the multichannel agent.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from langgraph.types import Command
import json
# ✅ Persistent checkpointing
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver
# Messages
from langchain_core.messages import HumanMessage

load_dotenv()
memory = MemorySaver()

# Flexible imports for package vs script
    # Absolute imports when run directly
from src.agent.state import AgentState
from src.agent.nodes.intent import intent_node
from src.agent.nodes.compose_email import compose_email
from src.agent.nodes.compose_linkedin import compose_linkedin
from src.agent.nodes.human_gate import human_gate, _process_edits, process_linkedin_edits
from langchain_core.messages import HumanMessage, AIMessageChunk, ToolMessage
from src.agent.nodes.chat import chat_node
from src.agent.nodes.send_email import send_email_node
from src.agent.nodes.post_linkedin import post_linkedin_node
from src.agent.nodes.compose_cal_events import compose_events


def create_workflow():
    """
    Create the LangGraph workflow for the multichannel agent.
    """
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("intent", intent_node)
    workflow.add_node("compose_email", compose_email)
    workflow.add_node("compose_linkedin", compose_linkedin)
    workflow.add_node("calendar", compose_events)
    workflow.add_node("post_linkedin", post_linkedin_node)
    workflow.add_node("human_gate", human_gate)
    workflow.add_node("edits", _process_edits)
    workflow.add_node("process_linkedin_edits", process_linkedin_edits)
    workflow.add_node("send_email", send_email_node)  # tool node
    workflow.add_node("chat", chat_node)

    # Entry
    workflow.set_entry_point("intent")

    # Edges
    workflow.add_edge("compose_email", "human_gate")
    workflow.add_edge("compose_linkedin", "human_gate")
    workflow.add_edge("edits", "human_gate")
    workflow.add_edge("process_linkedin_edits", "human_gate")
    workflow.add_edge("send_email", END)


    # ✅ Compile with persistent SQLite checkpointer
    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    # con = sqlite3.connect("new_checkpoints.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    app = workflow.compile(checkpointer=checkpointer)
    return app


def run_workflow(user_prompt: str, thread_id: str = "default") -> Dict[str, Any]:
    """
    Run the workflow with a single user turn; previous turns are restored
    from the persistent checkpoint (same thread_id).
    """
    app = create_workflow()
    config = {"configurable": {"thread_id": thread_id}}

    # ✅ Only add the new user message; history is persisted
    new_input = {"messages": [HumanMessage(content=user_prompt)],
                 "user_prompt": user_prompt}

    for event in app.stream(new_input, config):
        print(f"Event: {event}")
    final_state = app.get_state(config)
    return final_state.values


def run_workflow_interactive(user_prompt: str, thread_id: str = "default") -> Dict[str, Any]:
    app = create_workflow()
    config = {"configurable": {"thread_id": thread_id}}

    pending_state = {"messages": [HumanMessage(content=user_prompt)],
                     "user_prompt": user_prompt}

    while True:
        interrupted = False

        for event in app.stream(pending_state, config):
            # print(f"Event: {event}")

            if "__interrupt__" in event:
                interrupted = True
                intr = event["__interrupt__"][0]          # Interrupt object
                payload = getattr(intr, "value", {}) or {}
                msg = payload.get("message", "Provide input:")
                preview = payload.get("preview")
                if preview:
                    print("\n--- Preview ---")
                    print(preview)
                    print("----------------\n")

                # ONE resume per interrupt
                user_feedback = input(msg + "\n> ")
                app.invoke(Command(resume=user_feedback), config=config)

                # Continue from current state for the next step/interrupt
                pending_state = None
                break  # restart streaming loop

        if not interrupted:
            final_state = app.get_state(config)
            return final_state.values


def run_workflow_api(user_prompt: str, user_id : int, thread_id: str = "default") -> Dict[str, Any]:
    """
    Run workflow for API endpoints - returns interrupt state instead of blocking for input.
    """
    app = create_workflow()
    config = {"configurable": {"thread_id": thread_id}}

    pending_state = {"messages": [HumanMessage(content=user_prompt)],
                     "user_prompt": user_prompt, "user_id" : user_id}

    for event in app.stream(pending_state, config):
        print(event)
        if "__interrupt__" in event:
            # Return interrupt information for API handling
            intr = event["__interrupt__"][0]
            payload = getattr(intr, "value", {}) or {}
            
            return {
                "status": "interrupt",
                "interrupt": {
                    "message": payload.get("message", "Please provide input"),
                    "preview": payload.get("preview"),
                    "thread_id": thread_id
                },
                "state": app.get_state(config).values
            }

    # No interrupt occurred, workflow completed
    final_state = app.get_state(config)
    return final_state.values


def resume_workflow_api(user_feedback: str, thread_id: str = "default") -> Dict[str, Any]:
    """
    Resume workflow after receiving human feedback via API.
    """
    app = create_workflow()
    print(f"[RESUME] THREAD ID-", thread_id)
    config = {"configurable": {"thread_id": thread_id}}

    print("[RESUME] USER FEEDBACK -", user_feedback)

    print("[RESUME] Resuming Feedback")
    # Resume with the feedback
    app.invoke(Command(resume=user_feedback), config=config)

    print("[RESUME] Resume Feedback Done")
    # Continue streaming to check for more interrupts or completion
    for event in app.stream(None, config):
        if "__interrupt__" in event:
            # Another interrupt occurred
            intr = event["__interrupt__"][0]
            payload = getattr(intr, "value", {}) or {}
            
            return {
                "status": "interrupt",
                "interrupt": {
                    "message": payload.get("message", "Please provide additional input"),
                    "preview": payload.get("preview"),
                    "thread_id": thread_id
                },
                "state": app.get_state(config).values
            }

    # Workflow completed
    final_state = app.get_state(config)
    return final_state.values


def serialize_state(state):
    """
    Serialize LangGraph state to JSON-safe format.
    """
    if not state:
        return {}
    
    serialized = {}
    for key, value in state.items():
        if key == "messages":
            # Convert messages to serializable format
            serialized[key] = [
                {
                    "type": msg.__class__.__name__,
                    "content": msg.content if hasattr(msg, 'content') else str(msg)
                }
                for msg in value
            ]
        elif isinstance(value, (str, int, float, bool, type(None))):
            serialized[key] = value
        elif isinstance(value, (list, dict)):
            try:
                # Try to serialize complex objects
                serialized[key] = value
            except:
                serialized[key] = str(value)
        else:
            # Convert other objects to string
            serialized[key] = str(value)
    
    return serialized

# def serialise_ai_message_chunk(chunk): 
#     if(isinstance(chunk, AIMessageChunk)):
#         return chunk.content
#     else:
#         raise TypeError(
#             f"Object of type {type(chunk).__name__} is not correctly formatted for serialisation"
#         )


# async def run_workflow_streaming(user_prompt: str, thread_id: str = "default"):
#     """
#     Generator that yields streaming updates for the workflow.
#     Yields dictionaries with status updates, interrupts, and final results.
#     """
#     app = create_workflow()
#     config = {"configurable": {"thread_id": thread_id}}

#     pending_state = {"messages": [HumanMessage(content=user_prompt)],
#                      "user_prompt": user_prompt}

#     # Yield initial status
#     yield {
#         "type": "status",
#         "message": "Starting workflow...",
#         "thread_id": thread_id
#     }

#     try:
#         async for event in app.astream_events(pending_state, config):
#             print(event)
#             event_type = event["event"]
#             if event_type == "on_chat_model_stream":
#                 chunk_content = serialise_ai_message_chunk(event["data"]["chunk"])
#                 safe_content = chunk_content.replace("'", "\\'").replace("\n", "\\n")
#                 yield f"data: {{\"type\": \"content\", \"content\": \"{safe_content}\"}}\n\n"
            
#             elif event_type == "on_chat_model_end":
#                 # Check if there are tool calls for search
#                 tool_calls = event["data"]["output"].tool_calls if hasattr(event["data"]["output"], "tool_calls") else []
#                 search_calls = [call for call in tool_calls if call["name"] == "tavily_search_results_json"]
                
#                 if search_calls:
#                     # Signal that a search is starting
#                     search_query = search_calls[0]["args"].get("query", "")
#                     # Escape quotes and special characters
#                     safe_query = search_query.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
#                     yield f"data: {{\"type\": \"search_start\", \"query\": \"{safe_query}\"}}\n\n"
                    
#             elif event_type == "on_tool_end" and event["name"] == "tavily_search_results_json":
#                 # Search completed - send results or error
#                 output = event["data"]["output"]
                
#                 # Check if output is a list 
#                 if isinstance(output, list):
#                     # Extract URLs from list of search results
#                     urls = []
#                     for item in output:
#                         if isinstance(item, dict) and "url" in item:
#                             urls.append(item["url"])
                    
#                     # Convert URLs to JSON and yield them
#                     urls_json = json.dumps(urls)
#                     yield f"data: {{\"type\": \"search_results\", \"urls\": {urls_json}}}\n\n"
        
#         # Send an end event
#         yield f"data: {{\"type\": \"end\"}}\n\n"
#     except Exception as e:
#         yield {
#             "type": "error",
#             "message": f"Workflow failed: {str(e)}",
#             "error": str(e)
#         }


# def resume_workflow_streaming(user_feedback: str, thread_id: str = "default"):
#     """
#     Generator that yields streaming updates when resuming workflow.
#     """
#     app = create_workflow()
#     config = {"configurable": {"thread_id": thread_id}}

#     # Yield resume status
#     yield {
#         "type": "status",
#         "message": "Resuming workflow with feedback...",
#         "thread_id": thread_id
#     }

#     try:
#         # Resume with the feedback
#         app.invoke(Command(resume=user_feedback), config=config)

#         # Continue streaming to check for more interrupts or completion
#         for event in app.stream(None, config):
#             if "__interrupt__" in event:
#                 intr = event["__interrupt__"][0]
#                 payload = getattr(intr, "value", {}) or {}
                
#                 # Get current state and serialize it
#                 current_state = app.get_state(config).values
#                 serialized_state = serialize_state(current_state)
                
#                 yield {
#                     "type": "interrupt",
#                     "message": "Workflow interrupted again - additional input required",
#                     "interrupt": {
#                         "message": payload.get("message", "Please provide additional input"),
#                         "preview": payload.get("preview"),
#                         "thread_id": thread_id
#                     },
#                     "state": serialized_state
#                 }
#                 return  # Stop streaming on interrupt
            
#             # Yield node completion updates
#             for node_name, node_data in event.items():
#                 if node_name != "__interrupt__":
#                     yield {
#                         "type": "node_complete",
#                         "node": node_name,
#                         "message": f"Completed {node_name}",
#                         "data": serialize_state(node_data) if isinstance(node_data, dict) else str(node_data)
#                     }

#         # Workflow completed
#         final_state = app.get_state(config)
#         serialized_final_state = serialize_state(final_state.values)
        
#         yield {
#             "type": "complete",
#             "message": "Workflow completed successfully",
#             "result": final_state.values.get("result"),
#             "state": serialized_final_state
#         }

#     except Exception as e:
#         yield {
#             "type": "error",
#             "message": f"Workflow resume failed: {str(e)}",
#             "error": str(e)
#         }
