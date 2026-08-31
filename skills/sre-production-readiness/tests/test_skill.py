import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/"scripts/run.py"; s=importlib.util.spec_from_file_location("sre_run",P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
def test_restore_failure_is_no_go():
    p={k:True for k in m.REQ}; p["restore_test"]=False; assert m.run(p)["status"]=="NO_GO"
def test_complete_is_candidate_not_deploy():
    p={k:True for k in m.REQ}; out=m.run(p); assert out["status"]=="GO_CANDIDATE" and out["external_write"] is False
