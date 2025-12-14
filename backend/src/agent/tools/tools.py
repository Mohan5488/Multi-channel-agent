import os
import requests
from email.mime.text import MIMEText
import smtplib
from dotenv import load_dotenv
load_dotenv()
try:
    from langchain.tools import tool
except Exception:
    from langchain_core.tools import tool


from rest_framework.views import APIView
from rest_framework.response import Response
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
import base64
import os
import json
from ..utility_cred.creds import ensure_valid_and_persist

@tool("send_mail")
def send_email_tool(to: str, subject: str, body: str, user_id: int = None) -> dict:
    '''
        send mail using oauth credentials
    '''
    if not user_id:
        return {"status": "error", "message": "user_id is required"}

    service_name = "gmail"
    creds = ensure_valid_and_persist(user_id, service_name)
    if not creds:
        return {"status": "error", "message": "no credentials found for user/service"}

    try:
        service = build("gmail", "v1", credentials=creds)

        msg = MIMEText(body)
        msg["to"] = to
        msg["from"] = "me"
        msg["subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        sent = service.users().messages().send(
            userId="me", 
            body={"raw": raw}
        ).execute()

        return {"status":"success", "message": sent.get("id")}

    except Exception as exc:
        return {"status":"error", "message": str(exc)}

@tool("set_event")
def set_event_tool(summary, description, start, end, user_id):
    """
        Creates an event in calender using OAuth connectivity.
    """
    service_name = "google_calendar"
    creds = ensure_valid_and_persist(user_id, service_name)

    if not creds:
        return {"status": "error", "message": "no credentials found for user/service"}
    try:
        service = build('calendar', 'v3', credentials=creds)
        print("[CALENDER SERVICE BUILD")

        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start, 'timeZone': 'UTC+5:30'},
            'end': {'dateTime': end, 'timeZone': 'UTC+5:30'},
        }
        print("[CALENDER] EVENT SENDING .......")

        event = service.events().insert(calendarId='primary', body=event).execute()
        print("[CALENDER EVENT SEND SUCCESSFULLY")
        return {"status": "success", "message": event.get("id")}
    except Exception as exc:
            return {"status":"error", "message": str(exc)}

@tool("post_linkedin_text")
def post_linkedin_text(text: str) -> dict:
    """
    Publish a PUBLIC text-only LinkedIn post via UGC API.

    Env required:
      - LINKEDIN_ACCESS_TOKEN
      - LINKEDIN_PERSON_URN (e.g., 'urn:li:person:XXXX')
    """
    print("[POST_LINKEDIN_TEXT] Posting LinkedIn text", text)
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    author_urn = os.getenv("LINKEDIN_PERSON_URN")
    if not access_token or not author_urn:
        return {"status": "error", "message": "Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN"}

    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code in (200, 201):
            return {"status": "success", "message": "LinkedIn text post published"}
        return {"status": "error", "message": f"{resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

