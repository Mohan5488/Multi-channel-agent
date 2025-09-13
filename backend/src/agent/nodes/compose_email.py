"""
Email composition with extraction and human-in-the-loop.
"""

from typing import Dict, Any
# from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command, interrupt

import json
import re

def extract_email_details(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract email details (to, subject, sender_name body) from user prompt.
    """
    user_prompt = state.get("user_prompt", "")
    
    # llm = ChatOpenAI(model="gpt-4", temperature=0.1)
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.1)


    print("[LLM CALL] MAking GPT Call")

    system_prompt = """
    You extract email details from a single user input.
Return ONLY a valid JSON object. No prose, no code fences, no explanations.

Extract:
1) "to": Email recipient (email address or name if no email found)
2) "subject": Subject line (CREATE a concise subject from the input only if it is clearly inferable; otherwise leave "" and mark as missing)
3) "body": Email body content (capture only actual message content intended to be sent; DO NOT treat meta-instructions like “send mail”, “email X”, “write an email” as body)
4) "sender_name": Recipient name; if not explicitly given, derive from "to":
   - If "to" is an email, take the local-part before "@", strip digits and separators (._-), use the alphabetic portion; keep lowercase (e.g., "krishnabudumuru7" → "krishnabudumuru" or "krishna" if clearly present).
   - If "to" is a name string, use that name (lowercase).
5) "missing": Array of keys explicitly missing from the input context (subset of ["to","subject","body"])

Output schema (MUST match keys and types exactly):
{
  "to": "email@example.com",
  "subject": "Subject line",
  "body": "Email body content",
  "sender_name": "krishna",
  "missing": ["to","subject","body"]
}

Rules:
- If a field is clearly absent, include it in "missing".
- If a concise subject is NOT clearly inferable, set "subject": "" and include "subject" in "missing".
- If there is no actual message content, set "body": "" and include "body" in "missing".
- Normalize placeholders like "Missing", "None", "Unknown" to empty "" and include in "missing".
- Do not add any text outside the JSON object. Violations will be rejected.

Meta-intent detector (non-exhaustive):
Treat as meta-instructions (NOT body): “send mail”, “email <address>”, “write an email”, “draft mail”, “please mail”, “shoot an email”, “send this”.

Examples

Input:
send mail to krishnabudumuru7@gmail.com
Output:
{
  "to": "krishnabudumuru7@gmail.com",
  "subject": "",
  "body": "",
  "sender_name": "krishna",
  "missing": ["subject","body"]
}

Input:
Email Jane Doe about the meeting move to 3 PM tomorrow. Her email is jane.doe@example.com
Output:
{
  "to": "jane.doe@example.com",
  "subject": "Meeting moved to 3 PM tomorrow",
  "body": "The meeting is moved to 3 PM tomorrow.",
  "sender_name": "jane doe",
  "missing": []
}

