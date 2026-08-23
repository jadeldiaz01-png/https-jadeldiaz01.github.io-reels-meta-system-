import pytest

from cineforge.worker_discovery import (
    AutomationClass,
    GPUDevice,
    WorkerClass,
    WorkerProbe,
    choose_worker,
    recommend_model_for_worker,
)


def worker(vram: float, automation: AutomationClass = AutomationClass.PERSISTENT, *, quota=False, ephemeral=False):
    return WorkerProbe(
        worker_class=WorkerClass.LOCAL,
        automation_class=automation,
        cuda_available=True,
        devices=(GPUDevice(0, "test-gpu", vram, "8.9"),),
        source="test",
        quota_limited=quota,
        ephemeral=ephemeral,
    )


def test_6gb_worker_routes_to_framepack():
    assert recommend_model_for_worker(worker(8)).recommended_model == "framepack"


def test_12gb_worker_routes_to_cogvideox():
    assert recommend_model_for_worker(worker(16)).recommended_model == "cogvideox-2b"


def test_24gb_worker_routes_to_wan22():
    assert recommend_model_for_worker(worker(24)).recommended_model == "wan2.2-ti2v-5b"


def test_cpu_worker_fails_closed():
    cpu = WorkerProbe(WorkerClass.LOCAL, AutomationClass.PERSISTENT, False, (), "test")
    with pytest.raises(ValueError, match="gpu_worker_unavailable"):
        recommend_model_for_worker(cpu)


def test_persistent_worker_beats_shared_gpu_even_if_shared_has_more_vram():
    persistent = worker(24, AutomationClass.PERSISTENT)
    shared = WorkerProbe(
        worker_class=WorkerClass.HF_ZEROGPU,
        automation_class=AutomationClass.SHARED_API,
        cuda_available=True,
        devices=(GPUDevice(0, "shared", 48, None),),
        source="test",
        quota_limited=True,
        ephemeral=True,
    )
    assert choose_worker([shared, persistent]) is persistent


def test_no_worker_meets_floor_fails_closed():
    tiny = worker(4)
    with pytest.raises(ValueError, match="no_gpu_worker_meets_floor"):
        choose_worker([tiny])
