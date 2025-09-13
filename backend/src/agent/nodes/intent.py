"""
Simplified intent detection - only determines email vs LinkedIn.
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command


def detect_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect user intent: email or linkedin or general chat.
    """
    
    # llm = ChatOpenAI(model="gpt-4", temperature=0.1)
    llm = ChatGroq(model="openai/gpt-oss-120b")
    
    system_prompt = """Classify the user's request into one of: email, linkedin, chat.

- email: composing/sending an email, mentions email, mail, reply, forward, @address, etc.
- linkedin: posting to LinkedIn, share on LinkedIn, LinkedIn post, etc.
- chat: everything else (jokes, Q&A, small talk, general tasks).

Respond with ONLY one token: email | linkedin | chat
"""

    user_prompt = state.get("user_prompt", "")
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User input: {user_prompt}")
    ]
    
    response = llm.invoke(messages)
    intent = response.content.strip().lower()
    
    # Validate response
    if "email" in intent:
        intent = "email"
    elif "linkedin" in intent:
        intent = "linkedin"
    elif "chat" in intent:
        intent = "chat"
    else:
        # Fallback to keyword detection
        prompt_lower = user_prompt.lower()
        if any(word in prompt_lower for word in ["email", "@", "send to"]):
            intent = "email"
        elif any(word in prompt_lower for word in ["linkedin", "post", "share"]):
            intent = "linkedin"
        else:
            intent = "chat"  # Default
    
    state["intent"] = intent
    print("[INTENT] SET Intent -", intent)
    return state


def intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple intent detection - only determines email vs linkedin.
    """
    state = detect_intent(state)
    
    # Route based on intent
    if state.get("intent") == "email":
        print("SET NEXT STAGE - Compose email")
        return Command(goto="compose_email", update=state)
    elif state.get("intent") == "linkedin":
        return Command(goto="compose_linkedin", update=state)
    elif state.get("intent") == "chat":
        return Command(goto="chat", update=state)
    else:
        # Default to email
        state["intent"] = "chat"
        return Command(goto="chat", update=state)