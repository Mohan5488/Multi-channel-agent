from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command, interrupt
import json


# =========================
# EXTRACTOR (IMPROVED)
# =========================
def extract_linkedin_details(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract LinkedIn post details from user prompt:
      - topic (publishable only), tone, length, audience
      - hashtags, mentions, urls
      - missing (only 'topic' is considered critical for our flow)
    """
    user_prompt = state.get("user_prompt", "")

    # llm = ChatOpenAI(model="gpt-4", temperature=0.1)
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)
    

    system_prompt = """
You are a strict extractor for LinkedIn post inputs.

Return ONLY valid JSON with these fields:
{
  "topic": "LinkedIn post content",
  "tone": "professional|conversational|thought_leadership|''",
  "length": "short|medium|long|''",
  "audience": "string or ''",
  "hashtags": ["#hashtag1", "#hashtag2"],
  "mentions": ["@user1", "@user2"],
  "urls": ["https://example.com"],
  "missing": ["list of missing fields"]
}

Rules

TOPIC
- Capture only if input contains actual publishable content (sentences/phrases intended to be posted).
- Do NOT treat meta-intent/requests as topic (e.g., “write a post”, “I want to post on LinkedIn”, “draft a post”).
- If no publishable content, set "topic": "" and include "topic" in "missing".

TONE / LENGTH / AUDIENCE
- TONE: extract if user indicates tone (“conversational”, “professional”, “thought leadership”); else professional.
- LENGTH: map any size hints to one of: short|medium|long; else medium.
- AUDIENCE: extract if user names an audience (“for deep-tech founders”, “for investors”); else general groups.

HASHTAGS
- Collect tokens starting with # (letters/numbers/underscore). Keep original casing.
- If none, return [] (do NOT add to missing unless user explicitly asked to include hashtags).

MENTIONS
- Collect tokens starting with @ (letters/numbers/underscore). Keep original casing.
- If none, return [] (do NOT add to missing unless user explicitly asked to include mentions).

URLS
- Extract any http:// or https:// URLs.
- If none, return [] (do NOT add to missing unless user explicitly asked to include a link).

MISSING
- Always include fields the user explicitly requested but didn’t provide.
- Always include "topic" if no publishable content was found.
- Otherwise, [].

Formatting
- Output only the JSON object. No prose.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User input: {user_prompt}")
    ]

    try:
        response = llm.invoke(messages)
        try:
            data = json.loads(response.content.strip())
        except json.JSONDecodeError:
            data = {
                "topic": "",
                "tone": "",
                "length": "",
                "audience": "",
                "hashtags": [],
                "mentions": [],
                "urls": [],
                "missing": ["topic"]
            }

        # Update state
        state["topic"] = data.get("topic", "") or ""
        state["tone"] = data.get("tone", "") or state.get("tone") or ""
        state["length"] = data.get("length", "") or state.get("length") or ""
        state["audience"] = data.get("audience", "") or state.get("audience") or ""
        state["linkedin_hashtags"] = data.get("hashtags", []) or []
        state["linkedin_mentions"] = data.get("mentions", []) or []
        state["linkedin_urls"] = data.get("urls", []) or []

        # Critical missing: text
        critical_missing = []
        if not state["topic"]:
            critical_missing.append("topic")

        if critical_missing:
            state["needs_input"] = True
            missing_list = ", ".join(critical_missing)
            state["human_message"] = f"Missing LinkedIn information: {missing_list}. Please provide:\n- text: "
        else:
            state["needs_input"] = False
            state["human_message"] = None

    except Exception as e:
        state["error"] = f"Extraction failed: {str(e)}"
        state["needs_input"] = True
        state["human_message"] = "Could not extract LinkedIn details. Please provide post topic."

    return state


