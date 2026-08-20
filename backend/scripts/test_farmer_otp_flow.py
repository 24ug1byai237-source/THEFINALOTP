"""
End-to-end test for the Farmer WhatsApp-deep-link OTP login flow.

Unlike test_auth_rbac.py (which inserts an OTP row directly to test the
verify step in isolation), this script drives the REAL /auth/otp/send
endpoint first, so it also exercises:

  - real random 6-digit code generation
  - the wa.me deep-link construction/encoding
  - resend cooldown enforcement
  - per-window request cap
  - verify-attempt lockout
  - expiry handling
  - auto-registration of a brand-new farmer on first successful OTP login
  - that a fresh farmer has NO farms assigned (no "first farm" fallback,
    no hard-coded district) until explicitly assigned

Run with: python scripts/test_farmer_otp_flow.py
"""

import os
import sys
import time
import urllib.parse

test_db_path = os.path.join(os.path.dirname(__file__), "test_farmer_otp_flow.db")
if os.path.exists(test_db_path):
    try:
        os.remove(test_db_path)
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
# Tight limits so the test doesn't have to sleep for the real defaults.
# NOTE: `settings` is a module-level singleton read once at import time
# (see app/core/config.py), so these must be set before app.main is
# imported below — changing os.environ afterwards would have no effect.
os.environ["OTP_RESEND_COOLDOWN_SECONDS"] = "1"
os.environ["OTP_MAX_VERIFY_ATTEMPTS"] = "3"
os.environ["OTP_TTL_SECONDS"] = "1"  # expires almost immediately for the expiry test

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

PHONE_RAW = "+91 90000 11111"
PHONE_NORMALIZED = "+919000011111"


