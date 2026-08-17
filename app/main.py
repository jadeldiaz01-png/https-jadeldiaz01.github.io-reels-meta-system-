import os
from fastapi import FastAPI
from app.telemetry import configure_telemetry

app = FastAPI(title="Autonomous Course + Reels Revenue Engine", version="0.2.0")
configure_telemetry(app)

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/readyz")
def readyz() -> dict[str, object]:
    env = os.getenv("ENVIRONMENT", "development")
    external = os.getenv("EXTERNAL_EXECUTION_ENABLED", "false").lower() == "true"
    return {
        "status": "sandbox_ready" if env == "sandbox" and not external else "not_production_ready",
        "environment": env,
        "external_execution_enabled": external,
        "live_pilot_ready": False,
        "reason": "mandatory_evidence_and_human_go_live_approval_required",
    }
