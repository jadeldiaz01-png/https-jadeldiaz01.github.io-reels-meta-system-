import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/"scripts/run.py"; s=importlib.util.spec_from_file_location("research_run",P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
def test_material_claim_needs_source():
    out=m.run({"sources":[],"claims":[{"text":"x","source_ids":[],"material":True}]}); assert out["status"]=="INVALID_EVIDENCE"
def test_known_source_supports_claim():
    out=m.run({"sources":[{"id":"s1","url":"u","title":"t"}],"claims":[{"text":"x","source_ids":["s1"],"material":True}]}); assert out["status"]=="EVIDENCE_READY"
