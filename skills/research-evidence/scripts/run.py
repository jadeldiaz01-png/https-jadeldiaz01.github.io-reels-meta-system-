from __future__ import annotations
import json, sys
from pathlib import Path

def run(payload:dict)->dict:
    sources=payload.get("sources",[]); claims=payload.get("claims",[])
    source_ids={s.get("id") for s in sources if isinstance(s,dict) and s.get("id")}
    unsupported=[]; unknown=[]
    matrix=[]
    for claim in claims:
        refs=claim.get("source_ids",[]) if isinstance(claim,dict) else []
        bad=[r for r in refs if r not in source_ids]
        if bad: unknown.append({"claim":claim.get("text"),"source_ids":bad})
        if claim.get("material",True) and not refs: unsupported.append(claim.get("text"))
        matrix.append({"claim":claim.get("text"),"source_ids":refs,"supported":bool(refs) and not bad})
    status="INVALID_EVIDENCE" if unsupported or unknown else "EVIDENCE_READY"
    return {"status":status,"matrix":matrix,"unsupported_claims":unsupported,"unknown_sources":unknown,"uncertainties":payload.get("uncertainties",[]),"external_write":False}

def main()->int:
    p=json.loads(Path(sys.argv[1]).read_text() if len(sys.argv)>1 else sys.stdin.read()); print(json.dumps(run(p),indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
