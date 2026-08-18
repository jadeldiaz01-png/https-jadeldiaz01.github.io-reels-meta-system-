import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/"scripts/run.py"; s=importlib.util.spec_from_file_location("agent_run",P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)

def test_single_agent_default():
    out=m.run({"goal":"draft content","tools":["research"]}); assert out["mode"]=="single_agent" and out["external_write"] is False

def test_side_effect_requires_approval():
    out=m.run({"goal":"publish","tools":["publisher"],"side_effects":True}); assert "external_side_effects" in out["approvals_required"]
