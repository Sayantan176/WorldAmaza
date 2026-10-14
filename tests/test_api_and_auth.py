import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import hash_password, verify_password, create_session_token, verify_session_token
from app.schemas.watch import StructuredWatchRules

client = TestClient(app)


def test_password_hashing():
    pw = "SuperSecretPassword123!"
    hashed = hash_password(pw)
    assert hashed.startswith("pbkdf2:sha256:100000$")
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_session_token_integrity():
    token = create_session_token("user-uuid-1", "user@worldamaze.io")
    payload = verify_session_token(token)
    assert payload is not None
    assert payload["user_id"] == "user-uuid-1"
    assert payload["email"] == "user@worldamaze.io"

    # Tampered token check
    tampered = token[:-4] + "fake"
    assert verify_session_token(tampered) is None


def test_unauthenticated_api_access_blocked():
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 401


def test_registration_and_login_flow():
    unique_id = uuid.uuid4().hex[:8]
    test_email = f"analyst_{unique_id}@worldamaze.io"
    test_pw = "IntelligenceSecret2026!"

    # 1. Register
    reg_resp = client.post("/register", data={
        "email": test_email,
        "password": test_pw,
        "full_name": "Test Analyst",
        "timezone": "UTC"
    }, follow_redirects=False)

    assert reg_resp.status_code == 303
    assert "wa_session" in reg_resp.cookies

    cookie = reg_resp.cookies.get("wa_session")

    # 2. Access dashboard with session cookie
    dash_resp = client.get("/dashboard", cookies={"wa_session": cookie})
    assert dash_resp.status_code == 200
    assert "Overview Workspace" in dash_resp.text

    # 3. Access API dashboard with session cookie
    api_dash = client.get("/api/v1/dashboard", cookies={"wa_session": cookie})
    assert api_dash.status_code == 200
    data = api_dash.json()
    assert "active_watches" in data


@patch("app.routers.api.parse_watch_prompt")
def test_api_watch_interpret(mock_parser):
    mock_parser.return_value = StructuredWatchRules(
        title="India Defence Aviation",
        description="Track Tejas Mk1A first flight",
        subjects=["India", "Tejas Mk1A"],
        include_terms=["first flight", "prototype"],
        importance_threshold="high",
        evidence_requirement="official_confirmation"
    )

    unique_id = uuid.uuid4().hex[:8]
    reg_resp = client.post("/register", data={
        "email": f"interpret_{unique_id}@worldamaze.io",
        "password": "Password12345!",
    }, follow_redirects=False)
    assert reg_resp.status_code == 303
    cookie = reg_resp.cookies.get("wa_session")

    resp = client.post(
        "/api/v1/watches/interpret",
        json={"prompt": "Track Tejas Mk1A first flight"},
        cookies={"wa_session": cookie}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "India Defence Aviation"
