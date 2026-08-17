from __future__ import annotations

import hashlib
import hmac
import time


class WebhookVerificationError(ValueError):
    pass


def verify_stripe_signature(payload: bytes, signature_header: str, secret: str, *, tolerance_seconds: int = 300,
                            now: int | None = None) -> int:
    """Verify Stripe-style t=timestamp,v1=signature webhook headers without trusting request JSON first."""
    if not secret:
        raise WebhookVerificationError("missing_webhook_secret")
    parts: dict[str, list[str]] = {}
    for item in signature_header.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parts.setdefault(key.strip(), []).append(value.strip())
    try:
        timestamp = int(parts["t"][0])
        signatures = parts["v1"]
    except (KeyError, ValueError, IndexError) as exc:
        raise WebhookVerificationError("malformed_signature_header") from exc

    current = int(time.time()) if now is None else now
    if abs(current - timestamp) > tolerance_seconds:
        raise WebhookVerificationError("signature_timestamp_outside_tolerance")

    signed = str(timestamp).encode() + b"." + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise WebhookVerificationError("signature_mismatch")
    return timestamp
