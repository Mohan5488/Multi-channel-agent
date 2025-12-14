import datetime
from typing import Optional
from django.utils.dateparse import parse_datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from home.models import ServiceCredential

def _json_to_credentials(json_data: dict) -> Credentials:
    """
    Convert stored JSON to google.oauth2.credentials.Credentials (works for Google).
    If you plan to support other providers, create provider-specific mappers.
    """
    expiry = None
    if json_data.get("expiry"):
        expiry = parse_datetime(json_data["expiry"])
    creds = Credentials(
        token=json_data.get("token"),
        refresh_token=json_data.get("refresh_token"),
        token_uri=json_data.get("token_uri"),
        client_id=json_data.get("client_id"),
        client_secret=json_data.get("client_secret"),
        scopes=json_data.get("scopes"),
        expiry=expiry
    )
    return creds

def _credentials_to_json(creds: Credentials) -> dict:
    return {
        "token": creds.token,
        "refresh_token": getattr(creds, "refresh_token", None),
        "token_uri": getattr(creds, "token_uri", None),
        "client_id": getattr(creds, "client_id", None),
        "client_secret": getattr(creds, "client_secret", None),
        "scopes": getattr(creds, "scopes", None),
        "expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
    }

def load_service_creds(user_id: int, service: str) -> Optional[Credentials]:
    """
    Load credentials for a (user, service). Returns google.oauth2.credentials.Credentials or None.
    """
    try:
        row = ServiceCredential.objects.get(user_id=user_id, service=service)
    except ServiceCredential.DoesNotExist:
        return None

    return _json_to_credentials(row.data)

def save_service_creds(user_id: int, service: str, creds: Credentials):
    """
    Persist updated credentials back into DB (create or update the ServiceCredential row).
    Only stores fields from the Credentials object via the JSON mapping.
    """
    data = _credentials_to_json(creds)
    obj, _ = ServiceCredential.objects.update_or_create(
        user_id=user_id, service=service,
        defaults={"data": data}
    )
    return obj

def ensure_valid_and_persist(user_id: int, service: str):
    """
    Load creds, refresh if needed, and persist refreshed tokens back to DB.
    Returns Credentials object or None.
    """
    creds = load_service_creds(user_id, service)
    if creds is None:
        return None

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_service_creds(user_id, service, creds)
    
    print("CREDS -", creds)
    return creds
