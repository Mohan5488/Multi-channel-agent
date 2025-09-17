from typing import Dict, Any
from langgraph.types import Command, interrupt
from langgraph.graph import END
from langchain_openai import ChatOpenAI
# from langchain_groq imoprt ChatGroq
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import json

def human_gate(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Human gate with two phases:
      - awaiting == "decision": ask send/edit/cancel
      - awaiting == "edits": ask for edit text
    Exactly ONE interrupt per node call.
    """
    preview = state.get("preview", "No preview available")
    print(f"\n{preview}\n")

    awaiting = state.get("awaiting", "decision")
    intent = state.get("intent", "email")

    
    if intent == "email":
        if awaiting == "decision":
            user_decision = interrupt({
                "message": "Review the email above. Type 'send' to approve, 'edit' to modify, or 'cancel' to abort."
            })
            decision = str(user_decision).strip().lower()

            if decision == "send":
                state["approved"] = True
                state["awaiting"] = "decision"
                # Route to send_email node (LangChain tool), not end
                return Command(goto="send_email", update=state)

            if decision == "edit":
                # Next call to this node will request edit text
                state["awaiting"] = "edits"
                return Command(goto="edits", update=state)

            if decision == "cancel":
                state["approved"] = False
                state["error"] = "Workflow cancelled by user"
                state["awaiting"] = "decision"
                return Command(goto=END, update=state)

            # invalid input → ask again
            state["awaiting"] = "decision"
            return Command(goto="human_gate", update=state)
    elif intent == "linkedin":
        if awaiting == "decision":
            user_decision = interrupt({
                "message": "Review the LinkedIn post above. Type 'post' to approve, 'edit' to modify, or 'cancel' to abort."
            })
            decision = str(user_decision).strip().lower()
        if decision == "post":
            state["approved"] = True
            state["awaiting"] = "decision"
            return Command(goto="post_linkedin", update=state)
        if decision == "edit":
            state["awaiting"] = "edits"
            return Command(goto="process_linkedin_edits", update=state)
        if decision == "cancel":
            state["approved"] = False
            state["error"] = "Workflow cancelled by user"
            state["awaiting"] = "decision"
            return Command(goto=END, update=state)
        state["awaiting"] = "decision"
        return Command(goto="human_gate", update=state)
    else:
        state["awaiting"] = "decision"
        return Command(goto="human_gate", update=state)

def _process_edits(state: Dict[str, Any]) -> Dict[str, Any]:
    edit_feedback = interrupt({"message": "What would you like to change? Describe your edits."})

    # llm = ChatOpenAI(model="gpt-4", temperature=0.7)
    llm = ChatGroq(model="openai/gpt-oss-120b",temperature=0.7)
    current_to = state.get("to", "")
    current_subject = state.get("subject", "")
    current_body = state.get("body", "")

    system_prompt = f"""Edit the email based on human feedback.
Current email:
To: {current_to}
Subject: {current_subject}
Body: {current_body}

Apply the requested edits and respond in JSON:
{{
  "to": "updated recipient",
  "subject": "updated subject",
  "body": "updated body "
}}"""
    resp = llm.invoke([SystemMessage(content=system_prompt),
                       HumanMessage(content=f"Edit request: {edit_feedback}")])

    data = {}
    try:
        data = json.loads(resp.content.strip())
    except json.JSONDecodeError:
        data = {"to": current_to, "subject": current_subject, "body": current_body}

    new_to = data.get("to", current_to)
    new_subject = data.get("subject", current_subject)
    new_body = data.get("body", current_body)

    preview = (
        "📧 UPDATED EMAIL PREVIEW\n" + "=" * 40 + "\n\n"
        f"To: {new_to}\nSubject: {new_subject}\n\nBody:\n{new_body}\n\n"
        + "=" * 40 + "\nReady to send? Please review above."
    )

    return Command(goto="human_gate", update={
        "to": new_to,
        "subject": new_subject,
        "body": new_body,
        "preview": preview,
        "awaiting": "decision",
    })


def process_linkedin_edits(state: Dict[str, Any]) -> Dict[str, Any]:
    edit_feedback = interrupt({"message": "What would you like to change? Describe your edits."})

    # llm = ChatOpenAI(model="gpt-4", temperature=0.3)
    llm = ChatGroq(model = "openai/gpt-oss-120b", temperature = 0.7)
    current_text = state.get("generated_text", "")

    system_prompt = f"""
    You are an expert LinkedIn copy editor. Apply the user's edit request to the
    current post and return the improved post text only.

    Strict rules:
    - Maintain the original intent; address the requested changes precisely
    - Optimize for clarity, flow, and scannability (short paragraphs, clear lines)
    - Use short sentences; prefer active voice
    - You may use up to 3 concise bullet points only if it improves readability
    - Keep length around 80–220 words unless the edit explicitly asks otherwise
    - Use at most 0–2 relevant emojis, never more; avoid gimmicky tone
    - Add up to 3 relevant hashtags at the very end only if they add value
    - No markdown formatting (no **bold**, no code blocks), no titles or headers
    - No salutations or signatures unless explicitly requested
    - Keep URLs as-is; do not invent links
    - Do not add prefaces like "Here is the edited post:" — return ONLY the final post

    Current LinkedIn post:
    {current_text}

    User edit request:
    {edit_feedback}
    """
    resp = llm.invoke([SystemMessage(content=system_prompt),
                       HumanMessage(content=f"Edit request: {edit_feedback}")])

    # print(resp)
    data = resp.content.strip()
    new_text = data

    preview = (
        "📱 UPDATED LINKEDIN POST PREVIEW\n" + "=" * 40 + "\n\n"
        f"{new_text}\n\n"
        + "=" * 40 + "\nReady to post? Please review above."
    )

    return Command(goto="human_gate", update={
        "text": new_text,
        "preview": preview,
        "awaiting": "decision",
    })