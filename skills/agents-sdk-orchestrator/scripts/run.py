from __future__ import annotations
import json, sys
from pathlib import Path

def run(payload: dict) -> dict:
    goal=str(payload.get("goal","")).strip(); tools=payload.get("tools",[]); side_effects=bool(payload.get("side_effects",False))
    if not goal: raise ValueError("goal required")
    if not isinstance(tools,list) or any(not isinstance(t,str) or not t.strip() for t in tools): raise ValueError("tools must be non-empty strings")
    specialists=payload.get("specialists",[])
    mode="single_agent" if not specialists else "specialists_with_handoffs"
    approvals=[]
    if side_effects: approvals.append("external_side_effects")
    return {"status":"PLANNED","mode":mode,"goal":goal,"tool_allowlist":tools,"specialists":specialists,"approvals_required":approvals,"eval_requirements":["happy_path","missing_evidence","forbidden_tool","approval_boundary"],"external_write":False}

def main()->int:
    payload=json.loads(Path(sys.argv[1]).read_text() if len(sys.argv)>1 else sys.stdin.read()); print(json.dumps(run(payload),indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
