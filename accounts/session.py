
import secrets
import hmac
import hashlib
import base64
from datetime import timedelta, datetime
from django.conf import settings
from django.utils import timezone
from .models import UserSession  # your model from accounts/models.py

import logging

logger = logging.getLogger(__name__)

# Config (set these in settings.py)
COOKIE_NAME = getattr(settings, "SESSION_COOKIE_NAME", "XSESSIONID")
SECRET = getattr(settings, "SESSION_SECRET_KEY", settings.SECRET_KEY).encode()
DEFAULT_TTL_SECONDS = getattr(settings, "SESSION_TTL_SECONDS", 7 * 24 * 3600)

def _sign(value: str) -> str:
    mac = hmac.new(SECRET, value.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")

def make_cookie_token(session_key: str, expires_ts: int) -> str:
    # cookie format: session_key:expires_ts:signature
    payload = f"{session_key}:{expires_ts}"
    sig = _sign(payload)
    return f"{session_key}:{expires_ts}:{sig}"

def parse_cookie_token(cookie_value: str):
    try:
        session_key, expires_ts_str, sig = cookie_value.split(":")
        expires_ts = int(expires_ts_str)
        return session_key, expires_ts, sig
    except Exception:
        return None

def create_session_for_user(request, user, ttl_seconds: int = None):
    """
    Create a DB session row and return cookie value to set.
    """
    ttl = ttl_seconds or DEFAULT_TTL_SECONDS
    session_key = secrets.token_hex(32)  # 64 hex chars
    expires = timezone.now() + timedelta(seconds=ttl)

    us = UserSession.objects.create(
        user=user,
        session_key=session_key,
        device=(request.META.get("HTTP_USER_AGENT", "") or "")[:250],
        ip=request.META.get("REMOTE_ADDR", ""),
        status="active",
        expires=expires
    )
    token = make_cookie_token(session_key, int(expires.timestamp()))
    return token, us

def validate_cookie_token(cookie_value: str, request=None, delete_invalid=False):
    """
    Validate cookie token and return the UserSession instance (active), or None.
    """
    
    # print(cookie_value)
    parsed = parse_cookie_token(cookie_value)
    
    # print("parsed",parsed)
    if not parsed:
        return None
    session_key, expires_ts, sig = parsed
    payload = f"{session_key}:{expires_ts}"
    expected_sig = _sign(payload)
    
    logger.info(f"Validating cookie token: {payload}, Expected signature: {expected_sig}" )
    # use constant-time compare
    if not hmac.compare_digest(expected_sig, sig):
        logger.warning(f"Invalid signature for session key {session_key}.")
        return None

    # check expiry timestamp
    now_ts = int(timezone.now().timestamp())
    if expires_ts < now_ts:
        # expired cookie
        
        # print("exp")
        logger.warning(f"Session key {session_key} is expired.")
        return None

    # lookup DB session
    try:
        us = UserSession.objects.get(session_key=session_key, status="active")
    except UserSession.DoesNotExist:
        logger.warning(f"Session key {session_key} not found or not active in DB.")
        # print("no session in db")
        return None

    # optional: double-check DB expiry field if present
    if getattr(us, "expires", None):
        if us.expires.timestamp() < now_ts:
            us.status = "expired"
            us.save(update_fields=["status"])
            return None

    # optional fingerprint checks (user-agent/ip) — you can enable later
    # update last-seen fields if you have them
    try:
        us.save(update_fields=["device"])  # noop if unchanged; adjust as needed
        
    except Exception:
        
        logger.exception("Failed to update UserSession last-seen fields.")

    return us

def revoke_session_by_cookie(cookie_value: str):
    parsed = parse_cookie_token(cookie_value)
    if not parsed:
        return False
    session_key, _, _ = parsed
    UserSession.objects.filter(session_key=session_key).update(status="revoked")
    return True
