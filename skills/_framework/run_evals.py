from __future__ import annotations
import importlib.util, json, sys
from pathlib import Path

def load_runner(path: Path):
    spec=importlib.util.spec_from_file_location(f"skill_{path.parent.parent.name.replace('-','_')}",path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def subset(actual, expected):
    if isinstance(expected,dict): return isinstance(actual,dict) and all(k in actual and subset(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list): return actual==expected
    return actual==expected

def run_skill(skill_dir: Path) -> list[dict]:
    cases=json.loads((skill_dir/"evals/cases.json").read_text())
    mod=load_runner(skill_dir/"scripts/run.py"); results=[]
    for case in cases:
        ok=False; detail=""
        try:
            if skill_dir.name=="verified-skill-generator":
                files=mod.build(case["input"]); manifest=json.loads(files["manifest.json"]); ok=subset(manifest,case.get("expect_manifest",{})) and not case.get("expect_error",False)
            else:
                out=mod.run(case["input"]); ok=subset(out,case.get("expect",{})) and not case.get("expect_error",False)
        except Exception as exc:
            ok=bool(case.get("expect_error")); detail=type(exc).__name__+":"+str(exc)
        results.append({"id":case["id"],"ok":ok,"detail":detail})
    return results

def main()->int:
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path("skills"); report={}; failed=False
    for manifest in sorted(root.glob("*/manifest.json")):
        d=manifest.parent
        if (d/"evals/cases.json").exists():
            report[d.name]=run_skill(d); failed |= any(not r["ok"] for r in report[d.name])
    print(json.dumps({"ok":not failed,"skills":report},indent=2)); return 1 if failed else 0
if __name__=="__main__": raise SystemExit(main())