Input:
Please email finance@acme.co to request the updated invoice for order #4829.
Output:
{
  "to": "finance@acme.co",
  "subject": "Request for updated invoice (order #4829)",
  "body": "Please send the updated invoice for order #4829.",
  "sender_name": "finance",
  "missing": []
}

    """
 
   
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User input: {user_prompt}")
    ]
    
    try:
        response = llm.invoke(messages)
        raw = response.content
        print("[RAW LLM]", raw)

        try:
            data = json.loads(raw)
        except Exception as parse_err:
            print("[PARSE ERROR]", parse_err)
            data = {
                "to": "",
                "subject": "",
                "body": "",
                "sender_name" : "",
                "missing": ["to", "subject", "body"]
            }
        
        state["to"] = data.get("to")
        state["subject"] = data.get("subject") 
        state["body"] = data.get("body") 
        state["sender_name"] = data.get("sender_name")
        print("[UPDATED STATE]", state) 
        # Check for missing critical info 

        missing = data.get("missing", []) 
        critical_missing = [] 
        
        print("MISSING VALUES - ", missing) 

        if not state.get("to") or state.get("to").lower() in ["none", "unknown", "", "missing"]: 
            critical_missing.append("to") 
        if not state.get("body") or state.get("body").lower() in ["none", "unknown", "", "missing"]: 
            critical_missing.append("body") 
        
        print("CRITICAL MISSING -", critical_missing)
        if critical_missing: 
            print("CHANGING STATE TO NEED INPUT TRUE") 
            state["needs_input"] = True 
            state["human_message"] = f"Missing email information: {', '.join(critical_missing)}. Please provide:" 
            for field in critical_missing: 
                state["human_message"] += f"\n- {field}: " 

    except Exception as e: 
        state["error"] = f"Extraction failed: {str(e)}" 
        state["needs_input"] = True 
        state["human_message"] = "Could not extract email details. Please provide: to, subject, body" 
    print("FINAL STATE - ",state) 
    return state

def process_human_feedback(state: Dict[str, Any], feedback: str) -> Dict[str, Any]:
    """
    Process human feedback to fill/adjust email details using the same strict
    extraction rules as `extract_email_details`.
    """
    print("[LLM CALL] Making call to extract items from HUMAN FEEDBACK")

    # Keep your provider choice consistent with the rest of the file
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.1)

    # Build a normalized snapshot of current values for the prompt
    curr_to = state.get("to", "") or ""
    curr_subject = state.get("subject", "") or ""
    curr_body = state.get("body", "") or ""
    curr_sender = state.get("sender_name", "") or ""

    system_prompt = f"""
You extract email details from a single HUMAN FEEDBACK input, given current email state.
Return ONLY one valid JSON object. No prose, no code fences, no explanations.

CURRENT EMAIL STATE:
- to: {curr_to}
- subject: {curr_subject}
- body: {curr_body}
- sender_name: {curr_sender}

TASK:
Update/fill the email fields strictly from the HUMAN FEEDBACK. If a field is not clearly provided or inferable, leave it "" and list it in "missing".

Extract:
1) "to": Email recipient (email address or name if no email found)
2) "subject": Subject line (CREATE concise subject ONLY if clearly inferable from feedback; otherwise set "" and mark as missing)
3) "body": Email body content (capture only the actual message content intended to be sent; treat meta-instructions like “send”, “email X”, “draft this” as NOT body)
4) "sender_name": Recipient name; if not explicitly given, derive from "to":
   - If "to" is an email, take the local-part before "@", strip digits and separators (._-), keep the alphabetic portion in lowercase (e.g., "krishnabudumuru7" → "krishnabudumuru" or "krishna" if clearly present).
   - If "to" is a name string, use that name (lowercase).
5) "missing": Array of keys explicitly missing from the FEEDBACK context (subset of ["to","subject","body"])

Output schema (MUST match keys and types exactly):
{{
  "to": "email@example.com",
  "subject": "Subject line",
  "body": "Email body content",
  "sender_name": "krishna",
  "missing": ["to","subject","body"]
}}

Rules:
- If a field is clearly absent, include it in "missing".
- If a concise subject is NOT clearly inferable, set "subject": "" and include "subject" in "missing".
- If there is no actual message content, set "body": "" and include "body" in "missing".
- Normalize placeholders like "Missing", "None", "Unknown" to empty "" and include in "missing".
- Do not add any text outside the JSON object.

Meta-intent detector (non-exhaustive):
Treat as meta-instructions (NOT body): “send”, “send mail”, “email <address>”, “write an email”, “draft mail”, “please mail”, “shoot an email”, “send this”.

Examples

Feedback:
to jane.doe@example.com; keep the same message, just add “Thanks!”
Output:
{{
  "to": "jane.doe@example.com",
  "subject": "",
  "body": "Thanks!",
  "sender_name": "jane doe",
  "missing": ["subject"]
}}

