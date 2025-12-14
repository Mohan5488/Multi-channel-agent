from typing import Dict, Any, Optional, TypedDict, Literal, List
from typing_extensions import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """
    Minimal state for email + chat + LinkedIn with HITL.
    """
    user_id: int

    # Conversation history (persist via reducer)
    messages: Annotated[List[AnyMessage], add_messages]

    # Core
    user_prompt: str
    intent: Optional[Literal["email", "linkedin", "chat", "booking"]]

    # ----- Email (minimal) -----
    to: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    sender_name : Optional[str]

    # ----- LinkedIn (extraction + metadata) -----
    topic: Optional[str]      # publishable text provided by user (empty if meta-intent)
    hashtags: List[str]
    mentions: List[str]
    urls: List[str]

    generated_text: Optional[str]

    # ----- LinkedIn (generation controls) -----
    tone: Optional[Literal["professional","conversational","thought_leadership"]]
    length: Optional[Literal["short","medium","long"]]
    audience: Optional[str]            # e.g. "deep-tech founders", "investors"

    # ----- Calendar (events) -----
    calendar_summary: Optional[str]       # Event title
    calendar_description: Optional[str]   # Event description
    calendar_start: Optional[str]         # ISO 8601 start datetime
    calendar_end: Optional[str]           # ISO 8601 end datetime
    calendar_timezone: Optional[str]      # e.g., "Asia/Kolkata"
    calendar_location: Optional[str]      # optional event location
    calendar_attendees: Optional[List[str]] # optional list of emails


    # ----- UI / Human-in-the-loop -----
    preview: Optional[str]
    awaiting: Literal["decision", "edits"]
    needs_input: bool
    human_message: Optional[str]
    approved: Optional[bool]

    # Result & errors
    result: Optional[Dict[str, Any]]
    error: Optional[str]

    # ----- Booking (movies/events) -----
    movie_title: Optional[str]
    city: Optional[str]
    date: Optional[str]
    num_seats: Optional[int]
    seat_category: Optional[str]  # e.g., premium, regular
    showtime_id: Optional[str]
    hold_id: Optional[str]
    order_id: Optional[str]


def create_initial_state(user_prompt: str) -> AgentState:
    return {
        "messages": [],
        "user_prompt": user_prompt,
        "awaiting": "decision",
        "needs_input": False,
        # LinkedIn defaults
        "li_hashtags": [],
        "li_mentions": [],
        "li_urls": [],
        "tone": "professional",
        "length": "medium",
        "audience": None,

        "calendar_summary": None,
        "calendar_description": None,
        "calendar_start": None,
        "calendar_end": None,
        "calendar_timezone": "Asia/Kolkata",
        "calendar_location": None,
        "calendar_attendees": [],
    }
