import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/"scripts/run.py"; s=importlib.util.spec_from_file_location("skillgen_run",P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
def test_generated_skill_is_draft_and_cannot_self_promote():
    files=m.build({"name":"example-skill","domain":"research","purpose":"Example"}); import json; manifest=json.loads(files["manifest.json"]); assert manifest["lifecycle"]=="DRAFT" and manifest["self_promotion"] is False and manifest["external_writes"] is False
def test_rejects_pathlike_name():
    try: m.build({"name":"../escape","domain":"research","purpose":"x"})
    except ValueError: pass
    else: raise AssertionError("expected invalid name rejection")
