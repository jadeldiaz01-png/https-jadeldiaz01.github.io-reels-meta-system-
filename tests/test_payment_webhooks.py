import hashlib
import hmac
import pytest

from app.payment_webhooks import WebhookVerificationError, verify_stripe_signature


def header(payload: bytes, secret: str, timestamp: int) -> str:
    signed = str(timestamp).encode() + b"." + payload
    signature = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def test_valid_signature():
    payload = b'{"id":"evt_test"}'
    assert verify_stripe_signature(payload, header(payload, "whsec_test", 1000), "whsec_test", now=1000) == 1000


def test_tampered_payload_rejected():
    payload = b'{"id":"evt_test"}'
    with pytest.raises(WebhookVerificationError, match="signature_mismatch"):
        verify_stripe_signature(b'{"id":"tampered"}', header(payload, "whsec_test", 1000), "whsec_test", now=1000)


def test_replay_outside_tolerance_rejected():
    payload = b'{"id":"evt_test"}'
    with pytest.raises(WebhookVerificationError, match="outside_tolerance"):
        verify_stripe_signature(payload, header(payload, "whsec_test", 1000), "whsec_test", now=1401)
