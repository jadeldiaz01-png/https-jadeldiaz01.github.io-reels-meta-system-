from fastapi import FastAPI

from app.skills_runtime.api import router

app = FastAPI(title="Skills Runtime Control Plane", version="1.0.0")
app.include_router(router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