# =========================
# FEEDBACK (UPDATED)
# =========================
def process_linkedin_feedback(state: Dict[str, Any], feedback: str) -> Dict[str, Any]:
    """
    Process human feedback to fill missing LinkedIn details.
    Only set 'text' if feedback contains publishable sentences.
    Also extract tone/length/audience/hashtags/mentions/urls if provided.
    """
    # llm = ChatOpenAI(model="gpt-4", temperature=0.1)
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)


    system_prompt = f"""Extract LinkedIn information from human feedback.

Current:
topic={state.get('topic','')}
tone={state.get('tone','')}
length={state.get('length','')}
audience={state.get('audience','')}
hashtags={state.get('linkedin_hashtags',[])}
mentions={state.get('linkedin_mentions',[])}
urls={state.get('linkedin_urls',[])}

Return ONLY JSON:
{{
  "topic": "publishable content",
  "tone": "professional|conversational|thought_leadership|''",
  "length": "short|medium|long|''",
  "audience": "string or ''",
  "hashtags": ["#h1"],
  "mentions": ["@m1"],
  "urls": ["https://..."]
}}

Rules:
- Only set "topic" if feedback contains actual publishable sentences. If it's still meta-intent, leave "".
- Do not fabricate hashtags/mentions/urls; extract only what is present.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Human feedback: {feedback}")
    ]

    try:
        response = llm.invoke(messages)
        try:
            data = json.loads(response.content.strip())
        except json.JSONDecodeError:
            data = {}

        # Update fields if provided
        if isinstance(data.get("topic"), str):
            state["topic"] = data["topic"]  # may be ""

        if data.get("tone"):
            state["tone"] = data["tone"]
        if data.get("length"):
            state["length"] = data["length"]
        if data.get("audience"):
            state["audience"] = data["audience"]

        if isinstance(data.get("hashtags"), list):
            state["linkedin_hashtags"] = data["hashtags"]
        if isinstance(data.get("mentions"), list):
            state["linkedin_mentions"] = data["mentions"]
        if isinstance(data.get("urls"), list):
            state["linkedin_urls"] = data["urls"]

        # Re-evaluate missing
        if not (state.get("topic") or "").strip():
            state["needs_input"] = True
            state["human_message"] = "Still missing: topic. Please provide:\n- topic: "
        else:
            state["needs_input"] = False
            state["human_message"] = None

    except Exception as e:
        state["error"] = f"Failed to process feedback: {str(e)}"
        state["needs_input"] = True
        state["human_message"] = "Error processing your input. Please try again."

    return state


# =========================
# POST-INFO (NEW)
# =========================

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

def draft_linkedin_post_from_topic(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a well-structured LinkedIn post body from a topic (short phrase or notes).
    Uses tone, length, audience. Does NOT include hashtags/mentions/urls in the body.
    """
    topic = (state.get("topic") or "").strip()  # treat current 'topic' as topic if it's short
    tone = state.get("tone") or "professional"         # professional|conversational|thought_leadership
    length = state.get("length") or "medium"           # short|medium|long
    audience = state.get("audience") or "general professionals"

    # Optional: allow a CTA via state["cta"] if you want
    cta = (state.get("cta") or "").strip()

    # llm = ChatOpenAI(model="gpt-4", temperature=0.4)
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)


    sys = f"""You write complete, high-signal LinkedIn posts.
Requirements:
- INPUT will be a TOPIC (short phrase or notes).
- Produce a full post body suitable for LinkedIn.
- Include hashtags, @mentions, or URLs in the body (they will be appended later).
- Tone: {tone}
- Length: {length} (short≈40–80 words, medium≈80–140, long≈140–220)
- Audience: {audience}
- Use a clear hook, 1–2 concrete points or example, and a concise close.
- If CTA provided, include it naturally once: "{cta}" (omit if empty).
- No emojis unless present in the topic.
Return ONLY the post body text.
"""

    messages = [
        SystemMessage(content=sys),
        HumanMessage(content=f"TOPIC:\n{topic}")
    ]

    try:
        resp = llm.invoke(messages)
        post_body = (resp.content or "").strip()
        if post_body:
            state["generated_text"] = post_body
            state["needs_input"] = False
            state["human_message"] = None
        else:
            # Fallback: keep needs_input if nothing generated
            state["needs_input"] = True
            state["human_message"] = "Could not generate a post from the topic. Please provide 1–2 sentences."
    except Exception as e:
        state["error"] = f"Generation failed: {str(e)}"
        state["needs_input"] = True
        state["human_message"] = "Error generating the post. Please provide 1–2 sentences."

    return state


# =========================
# ASSEMBLER (UPDATED)
# =========================
def create_final_linkedin_post(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose final post. Prefer refined 'post_info.post_body' when available;
    otherwise use user-provided 'topic'. Append mentions/hashtags/urls separately.
    """
    post_info = state.get("post_info") or {}
    refined = (post_info.get("post_body") or "").strip()
    base_text = refined or (state.get("generated_text") or "").strip()

    hashtags = state.get("linkedin_hashtags", []) or []
    mentions = state.get("linkedin_mentions", []) or []
    urls = state.get("linkedin_urls", []) or []

    post_content = base_text
    if mentions:
        post_content += f"\n\nMentions: {' '.join(mentions)}"
    if hashtags:
        post_content += f"\n\n{' '.join(hashtags)}"
    if urls:
        post_content += f"\n\nLinks: {' '.join(urls)}"

    preview = f"""📱 LINKEDIN POST PREVIEW
{'=' * 40}

{post_content}

{'=' * 40}
Ready to post? Please review above."""
    state["preview"] = preview
    state["text"] = post_content  # keep for downstream compatibility
    return state


# =========================
# ORCHESTRATOR (UNCHANGED FLOW, + post_info)
# =========================
def compose_linkedin(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose LinkedIn post with extraction and human-in-the-loop.
    After fields are ready, fetch post_info, then compose preview.
    """
    # Extract
    state = extract_linkedin_details(state)
    print("[Compose LinkedIn] After extract -", state)

    # Human input loop if text missing
    if state.get("needs_input"):
        user_feedback = interrupt({
            "message": state.get("human_message", "Please provide missing LinkedIn information")
        })
        print(f"[compose_linkedin] Human feedback: {user_feedback}")

        state = process_linkedin_feedback(state, user_feedback)
        print("[Compose LinkedIn] After feedback -", state)

        if state.get("needs_input"):
            return compose_linkedin(state)

    # Post-info (refinement & diagnostics; no new claims)
    state = draft_linkedin_post_from_topic(state)
    print("[Compose LinkedIn] Post info -", state.get("post_info"))

    # Final assemble + preview
    state = create_final_linkedin_post(state)
    print("[Compose LinkedIn] Final state -", state)

    return Command(goto="human_gate", update=state)
