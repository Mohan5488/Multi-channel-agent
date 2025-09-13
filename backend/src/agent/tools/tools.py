
import os
import requests
from email.mime.text import MIMEText
import smtplib
from dotenv import load_dotenv
load_dotenv()

# Prefer legacy import path; fall back to core
try:
    from langchain.tools import tool
except Exception:
    from langchain_core.tools import tool


@tool("send_email")
def send_email_tool(to: str, subject: str, body: str) -> dict:
    """
    Send a plain-text email via SMTP.

    Env required:
      - SENDER_EMAIL
      - SMTP_APP_PASSWORD  (e.g., Gmail App Password)
    Optional:
      - SMTP_SERVER (default: smtp.gmail.com)
      - SMTP_PORT   (default: 587)
    """
    print("[SEND_EMAIL_TOOL] Sending email to", to, subject, body)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

    if not SENDER_EMAIL or not APP_PASSWORD:
        return {"status": "error", "message": "Missing SENDER_EMAIL or SMTP_APP_PASSWORD"}

    try:
        msg = MIMEText(body or "")
        msg["Subject"] = subject or "(no subject)"
        msg["From"] = SENDER_EMAIL
        msg["To"] = to

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)

        return {"status": "success", "message": f"Email sent to {to}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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

