from __future__ import annotations
import argparse, json, re
from pathlib import Path
DOMAINS={"video","agentic","devsecops","sre","research","skill-generation"}

def build(spec:dict)->dict[str,str]:
    name=str(spec.get("name","")).strip(); domain=spec.get("domain"); purpose=str(spec.get("purpose","")).strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]+",name): raise ValueError("invalid skill name")
    if domain not in DOMAINS: raise ValueError("invalid domain")
    if not purpose: raise ValueError("purpose required")
    manifest={"name":name,"version":"0.1.0","domain":domain,"risk":spec.get("risk","medium"),"entrypoint":"scripts/run.py","inputs":{"schema":"schemas/input.schema.json"},"outputs":{"type":"skill_result"},"approvals":spec.get("approvals",[]),"evidence":["input","result","validation"],"lifecycle":"DRAFT","external_writes":False,"self_promotion":False}
    files={
      "SKILL.md":f"---\nname: {name}\nversion: 0.1.0\ndomain: {domain}\n---\n# {name}\n\n{purpose}\n\nGenerated as DRAFT. Validate, test and review before promotion.\n",
      "manifest.json":json.dumps(manifest,indent=2),
      "scripts/run.py":"from __future__ import annotations\n\ndef run(payload: dict) -> dict:\n    return {'status':'DRAFT_RESULT','input':payload,'external_write':False}\n",
      "schemas/input.schema.json":json.dumps({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object"},indent=2),
      "tests/test_skill.py":"def test_generated_contract():\n    assert True\n",
      "evals/cases.json":json.dumps([{"id":"smoke","input":{},"expect":{"status":"DRAFT_RESULT"}}],indent=2),
    }
    return files

def apply(files:dict[str,str],root:Path,name:str)->Path:
    root=root.resolve(); target=(root/name).resolve()
    if root != target.parent: raise ValueError("path traversal rejected")
    if target.exists(): raise FileExistsError(target)
    for rel,content in files.items():
        p=target/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8")
    return target

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--apply",action="store_true"); ap.add_argument("--root",default="skills/generated"); a=ap.parse_args()
    spec=json.loads(Path(a.spec).read_text()); files=build(spec); out={"status":"DRAFT_GENERATED","name":spec["name"],"files":files,"applied":False}
    if a.apply: out["path"]=str(apply(files,Path(a.root),spec["name"])); out["applied"]=True
    print(json.dumps(out,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
