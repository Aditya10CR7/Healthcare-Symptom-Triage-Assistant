import base64
import hashlib
import hmac
import json
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.schemas import LoginRequest, LoginResponse


security = HTTPBearer(auto_error=False)


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(username: str, settings: Settings) -> str:
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60 * 8,
    }
    payload_text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    encoded_payload = base64.urlsafe_b64encode(payload_text.encode()).decode()
    signature = _sign(encoded_payload, settings.admin_secret)
    return f"{encoded_payload}.{signature}"


def verify_token(token: str, settings: Settings) -> bool:
    try:
        encoded_payload, signature = token.split(".", 1)
        expected = _sign(encoded_payload, settings.admin_secret)
        if not hmac.compare_digest(signature, expected):
            return False
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload.encode()).decode())
        return payload.get("sub") == settings.admin_username and int(payload.get("exp", 0)) >= int(time.time())
    except Exception:
        return False


def login(payload: LoginRequest, settings: Settings) -> LoginResponse:
    if not (
        hmac.compare_digest(payload.username, settings.admin_username)
        and hmac.compare_digest(payload.password, settings.admin_password)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return LoginResponse(access_token=create_token(payload.username, settings))


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    if not verify_token(credentials.credentials, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return settings.admin_username