Feedback:
Subject should be “Invoice clarification for #4829”. Body: “Could you share the revised invoice with the corrected tax lines?”
Output:
{{
  "to": "",
  "subject": "Invoice clarification for #4829",
  "body": "Could you share the revised invoice with the corrected tax lines?",
  "sender_name": "",
  "missing": ["to"]
}}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"HUMAN FEEDBACK: {feedback}")
    ]

    try:
        resp = llm.invoke(messages)
        raw = (resp.content or "").strip()
        print("[RAW HUMAN FEEDBACK LLM]", raw)

        try:
            data = json.loads(raw)
        except Exception as parse_err:
            print("[PARSE ERROR - HUMAN FEEDBACK]", parse_err)
            # Fallback defaults: nothing confidently extracted
            data = {
                "to": "",
                "subject": "",
                "body": "",
                "sender_name": "",
                "missing": ["to", "subject", "body"]
            }

        # Normalize placeholders if model returned any (belt-and-suspenders)
        def _norm(x: Any) -> str:
            if not isinstance(x, str):
                return ""
            val = x.strip()
            return "" if val.lower() in {"missing", "none", "unknown"} else val

        new_to = _norm(data.get("to", ""))
        new_subject = _norm(data.get("subject", ""))
        new_body = _norm(data.get("body", ""))
        new_sender = _norm(data.get("sender_name", ""))

        # If sender_name still empty but to looks like an email, derive a name
        if not new_sender and "@" in new_to:
            local = new_to.split("@", 1)[0]
            local = re.sub(r"[\d._-]+", " ", local).strip()
            if local:
                # keep lowercase per your rule
                new_sender = local.lower().split()[0]

        # Merge with existing state: adopt any non-empty values from feedback
        if new_to:
            state["to"] = new_to
        if new_subject != "":
            state["subject"] = new_subject
        if new_body != "":
            state["body"] = new_body
        if new_sender:
            state["sender_name"] = new_sender

        # Compute missing (critical for loop control)
        # Prefer model's "missing" if provided and valid; otherwise recompute
        model_missing = data.get("missing", [])
        if not isinstance(model_missing, list):
            model_missing = []

        # Recalculate critical missing from current state to be safe
        critical_missing = []
        if not state.get("to") or state.get("to", "").strip() == "":
            critical_missing.append("to")
        if not state.get("body") or state.get("body", "").strip() == "":
            critical_missing.append("body")

        # If subject is empty, include in missing (non-critical but informative)
        if not state.get("subject") or state.get("subject", "").strip() == "":
            if "subject" not in model_missing:
                model_missing.append("subject")

        # Merge unique keys: model_missing + critical_missing
        merged_missing = list({*model_missing, *critical_missing})

        if critical_missing:
            state["needs_input"] = True
            # Build a clean prompt for the next loop
            ask_lines = ["Missing email information: " + ", ".join(critical_missing) + ". Please provide:"]
            for key in critical_missing:
                ask_lines.append(f"- {key}: ")
            state["human_message"] = "\n".join(ask_lines)
        else:
            state["needs_input"] = False
            state["human_message"] = None

        # Optionally store merged "missing" for visibility/debugging
        state["missing"] = merged_missing

    except Exception as e:
        state["error"] = f"Failed to process feedback: {str(e)}"
        state["needs_input"] = True
        state["human_message"] = "Error processing your input. Please provide: to, body (and subject if available)."

    print("[STATE IN HUMAN FEEDBACK]", state)
    return state


