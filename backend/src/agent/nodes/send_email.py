from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END
from langchain_core.messages import AIMessage
from src.agent.tools.tools import send_email_tool

def send_email_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke the LangChain email tool and go to end."""
    to = (state.get("to") or "").strip()
    subject = (state.get("subject") or "No subject").strip()
    body = state.get("body") or ""
    user_id = state.get("user_id") or ''
  
    if not to:
        result = {"status": "error", "message": "Missing recipient email"}
        print("[SEND EMAIL] ERROR - ", result)
    else:
        result = send_email_tool.invoke({"to": to, "subject": subject, "body": body, "user_id" : user_id})
        print("[SEND EMAIL] RESULT - ", result)
    status = result.get("status")
    message = result.get("message", "")
    footer = f"\n\n📤 Send result: {status} — {message}"
    print("[SEND EMAIL] FOOTER - ", footer)
    preview = (state.get("preview") or "") + footer
    ai_note = f"Email send status: {status} — {message}"
    print("[SEND EMAIL] AI NOTE - ", ai_note)
    return Command(goto=END, update={
        "result": result,
        "preview": preview,
        "messages": [AIMessage(content=ai_note)],
    })
