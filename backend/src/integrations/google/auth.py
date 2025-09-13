from __future__ import annotations
from pathlib import Path
from typing import Sequence
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SECRETS_PATH = Path("client_secret.json")
TOKEN_PATH = Path("token.json")

def get_credentials(scopes: Sequence[str]) -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS_PATH), scopes)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds

print(get_credentials(["https://www.googleapis.com/auth/calendar"]))