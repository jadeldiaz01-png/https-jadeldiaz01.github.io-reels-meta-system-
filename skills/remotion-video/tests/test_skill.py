import importlib.util
from pathlib import Path

P=Path(__file__).parents[1]/"scripts/run.py"
spec=importlib.util.spec_from_file_location("remotion_video_run",P); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_valid_plan():
    out=m.run({"composition_id":"reel","width":1080,"height":1920,"fps":30,"duration_frames":900,"assets":[{"source":"owned.mp4","rights_status":"owned"}]})
    assert out["status"]=="READY_FOR_RENDER_QA" and out["external_write"] is False

def test_rejects_missing_rights():
    try: m.run({"composition_id":"x","width":1,"height":1,"fps":1,"duration_frames":1,"assets":[{"source":"x"}]})
    except ValueError as e: assert "rights" in str(e)
    else: raise AssertionError("expected rejection")
