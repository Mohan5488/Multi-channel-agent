# mcp_channels.py
import os, smtplib, json, requests
from email.mime.text import MIMEText
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ChannelsMCP")

# ----------------------
# Email (SMTP) tool
# ----------------------
@mcp.tool()
def send_email(to: str, subject: str, body: str):
    """Send plain-text email via SMTP."""
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

    if not SENDER_EMAIL or not APP_PASSWORD:
        return {"status": "error", "message": "Missing SENDER_EMAIL or SMTP_APP_PASSWORD env var"}

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)

        return {"status": "success", "message": f"Email sent to {to}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------------
# LinkedIn helpers
# ----------------------
def _linkedin_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

def _require_li_env():
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    author_urn = os.getenv("LINKEDIN_PERSON_URN")
    if not access_token or not author_urn:
        return None, None, {"status": "error", "message": "Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN"}
    return access_token, author_urn, None

@mcp.tool()
def post_text_share(text: str):
    """Publish a PUBLIC text-only LinkedIn post (UGC API)."""
    access_token, author_urn, err = _require_li_env()
    if err: return err

    url = "https://api.linkedin.com/v2/ugcPosts"
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
        resp = requests.post(url, headers=_linkedin_headers(access_token), json=payload, timeout=20)
        if resp.status_code in (200, 201):
            return {"status": "success", "message": "LinkedIn text post published"}
        return {"status": "error", "message": f"{resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def post_article_share(text: str, original_url: str, title: Optional[str] = None, description: Optional[str] = None):
    """Publish an ARTICLE share with a URL."""
    access_token, author_urn, err = _require_li_env()
    if err: return err

    url = "https://api.linkedin.com/v2/ugcPosts"
    media_obj = {"status": "READY", "originalUrl": original_url}
    if title:       media_obj["title"] = {"text": title}
    if description: media_obj["description"] = {"text": description}

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "ARTICLE",
                "media": [media_obj],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    try:
        resp = requests.post(url, headers=_linkedin_headers(access_token), json=payload, timeout=20)
        if resp.status_code in (200, 201):
            return {"status": "success", "message": "LinkedIn article post published"}
        return {"status": "error", "message": f"{resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _register_image_upload(access_token: str, author_urn: str):
    url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author_urn,
            "serviceRelationships": [{"relationshipType": "OWNER","identifier": "urn:li:userGeneratedContent"}],
        }
    }
    resp = requests.post(url, headers=_linkedin_headers(access_token), json=payload, timeout=20)
    if resp.status_code not in (200, 201):
        return None, None
    val = resp.json().get("value", {})
    upload_url = (val.get("uploadMechanism", {})
                    .get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
                    .get("uploadUrl"))
    asset = val.get("asset")
    return upload_url, asset

@mcp.tool()
def post_image_share(text: str, image_file_path: str, title: Optional[str] = None, description: Optional[str] = None):
    """Publish an IMAGE share by registering/uploading asset then posting."""
    access_token, author_urn, err = _require_li_env()
    if err: return err

    up_url, asset = _register_image_upload(access_token, author_urn)
    if not up_url or not asset:
        return {"status": "error", "message": "registerUpload failed"}

    try:
        with open(image_file_path, "rb") as f:
            headers = {"Authorization": f"Bearer {access_token}"}
            up_resp = requests.post(up_url, headers=headers, data=f, timeout=60)
        if up_resp.status_code not in (200, 201):
            return {"status": "error", "message": f"binary upload failed: {up_resp.status_code} {up_resp.text}"}
    except Exception as e:
        return {"status": "error", "message": f"binary upload exception: {e}"}

    url = "https://api.linkedin.com/v2/ugcPosts"
    media_obj = {"status": "READY", "media": asset}
    if title:       media_obj["title"] = {"text": title}
    if description: media_obj["description"] = {"text": description}

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [media_obj],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    try:
        resp = requests.post(url, headers=_linkedin_headers(access_token), json=payload, timeout=20)
        if resp.status_code in (200, 201):
            return {"status": "success", "message": "LinkedIn image post published"}
        return {"status": "error", "message": f"{resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    mcp.run(transport="stdio")
