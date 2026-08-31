from __future__ import annotations

import os
from pathlib import Path


class WorkloadTokenProvider:
    """Reads a short-lived OpenBao token delivered by an auth sidecar/agent token sink.

    The application never accepts OPENBAO_TOKEN from environment. The sink path can be
    mounted read-only and rotated independently by the identity agent.
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or os.getenv("OPENBAO_TOKEN_FILE", "/run/openbao/token"))

    def get(self) -> str:
        try:
            token = self.path.read_text().strip()
        except OSError as exc:
            raise RuntimeError("openbao_workload_identity_unavailable") from exc
        if not token:
            raise RuntimeError("openbao_workload_identity_empty")
        return token
