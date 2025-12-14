from typing import Dict, Any
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from ..tools.tools import set_event_tool
from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
import json

load_dotenv()

def extract_details(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose a calendar event from user input using LLM for extraction
    and then call the set_event tool.
    """
    user_input = state.get("user_prompt", "")
    system_prompt = """
    You are a smart assistant that extracts structured information for creating a Google Calendar event.

    Instructions:
    1. Extract these fields from the user's input:
    - summary: Title of the event
    - description: Description/details of the event
    - start: Start datetime in ISO 8601 format with timezone (Asia/Kolkata, UTC+5:30)
    - end: End datetime in ISO 8601 format with timezone (Asia/Kolkata, UTC+5:30)

    2. If any information is missing or ambiguous, detect the intent and provide a reasonable suggestion.

    3. Output only valid JSON. No extra text.

    4. Convert natural language dates/times into ISO 8601 format (YYYY-MM-DDTHH:MM:SS+05:30).

    Examples:

    Input:
    "Schedule a meeting called 'Team Sync' about 'project updates' tomorrow from 10 AM to 11 AM."
    Output:
    {{
    "summary": "Team Sync",
    "description": "project updates",
    "start": "2025-10-12T10:00:00+05:30",
    "end": "2025-10-12T11:00:00+05:30"
    }}

    Input:
    "Set up a call with client next Monday at 3 PM."
    Output:
    {{
    "summary": "Call with client",
    "description": "General discussion",
    "start": "2025-10-14T15:00:00+05:30",
    "end": "2025-10-14T16:00:00+05:30"
    }}

    Input:
    "Remind me to submit the report."
    Output:
    {{
    "summary": "Submit report",
    "description": "Reminder for report submission",
    "start": "2025-10-11T09:00:00+05:30",
    "end": "2025-10-11T10:00:00+05:30"
    }}
    """
    llm = ChatGroq(model="openai/gpt-oss-120b")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User input: {user_input}")
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
                "summary": "",
                "description": "",
                "start" : "",
                "end": ""
            }
        
        state['calendar_summary'] = data.get('summary')
        state['calendar_description'] = data.get('description')
        state['calendar_start'] = data.get('start')
        state['calendar_end'] = data.get('end')

    except Exception as e: 
        state["error"] = f"Extraction failed: {str(e)}" 
        state["human_message"] = "Could not extract email details. Please provide: to, subject, body" 
    print("FINAL STATE - ",state) 
    return state

def compose_events(state: Dict[str, Any]) -> Dict[str, Any]:
    state = extract_details(state)
    summary = state.get("calendar_summary")
    description = state.get("calendar_description")
    start = state.get("calendar_start")
    end = state.get("calendar_end")
    user_id = state.get("user_id")

    result = set_event_tool.invoke({"summary":summary,"description":description ,"start":start,"end":end ,"user_id" : user_id})
    print("RESULT -", result)
    status = result.get("status")
    message = result.get("message", "")
    footer = f"\n\n📤 Send result: {status} — {message}"
    print("[CALENDAR] FOOTER - ", footer)
    preview = (state.get("preview") or "") + footer
    ai_note = f"CALENDAR EVENT SET status: {status} — {message}"
    print("[CALENDAR] AI NOTE - ", ai_note)
    return Command(goto=END, update={
        "result": result,
        "preview": preview,
        "messages": [AIMessage(content=ai_note)],
    })


        