def compose_email(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose email with extraction and human-in-the-loop.
    """
    
    print("[COMPOSE EMAIL] Entered into stage of EMAIL")
    state = extract_email_details(state)

    # Handle multiple rounds of human input with a loop
    while state.get("needs_input"):
        # Interrupt for human input
        print("[COMPOSE MAIL] EMAIL MISSING INTERRUPT")
        user_feedback = interrupt({
            "message": state.get("human_message", "Please provide missing email information")
        })
        
        print(f"[compose_email] Human feedback: {user_feedback}")
        
        # Process human feedback
        print(f"PROCESSING HUMAN FEEDBACK")
        state = process_human_feedback(state, user_feedback)

        print("[COMPOSE MAIL] After Human Feedback STATE -", state)
        
        # The while loop will continue if needs_input is still True
        # This prevents the recursive call that was causing the restart
    
    print("[COMPOSE MAIL] After compose email need to generate draft")
    state = generate_email_draft(state)
    print("[STATE] After generate draft State - ", state)

    # Compose final email
    print("[FINAL PREVIEW]")
    state = create_final_email(state)
    print("[FINAL PREVIEW] ", state["preview"])
    
    # Route to human gate for approval
    return Command(goto="human_gate", update=state)

def generate_email_draft(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a Gmail-ready draft from current AgentState.
    - Produces subject/body only when missing or too short; preserves user-provided fields.
    - Returns JSON and updates state in-place.
    """
    # Decide if drafting is needed
    to_val = (state.get("to") or "").strip()
    subj = (state.get("subject") or "").strip()
    body = (state.get("body") or "").strip()

    need_subject = len(subj) < 4
    need_body = len(body) < 8

    # If nothing to draft, return immediately
    if not need_subject and not need_body:
        return state

    # Defaults
    tone = (state.get("tone") or "polite").lower()
    length = (state.get("length") or "short").lower()
    sender_name = (state.get("sender_name") or "").strip()
    user_prompt = (state.get("user_prompt") or "").strip()

    # If sender_name missing but "to" looks like an email, derive a name
    if not sender_name and "@" in to_val:
        local = to_val.split("@", 1)[0]
        # strip digits and separators
        import re as _re
        local = _re.sub(r"[\d._-]+", " ", local).strip()
        if local:
            sender_name = local.split()[0].title()
            state["sender_name"] = sender_name

    # LLM
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)

    system_prompt = """You generate a Gmail-ready draft email from a single JSON state object.
Return ONLY one valid JSON object. No prose, no code fences, no explanations.

INPUT: A JSON object named AgentState with (possibly partial) fields:
{
  "user_prompt": string,
  "to": string|null,
  "subject": string|null,
  "body": string|null,
  "sender_name": string|null,
  "tone": "formal"|"polite"|"concise"|"friendly"|"professional"|"conversational"|"thought_leadership"|null,
  "length": "short"|"medium"|"long"|null
}

OUTPUT (must match EXACTLY):
{
  "to": "email@example.com",
  "subject": "Subject line",
  "body": "Email body content",
}

DRAFTING RULES
- Only fill fields that are missing or clearly too short; preserve provided fields.
- "to" and "body" are required to send. If unknown, set "" and include in "missing".
- Subject: create a concise, accurate subject if reasonably inferable; else "" and include "subject" in "missing".
- Use greeting with sender_name if plausible; else generic "Hello".
- Tone default: "polite". Length default: "short" (2–4 sentences; medium 4–7; long 7–12).
- Clear, direct, courteous. No emojis or disclaimers. Don’t invent unknown facts (dates, amounts, links).
- If critical info missing, ask briefly in the body.
- Output ONLY the JSON object.
"""

    # Build payload for the model
    payload = {
        "user_prompt": user_prompt,
        "to": to_val or None,
        "subject": subj or None,
        "body": body or None,
        "sender_name": sender_name or None,
        "tone": tone,
        "length": length,
    }

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps({"AgentState": payload}, ensure_ascii=False))
    ]

    try:
        resp = llm.invoke(messages)
        raw = resp.content
        print("[RAW]",raw)
        # Parse robustly
        try:
            data = json.loads(raw)
            print(data)
        except Exception:
            data = {
                "to": to_val,
                "subject": subj,
                "body": body,
            }

        # Preserve provided fields if generator tried to overwrite with empty/irrelevant
        state["to"] = data.get("to")
        state["subject"] = data.get("subject")
        state["body"] = data.get("body")

    except Exception as e:
        state["error"] = f"Drafting failed: {str(e)}"
        state["needs_input"] = True
        state["human_message"] = "I couldn't draft the email. Please provide subject/body."

    return state



def create_final_email(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create final email content.
    """
    to = state.get("to", "")
    subject = state.get("subject", "Email")
    body = state.get("body", "")
    sender_name = state.get("sender_name", "")
    
    # Create a simple email preview
    preview = f"""📧 EMAIL PREVIEW
{'=' * 40}

To: {to}
Subject: {subject}

Body:
{body}

{'=' * 40}
Ready to send? Please review above."""
    
    state["preview"] = preview
    return state