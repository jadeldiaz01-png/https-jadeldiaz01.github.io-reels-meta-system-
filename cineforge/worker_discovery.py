from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import shutil
import subprocess
from typing import Iterable


class WorkerClass(str, Enum):
    LOCAL = "LOCAL"
    VPS = "VPS"
    COLAB_FREE = "COLAB_FREE"
    KAGGLE_FREE = "KAGGLE_FREE"
    HF_ZEROGPU = "HF_ZEROGPU"
    OTHER_SHARED = "OTHER_SHARED"


class AutomationClass(str, Enum):
    PERSISTENT = "PERSISTENT"
    SESSION_ONLY = "SESSION_ONLY"
    SHARED_API = "SHARED_API"


@dataclass(frozen=True)
class GPUDevice:
    index: int
    name: str
    total_vram_gb: float
    compute_capability: str | None = None


@dataclass(frozen=True)
class WorkerProbe:
    worker_class: WorkerClass
    automation_class: AutomationClass
    cuda_available: bool
    devices: tuple[GPUDevice, ...]
    source: str
    quota_limited: bool = False
    ephemeral: bool = False

    @property
    def max_vram_gb(self) -> float:
        return max((d.total_vram_gb for d in self.devices), default=0.0)


@dataclass(frozen=True)
class WorkerDecision:
    worker: WorkerProbe
    recommended_model: str
    reason: str


def detect_local_gpu() -> WorkerProbe:
    """Detect NVIDIA GPUs using nvidia-smi; fail safely when unavailable."""
    smi = shutil.which("nvidia-smi")
    if smi is None:
        return WorkerProbe(
            worker_class=WorkerClass.LOCAL,
            automation_class=AutomationClass.PERSISTENT,
            cuda_available=False,
            devices=(),
            source="nvidia-smi-not-found",
        )
    cmd = [
        smi,
        "--query-gpu=index,name,memory.total,compute_cap",
        "--format=csv,noheader,nounits",
    ]
    try:
        raw = subprocess.check_output(cmd, text=True, timeout=10)
    except Exception:
        return WorkerProbe(
            worker_class=WorkerClass.LOCAL,
            automation_class=AutomationClass.PERSISTENT,
            cuda_available=False,
            devices=(),
            source="nvidia-smi-query-failed",
        )
    devices: list[GPUDevice] = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            idx = int(parts[0])
            name = parts[1]
            vram_gb = float(parts[2]) / 1024.0
            cc = parts[3] if len(parts) > 3 else None
            devices.append(GPUDevice(idx, name, round(vram_gb, 2), cc))
        except ValueError:
            continue
    return WorkerProbe(
        worker_class=WorkerClass.LOCAL,
        automation_class=AutomationClass.PERSISTENT,
        cuda_available=bool(devices),
        devices=tuple(devices),
        source="nvidia-smi",
    )


def recommend_model_for_worker(worker: WorkerProbe) -> WorkerDecision:
    if not worker.cuda_available or worker.max_vram_gb <= 0:
        raise ValueError("gpu_worker_unavailable")
    vram = worker.max_vram_gb
    if vram >= 24:
        return WorkerDecision(worker, "wan2.2-ti2v-5b", "24GB+ VRAM: preferred first production smoke-test path")
    if vram >= 12:
        return WorkerDecision(worker, "cogvideox-2b", "12-23GB VRAM: lower-resource deterministic fallback")
    if vram >= 6:
        return WorkerDecision(worker, "framepack", "6-11GB VRAM: strongest low-VRAM candidate")
    raise ValueError("gpu_vram_below_supported_floor")


def choose_worker(workers: Iterable[WorkerProbe]) -> WorkerProbe:
    candidates = [w for w in workers if w.cuda_available and w.max_vram_gb >= 6]
    if not candidates:
        raise ValueError("no_gpu_worker_meets_floor")
    automation_rank = {
        AutomationClass.PERSISTENT: 3,
        AutomationClass.SHARED_API: 2,
        AutomationClass.SESSION_ONLY: 1,
    }
    return max(
        candidates,
        key=lambda w: (
            automation_rank[w.automation_class],
            not w.ephemeral,
            not w.quota_limited,
            w.max_vram_gb,
        ),
    )