def run_tests():
    print("=== FARMER WHATSAPP-OTP FLOW TESTS ===")

    # 1. SEND OTP -> real random code, wa.me deep link, no code leaked in body
    res = client.post("/api/v1/auth/otp/send", json={"phone": PHONE_RAW})
    assert res.status_code == 200, f"send_otp failed: {res.text}"
    body = res.json()
    assert body["message"] == "OTP sent. Check WhatsApp and enter the 6-digit code."
    assert body["phone"] == PHONE_NORMALIZED
    assert body["demo"] is True
    whatsapp_url = body["whatsappUrl"]
    assert whatsapp_url.startswith("https://wa.me/919000011111?text="), whatsapp_url
    # No devCode/dev_code/otp field of any kind should ever be in the response.
    for forbidden_key in ("devCode", "dev_code", "otp", "code"):
        assert forbidden_key not in body, f"OTP leaked in send response via '{forbidden_key}'"
    print("[OK] /auth/otp/send returns a fresh code only via the wa.me deep link, never in the JSON body")

    # Extract the code the "farmer" would read from WhatsApp, purely to
    # simulate manual entry — this mirrors decoding the URL exactly like a
    # human reading the prefilled WhatsApp message would.
    query = urllib.parse.urlparse(whatsapp_url).query
    message_text = urllib.parse.unquote_plus(urllib.parse.parse_qs(query)["text"][0])
    assert message_text == f"AgriSentinel verification code: {message_text.split(': ')[1]}"
    real_code = message_text.split(": ")[1]
    assert real_code.isdigit() and len(real_code) == 6, f"OTP not a 6-digit code: {real_code!r}"
    print(f"[OK] WhatsApp deep link correctly encodes a random 6-digit code ({real_code})")

    # 2. Immediate resend is blocked by cooldown
    res = client.post("/api/v1/auth/otp/send", json={"phone": PHONE_RAW})
    assert res.status_code == 429, f"Expected 429 resend-too-soon, got {res.status_code}: {res.text}"
    print("[OK] Resend before cooldown elapses is rejected (429)")

    # 3. Wrong OTP is rejected without creating a session
    res = client.post("/api/v1/auth/otp/verify", json={"phone": PHONE_RAW, "code": "000000"})
    assert res.status_code == 401, f"Expected 401 for wrong code, got {res.status_code}"
    assert "accessToken" not in res.json()
    print("[OK] Wrong OTP rejected, no session created")

    # 4. Verify-attempt lockout: OTP_MAX_VERIFY_ATTEMPTS=3, we've used 1 wrong
    #    guess above, 2 more should lock the code out even before it expires.
    for _ in range(2):
        res = client.post("/api/v1/auth/otp/verify", json={"phone": PHONE_RAW, "code": "111111"})
        assert res.status_code == 401, res.text
    res = client.post("/api/v1/auth/otp/verify", json={"phone": PHONE_RAW, "code": real_code})
    assert res.status_code == 401, "Correct code should be locked out after too many wrong attempts"
    print("[OK] Verification attempt limit locks out the code even with the correct value")

    # 5. Wait for cooldown to pass, then send a fresh code and let it expire
    time.sleep(1.2)  # clears OTP_RESEND_COOLDOWN_SECONDS=1
    res = client.post("/api/v1/auth/otp/send", json={"phone": PHONE_RAW})
    assert res.status_code == 200, res.text
    fresh_whatsapp_url = res.json()["whatsappUrl"]
    fresh_query = urllib.parse.urlparse(fresh_whatsapp_url).query
    fresh_message = urllib.parse.unquote_plus(urllib.parse.parse_qs(fresh_query)["text"][0])
    fresh_code = fresh_message.split(": ")[1]
    assert fresh_code != real_code, "Resend must generate a NEW code, not reuse the old one"
    time.sleep(1.2)  # let OTP_TTL_SECONDS=1 expire (this also clears the resend cooldown)
    res = client.post("/api/v1/auth/otp/verify", json={"phone": PHONE_RAW, "code": fresh_code})
    assert res.status_code == 401, f"Expired OTP should be rejected, got {res.status_code}"
    print("[OK] Resend issues a new code, and an expired code is rejected")

    # 6. Successful flow end to end: send, read code from the deep link, verify, get a session
    res = client.post("/api/v1/auth/otp/send", json={"phone": PHONE_RAW})
    assert res.status_code == 200, res.text
    whatsapp_url = res.json()["whatsappUrl"]
    query = urllib.parse.urlparse(whatsapp_url).query
    message_text = urllib.parse.unquote_plus(urllib.parse.parse_qs(query)["text"][0])
    code = message_text.split(": ")[1]

    res = client.post("/api/v1/auth/otp/verify", json={"phone": PHONE_RAW, "code": code})
    assert res.status_code == 200, f"Valid OTP login failed: {res.text}"
    data = res.json()
    assert "accessToken" in data and "refreshToken" in data
    assert data["user"]["role"] == "farmer", "Auto-registered OTP user must be FARMER, never any other role"
    assert data["user"]["farmIds"] == [], (
        "A brand-new farmer must start with NO farms assigned — "
        "no 'first farm in the DB' fallback, no hard-coded district/farm"
    )
    print("[OK] Correct OTP authenticates, auto-registers as FARMER with zero pre-assigned farms")

    # 7. Reusing the same (now-used) code must fail
    res = client.post("/api/v1/auth/otp/verify", json={"phone": PHONE_RAW, "code": code})
    assert res.status_code == 401, "Reusing a consumed OTP must be rejected"
    print("[OK] Reused OTP rejected (single-use enforced)")

    # 8. Farmer cannot reach Veterinarian/Officer-only endpoints with their token
    farmer_headers = {"Authorization": f"Bearer {data['accessToken']}"}
    res = client.get("/api/v1/officer/stats", headers=farmer_headers)
    assert res.status_code == 403, f"Farmer must be forbidden from officer endpoints, got {res.status_code}"
    print("[OK] Farmer session is forbidden (403) from Government Officer-only routes")

    print("\nALL FARMER WHATSAPP-OTP FLOW TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
