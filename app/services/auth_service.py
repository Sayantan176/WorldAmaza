import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from supabase import create_client, Client
from app.config import settings
from app.models import User

logger = logging.getLogger("worldamaze.auth")

COOKIE_NAME = "wa_session"
SESSION_DURATION_SECONDS = 7 * 24 * 3600  # 7 days


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = secrets.token_hex(16)
    kdf = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2:sha256:100000${salt}${base64.b64encode(kdf).decode('ascii')}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored PBKDF2 hash."""
    if not hashed_password or not hashed_password.startswith("pbkdf2:sha256:"):
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        iterations = int(parts[0].split(":")[2])
        salt = parts[1]
        expected_hash = base64.b64decode(parts[2].encode("ascii"))
        computed_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def create_session_token(user_id: str, email: str) -> str:
    """Creates a signed, tamper-proof session token."""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": int(time.time()) + SESSION_DURATION_SECONDS
    }
    raw = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), raw, hashlib.sha256).digest()
    return f"{base64.urlsafe_b64encode(raw).decode('ascii')}.{base64.urlsafe_b64encode(sig).decode('ascii')}"


def verify_session_token(token: str) -> Optional[dict]:
    """Verifies signature and expiration of session token."""
    if not token or "." not in token:
        return None
    try:
        raw_b64, sig_b64 = token.split(".", 1)
        raw = base64.urlsafe_b64decode(raw_b64.encode("ascii"))
        sig = base64.urlsafe_b64decode(sig_b64.encode("ascii"))
        expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(raw.decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


class AuthService:
    def __init__(self):
        self._supabase: Optional[Client] = None
        if settings.SUPABASE_URL and settings.SUPABASE_PUBLISHABLE_KEY:
            try:
                self._supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY)
            except Exception as e:
                logger.warning(f"Could not initialize Supabase client: {e}")

    def register_user(
        self,
        db: Session,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        timezone: str = "UTC"
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Registers a new user. Integrates with Supabase Auth where accessible,
        and securely manages local user profile and credentials.
        """
        clean_email = email.strip().lower()
        existing = db.query(User).filter(User.email == clean_email).first()
        if existing:
            return None, "An account with this email already exists."

        supabase_user_id = None
        if self._supabase:
            try:
                sb_res = self._supabase.auth.sign_up({
                    "email": clean_email,
                    "password": password
                })
                if sb_res and sb_res.user:
                    supabase_user_id = sb_res.user.id
                    logger.info(f"Supabase Auth registered user {clean_email}")
            except Exception as e:
                logger.info(f"Supabase Auth notice during signup: {e} (Falling back to internal authentication)")

        pw_hash = hash_password(password)
        new_user = User(
            email=clean_email,
            password_hash=pw_hash,
            supabase_user_id=supabase_user_id,
            full_name=full_name,
            timezone=timezone,
            email_notifications_enabled=True,
            digest_frequency="daily",
            digest_time="08:00"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user, None

    def authenticate_user(
        self,
        db: Session,
        email: str,
        password: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticates a user via Supabase Auth or verified local credentials.
        """
        clean_email = email.strip().lower()
        user = db.query(User).filter(User.email == clean_email).first()

        # Try Supabase Auth first if client is available
        if self._supabase:
            try:
                sb_res = self._supabase.auth.sign_in_with_password({
                    "email": clean_email,
                    "password": password
                })
                if sb_res and sb_res.user:
                    # Sync with local user
                    if not user:
                        user = User(
                            email=clean_email,
                            supabase_user_id=sb_res.user.id,
                            timezone="UTC"
                        )
                        db.add(user)
                        db.commit()
                        db.refresh(user)
                    return user, None
            except Exception as e:
                logger.debug(f"Supabase login attempt returned: {e}")

        # Check local hash
        if user and user.password_hash and verify_password(password, user.password_hash):
            return user, None

        return None, "Invalid email or password."


auth_service = AuthService()
