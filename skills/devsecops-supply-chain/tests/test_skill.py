import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/"scripts/run.py"; s=importlib.util.spec_from_file_location("devsecops_run",P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
def test_fail_closed():
    assert m.run({})["status"]=="NO_GO"
def test_ready_requires_all_evidence():
    p={k:True for k in m.REQ}; out=m.run(p); assert out["status"]=="READY_FOR_RELEASE_APPROVAL" and out["approval_required"]
