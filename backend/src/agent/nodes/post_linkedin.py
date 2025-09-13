from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END
from langchain_core.messages import AIMessage
from src.agent.tools.tools import post_linkedin_text

def post_linkedin_node(state):
    """Invoke the LangChain linkedin tool and go to end."""
    generated_text = state.get("generated_text")

    if not generated_text:
        result = {"status": "error", "message": "Missing Post Draft"}
    else:
        result = post_linkedin_text.invoke({"text" : generated_text})

    status = result.get("status")
    message = result.get("message", "")
    footer = f"\n\n📤 Send result: {status} — {message}"
    print("[POST LINKEDIN] FOOTER - ", footer)
    preview = (state.get("preview") or "") + footer
    ai_note = f"Email send status: {status} — {message}"
    print("[POST LINKEDIN] AI NOTE - ", ai_note)
    return Command(goto=END, update={
        "result": result,
        "preview": preview,
        "messages": [AIMessage(content=ai_note)],
    })