from fastapi import FastAPI

app = FastAPI(title="Autonomous Course + Reels Revenue Engine", version="0.1.0")

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "not_production_ready", "reason": "credentials_and_e2e_evidence_required"}
